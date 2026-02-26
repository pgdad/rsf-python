"""Integration tests for the order-processing example.

Deploys to real AWS, invokes the durable Lambda, and verifies:
- Lambda return value (SUCCEEDED terminal state) [VERF-01]
- CloudWatch log assertions for intermediate state transitions [VERF-02]
- Fail state type exercised via error path [VERF-03]

State types exercised: Task, Choice, Parallel, Succeed, Fail
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


class TestOrderProcessingIntegration:
    """Deploy, invoke, verify, and teardown the order-processing example."""

    EXAMPLE_DIR = EXAMPLES_ROOT / "order-processing"

    # Happy path: total <= 1000, non-empty items → ProcessOrder → OrderComplete
    HAPPY_EVENT = {
        "orderId": "test-001",
        "customerEmail": "test@example.com",
        "total": 59.98,
        "items": [{"name": "Widget", "price": 29.99, "quantity": 2}],
    }

    # Error path: empty items → itemCount == 0 → OrderRejected (Fail state)
    ERROR_EVENT = {
        "orderId": "test-empty",
        "customerEmail": "test@example.com",
        "total": 0,
        "items": [],
    }

    @pytest.fixture(scope="class")
    def deployment(self, lambda_client, logs_client):
        """Deploy infrastructure, invoke happy-path workflow, yield context."""
        outputs = terraform_deploy(self.EXAMPLE_DIR)
        iam_propagation_wait()

        fn = outputs["function_name"]
        exec_id = make_execution_id("order-processing")
        start_time = datetime.now(timezone.utc)

        lambda_client.invoke(
            FunctionName=fn,
            InvocationType="Event",
            Payload=json.dumps(self.HAPPY_EVENT),
            DurableExecutionName=exec_id,
        )

        execution = poll_execution(lambda_client, fn, exec_id)

        yield {
            "execution": execution,
            "outputs": outputs,
            "start_time": start_time,
            "function_name": fn,
        }

        terraform_teardown(
            self.EXAMPLE_DIR, logs_client, outputs["log_group_name"]
        )

    def test_execution_succeeds(self, deployment):
        """Happy path reaches SUCCEEDED terminal state (VERF-01)."""
        assert deployment["execution"]["Status"] == "SUCCEEDED"

    def test_handler_log_entries(self, deployment, logs_client):
        """CloudWatch logs confirm handler execution sequence (VERF-02).

        Expected path: ValidateOrder → CheckOrderValue → ProcessOrder
        (Parallel: ProcessPayment + ReserveInventory) → SendConfirmation
        → OrderComplete.
        """
        log_group = deployment["outputs"]["log_group_name"]
        start_time = deployment["start_time"]

        query = (
            "fields @message"
            " | filter @message like /step_name/"
            " | sort @timestamp asc"
        )
        results = query_logs(logs_client, log_group, query, start_time)

        messages = " ".join(
            next((f["value"] for f in row if f["field"] == "@message"), "")
            for row in results
        )

        for step in (
            "ValidateOrder",
            "ProcessPayment",
            "ReserveInventory",
            "SendConfirmation",
        ):
            assert step in messages, (
                f"Handler '{step}' not found in CloudWatch logs"
            )

    def test_fail_state_exercised(self, deployment, lambda_client):
        """Error path exercises Fail state type (VERF-03).

        Sends empty items (itemCount=0) → Choice routes to OrderRejected
        (Fail state), confirming the Fail state type works in real AWS.
        """
        fn = deployment["function_name"]
        exec_id = make_execution_id("order-rejected")

        lambda_client.invoke(
            FunctionName=fn,
            InvocationType="Event",
            Payload=json.dumps(self.ERROR_EVENT),
            DurableExecutionName=exec_id,
        )

        execution = poll_execution(lambda_client, fn, exec_id)
        assert execution["Status"] == "FAILED"
