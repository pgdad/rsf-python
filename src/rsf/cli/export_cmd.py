"""RSF export subcommand — generate CloudFormation/SAM templates from workflow definitions."""

from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console

from rsf.dsl.parser import load_definition
from rsf.providers.metadata import create_metadata, derive_workflow_name

console = Console()


def _sanitize_logical_id(name: str) -> str:
    """Convert a name to a valid CloudFormation logical ID (PascalCase, alphanumeric)."""
    # Replace non-alphanumeric with space, title case, remove spaces
    cleaned = re.sub(r"[^a-zA-Z0-9]", " ", name)
    return "".join(word.capitalize() for word in cleaned.split())


def _build_sam_template(infra: dict[str, Any]) -> dict[str, Any]:
    """Build a complete SAM template dict from extracted infrastructure.

    Returns a dict suitable for YAML serialization as a SAM template.
    """
    workflow_name = infra["workflow_name"]
    logical_id = _sanitize_logical_id(workflow_name)

    template: dict[str, Any] = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Transform": "AWS::Serverless-2016-10-31",
        "Description": f"RSF workflow - {workflow_name}",
        "Globals": {
            "Function": {
                "Runtime": "python3.12",
                "Timeout": infra.get("timeout_seconds") or 900,
                "MemorySize": 256,
            },
        },
        "Resources": {},
        "Outputs": {},
    }

    resources = template["Resources"]
    outputs = template["Outputs"]

    # --- Lambda Function (AWS::Serverless::Function) ---
    function_resource: dict[str, Any] = {
        "Type": "AWS::Serverless::Function",
        "Properties": {
            "FunctionName": {
                "Fn::Sub": f"${{AWS::StackName}}-{workflow_name}-orchestrator"
            },
            "Handler": "orchestrator.handler",
            "CodeUri": ".",
            "Policies": [
                {
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": [
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                            ],
                            "Resource": "*",
                        },
                        {
                            "Effect": "Allow",
                            "Action": ["lambda:InvokeFunction"],
                            "Resource": "*",
                        },
                        {
                            "Effect": "Allow",
                            "Action": [
                                "lambda:CheckpointDurableExecution",
                                "lambda:GetDurableExecution",
                                "lambda:ListDurableExecutionsByFunction",
                            ],
                            "Resource": "*",
                        },
                    ],
                },
            ],
        },
    }

    # Events (triggers)
    events: dict[str, Any] = {}
    for i, trigger in enumerate(infra.get("triggers", [])):
        if trigger["type"] == "eventbridge":
            event_name = f"EventBridgeRule{i + 1}"
            event_def: dict[str, Any] = {
                "Type": "Schedule"
                if trigger.get("schedule_expression")
                else "EventBridgeRule"
            }
            if trigger.get("schedule_expression"):
                event_def["Properties"] = {
                    "Schedule": trigger["schedule_expression"]
                }
            elif trigger.get("event_pattern"):
                event_def["Properties"] = {"Pattern": trigger["event_pattern"]}
            events[event_name] = event_def
        elif trigger["type"] == "sqs":
            event_name = f"SQSTrigger{i + 1}"
            events[event_name] = {
                "Type": "SQS",
                "Properties": {
                    "Queue": {"Fn::GetAtt": [f"TriggerQueue{i + 1}", "Arn"]},
                    "BatchSize": trigger.get("batch_size", 10),
                },
            }
        elif trigger["type"] == "sns":
            event_name = f"SNSTrigger{i + 1}"
            events[event_name] = {
                "Type": "SNS",
                "Properties": {
                    "Topic": trigger.get(
                        "topic_arn", {"Ref": f"TriggerTopic{i + 1}"}
                    ),
                },
            }

    if events:
        function_resource["Properties"]["Events"] = events

    # Lambda URL
    if infra.get("lambda_url_enabled"):
        function_resource["Properties"]["FunctionUrlConfig"] = {
            "AuthType": infra.get("lambda_url_auth_type", "NONE"),
        }

    # DLQ (DeadLetterQueue on function)
    if infra.get("dlq_enabled"):
        function_resource["Properties"]["DeadLetterQueue"] = {
            "Type": "SQS",
            "TargetArn": {"Fn::GetAtt": ["DeadLetterQueue", "Arn"]},
        }

    resources[f"{logical_id}Function"] = function_resource

    # --- CloudWatch Log Group ---
    resources[f"{logical_id}LogGroup"] = {
        "Type": "AWS::Logs::LogGroup",
        "Properties": {
            "LogGroupName": {
                "Fn::Sub": f"/aws/lambda/${{AWS::StackName}}-{workflow_name}-orchestrator"
            },
            "RetentionInDays": 14,
        },
    }

    # --- DynamoDB Tables ---
    for table in infra.get("dynamodb_tables", []):
        table_logical_id = _sanitize_logical_id(table["table_name"])
        dynamo_resource: dict[str, Any] = {
            "Type": "AWS::DynamoDB::Table",
            "Properties": {
                "TableName": {
                    "Fn::Sub": f"${{AWS::StackName}}-{table['table_name']}"
                },
                "BillingMode": table.get("billing_mode", "PAY_PER_REQUEST"),
                "AttributeDefinitions": [
                    {
                        "AttributeName": table["partition_key"]["name"],
                        "AttributeType": table["partition_key"]["type"],
                    },
                ],
                "KeySchema": [
                    {
                        "AttributeName": table["partition_key"]["name"],
                        "KeyType": "HASH",
                    },
                ],
            },
        }

        if table.get("sort_key"):
            dynamo_resource["Properties"]["AttributeDefinitions"].append(
                {
                    "AttributeName": table["sort_key"]["name"],
                    "AttributeType": table["sort_key"]["type"],
                }
            )
            dynamo_resource["Properties"]["KeySchema"].append(
                {
                    "AttributeName": table["sort_key"]["name"],
                    "KeyType": "RANGE",
                }
            )

        if table.get("read_capacity") and table.get("write_capacity"):
            dynamo_resource["Properties"]["ProvisionedThroughput"] = {
                "ReadCapacityUnits": table["read_capacity"],
                "WriteCapacityUnits": table["write_capacity"],
            }

        resources[f"{table_logical_id}Table"] = dynamo_resource

        # Add DynamoDB permissions to function policy
        function_resource["Properties"]["Policies"][0]["Statement"].append(
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                ],
                "Resource": {
                    "Fn::GetAtt": [f"{table_logical_id}Table", "Arn"]
                },
            }
        )

    # --- SQS Trigger Queues ---
    for i, trigger in enumerate(infra.get("triggers", [])):
        if trigger["type"] == "sqs" and trigger.get("queue_name"):
            resources[f"TriggerQueue{i + 1}"] = {
                "Type": "AWS::SQS::Queue",
                "Properties": {
                    "QueueName": {
                        "Fn::Sub": f"${{AWS::StackName}}-{trigger['queue_name']}"
                    },
                },
            }

    # --- Dead Letter Queue ---
    if infra.get("dlq_enabled"):
        dlq_name = infra.get("dlq_queue_name") or f"{workflow_name}-dlq"
        resources["DeadLetterQueue"] = {
            "Type": "AWS::SQS::Queue",
            "Properties": {
                "QueueName": {"Fn::Sub": f"${{AWS::StackName}}-{dlq_name}"},
                "MessageRetentionPeriod": 1209600,  # 14 days
            },
        }

    # --- CloudWatch Alarms ---
    for i, alarm in enumerate(infra.get("alarms", [])):
        alarm_type = alarm["type"]
        alarm_logical_id = (
            f"{logical_id}{_sanitize_logical_id(alarm_type)}Alarm{i + 1}"
        )

        metric_name = {
            "error_rate": "Errors",
            "duration": "Duration",
            "throttle": "Throttles",
        }.get(alarm_type, "Errors")

        alarm_resource: dict[str, Any] = {
            "Type": "AWS::CloudWatch::Alarm",
            "Properties": {
                "AlarmName": {
                    "Fn::Sub": f"${{AWS::StackName}}-{workflow_name}-{alarm_type}"
                },
                "MetricName": metric_name,
                "Namespace": "AWS/Lambda",
                "Statistic": "Sum",
                "Period": alarm.get("period", 300),
                "EvaluationPeriods": alarm.get("evaluation_periods", 1),
                "Threshold": alarm["threshold"],
                "ComparisonOperator": "GreaterThanOrEqualToThreshold",
                "Dimensions": [
                    {
                        "Name": "FunctionName",
                        "Value": {"Ref": f"{logical_id}Function"},
                    },
                ],
            },
        }

        if alarm.get("sns_topic_arn"):
            alarm_resource["Properties"]["AlarmActions"] = [
                alarm["sns_topic_arn"]
            ]

        resources[alarm_logical_id] = alarm_resource

    # --- Outputs ---
    outputs[f"{logical_id}FunctionArn"] = {
        "Description": f"{workflow_name} Lambda function ARN",
        "Value": {"Fn::GetAtt": [f"{logical_id}Function", "Arn"]},
    }

    outputs[f"{logical_id}FunctionName"] = {
        "Description": f"{workflow_name} Lambda function name",
        "Value": {"Ref": f"{logical_id}Function"},
    }

    return template


def export_workflow(
    workflow: Path = typer.Argument(
        "workflow.yaml", help="Path to workflow YAML file"
    ),
    format: str = typer.Option(
        "cloudformation",
        "--format",
        "-f",
        help="Export format: cloudformation",
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output file path (default: stdout)"
    ),
) -> None:
    """Export a workflow definition to CloudFormation/SAM format.

    Reads the workflow YAML and generates an equivalent SAM template
    that can be deployed with `sam build && sam deploy`.
    """
    # Validate format
    if format.lower() not in ("cloudformation", "cfn", "sam"):
        console.print(
            f"[red]Error:[/red] Unsupported format: [bold]{format}[/bold]\n"
            "Supported formats: cloudformation (aliases: cfn, sam)"
        )
        raise typer.Exit(code=1)

    # Check workflow file
    if not workflow.exists():
        console.print(
            f"[red]Error:[/red] Workflow file not found: [bold]{workflow}[/bold]\n"
            "Create one with [bold]rsf init <project>[/bold] or specify a path."
        )
        raise typer.Exit(code=1)

    # Load and validate workflow
    try:
        definition = load_definition(workflow)
    except Exception as exc:
        console.print(f"[red]Error:[/red] Invalid workflow: {exc}")
        raise typer.Exit(code=1)

    # Derive workflow name
    workflow_name = derive_workflow_name(definition, workflow)

    # Extract infrastructure metadata and build template
    metadata = create_metadata(definition, workflow_name)
    infra = asdict(metadata)
    template = _build_sam_template(infra)

    # Serialize to YAML
    yaml_output = yaml.dump(
        template,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )

    # Output
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(yaml_output, encoding="utf-8")
        console.print(f"[green]SAM template written to:[/green] {output}")
    else:
        typer.echo(yaml_output)
