"""Choice routing parity test: config-driven format routing (CSV vs JSON).

Runs twice — once with CSV config, once with JSON config. For each format,
seeds S3, runs SF, resets, runs RSF, and compares outputs and traces.

Also verifies the Fail path for unknown formats.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import pytest

from tests.parity.conftest import (
    PARITY_ROOT,
    compare_s3_outputs,
    compare_state_sequences,
    get_rsf_trace,
    get_sf_trace,
    poll_sf_execution,
    start_sf_execution,
    upload_test_file,
)
from tests.test_examples.conftest import (
    iam_propagation_wait,
    make_execution_id,
    poll_execution,
    terraform_deploy,
    terraform_teardown,
)

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.parity

TEST_DIR = PARITY_ROOT / "test-03-choice-routing"
TEST_DATA_DIR = TEST_DIR / "test_data"

# SF has extra states for S3 reads that RSF does internally
SF_EXTRA_STATES = {"ExtractConfig", "ReadSourceCSV", "ReadSourceJSON"}


@pytest.mark.parity
class TestChoiceRoutingParity:
    """Deploy, run SF and RSF choice routing workflows, and compare results."""

    @pytest.fixture(scope="class")
    def deployment(self, shared_infra, sfn_client, lambda_client, logs_client, s3_client):
        """Deploy choice routing infrastructure, run all workflows, yield context."""
        outputs = terraform_deploy(
            TEST_DIR,
            tf_vars={
                "s3_bucket_name": shared_infra["s3_bucket_name"],
                "lambda_role_arn": shared_infra["lambda_role_arn"],
                "sfn_role_arn": shared_infra["sfn_role_arn"],
            },
        )
        iam_propagation_wait()

        bucket = shared_infra["s3_bucket_name"]
        sfn_arn = outputs["sfn_arn"]
        rsf_fn = outputs["rsf_function_name"]
        rsf_alias = outputs["rsf_alias_arn"]
        rsf_log_group = outputs["rsf_log_group_name"]

        # --- Seed all test data to S3 ---
        upload_test_file(s3_client, bucket, "input/choice-routing/config_csv.json", TEST_DATA_DIR / "config_csv.json")
        upload_test_file(s3_client, bucket, "input/choice-routing/config_json.json", TEST_DATA_DIR / "config_json.json")
        upload_test_file(s3_client, bucket, "input/choice-routing/sample.csv", TEST_DATA_DIR / "sample.csv")
        upload_test_file(s3_client, bucket, "input/choice-routing/sample.json", TEST_DATA_DIR / "sample.json")

        results = {
            "bucket": bucket,
            "sfn_arn": sfn_arn,
            "rsf_fn": rsf_fn,
            "rsf_alias": rsf_alias,
            "rsf_log_group": rsf_log_group,
            "outputs": outputs,
        }

        # --- CSV format ---
        csv_sf = _run_sf_workflow(
            sfn_client,
            sfn_arn,
            bucket,
            config_key="input/choice-routing/config_csv.json",
            output_prefix="sf/choice-routing",
            exec_name="choice-csv-sf",
        )
        results["csv_sf"] = csv_sf

        csv_rsf = _run_rsf_workflow(
            lambda_client,
            logs_client,
            rsf_alias,
            rsf_fn,
            rsf_log_group,
            bucket,
            config_key="input/choice-routing/config_csv.json",
            output_prefix="rsf/choice-routing",
            exec_name="choice-csv-rsf",
        )
        results["csv_rsf"] = csv_rsf

        # --- JSON format ---
        json_sf = _run_sf_workflow(
            sfn_client,
            sfn_arn,
            bucket,
            config_key="input/choice-routing/config_json.json",
            output_prefix="sf/choice-routing",
            exec_name="choice-json-sf",
        )
        results["json_sf"] = json_sf

        json_rsf = _run_rsf_workflow(
            lambda_client,
            logs_client,
            rsf_alias,
            rsf_fn,
            rsf_log_group,
            bucket,
            config_key="input/choice-routing/config_json.json",
            output_prefix="rsf/choice-routing",
            exec_name="choice-json-rsf",
        )
        results["json_rsf"] = json_rsf

        # --- Unknown format (Fail path) ---
        # Upload a config with unsupported format
        unknown_config = json.dumps({"format": "xml", "source_key": "input/choice-routing/sample.csv"}).encode()
        s3_client.put_object(
            Bucket=bucket,
            Key="input/choice-routing/config_xml.json",
            Body=unknown_config,
            ContentType="application/json",
        )

        # SF unknown format
        sf_fail_id = make_execution_id("choice-xml-sf")
        sf_fail_arn = start_sf_execution(
            sfn_client,
            sfn_arn,
            {
                "config_key": "input/choice-routing/config_xml.json",
                "output_prefix": "sf/choice-routing",
                "s3_bucket": bucket,
            },
            name=sf_fail_id,
        )
        sf_fail_result = poll_sf_execution(sfn_client, sf_fail_arn, timeout=120)
        results["sf_fail_result"] = sf_fail_result

        # RSF unknown format
        rsf_fail_id = make_execution_id("choice-xml-rsf")
        _ = datetime.now(timezone.utc)  # timestamp for potential log query
        lambda_client.invoke(
            FunctionName=rsf_alias,
            InvocationType="Event",
            Payload=json.dumps(
                {
                    "config_key": "input/choice-routing/config_xml.json",
                    "output_prefix": "rsf/choice-routing",
                    "s3_bucket": bucket,
                }
            ),
            DurableExecutionName=rsf_fail_id,
        )
        rsf_fail_result = poll_execution(lambda_client, rsf_fn, rsf_fail_id, timeout=120)
        results["rsf_fail_result"] = rsf_fail_result

        yield results

        terraform_teardown(
            TEST_DIR,
            logs_client,
            rsf_log_group,
            tf_vars={
                "s3_bucket_name": shared_infra["s3_bucket_name"],
                "lambda_role_arn": shared_infra["lambda_role_arn"],
                "sfn_role_arn": shared_infra["sfn_role_arn"],
            },
        )

    # --- CSV tests ---

    def test_csv_sf_succeeds(self, deployment):
        """SF CSV workflow reaches SUCCEEDED."""
        assert deployment["csv_sf"]["result"]["status"] == "SUCCEEDED"

    def test_csv_rsf_succeeds(self, deployment):
        """RSF CSV workflow reaches SUCCEEDED."""
        assert deployment["csv_rsf"]["result"]["Status"] == "SUCCEEDED"

    def test_csv_output_parity(self, deployment, s3_client):
        """CSV outputs match between SF and RSF."""
        assert compare_s3_outputs(
            s3_client,
            deployment["bucket"],
            sf_key="sf/choice-routing/csv/result.json",
            rsf_key="rsf/choice-routing/csv/result.json",
        )

    def test_trace_parity_csv(self, deployment):
        """CSV state visit sequences match (excluding SF-only states)."""
        if not deployment["csv_rsf"]["trace"]:
            pytest.skip("RSF trace empty — durable execution SDK does not emit step_name logs")
        assert compare_state_sequences(
            deployment["csv_sf"]["trace"],
            deployment["csv_rsf"]["trace"],
            sf_extra_states=SF_EXTRA_STATES,
        )

    # --- JSON tests ---

    def test_json_sf_succeeds(self, deployment):
        """SF JSON workflow reaches SUCCEEDED."""
        assert deployment["json_sf"]["result"]["status"] == "SUCCEEDED"

    def test_json_rsf_succeeds(self, deployment):
        """RSF JSON workflow reaches SUCCEEDED."""
        assert deployment["json_rsf"]["result"]["Status"] == "SUCCEEDED"

    def test_json_output_parity(self, deployment, s3_client):
        """JSON outputs match between SF and RSF."""
        assert compare_s3_outputs(
            s3_client,
            deployment["bucket"],
            sf_key="sf/choice-routing/json/result.json",
            rsf_key="rsf/choice-routing/json/result.json",
        )

    def test_trace_parity_json(self, deployment):
        """JSON state visit sequences match (excluding SF-only states)."""
        if not deployment["json_rsf"]["trace"]:
            pytest.skip("RSF trace empty — durable execution SDK does not emit step_name logs")
        assert compare_state_sequences(
            deployment["json_sf"]["trace"],
            deployment["json_rsf"]["trace"],
            sf_extra_states=SF_EXTRA_STATES,
        )

    # --- Fail path ---

    def test_unknown_format_fails(self, deployment):
        """Both SF and RSF fail on unknown format."""
        assert deployment["sf_fail_result"]["status"] == "FAILED"
        assert deployment["rsf_fail_result"]["Status"] == "FAILED"


def _run_sf_workflow(
    sfn_client,
    sfn_arn: str,
    bucket: str,
    *,
    config_key: str,
    output_prefix: str,
    exec_name: str,
) -> dict:
    """Run a Step Functions workflow and return result + trace."""
    exec_id = make_execution_id(exec_name)
    sf_input = {
        "config_key": config_key,
        "output_prefix": output_prefix,
        "s3_bucket": bucket,
    }
    execution_arn = start_sf_execution(sfn_client, sfn_arn, sf_input, name=exec_id)
    result = poll_sf_execution(sfn_client, execution_arn, timeout=120)
    trace = get_sf_trace(sfn_client, execution_arn)
    return {"result": result, "trace": trace}


def _run_rsf_workflow(
    lambda_client,
    logs_client,
    rsf_alias: str,
    rsf_fn: str,
    rsf_log_group: str,
    bucket: str,
    *,
    config_key: str,
    output_prefix: str,
    exec_name: str,
) -> dict:
    """Run an RSF workflow and return result + trace."""
    exec_id = make_execution_id(exec_name)
    start_time = datetime.now(timezone.utc)
    rsf_input = {
        "config_key": config_key,
        "output_prefix": output_prefix,
        "s3_bucket": bucket,
    }
    lambda_client.invoke(
        FunctionName=rsf_alias,
        InvocationType="Event",
        Payload=json.dumps(rsf_input),
        DurableExecutionName=exec_id,
    )
    result = poll_execution(lambda_client, rsf_fn, exec_id, timeout=120)
    trace = get_rsf_trace(logs_client, rsf_log_group, start_time)
    return {"result": result, "trace": trace}
