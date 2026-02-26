"""Integration tests for the data-pipeline example.

Deploys to real AWS, invokes the durable Lambda, and verifies:
- Lambda return value (SUCCEEDED terminal state) [VERF-01]
- CloudWatch log assertions for intermediate state transitions [VERF-02]
- DynamoDB batch write operations logged [VERF-02]

State types exercised: Task, Pass, Map
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


class TestDataPipelineIntegration:
    """Deploy, invoke, verify, and teardown the data-pipeline example."""

    EXAMPLE_DIR = EXAMPLES_ROOT / "data-pipeline"

    EVENT = {
        "source": {"bucket": "test-bucket", "prefix": "data/"},
    }

    @pytest.fixture(scope="class")
    def deployment(self, lambda_client, logs_client):
        """Deploy infrastructure, invoke pipeline, yield context."""
        outputs = terraform_deploy(self.EXAMPLE_DIR)
        iam_propagation_wait()

        fn = outputs["function_name"]
        exec_id = make_execution_id("data-pipeline")
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

        terraform_teardown(
            self.EXAMPLE_DIR, logs_client, outputs["log_group_name"]
        )

    def test_execution_succeeds(self, deployment):
        """Pipeline reaches SUCCEEDED terminal state (VERF-01)."""
        assert deployment["execution"]["Status"] == "SUCCEEDED"

    def test_handler_log_entries(self, deployment, logs_client):
        """CloudWatch logs confirm pipeline handler execution (VERF-02).

        Expected path: InitPipeline (Pass) → FetchRecords → TransformRecords
        (Map: ValidateRecord + EnrichRecord per item) → StoreResults
        → PipelineComplete (Pass).
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
            "FetchRecords",
            "ValidateRecord",
            "EnrichRecord",
            "StoreResults",
        ):
            assert step in messages, (
                f"Handler '{step}' not found in CloudWatch logs"
            )

    def test_dynamodb_operations_logged(self, deployment, logs_client):
        """CloudWatch logs confirm DynamoDB batch write operations (VERF-02).

        The StoreResults handler logs each item written to DynamoDB.
        """
        log_group = deployment["outputs"]["log_group_name"]
        start_time = deployment["start_time"]

        query = (
            "fields @message"
            " | filter @message like /batch write/i"
            " | sort @timestamp asc"
        )
        results = query_logs(logs_client, log_group, query, start_time)

        assert len(results) > 0, (
            "DynamoDB batch write operations not found in CloudWatch logs"
        )
