"""Tests for rsf export CLI command."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from rsf.cli.export_cmd import (
    _build_sam_template,
    _extract_infrastructure_from_definition,
    _sanitize_logical_id,
)
from rsf.dsl.parser import load_definition


# --- Helper to create workflow files ---


def _write_workflow(path: Path, content: str) -> Path:
    """Write a workflow YAML file and return its path."""
    workflow = path / "workflow.yaml"
    workflow.write_text(content)
    return workflow


MINIMAL_WORKFLOW = """\
StartAt: ProcessOrder
States:
  ProcessOrder:
    Type: Task
    Next: SendEmail
  SendEmail:
    Type: Task
    End: true
"""

WORKFLOW_WITH_TRIGGERS = """\
StartAt: ProcessOrder
States:
  ProcessOrder:
    Type: Task
    End: true
triggers:
  - type: eventbridge
    schedule_expression: "rate(5 minutes)"
  - type: sqs
    queue_name: orders-queue
    batch_size: 5
  - type: sns
    topic_arn: "arn:aws:sns:us-east-1:123456789:orders-topic"
"""

WORKFLOW_WITH_DYNAMODB = """\
StartAt: ProcessOrder
States:
  ProcessOrder:
    Type: Task
    End: true
dynamodb_tables:
  - table_name: orders
    partition_key:
      name: order_id
      type: S
    billing_mode: PAY_PER_REQUEST
"""

WORKFLOW_WITH_ALARMS = """\
StartAt: ProcessOrder
States:
  ProcessOrder:
    Type: Task
    End: true
alarms:
  - type: error_rate
    threshold: 5.0
    period: 300
    evaluation_periods: 1
    sns_topic_arn: "arn:aws:sns:us-east-1:123456789:alerts"
"""

WORKFLOW_WITH_DLQ = """\
StartAt: ProcessOrder
States:
  ProcessOrder:
    Type: Task
    End: true
dead_letter_queue:
  enabled: true
  max_receive_count: 5
  queue_name: orders-dlq
"""

WORKFLOW_WITH_LAMBDA_URL = """\
StartAt: ProcessOrder
States:
  ProcessOrder:
    Type: Task
    End: true
lambda_url:
  enabled: true
  auth_type: NONE
"""


# --- SAM template builder tests ---


class TestBuildSamTemplate:
    """Tests for _build_sam_template."""

    def test_minimal_workflow_produces_valid_sam(self, tmp_path: Path) -> None:
        """Test 1: Minimal workflow produces valid SAM template."""
        workflow = _write_workflow(tmp_path, MINIMAL_WORKFLOW)
        definition = load_definition(workflow)
        infra = _extract_infrastructure_from_definition(definition, "my-workflow")
        template = _build_sam_template(infra)

        assert template["AWSTemplateFormatVersion"] == "2010-09-09"
        assert template["Transform"] == "AWS::Serverless-2016-10-31"

        # Should have a function resource
        resources = template["Resources"]
        fn_key = [k for k in resources if resources[k]["Type"] == "AWS::Serverless::Function"]
        assert len(fn_key) == 1

    def test_includes_iam_policy_statements(self, tmp_path: Path) -> None:
        """Test 2: SAM template includes required IAM policy statements."""
        workflow = _write_workflow(tmp_path, MINIMAL_WORKFLOW)
        definition = load_definition(workflow)
        infra = _extract_infrastructure_from_definition(definition, "my-workflow")
        template = _build_sam_template(infra)

        resources = template["Resources"]
        fn_key = [k for k in resources if resources[k]["Type"] == "AWS::Serverless::Function"][0]
        policies = resources[fn_key]["Properties"]["Policies"]
        statements = policies[0]["Statement"]

        # Check for CloudWatch, Lambda self-invoke, Durable Execution
        actions_flat = []
        for stmt in statements:
            actions_flat.extend(stmt["Action"])

        assert "logs:CreateLogGroup" in actions_flat
        assert "lambda:InvokeFunction" in actions_flat
        assert "lambda:CheckpointDurableExecution" in actions_flat

    def test_includes_cloudwatch_log_group(self, tmp_path: Path) -> None:
        """Test 3: SAM template includes CloudWatch LogGroup with 14-day retention."""
        workflow = _write_workflow(tmp_path, MINIMAL_WORKFLOW)
        definition = load_definition(workflow)
        infra = _extract_infrastructure_from_definition(definition, "my-workflow")
        template = _build_sam_template(infra)

        resources = template["Resources"]
        log_groups = [
            k for k in resources if resources[k]["Type"] == "AWS::Logs::LogGroup"
        ]
        assert len(log_groups) == 1
        assert resources[log_groups[0]]["Properties"]["RetentionInDays"] == 14

    def test_eventbridge_trigger(self, tmp_path: Path) -> None:
        """Test 4: EventBridge trigger produces Events section."""
        workflow = _write_workflow(tmp_path, WORKFLOW_WITH_TRIGGERS)
        definition = load_definition(workflow)
        infra = _extract_infrastructure_from_definition(definition, "my-workflow")
        template = _build_sam_template(infra)

        resources = template["Resources"]
        fn_key = [k for k in resources if resources[k]["Type"] == "AWS::Serverless::Function"][0]
        events = resources[fn_key]["Properties"]["Events"]

        # Should have EventBridge event
        eb_events = [k for k in events if "EventBridge" in k]
        assert len(eb_events) >= 1
        assert events[eb_events[0]]["Type"] == "Schedule"

    def test_sqs_trigger(self, tmp_path: Path) -> None:
        """Test 5: SQS trigger produces Events section with SQS event type."""
        workflow = _write_workflow(tmp_path, WORKFLOW_WITH_TRIGGERS)
        definition = load_definition(workflow)
        infra = _extract_infrastructure_from_definition(definition, "my-workflow")
        template = _build_sam_template(infra)

        resources = template["Resources"]
        fn_key = [k for k in resources if resources[k]["Type"] == "AWS::Serverless::Function"][0]
        events = resources[fn_key]["Properties"]["Events"]

        sqs_events = [k for k in events if "SQS" in k]
        assert len(sqs_events) >= 1
        assert events[sqs_events[0]]["Type"] == "SQS"

    def test_sns_trigger(self, tmp_path: Path) -> None:
        """Test 6: SNS trigger produces Events section with SNS event type."""
        workflow = _write_workflow(tmp_path, WORKFLOW_WITH_TRIGGERS)
        definition = load_definition(workflow)
        infra = _extract_infrastructure_from_definition(definition, "my-workflow")
        template = _build_sam_template(infra)

        resources = template["Resources"]
        fn_key = [k for k in resources if resources[k]["Type"] == "AWS::Serverless::Function"][0]
        events = resources[fn_key]["Properties"]["Events"]

        sns_events = [k for k in events if "SNS" in k]
        assert len(sns_events) >= 1
        assert events[sns_events[0]]["Type"] == "SNS"

    def test_dynamodb_table(self, tmp_path: Path) -> None:
        """Test 7: DynamoDB tables produce AWS::DynamoDB::Table resources and IAM permissions."""
        workflow = _write_workflow(tmp_path, WORKFLOW_WITH_DYNAMODB)
        definition = load_definition(workflow)
        infra = _extract_infrastructure_from_definition(definition, "my-workflow")
        template = _build_sam_template(infra)

        resources = template["Resources"]
        dynamo_keys = [
            k for k in resources if resources[k]["Type"] == "AWS::DynamoDB::Table"
        ]
        assert len(dynamo_keys) == 1

        # Check IAM permissions include DynamoDB actions
        fn_key = [k for k in resources if resources[k]["Type"] == "AWS::Serverless::Function"][0]
        policies = resources[fn_key]["Properties"]["Policies"]
        statements = policies[0]["Statement"]
        dynamo_actions = []
        for stmt in statements:
            for action in stmt["Action"]:
                if action.startswith("dynamodb:"):
                    dynamo_actions.append(action)
        assert "dynamodb:GetItem" in dynamo_actions
        assert "dynamodb:PutItem" in dynamo_actions

    def test_alarms(self, tmp_path: Path) -> None:
        """Test 8: Alarms produce AWS::CloudWatch::Alarm resources."""
        workflow = _write_workflow(tmp_path, WORKFLOW_WITH_ALARMS)
        definition = load_definition(workflow)
        infra = _extract_infrastructure_from_definition(definition, "my-workflow")
        template = _build_sam_template(infra)

        resources = template["Resources"]
        alarm_keys = [
            k for k in resources if resources[k]["Type"] == "AWS::CloudWatch::Alarm"
        ]
        assert len(alarm_keys) == 1

        alarm = resources[alarm_keys[0]]
        assert alarm["Properties"]["MetricName"] == "Errors"
        assert alarm["Properties"]["Threshold"] == 5.0
        assert "AlarmActions" in alarm["Properties"]

    def test_dlq(self, tmp_path: Path) -> None:
        """Test 9: DLQ produces AWS::SQS::Queue resource and DeadLetterQueue config."""
        workflow = _write_workflow(tmp_path, WORKFLOW_WITH_DLQ)
        definition = load_definition(workflow)
        infra = _extract_infrastructure_from_definition(definition, "my-workflow")
        template = _build_sam_template(infra)

        resources = template["Resources"]

        # Should have SQS queue for DLQ
        sqs_keys = [
            k for k in resources if resources[k]["Type"] == "AWS::SQS::Queue"
        ]
        assert len(sqs_keys) >= 1

        # Function should have DeadLetterQueue config
        fn_key = [k for k in resources if resources[k]["Type"] == "AWS::Serverless::Function"][0]
        assert "DeadLetterQueue" in resources[fn_key]["Properties"]

    def test_lambda_url(self, tmp_path: Path) -> None:
        """Test 10: Lambda URL produces FunctionUrlConfig."""
        workflow = _write_workflow(tmp_path, WORKFLOW_WITH_LAMBDA_URL)
        definition = load_definition(workflow)
        infra = _extract_infrastructure_from_definition(definition, "my-workflow")
        template = _build_sam_template(infra)

        resources = template["Resources"]
        fn_key = [k for k in resources if resources[k]["Type"] == "AWS::Serverless::Function"][0]
        assert "FunctionUrlConfig" in resources[fn_key]["Properties"]
        assert resources[fn_key]["Properties"]["FunctionUrlConfig"]["AuthType"] == "NONE"

    def test_generated_yaml_is_valid(self, tmp_path: Path) -> None:
        """Test 11: Generated YAML is valid and parseable."""
        workflow = _write_workflow(tmp_path, MINIMAL_WORKFLOW)
        definition = load_definition(workflow)
        infra = _extract_infrastructure_from_definition(definition, "my-workflow")
        template = _build_sam_template(infra)

        yaml_output = yaml.dump(template, default_flow_style=False)
        parsed = yaml.safe_load(yaml_output)
        assert parsed["AWSTemplateFormatVersion"] == "2010-09-09"
        assert "Resources" in parsed

    def test_extract_infrastructure(self, tmp_path: Path) -> None:
        """Test 12: _extract_infrastructure_from_definition extracts all DSL features."""
        workflow = _write_workflow(tmp_path, WORKFLOW_WITH_TRIGGERS)
        definition = load_definition(workflow)
        infra = _extract_infrastructure_from_definition(definition, "my-workflow")

        assert infra["workflow_name"] == "my-workflow"
        assert infra["handler_count"] == 1
        assert len(infra["triggers"]) == 3


# --- CLI command tests ---


class TestExportCommand:
    """Tests for the export CLI command."""

    def test_cloudformation_format_outputs_sam_yaml(self, tmp_path: Path) -> None:
        """Test 13: --format cloudformation outputs valid SAM YAML to stdout."""
        _write_workflow(tmp_path, MINIMAL_WORKFLOW)

        from typer.testing import CliRunner
        from rsf.cli.main import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "export",
                str(tmp_path / "workflow.yaml"),
                "--format",
                "cloudformation",
            ],
        )

        assert result.exit_code == 0
        parsed = yaml.safe_load(result.output)
        assert parsed["AWSTemplateFormatVersion"] == "2010-09-09"
        assert parsed["Transform"] == "AWS::Serverless-2016-10-31"

    def test_output_flag_writes_to_file(self, tmp_path: Path) -> None:
        """Test 14: --output flag writes SAM template to specified file."""
        _write_workflow(tmp_path, MINIMAL_WORKFLOW)
        output_file = tmp_path / "output" / "template.yaml"

        from typer.testing import CliRunner
        from rsf.cli.main import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "export",
                str(tmp_path / "workflow.yaml"),
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        parsed = yaml.safe_load(output_file.read_text())
        assert parsed["AWSTemplateFormatVersion"] == "2010-09-09"

    def test_invalid_workflow_exits_1(self, tmp_path: Path) -> None:
        """Test 15: Invalid workflow file prints error and exits 1."""
        from typer.testing import CliRunner
        from rsf.cli.main import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "export",
                str(tmp_path / "nonexistent.yaml"),
            ],
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_unsupported_format_exits_1(self, tmp_path: Path) -> None:
        """Test 16: Unsupported --format prints error and exits 1."""
        _write_workflow(tmp_path, MINIMAL_WORKFLOW)

        from typer.testing import CliRunner
        from rsf.cli.main import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "export",
                str(tmp_path / "workflow.yaml"),
                "--format",
                "terraform",
            ],
        )

        assert result.exit_code == 1
        assert "unsupported" in result.output.lower()

    def test_default_outputs_to_stdout(self, tmp_path: Path) -> None:
        """Test 17: Default outputs to stdout (pipeable)."""
        _write_workflow(tmp_path, MINIMAL_WORKFLOW)

        from typer.testing import CliRunner
        from rsf.cli.main import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["export", str(tmp_path / "workflow.yaml")],
        )

        assert result.exit_code == 0
        assert "AWSTemplateFormatVersion" in result.output

    def test_template_contains_headers(self, tmp_path: Path) -> None:
        """Test 18: Template contains AWSTemplateFormatVersion and Transform headers."""
        _write_workflow(tmp_path, MINIMAL_WORKFLOW)

        from typer.testing import CliRunner
        from rsf.cli.main import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["export", str(tmp_path / "workflow.yaml")],
        )

        assert "AWSTemplateFormatVersion" in result.output
        assert "AWS::Serverless-2016-10-31" in result.output

    def test_triggers_in_output(self, tmp_path: Path) -> None:
        """Test 19: Workflow with triggers includes trigger resources."""
        _write_workflow(tmp_path, WORKFLOW_WITH_TRIGGERS)

        from typer.testing import CliRunner
        from rsf.cli.main import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["export", str(tmp_path / "workflow.yaml")],
        )

        assert result.exit_code == 0
        parsed = yaml.safe_load(result.output)
        resources = parsed["Resources"]

        # Should have SQS queue resource for trigger
        sqs_keys = [k for k in resources if resources[k]["Type"] == "AWS::SQS::Queue"]
        assert len(sqs_keys) >= 1

    def test_dynamodb_in_output(self, tmp_path: Path) -> None:
        """Test 20: Workflow with DynamoDB tables includes table resources."""
        _write_workflow(tmp_path, WORKFLOW_WITH_DYNAMODB)

        from typer.testing import CliRunner
        from rsf.cli.main import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["export", str(tmp_path / "workflow.yaml")],
        )

        assert result.exit_code == 0
        parsed = yaml.safe_load(result.output)
        resources = parsed["Resources"]

        dynamo_keys = [k for k in resources if resources[k]["Type"] == "AWS::DynamoDB::Table"]
        assert len(dynamo_keys) == 1
