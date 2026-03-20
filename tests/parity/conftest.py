"""Shared parity test harness.

Extends tests/test_examples/conftest.py helpers with Step Functions
execution, trace comparison, and data seeding utilities.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import pytest

# Reuse existing integration test helpers
from tests.test_examples.conftest import (
    iam_propagation_wait,
    make_execution_id,
    poll_execution,
    query_logs,
    terraform_deploy,
    terraform_teardown,
)

logger = logging.getLogger(__name__)

PARITY_ROOT = Path(__file__).parent
PROJECT_ROOT = PARITY_ROOT.parent.parent

# ---------------------------------------------------------------------------
# Pytest markers
# ---------------------------------------------------------------------------


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "parity: Step Functions vs RSF parity tests (require AWS credentials and terraform)",
    )


# ---------------------------------------------------------------------------
# AWS clients (session-scoped)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def aws_region():
    return "us-east-2"


@pytest.fixture(scope="session")
def s3_client(aws_region):
    return boto3.client("s3", region_name=aws_region)


@pytest.fixture(scope="session")
def sqs_client(aws_region):
    return boto3.client("sqs", region_name=aws_region)


@pytest.fixture(scope="session")
def sfn_client(aws_region):
    return boto3.client("stepfunctions", region_name=aws_region)


@pytest.fixture(scope="session")
def lambda_client(aws_region):
    return boto3.client("lambda", region_name=aws_region)


@pytest.fixture(scope="session")
def logs_client(aws_region):
    return boto3.client("logs", region_name=aws_region)


# ---------------------------------------------------------------------------
# Shared infrastructure (session-scoped)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def shared_infra(logs_client):
    """Deploy shared Terraform (S3, SQS, IAM). Teardown at session end."""
    shared_dir = PARITY_ROOT / "shared"
    outputs = terraform_deploy(shared_dir)
    iam_propagation_wait()

    yield outputs

    terraform_teardown(shared_dir)


# ---------------------------------------------------------------------------
# Common types
# ---------------------------------------------------------------------------


@dataclass
class StateTransition:
    state_name: str
    status: str  # entered, succeeded, failed


# ---------------------------------------------------------------------------
# Step Functions execution helpers
# ---------------------------------------------------------------------------


def start_sf_execution(
    sfn_client: Any,
    state_machine_arn: str,
    input_data: dict,
    name: str | None = None,
) -> str:
    """Start a Step Functions execution. Returns execution ARN."""
    name = name or f"parity-{uuid.uuid4().hex[:8]}"
    response = sfn_client.start_execution(
        stateMachineArn=state_machine_arn,
        name=name,
        input=json.dumps(input_data),
    )
    return response["executionArn"]


def poll_sf_execution(
    sfn_client: Any,
    execution_arn: str,
    timeout: float = 300,
    poll_interval: float = 5.0,
) -> dict:
    """Poll Step Functions execution until terminal state."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = sfn_client.describe_execution(executionArn=execution_arn)
        status = response["status"]
        if status in ("SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"):
            return response
        time.sleep(poll_interval)
    raise TimeoutError(f"SF execution {execution_arn} did not complete within {timeout}s")


def get_sf_trace(sfn_client: Any, execution_arn: str) -> list[StateTransition]:
    """Extract state transitions from Step Functions execution history."""
    transitions = []
    paginator = sfn_client.get_paginator("get_execution_history")
    for page in paginator.paginate(executionArn=execution_arn):
        for event in page["events"]:
            event_type = event["type"]
            # Map SF event types to state transitions
            if "StateEntered" in event_type:
                detail = event.get("stateEnteredEventDetails", {})
                transitions.append(StateTransition(
                    state_name=detail.get("name", ""),
                    status="entered",
                ))
            elif "StateExited" in event_type:
                detail = event.get("stateExitedEventDetails", {})
                transitions.append(StateTransition(
                    state_name=detail.get("name", ""),
                    status="succeeded",
                ))
    return transitions


# ---------------------------------------------------------------------------
# RSF trace extraction
# ---------------------------------------------------------------------------


def get_rsf_trace(
    logs_client: Any,
    log_group: str,
    start_time: datetime,
) -> list[StateTransition]:
    """Extract state transitions from RSF CloudWatch logs."""
    messages = query_logs(
        logs_client,
        log_group,
        "step_name",
        start_time,
        propagation_wait=15.0,
        max_retries=5,
    )
    transitions = []
    for msg in messages:
        try:
            data = json.loads(msg)
            transitions.append(StateTransition(
                state_name=data.get("step_name", ""),
                status="entered" if "starting" in msg.lower() else "succeeded",
            ))
        except json.JSONDecodeError:
            continue
    return transitions


# ---------------------------------------------------------------------------
# Parity comparison
# ---------------------------------------------------------------------------


def compare_state_sequences(
    sf_trace: list[StateTransition],
    rsf_trace: list[StateTransition],
    sf_extra_states: set[str] | None = None,
) -> bool:
    """Compare the sequence of states entered (ignoring timing).

    sf_extra_states: states present in SF but not RSF (e.g., extra S3 read
    states added because SF uses SDK integrations). These are excluded from
    the SF trace before comparison.
    """
    exclude = sf_extra_states or set()
    sf_states = [t.state_name for t in sf_trace if t.status == "entered" and t.state_name not in exclude]
    rsf_states = [t.state_name for t in rsf_trace if t.status == "entered"]
    return sf_states == rsf_states


def compare_s3_outputs(
    s3_client: Any,
    bucket: str,
    sf_key: str,
    rsf_key: str,
    ignore_fields: list[str] | None = None,
) -> bool:
    """Compare JSON objects written to S3 by SF and RSF.

    Optionally ignores fields that are expected to differ (e.g., timestamps).
    """
    sf_data = json.loads(
        s3_client.get_object(Bucket=bucket, Key=sf_key)["Body"].read()
    )
    rsf_data = json.loads(
        s3_client.get_object(Bucket=bucket, Key=rsf_key)["Body"].read()
    )

    if ignore_fields:
        sf_data = _strip_fields(sf_data, ignore_fields)
        rsf_data = _strip_fields(rsf_data, ignore_fields)

    return sf_data == rsf_data


def _strip_fields(data: Any, fields: list[str]) -> Any:
    """Recursively remove specified fields from nested dicts/lists."""
    if isinstance(data, dict):
        return {k: _strip_fields(v, fields) for k, v in data.items() if k not in fields}
    if isinstance(data, list):
        return [_strip_fields(item, fields) for item in data]
    return data


# ---------------------------------------------------------------------------
# Test data seeding
# ---------------------------------------------------------------------------


def upload_test_file(s3_client: Any, bucket: str, key: str, local_path: Path) -> None:
    """Upload a local file to S3."""
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=local_path.read_bytes(),
        ContentType="application/json" if local_path.suffix == ".json" else "text/plain",
    )


def send_sqs_messages(
    sqs_client: Any,
    queue_url: str,
    messages: list[dict],
    stagger_seconds: float = 9.0,
) -> None:
    """Send messages to SQS with staggered timing (in a background thread)."""
    def _send():
        for i, msg in enumerate(messages):
            sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(msg),
            )
            logger.info("Sent SQS message %d/%d", i + 1, len(messages))
            if i < len(messages) - 1:
                time.sleep(stagger_seconds)

    thread = threading.Thread(target=_send, daemon=True)
    thread.start()
    return thread


def purge_sqs_queue(sqs_client: Any, queue_url: str) -> None:
    """Drain all messages from an SQS queue.

    Uses receive + delete rather than PurgeQueue to avoid the 60-second
    cooldown between PurgeQueue calls (which would fail between SF and RSF runs).
    """
    while True:
        resp = sqs_client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=2)
        msgs = resp.get("Messages", [])
        if not msgs:
            break
        entries = [{"Id": str(i), "ReceiptHandle": m["ReceiptHandle"]} for i, m in enumerate(msgs)]
        sqs_client.delete_message_batch(QueueUrl=queue_url, Entries=entries)
    logger.info("purge_sqs_queue: queue drained")
