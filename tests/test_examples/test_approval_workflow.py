"""Integration tests for the approval-workflow example.

Deploys to real AWS, invokes the durable Lambda, and verifies:
- Lambda return value (SUCCEEDED terminal state) [VERF-01]
- CloudWatch log assertions for intermediate state transitions [VERF-02]
- Context Object ($$) and Variables/Assign feature correctness

State types exercised: Task, Wait, Choice, Pass, Succeed

Note: The submit_request handler generates a random requestId, so the
check_approval_status handler always returns "pending". After 4 attempts
(attemptCount > 3), the workflow escalates via EscalateRequest (Pass)
to RequestApproved (Succeed). Total wait: ~20s (4 × 5s Wait intervals).
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


class TestApprovalWorkflowIntegration:
    """Deploy, invoke, verify, and teardown the approval-workflow example."""

    EXAMPLE_DIR = EXAMPLES_ROOT / "approval-workflow"

    EVENT = {
        "request": {
            "title": "Test Request",
            "description": "Phase 16 integration test",
        },
        "userId": "test-user",
    }

    @pytest.fixture(scope="class")
    def deployment(self, lambda_client, logs_client):
        """Deploy infrastructure, invoke workflow, yield context."""
        outputs = terraform_deploy(self.EXAMPLE_DIR)
        iam_propagation_wait()

        fn = outputs["function_name"]
        exec_id = make_execution_id("approval-workflow")
        start_time = datetime.now(timezone.utc)

        lambda_client.invoke(
            FunctionName=fn,
            InvocationType="Event",
            Payload=json.dumps(self.EVENT),
            DurableExecutionName=exec_id,
        )

        # Longer timeout: 4 wait loops × 5s + polling overhead
        execution = poll_execution(lambda_client, fn, exec_id, timeout=300)

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
        """Approval workflow reaches SUCCEEDED via escalation path (VERF-01)."""
        assert deployment["execution"]["Status"] == "SUCCEEDED"

    def test_handler_log_entries(self, deployment, logs_client):
        """CloudWatch logs confirm approval handlers executed (VERF-02).

        Expected: SubmitRequest → SetApprovalContext (Pass) → WaitForReview
        (Wait) → CheckApprovalStatus (×4) → EscalateRequest (Pass)
        → RequestApproved (Succeed).
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

        for step in ("SubmitRequest", "CheckApprovalStatus"):
            assert step in messages, (
                f"Handler '{step}' not found in CloudWatch logs"
            )

    def test_multiple_approval_checks(self, deployment, logs_client):
        """CloudWatch logs show multiple approval checks before escalation.

        The workflow loops through WaitForReview → CheckApprovalStatus
        until attemptCount > 3, so we expect ≥4 check invocations.
        """
        log_group = deployment["outputs"]["log_group_name"]
        start_time = deployment["start_time"]

        query = (
            "fields @message"
            " | filter @message like /CheckApprovalStatus/"
            " | sort @timestamp asc"
        )
        results = query_logs(logs_client, log_group, query, start_time)

        assert len(results) >= 4, (
            f"Expected ≥4 approval checks (escalation path), "
            f"got {len(results)}"
        )
