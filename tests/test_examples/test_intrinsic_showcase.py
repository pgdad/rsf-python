"""Integration tests for the intrinsic-showcase example.

Deploys to real AWS, invokes the durable Lambda, and verifies:
- Lambda return value (SUCCEEDED terminal state) [VERF-01]
- CloudWatch log assertions for intrinsic function handlers [VERF-02]
- All 5 I/O pipeline stages exercised (InputPath, Parameters,
  ResultSelector, ResultPath, OutputPath)

State types exercised: Task, Pass, Choice, Succeed
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import pytest

from tests.test_examples.conftest import (
    EXAMPLES_ROOT,
    iam_propagation_wait,
    make_execution_id,
    poll_execution,
    query_logs,
    terraform_deploy,
    terraform_teardown,
)

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.integration


class TestIntrinsicShowcaseIntegration:
    """Deploy, invoke, verify, and teardown the intrinsic-showcase example."""

    EXAMPLE_DIR = EXAMPLES_ROOT / "intrinsic-showcase"

    EVENT = {
        "input": {"userName": "Test User"},
    }

    @pytest.fixture(scope="class")
    def deployment(self, lambda_client, logs_client):
        """Deploy infrastructure, invoke workflow, yield context."""
        outputs = terraform_deploy(self.EXAMPLE_DIR)
        iam_propagation_wait()

        fn = outputs["function_name"]
        exec_id = make_execution_id("intrinsic-showcase")
        start_time = datetime.now(timezone.utc)

        lambda_client.invoke(
            FunctionName=fn,
            InvocationType="Event",
            Payload=json.dumps(self.EVENT),
            DurableExecutionName=exec_id,
        )

        execution = poll_execution(lambda_client, fn, exec_id)

        yield {
            "execution": execution,
            "outputs": outputs,
            "start_time": start_time,
            "function_name": fn,
        }

        terraform_teardown(self.EXAMPLE_DIR, logs_client, outputs["log_group_name"])

    def test_execution_succeeds(self, deployment):
        """Intrinsic showcase reaches SUCCEEDED terminal state (VERF-01)."""
        assert deployment["execution"]["Status"] == "SUCCEEDED"

    def test_handler_log_entries(self, deployment, logs_client):
        """CloudWatch logs confirm intrinsic function handlers executed (VERF-02).

        Expected path: PrepareData (Pass) → StringOperations →
        ArrayOperations → MathAndJsonOps → CheckResults (Choice)
        → ShowcaseComplete (Succeed).
        """
        log_group = deployment["outputs"]["log_group_name"]
        start_time = deployment["start_time"]

        query = "fields @message | filter @message like /step_name/ | sort @timestamp asc"
        results = query_logs(logs_client, log_group, query, start_time)

        messages = " ".join(next((f["value"] for f in row if f["field"] == "@message"), "") for row in results)

        for step in ("StringOperations", "ArrayOperations", "MathAndJsonOps"):
            assert step in messages, f"Handler '{step}' not found in CloudWatch logs"
