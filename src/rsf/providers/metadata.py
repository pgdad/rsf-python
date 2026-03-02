"""WorkflowMetadata dataclass and create_metadata() factory.

Provides the canonical metadata schema for RSF workflow infrastructure.
WorkflowMetadata is a stdlib dataclass (not Pydantic) — use
dataclasses.asdict() to produce valid JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rsf.dsl.models import StateMachineDefinition, TaskState


@dataclass
class WorkflowMetadata:
    """Canonical metadata schema for RSF workflow infrastructure.

    Captures all DSL infrastructure fields as a stdlib dataclass.
    Use ``dataclasses.asdict()`` to produce valid JSON.

    This is a data-transfer object (DTO), not a validation model.
    Validation happens in the DSL layer (Pydantic models).

    Fields mirror the output of
    ``export_cmd._extract_infrastructure_from_definition()``.
    """

    workflow_name: str
    stage: str | None = None
    handler_count: int = 0
    timeout_seconds: int | None = None
    triggers: list[dict[str, Any]] = field(default_factory=list)
    dynamodb_tables: list[dict[str, Any]] = field(default_factory=list)
    alarms: list[dict[str, Any]] = field(default_factory=list)
    dlq_enabled: bool = False
    dlq_max_receive_count: int = 3
    dlq_queue_name: str | None = None
    lambda_url_enabled: bool = False
    lambda_url_auth_type: str = "NONE"


def create_metadata(
    definition: StateMachineDefinition,
    workflow_name: str,
    stage: str | None = None,
) -> WorkflowMetadata:
    """Extract infrastructure metadata from a DSL definition.

    Mirrors the logic of ``export_cmd._extract_infrastructure_from_definition()``
    but returns a typed ``WorkflowMetadata`` instead of an untyped dict.

    Args:
        definition: Parsed and validated DSL workflow definition.
        workflow_name: Human-readable workflow name.
        stage: Optional deployment stage (e.g., "dev", "prod").

    Returns:
        WorkflowMetadata with all infrastructure fields extracted.
    """
    # Count handler (TaskState) instances
    handler_count = sum(
        1 for s in definition.states.values() if isinstance(s, TaskState)
    )

    # Extract triggers
    triggers: list[dict[str, Any]] = []
    if definition.triggers:
        for trigger in definition.triggers:
            trigger_dict: dict[str, Any] = {"type": trigger.type}
            if trigger.type == "eventbridge":
                trigger_dict["schedule_expression"] = trigger.schedule_expression
                trigger_dict["event_pattern"] = trigger.event_pattern
            elif trigger.type == "sqs":
                trigger_dict["queue_name"] = trigger.queue_name
                trigger_dict["batch_size"] = trigger.batch_size
            elif trigger.type == "sns":
                trigger_dict["topic_arn"] = trigger.topic_arn
            triggers.append(trigger_dict)

    # Extract DynamoDB tables
    dynamodb_tables: list[dict[str, Any]] = []
    if definition.dynamodb_tables:
        for table in definition.dynamodb_tables:
            table_dict: dict[str, Any] = {
                "table_name": table.table_name,
                "partition_key": {
                    "name": table.partition_key.name,
                    "type": table.partition_key.type.value,
                },
                "billing_mode": table.billing_mode.value,
            }
            if table.sort_key:
                table_dict["sort_key"] = {
                    "name": table.sort_key.name,
                    "type": table.sort_key.type.value,
                }
            if table.read_capacity is not None:
                table_dict["read_capacity"] = table.read_capacity
            if table.write_capacity is not None:
                table_dict["write_capacity"] = table.write_capacity
            dynamodb_tables.append(table_dict)

    # Extract alarms
    alarms: list[dict[str, Any]] = []
    if definition.alarms:
        for alarm in definition.alarms:
            alarms.append(
                {
                    "type": alarm.type,
                    "threshold": alarm.threshold,
                    "period": alarm.period,
                    "evaluation_periods": alarm.evaluation_periods,
                    "sns_topic_arn": alarm.sns_topic_arn,
                }
            )

    # Extract DLQ config
    dlq_enabled = False
    dlq_max_receive_count = 3
    dlq_queue_name: str | None = None
    if definition.dead_letter_queue and definition.dead_letter_queue.enabled:
        dlq_enabled = True
        dlq_max_receive_count = definition.dead_letter_queue.max_receive_count
        dlq_queue_name = definition.dead_letter_queue.queue_name

    # Extract Lambda URL config
    lambda_url_enabled = False
    lambda_url_auth_type = "NONE"
    if (
        hasattr(definition, "lambda_url")
        and definition.lambda_url
        and definition.lambda_url.enabled
    ):
        lambda_url_enabled = True
        lambda_url_auth_type = definition.lambda_url.auth_type.value

    return WorkflowMetadata(
        workflow_name=workflow_name,
        stage=stage,
        handler_count=handler_count,
        timeout_seconds=definition.timeout_seconds,
        triggers=triggers,
        dynamodb_tables=dynamodb_tables,
        alarms=alarms,
        dlq_enabled=dlq_enabled,
        dlq_max_receive_count=dlq_max_receive_count,
        dlq_queue_name=dlq_queue_name,
        lambda_url_enabled=lambda_url_enabled,
        lambda_url_auth_type=lambda_url_auth_type,
    )
