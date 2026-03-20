"""SQS collector parity test: poll SQS -> accumulate -> write S3 -> delete.

Long-running test (~3 min). Sends 10 staggered messages, runs SF then RSF,
and compares collected outputs (order-independent) and execution traces.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tests.parity.conftest import (
    PARITY_ROOT,
    compare_state_sequences,
    get_rsf_trace,
    get_sf_trace,
    poll_sf_execution,
    purge_sqs_queue,
    send_sqs_messages,
    start_sf_execution,
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

TEST_DIR = PARITY_ROOT / "test-02-sqs-collector"
TEST_DATA_DIR = TEST_DIR / "test_data"


@pytest.mark.parity
class TestSQSCollectorParity:
    """Deploy, run SF and RSF SQS collector workflows, and compare results."""

    @pytest.fixture(scope="class")
    def deployment(self, shared_infra, sfn_client, lambda_client, logs_client, sqs_client, s3_client):
        """Deploy SQS collector infrastructure, run both workflows, yield context."""
        outputs = terraform_deploy(TEST_DIR)
        iam_propagation_wait()

        bucket = shared_infra["s3_bucket_name"]
        queue_url = shared_infra["sqs_queue_url"]
        sfn_arn = outputs["sfn_arn"]
        rsf_fn = outputs["rsf_function_name"]
        rsf_alias = outputs["rsf_alias_arn"]
        rsf_log_group = outputs["rsf_log_group_name"]

        # Load test messages
        messages = json.loads((TEST_DATA_DIR / "messages.json").read_text())

        # --- Purge queue before starting ---
        purge_sqs_queue(sqs_client, queue_url)

        # --- Run Step Functions ---
        sf_exec_id = make_execution_id("sqs-sf")
        sf_input = {
            "output_key": "sf/sqs-collector/result.json",
            "s3_bucket": bucket,
            "queue_url": queue_url,
        }

        # Start sending messages in background (staggered)
        sf_send_thread = send_sqs_messages(sqs_client, queue_url, messages, stagger_seconds=9.0)

        # Start SF immediately (it will poll for messages)
        sf_execution_arn = start_sf_execution(sfn_client, sfn_arn, sf_input, name=sf_exec_id)
        sf_result = poll_sf_execution(sfn_client, sf_execution_arn, timeout=300)
        sf_trace = get_sf_trace(sfn_client, sf_execution_arn)

        # Wait for send thread to finish
        sf_send_thread.join(timeout=120)

        # Verify queue is drained after SF run
        sf_queue_empty = _check_queue_empty(sqs_client, queue_url)

        # --- Reset: purge queue and re-send messages ---
        purge_sqs_queue(sqs_client, queue_url)

        # --- Run RSF ---
        rsf_exec_id = make_execution_id("sqs-rsf")
        rsf_start_time = datetime.now(timezone.utc)
        rsf_input = {
            "output_key": "rsf/sqs-collector/result.json",
            "s3_bucket": bucket,
            "queue_url": queue_url,
        }

        # Start sending messages in background (staggered)
        rsf_send_thread = send_sqs_messages(sqs_client, queue_url, messages, stagger_seconds=9.0)

        # Start RSF immediately
        lambda_client.invoke(
            FunctionName=rsf_alias,
            InvocationType="Event",
            Payload=json.dumps(rsf_input),
            DurableExecutionName=rsf_exec_id,
        )
        rsf_result = poll_execution(lambda_client, rsf_fn, rsf_exec_id, timeout=300)
        rsf_trace = get_rsf_trace(logs_client, rsf_log_group, rsf_start_time)

        # Wait for send thread to finish
        rsf_send_thread.join(timeout=120)

        # Verify queue is drained after RSF run
        rsf_queue_empty = _check_queue_empty(sqs_client, queue_url)

        # Read S3 outputs for comparison
        sf_output = _read_s3_json(s3_client, bucket, "sf/sqs-collector/result.json")
        rsf_output = _read_s3_json(s3_client, bucket, "rsf/sqs-collector/result.json")

        yield {
            "sf_result": sf_result,
            "rsf_result": rsf_result,
            "sf_trace": sf_trace,
            "rsf_trace": rsf_trace,
            "sf_output": sf_output,
            "rsf_output": rsf_output,
            "sf_queue_empty": sf_queue_empty,
            "rsf_queue_empty": rsf_queue_empty,
            "bucket": bucket,
            "outputs": outputs,
        }

        terraform_teardown(TEST_DIR, logs_client, rsf_log_group)

    def test_sf_succeeds(self, deployment):
        """Step Functions execution reaches SUCCEEDED."""
        assert deployment["sf_result"]["status"] == "SUCCEEDED"

    def test_rsf_succeeds(self, deployment):
        """RSF durable execution reaches SUCCEEDED."""
        assert deployment["rsf_result"]["Status"] == "SUCCEEDED"

    def test_sf_queue_drained(self, deployment):
        """SF run drains the SQS queue."""
        assert deployment["sf_queue_empty"], "Queue not empty after SF run"

    def test_rsf_queue_drained(self, deployment):
        """RSF run drains the SQS queue."""
        assert deployment["rsf_queue_empty"], "Queue not empty after RSF run"

    def test_output_parity(self, deployment):
        """Both collected the same 10 messages (order-independent)."""
        sf_messages = deployment["sf_output"]
        rsf_messages = deployment["rsf_output"]

        # Sort by a stable key for comparison (since poll order may differ)
        sf_sorted = sorted(sf_messages, key=lambda m: json.dumps(m, sort_keys=True))
        rsf_sorted = sorted(rsf_messages, key=lambda m: json.dumps(m, sort_keys=True))

        assert len(sf_sorted) == 10, f"SF collected {len(sf_sorted)} messages, expected 10"
        assert len(rsf_sorted) == 10, f"RSF collected {len(rsf_sorted)} messages, expected 10"
        assert sf_sorted == rsf_sorted

    def test_trace_parity(self, deployment):
        """Both reach WriteCollected and DeleteMessages states."""
        sf_entered = {t.state_name for t in deployment["sf_trace"] if t.status == "entered"}
        rsf_entered = {t.state_name for t in deployment["rsf_trace"] if t.status == "entered"}

        # Both must reach the terminal processing states
        for state in ("WriteCollected", "DeleteMessages", "Done"):
            assert state in sf_entered, f"SF did not reach {state}"
            assert state in rsf_entered, f"RSF did not reach {state}"


def _check_queue_empty(sqs_client, queue_url: str) -> bool:
    """Check if SQS queue has no messages available."""
    resp = sqs_client.receive_message(
        QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=2
    )
    return len(resp.get("Messages", [])) == 0


def _read_s3_json(s3_client, bucket: str, key: str):
    """Read and parse a JSON file from S3."""
    return json.loads(s3_client.get_object(Bucket=bucket, Key=key)["Body"].read())
