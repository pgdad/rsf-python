"""ETL parity test: S3 read -> Map transform -> S3 write.

Deploys both SF and RSF versions, runs each with the same input,
and compares S3 outputs and execution traces.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

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

TEST_DIR = PARITY_ROOT / "test-01-etl"
TEST_DATA_DIR = TEST_DIR / "test_data"


@pytest.mark.parity
class TestETLParity:
    """Deploy, run SF and RSF ETL workflows, and compare results."""

    @pytest.fixture(scope="class")
    def deployment(self, shared_infra, sfn_client, lambda_client, logs_client, s3_client):
        """Deploy ETL infrastructure, run both workflows, yield context."""
        outputs = terraform_deploy(TEST_DIR, tf_vars={
            "s3_bucket_name": shared_infra["s3_bucket_name"],
            "lambda_role_arn": shared_infra["lambda_role_arn"],
            "sfn_role_arn": shared_infra["sfn_role_arn"],
        })
        iam_propagation_wait()

        bucket = shared_infra["s3_bucket_name"]
        sfn_arn = outputs["sfn_arn"]
        rsf_fn = outputs["rsf_function_name"]
        rsf_alias = outputs["rsf_alias_arn"]
        rsf_log_group = outputs["rsf_log_group_name"]

        # --- Seed input data ---
        upload_test_file(s3_client, bucket, "input/etl/data.json", TEST_DATA_DIR / "input.json")

        # --- Run Step Functions ---
        sf_exec_id = make_execution_id("etl-sf")
        sf_input = {
            "source_key": "input/etl/data.json",
            "output_key": "sf/etl/result.json",
        }
        sf_execution_arn = start_sf_execution(sfn_client, sfn_arn, sf_input, name=sf_exec_id)
        sf_result = poll_sf_execution(sfn_client, sf_execution_arn, timeout=120)
        logger.info("SF result status=%s error=%s cause=%s", sf_result.get("status"), sf_result.get("error"), sf_result.get("cause"))
        sf_trace = get_sf_trace(sfn_client, sf_execution_arn)

        # --- Reset: re-upload input (S3 is idempotent, but good practice) ---
        upload_test_file(s3_client, bucket, "input/etl/data.json", TEST_DATA_DIR / "input.json")

        # --- Run RSF ---
        rsf_exec_id = make_execution_id("etl-rsf")
        rsf_start_time = datetime.now(timezone.utc)
        rsf_input = {
            "source_key": "input/etl/data.json",
            "output_key": "rsf/etl/result.json",
        }
        lambda_client.invoke(
            FunctionName=rsf_alias,
            InvocationType="Event",
            Payload=json.dumps(rsf_input),
            DurableExecutionName=rsf_exec_id,
        )
        rsf_result = poll_execution(lambda_client, rsf_fn, rsf_exec_id, timeout=120)
        logger.info("RSF result: %s", json.dumps({k: str(v) for k, v in rsf_result.items()}, indent=2))
        rsf_trace = get_rsf_trace(logs_client, rsf_log_group, rsf_start_time)

        yield {
            "sf_result": sf_result,
            "rsf_result": rsf_result,
            "sf_trace": sf_trace,
            "rsf_trace": rsf_trace,
            "bucket": bucket,
            "outputs": outputs,
        }

        terraform_teardown(TEST_DIR, logs_client, rsf_log_group, tf_vars={
            "s3_bucket_name": shared_infra["s3_bucket_name"],
            "lambda_role_arn": shared_infra["lambda_role_arn"],
            "sfn_role_arn": shared_infra["sfn_role_arn"],
        })

    def test_sf_succeeds(self, deployment):
        """Step Functions execution reaches SUCCEEDED."""
        sf = deployment["sf_result"]
        assert sf["status"] == "SUCCEEDED", f"SF failed: error={sf.get('error')} cause={sf.get('cause')}"

    def test_rsf_succeeds(self, deployment):
        """RSF durable execution reaches SUCCEEDED."""
        rsf = deployment["rsf_result"]
        assert rsf["Status"] == "SUCCEEDED", f"RSF failed: {rsf.get('FailureReason', rsf.get('Output', ''))}"

    def test_output_parity(self, deployment, s3_client):
        """S3 outputs match (ignoring processed_at timestamps)."""
        result = compare_s3_outputs(
            s3_client,
            deployment["bucket"],
            sf_key="sf/etl/result.json",
            rsf_key="rsf/etl/result.json",
            ignore_fields=["processed_at"],
        )
        if not result:
            sf_data = json.loads(s3_client.get_object(Bucket=deployment["bucket"], Key="sf/etl/result.json")["Body"].read())
            rsf_data = json.loads(s3_client.get_object(Bucket=deployment["bucket"], Key="rsf/etl/result.json")["Body"].read())
            logger.error("SF output: %s", json.dumps(sf_data, indent=2, default=str))
            logger.error("RSF output: %s", json.dumps(rsf_data, indent=2, default=str))
        assert result, "S3 outputs differ between SF and RSF"

    def test_trace_parity(self, deployment):
        """State visit sequences match between SF and RSF."""
        if not deployment["rsf_trace"]:
            pytest.skip("RSF trace empty — durable execution SDK does not emit step_name logs")
        # SF has extra PrepareRecords Pass state not in RSF
        assert compare_state_sequences(
            deployment["sf_trace"],
            deployment["rsf_trace"],
            sf_extra_states={"PrepareRecords"},
        )
