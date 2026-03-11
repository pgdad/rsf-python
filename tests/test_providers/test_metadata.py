"""Tests for WorkflowMetadata dataclass and create_metadata() factory."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any


# Import dsl package to initialize state validators
import rsf.dsl  # noqa: F401
from rsf.dsl.models import StateMachineDefinition
from rsf.providers.metadata import WorkflowMetadata, create_metadata


# --- WorkflowMetadata dataclass tests ---


class TestWorkflowMetadata:
    """Verify WorkflowMetadata dataclass structure and serialization."""

    def test_minimal_instance(self) -> None:
        """WorkflowMetadata with only workflow_name creates valid instance."""
        meta = WorkflowMetadata(workflow_name="test-wf")
        assert meta.workflow_name == "test-wf"

    def test_default_values(self) -> None:
        """Default values match export_cmd pattern."""
        meta = WorkflowMetadata(workflow_name="test")
        assert meta.stage is None
        assert meta.handler_count == 0
        assert meta.timeout_seconds is None
        assert meta.triggers == []
        assert meta.dynamodb_tables == []
        assert meta.alarms == []
        assert meta.dlq_enabled is False
        assert meta.dlq_max_receive_count == 3
        assert meta.dlq_queue_name is None
        assert meta.lambda_url_enabled is False
        assert meta.lambda_url_auth_type == "NONE"

    def test_all_fields_accessible(self) -> None:
        """All 12 fields are accessible on the instance."""
        meta = WorkflowMetadata(
            workflow_name="my-wf",
            stage="dev",
            handler_count=3,
            timeout_seconds=300,
            triggers=[{"type": "eventbridge"}],
            dynamodb_tables=[{"table_name": "items"}],
            alarms=[{"type": "error_rate"}],
            dlq_enabled=True,
            dlq_max_receive_count=5,
            dlq_queue_name="my-dlq",
            lambda_url_enabled=True,
            lambda_url_auth_type="AWS_IAM",
        )
        assert meta.workflow_name == "my-wf"
        assert meta.stage == "dev"
        assert meta.handler_count == 3
        assert meta.timeout_seconds == 300
        assert meta.triggers == [{"type": "eventbridge"}]
        assert meta.dynamodb_tables == [{"table_name": "items"}]
        assert meta.alarms == [{"type": "error_rate"}]
        assert meta.dlq_enabled is True
        assert meta.dlq_max_receive_count == 5
        assert meta.dlq_queue_name == "my-dlq"
        assert meta.lambda_url_enabled is True
        assert meta.lambda_url_auth_type == "AWS_IAM"

    def test_asdict_returns_all_keys(self) -> None:
        """dataclasses.asdict() returns dict with all field names."""
        meta = WorkflowMetadata(workflow_name="test")
        d = asdict(meta)
        expected_keys = {
            "workflow_name",
            "stage",
            "handler_count",
            "timeout_seconds",
            "triggers",
            "dynamodb_tables",
            "alarms",
            "dlq_enabled",
            "dlq_max_receive_count",
            "dlq_queue_name",
            "lambda_url_enabled",
            "lambda_url_auth_type",
        }
        assert set(d.keys()) == expected_keys

    def test_json_serialization_minimal(self) -> None:
        """JSON serialization works for minimal metadata."""
        meta = WorkflowMetadata(workflow_name="test")
        j = json.dumps(asdict(meta))
        parsed = json.loads(j)
        assert parsed["workflow_name"] == "test"
        assert parsed["triggers"] == []

    def test_json_serialization_with_triggers(self) -> None:
        """JSON round-trip works with populated triggers."""
        meta = WorkflowMetadata(
            workflow_name="test",
            triggers=[
                {"type": "eventbridge", "schedule_expression": "rate(1 hour)"},
                {"type": "sqs", "queue_name": "my-queue", "batch_size": 10},
            ],
        )
        j = json.dumps(asdict(meta))
        parsed = json.loads(j)
        assert len(parsed["triggers"]) == 2
        assert parsed["triggers"][0]["type"] == "eventbridge"
        assert parsed["triggers"][1]["queue_name"] == "my-queue"

    def test_json_serialization_with_all_features(self) -> None:
        """JSON round-trip works with all infrastructure features populated."""
        meta = WorkflowMetadata(
            workflow_name="full-wf",
            stage="prod",
            handler_count=5,
            timeout_seconds=900,
            triggers=[{"type": "sns", "topic_arn": "arn:aws:sns:us-east-1:123:topic"}],
            dynamodb_tables=[
                {
                    "table_name": "items",
                    "partition_key": {"name": "id", "type": "S"},
                    "billing_mode": "PAY_PER_REQUEST",
                }
            ],
            alarms=[
                {
                    "type": "error_rate",
                    "threshold": 5.0,
                    "period": 300,
                    "evaluation_periods": 1,
                    "sns_topic_arn": None,
                }
            ],
            dlq_enabled=True,
            dlq_max_receive_count=5,
            dlq_queue_name="my-dlq",
            lambda_url_enabled=True,
            lambda_url_auth_type="AWS_IAM",
        )
        j = json.dumps(asdict(meta))
        parsed = json.loads(j)
        assert parsed["workflow_name"] == "full-wf"
        assert parsed["stage"] == "prod"
        assert parsed["dlq_enabled"] is True
        assert parsed["lambda_url_auth_type"] == "AWS_IAM"
        assert len(parsed["dynamodb_tables"]) == 1


# --- create_metadata() factory tests ---


def _make_definition(
    *,
    states: dict[str, Any] | None = None,
    triggers: list[dict[str, Any]] | None = None,
    dynamodb_tables: list[dict[str, Any]] | None = None,
    alarms: list[dict[str, Any]] | None = None,
    dead_letter_queue: dict[str, Any] | None = None,
    lambda_url: dict[str, Any] | None = None,
    timeout_seconds: int | None = None,
) -> StateMachineDefinition:
    """Build a minimal valid StateMachineDefinition for testing."""
    if states is None:
        states = {
            "Start": {"Type": "Pass", "End": True},
        }

    raw: dict[str, Any] = {
        "StartAt": "Start",
        "States": states,
    }
    if triggers is not None:
        raw["triggers"] = triggers
    if dynamodb_tables is not None:
        raw["dynamodb_tables"] = dynamodb_tables
    if alarms is not None:
        raw["alarms"] = alarms
    if dead_letter_queue is not None:
        raw["dead_letter_queue"] = dead_letter_queue
    if lambda_url is not None:
        raw["lambda_url"] = lambda_url
    if timeout_seconds is not None:
        raw["TimeoutSeconds"] = timeout_seconds

    return StateMachineDefinition.model_validate(raw)


class TestCreateMetadata:
    """Verify create_metadata() factory function."""

    def test_minimal_definition(self) -> None:
        """Minimal definition (no infra) returns metadata with defaults."""
        defn = _make_definition()
        meta = create_metadata(defn, "test-wf")
        assert meta.workflow_name == "test-wf"
        assert meta.stage is None
        assert meta.handler_count == 0
        assert meta.triggers == []
        assert meta.dynamodb_tables == []
        assert meta.alarms == []
        assert meta.dlq_enabled is False
        assert meta.lambda_url_enabled is False

    def test_stage_passthrough(self) -> None:
        """Stage parameter is passed through to metadata."""
        defn = _make_definition()
        meta = create_metadata(defn, "test-wf", stage="prod")
        assert meta.stage == "prod"

    def test_handler_count(self) -> None:
        """Handler count equals number of TaskState instances."""
        defn = _make_definition(
            states={
                "Step1": {"Type": "Task", "Next": "Step2"},
                "Step2": {"Type": "Task", "Next": "Done"},
                "Done": {"Type": "Pass", "End": True},
            }
        )
        meta = create_metadata(defn, "test-wf")
        assert meta.handler_count == 2

    def test_timeout_seconds(self) -> None:
        """Timeout seconds extracted from definition."""
        defn = _make_definition(timeout_seconds=300)
        meta = create_metadata(defn, "test-wf")
        assert meta.timeout_seconds == 300

    def test_eventbridge_trigger(self) -> None:
        """EventBridge trigger extracted with schedule_expression."""
        defn = _make_definition(
            triggers=[
                {
                    "type": "eventbridge",
                    "schedule_expression": "rate(1 hour)",
                }
            ]
        )
        meta = create_metadata(defn, "test-wf")
        assert len(meta.triggers) == 1
        assert meta.triggers[0]["type"] == "eventbridge"
        assert meta.triggers[0]["schedule_expression"] == "rate(1 hour)"

    def test_sqs_trigger(self) -> None:
        """SQS trigger extracted with queue_name and batch_size."""
        defn = _make_definition(
            triggers=[
                {
                    "type": "sqs",
                    "queue_name": "my-queue",
                    "batch_size": 5,
                }
            ]
        )
        meta = create_metadata(defn, "test-wf")
        assert len(meta.triggers) == 1
        assert meta.triggers[0]["type"] == "sqs"
        assert meta.triggers[0]["queue_name"] == "my-queue"
        assert meta.triggers[0]["batch_size"] == 5

    def test_sns_trigger(self) -> None:
        """SNS trigger extracted with topic_arn."""
        defn = _make_definition(
            triggers=[
                {
                    "type": "sns",
                    "topic_arn": "arn:aws:sns:us-east-1:123456:my-topic",
                }
            ]
        )
        meta = create_metadata(defn, "test-wf")
        assert len(meta.triggers) == 1
        assert meta.triggers[0]["type"] == "sns"
        assert meta.triggers[0]["topic_arn"] == "arn:aws:sns:us-east-1:123456:my-topic"

    def test_dynamodb_table(self) -> None:
        """DynamoDB table extracted with partition_key and billing_mode."""
        defn = _make_definition(
            dynamodb_tables=[
                {
                    "table_name": "items",
                    "partition_key": {"name": "id", "type": "S"},
                }
            ]
        )
        meta = create_metadata(defn, "test-wf")
        assert len(meta.dynamodb_tables) == 1
        table = meta.dynamodb_tables[0]
        assert table["table_name"] == "items"
        assert table["partition_key"]["name"] == "id"
        assert table["partition_key"]["type"] == "S"
        assert table["billing_mode"] == "PAY_PER_REQUEST"

    def test_dynamodb_table_with_sort_key(self) -> None:
        """DynamoDB table with sort key extracted."""
        defn = _make_definition(
            dynamodb_tables=[
                {
                    "table_name": "items",
                    "partition_key": {"name": "pk", "type": "S"},
                    "sort_key": {"name": "sk", "type": "N"},
                }
            ]
        )
        meta = create_metadata(defn, "test-wf")
        table = meta.dynamodb_tables[0]
        assert table["sort_key"]["name"] == "sk"
        assert table["sort_key"]["type"] == "N"

    def test_alarm_extraction(self) -> None:
        """Alarm extracted with all fields."""
        defn = _make_definition(
            alarms=[
                {
                    "type": "error_rate",
                    "threshold": 5.0,
                    "period": 300,
                    "evaluation_periods": 2,
                    "sns_topic_arn": "arn:aws:sns:us-east-1:123:alerts",
                }
            ]
        )
        meta = create_metadata(defn, "test-wf")
        assert len(meta.alarms) == 1
        alarm = meta.alarms[0]
        assert alarm["type"] == "error_rate"
        assert alarm["threshold"] == 5.0
        assert alarm["period"] == 300
        assert alarm["evaluation_periods"] == 2
        assert alarm["sns_topic_arn"] == "arn:aws:sns:us-east-1:123:alerts"

    def test_dlq_extraction(self) -> None:
        """DLQ config extracted when enabled."""
        defn = _make_definition(
            dead_letter_queue={
                "enabled": True,
                "max_receive_count": 5,
                "queue_name": "my-dlq",
            }
        )
        meta = create_metadata(defn, "test-wf")
        assert meta.dlq_enabled is True
        assert meta.dlq_max_receive_count == 5
        assert meta.dlq_queue_name == "my-dlq"

    def test_dlq_disabled(self) -> None:
        """DLQ config not extracted when disabled."""
        defn = _make_definition(
            dead_letter_queue={
                "enabled": False,
            }
        )
        meta = create_metadata(defn, "test-wf")
        assert meta.dlq_enabled is False
        assert meta.dlq_max_receive_count == 3  # default
        assert meta.dlq_queue_name is None

    def test_lambda_url_extraction(self) -> None:
        """Lambda URL config extracted when enabled."""
        defn = _make_definition(
            lambda_url={
                "enabled": True,
                "auth_type": "AWS_IAM",
            }
        )
        meta = create_metadata(defn, "test-wf")
        assert meta.lambda_url_enabled is True
        assert meta.lambda_url_auth_type == "AWS_IAM"

    def test_lambda_url_disabled(self) -> None:
        """Lambda URL not extracted when not present."""
        defn = _make_definition()
        meta = create_metadata(defn, "test-wf")
        assert meta.lambda_url_enabled is False
        assert meta.lambda_url_auth_type == "NONE"
