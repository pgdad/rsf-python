"""Integration tests for the registry-modules-demo example (TEST-02, TEST-03).

Deploys via rsf deploy (custom provider pipeline), invokes a durable execution,
polls to SUCCEEDED, verifies CloudWatch logs, and tears down via rsf deploy --teardown.
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
import pytest
from botocore.exceptions import ClientError

from tests.test_examples.conftest import (
    EXAMPLES_ROOT,
    iam_propagation_wait,
    make_execution_id,
    poll_execution,
    query_logs,
)

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.integration

EXAMPLE_DIR = EXAMPLES_ROOT / "registry-modules-demo"
TF_DIR = EXAMPLE_DIR / "terraform"

HAPPY_EVENT = {
    "image_id": "test-001",
    "format": "jpeg",
    "size_bytes": 1048576,
    "width": 1920,
    "height": 1080,
    "target_width": 960,
}

RSF_TOML_PLACEHOLDER = "/REPLACE/WITH/YOUR/ABSOLUTE/PATH/TO/examples/registry-modules-demo/deploy.sh"


class TestRegistryModulesDemoIntegration:
    """Deploy via rsf deploy (custom provider pipeline), invoke, verify, and teardown."""

    @pytest.fixture(scope="class")
    def deployment(self, lambda_client, logs_client):
        """Deploy infrastructure via rsf deploy, invoke durable execution, yield context.

        Patches rsf.toml placeholder with the real deploy.sh path for the duration
        of the test class (deploy + teardown test). Restores the placeholder in the
        finally block regardless of test outcome.

        Safety net: if the teardown test fails to destroy resources, the fixture
        cleanup falls back to direct terraform destroy and explicit log group deletion.
        """
        rsf_toml = EXAMPLE_DIR / "rsf.toml"
        original_toml = rsf_toml.read_text()
        patched = original_toml.replace(RSF_TOML_PLACEHOLDER, str(EXAMPLE_DIR / "deploy.sh"))
        rsf_toml.write_text(patched)

        alias_arn: str | None = None
        function_name: str | None = None
        log_group: str | None = None

        try:
            # Step 1: Generate workflow source code (creates src/generated/)
            logger.info("deployment: rsf generate %s", EXAMPLE_DIR)
            subprocess.run(
                ["rsf", "generate", "workflow.yaml"],
                cwd=EXAMPLE_DIR,
                check=True,
                capture_output=True,
                text=True,
            )

            # Step 2: Full custom provider pipeline deploy
            # rsf.toml -> CustomProvider -> FileTransport -> deploy.sh -> terraform apply
            logger.info("deployment: rsf deploy %s", EXAMPLE_DIR)
            subprocess.run(
                ["rsf", "deploy", "workflow.yaml", "--auto-approve"],
                cwd=EXAMPLE_DIR,
                check=True,
                capture_output=True,
                text=True,
            )

            # Step 3: Read terraform outputs to get alias_arn and function_name
            logger.info("deployment: reading terraform outputs from %s", TF_DIR)
            result = subprocess.run(
                ["terraform", "output", "-json"],
                cwd=TF_DIR,
                check=True,
                capture_output=True,
                text=True,
            )
            raw_outputs = json.loads(result.stdout)
            # terraform output -json wraps each in {"value": ..., "type": ...}
            outputs = {k: v["value"] for k, v in raw_outputs.items()}
            alias_arn = outputs["alias_arn"]
            function_name = outputs["function_name"]

            # Step 4: Derive log group (no log_group_name terraform output exists)
            log_group = f"/aws/lambda/{function_name}"

            # Step 5: Wait for IAM propagation after terraform apply
            iam_propagation_wait()

            # Step 6: Create unique execution ID and record start time
            exec_id = make_execution_id("registry-modules-demo")
            start_time = datetime.now(timezone.utc)

            # Step 7: Invoke Lambda via alias ARN (MUST use alias_arn, not function_name)
            # Using function_name directly fails due to issue #45800 (AllowInvokeLatest unresolved)
            logger.info("deployment: invoking %s exec_id=%s", alias_arn, exec_id)
            lambda_client.invoke(
                FunctionName=alias_arn,
                InvocationType="Event",
                Payload=json.dumps(HAPPY_EVENT),
                DurableExecutionName=exec_id,
            )

            # Step 8: Poll until terminal state
            # Use function_name (not alias_arn) for polling — the ListDurableExecutionsByFunction
            # API rejects DurableExecutionName filter when both FunctionName and Qualifier are provided.
            execution = poll_execution(lambda_client, function_name, exec_id)

            yield {
                "execution": execution,
                "alias_arn": alias_arn,
                "function_name": function_name,
                "log_group": log_group,
                "start_time": start_time,
                "exec_id": exec_id,
            }

        finally:
            # Safety net: restore rsf.toml placeholder first
            rsf_toml.write_text(original_toml)
            logger.info("deployment: restored rsf.toml placeholder")

            # Safety net: if terraform state is non-empty, run direct destroy
            if TF_DIR.exists():
                state_check = subprocess.run(
                    ["terraform", "state", "list"],
                    cwd=TF_DIR,
                    capture_output=True,
                    text=True,
                )
                if state_check.stdout.strip():
                    logger.warning("deployment: safety net — terraform state not empty, running direct destroy")
                    subprocess.run(
                        [
                            "terraform",
                            "destroy",
                            "-auto-approve",
                            "-input=false",
                            "-var-file=terraform.tfvars.json",
                        ],
                        cwd=TF_DIR,
                        capture_output=True,
                        text=True,
                    )

            # Safety net: delete orphaned log group if it still exists
            if log_group is not None:
                try:
                    logs_client.delete_log_group(logGroupName=log_group)
                    logger.info("deployment: safety net — deleted log group %s", log_group)
                except ClientError as e:
                    if e.response["Error"]["Code"] == "ResourceNotFoundException":
                        logger.info("deployment: log group already deleted: %s", log_group)
                    else:
                        raise

    def test_a_execution_succeeds(self, deployment):
        """Durable execution reaches SUCCEEDED terminal state (TEST-02)."""
        assert deployment["execution"]["Status"] == "SUCCEEDED"

    def test_b_handler_log_entries(self, deployment, logs_client):
        """CloudWatch logs confirm all 4 handler names executed (TEST-02).

        Expected pipeline: ValidateImage -> ResizeImage -> AnalyzeContent -> CatalogueImage
        """
        query = "fields @message | filter @message like /step_name/ | sort @timestamp asc"
        results = query_logs(
            logs_client,
            deployment["log_group"],
            query,
            deployment["start_time"],
        )

        messages = " ".join(next((f["value"] for f in row if f["field"] == "@message"), "") for row in results)

        for handler in ("ValidateImage", "ResizeImage", "AnalyzeContent", "CatalogueImage"):
            assert handler in messages, f"Handler '{handler}' not found in CloudWatch logs"

    def test_z_teardown_leaves_empty_state(self, deployment, logs_client):
        """Teardown via rsf deploy --teardown leaves empty terraform state (TEST-03).

        This test MUST run last (z prefix ensures alphabetical ordering places it last).
        rsf.toml remains patched during this method because the fixture's finally block
        (which restores the placeholder) executes after all test methods complete.

        Verifies:
        - rsf deploy --teardown exits zero
        - terraform state list returns empty output
        - CloudWatch log group is deleted (no orphaned resources)
        """
        teardown_ok = True

        try:
            logger.info("test_z_teardown: rsf deploy --teardown %s", EXAMPLE_DIR)
            subprocess.run(
                ["rsf", "deploy", "workflow.yaml", "--teardown", "--auto-approve"],
                cwd=EXAMPLE_DIR,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            logger.error(
                "test_z_teardown: rsf deploy --teardown failed (exit %d): %s",
                exc.returncode,
                exc.stderr,
            )
            teardown_ok = False
            # Fallback: direct terraform destroy so we do not leave orphaned resources
            logger.warning("test_z_teardown: falling back to direct terraform destroy")
            subprocess.run(
                [
                    "terraform",
                    "destroy",
                    "-auto-approve",
                    "-input=false",
                    "-var-file=terraform.tfvars.json",
                ],
                cwd=TF_DIR,
                capture_output=True,
                text=True,
            )

        # Verify terraform state is empty regardless of which destroy path ran
        state_result = subprocess.run(
            ["terraform", "state", "list"],
            cwd=TF_DIR,
            capture_output=True,
            text=True,
        )
        assert state_result.stdout.strip() == "", (
            f"Terraform state not empty after teardown: {state_result.stdout.strip()}"
        )

        # Delete orphaned log group (CloudWatch log groups survive terraform destroy)
        log_group = deployment["log_group"]
        logger.info("test_z_teardown: deleting log group %s", log_group)
        try:
            logs_client.delete_log_group(logGroupName=log_group)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.info("test_z_teardown: log group already deleted: %s", log_group)
            else:
                raise

        assert teardown_ok, "rsf deploy --teardown exited non-zero (see logs for details)"
