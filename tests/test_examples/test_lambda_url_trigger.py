"""Integration tests for the lambda-url-trigger example.

Deploys to real AWS, POSTs to the Lambda Function URL, and verifies:
- Lambda Function URL is accessible and returns HTTPS endpoint [EX-03]
- HTTP POST triggers a durable execution [EX-03]
- Execution completes with SUCCEEDED status [EX-03]

State types exercised: Task, Succeed
Lambda URL feature: auth_type NONE (public endpoint)
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import pytest
import requests

from tests.test_examples.conftest import (
    EXAMPLES_ROOT,
    iam_propagation_wait,
    terraform_deploy,
    terraform_teardown,
    TERMINAL_STATUSES,
)

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.integration


def poll_latest_execution(
    lambda_client,
    function_name: str,
    after_time: datetime,
    timeout: float = 120.0,
    poll_interval: float = 5.0,
) -> dict:
    """Poll for the most recent durable execution that started after after_time.

    Lists all recent executions and returns the first one that reaches
    a terminal state.
    """
    from botocore.exceptions import ClientError

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            response = lambda_client.list_durable_executions_by_function(
                FunctionName=function_name,
                MaxItems=10,
            )
            executions = response.get("DurableExecutions", [])

            for execution in executions:
                start_ts = execution.get("StartTimestamp")
                if start_ts is not None:
                    if hasattr(start_ts, "replace"):
                        # It's a datetime object
                        exec_start = start_ts.replace(tzinfo=timezone.utc) if start_ts.tzinfo is None else start_ts
                    else:
                        exec_start = start_ts
                    if exec_start >= after_time:
                        status = execution.get("Status", "")
                        if status in TERMINAL_STATUSES:
                            return execution

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code not in ("TooManyRequestsException", "ThrottlingException"):
                raise

        time.sleep(poll_interval)

    raise TimeoutError(f"No completed execution found after {after_time} within {timeout}s")


class TestLambdaUrlTriggerIntegration:
    """Deploy, invoke via Lambda URL, verify, and teardown the lambda-url-trigger example."""

    EXAMPLE_DIR = EXAMPLES_ROOT / "lambda-url-trigger"

    ORDER_EVENT = {
        "orderId": "test-url-001",
        "items": [{"name": "Widget", "price": 29.99, "quantity": 2}],
        "total": 59.98,
    }

    @pytest.fixture(scope="class")
    def deployment(self, lambda_client, logs_client):
        """Deploy infrastructure, invoke via Lambda URL, yield context."""
        outputs = terraform_deploy(self.EXAMPLE_DIR)
        iam_propagation_wait()

        fn = outputs["function_name"]
        function_url = outputs["function_url"]
        start_time = datetime.now(timezone.utc)

        # POST to the Lambda Function URL (public, auth_type=NONE)
        response = requests.post(
            function_url,
            json=self.ORDER_EVENT,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        logger.info(
            "Lambda URL POST: status=%d, body=%s",
            response.status_code,
            response.text[:200],
        )

        # Poll for execution completion by listing recent executions
        execution = poll_latest_execution(lambda_client, fn, start_time, timeout=120)

        yield {
            "execution": execution,
            "outputs": outputs,
            "start_time": start_time,
            "function_name": fn,
            "function_url": function_url,
            "post_response": response,
        }

        # Teardown
        log_group = outputs.get("log_group_name")
        terraform_teardown(self.EXAMPLE_DIR, logs_client, log_group)

    def test_function_url_exists(self, deployment):
        """Terraform outputs should include function_url."""
        assert "function_url" in deployment["outputs"]

    def test_function_url_is_https(self, deployment):
        """Lambda Function URL should use HTTPS."""
        assert deployment["function_url"].startswith("https://")

    def test_post_returns_success(self, deployment):
        """HTTP POST to Lambda URL should return a success status code."""
        response = deployment["post_response"]
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_execution_succeeded(self, deployment):
        """Durable execution should complete with SUCCEEDED status."""
        execution = deployment["execution"]
        assert execution["Status"] == "SUCCEEDED", f"Expected SUCCEEDED, got {execution.get('Status')}"
