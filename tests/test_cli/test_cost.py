"""Tests for the rsf cost CLI command."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from rsf.cli.cost_cmd import (
    DEFAULT_PRICING,
    _calculate_data_transfer_cost,
    _calculate_dynamodb_cost,
    _calculate_lambda_cost,
    _calculate_trigger_cost,
    _count_dynamodb_operations,
    _count_lambda_invocations,
    _get_pricing,
)
from rsf.dsl.parser import load_definition


@pytest.fixture
def simple_workflow(tmp_path: Path) -> Path:
    """A simple linear workflow with 3 Task states."""
    wf = tmp_path / "workflow.yaml"
    wf.write_text(
        textwrap.dedent("""\
        rsf_version: "1.0"
        StartAt: StepA
        States:
          StepA:
            Type: Task
            Next: StepB
          StepB:
            Type: Task
            Next: StepC
          StepC:
            Type: Task
            End: true
    """)
    )
    return wf


@pytest.fixture
def parallel_workflow(tmp_path: Path) -> Path:
    """Workflow with a Parallel state containing 2 branches, each with 1 Task."""
    wf = tmp_path / "workflow.yaml"
    wf.write_text(
        textwrap.dedent("""\
        rsf_version: "1.0"
        StartAt: Init
        States:
          Init:
            Type: Task
            Next: DoParallel
          DoParallel:
            Type: Parallel
            Branches:
              - StartAt: BranchA
                States:
                  BranchA:
                    Type: Task
                    End: true
              - StartAt: BranchB
                States:
                  BranchB:
                    Type: Task
                    End: true
            Next: Done
          Done:
            Type: Succeed
    """)
    )
    return wf


@pytest.fixture
def choice_workflow(tmp_path: Path) -> Path:
    """Workflow with a Choice state and two branches."""
    wf = tmp_path / "workflow.yaml"
    wf.write_text(
        textwrap.dedent("""\
        rsf_version: "1.0"
        StartAt: Check
        States:
          Check:
            Type: Choice
            Choices:
              - Variable: "$.value"
                NumericGreaterThan: 100
                Next: HighPath
            Default: LowPath
          HighPath:
            Type: Task
            End: true
          LowPath:
            Type: Task
            End: true
    """)
    )
    return wf


@pytest.fixture
def dynamo_workflow(tmp_path: Path) -> Path:
    """Workflow with DynamoDB tables defined."""
    wf = tmp_path / "workflow.yaml"
    wf.write_text(
        textwrap.dedent("""\
        rsf_version: "1.0"
        StartAt: Process
        States:
          Process:
            Type: Task
            End: true
        dynamodb_tables:
          - table_name: orders
            partition_key:
              name: order_id
              type: S
    """)
    )
    return wf


class TestGetPricing:
    """Tests for _get_pricing function."""

    def test_us_east_1_returns_default_pricing(self):
        pricing = _get_pricing("us-east-1")
        assert pricing["lambda_request_per_million"] == DEFAULT_PRICING["lambda_request_per_million"]

    def test_us_east_2_same_as_us_east_1(self):
        pricing_1 = _get_pricing("us-east-1")
        pricing_2 = _get_pricing("us-east-2")
        assert pricing_1["lambda_request_per_million"] == pricing_2["lambda_request_per_million"]

    def test_eu_west_1_has_higher_pricing(self):
        pricing_us = _get_pricing("us-east-1")
        pricing_eu = _get_pricing("eu-west-1")
        assert pricing_eu["lambda_request_per_million"] > pricing_us["lambda_request_per_million"]

    def test_unknown_region_uses_default(self):
        pricing = _get_pricing("unknown-region-99")
        assert pricing["lambda_request_per_million"] == DEFAULT_PRICING["lambda_request_per_million"]


class TestCountLambdaInvocations:
    """Tests for _count_lambda_invocations function."""

    def test_simple_linear_workflow(self, simple_workflow: Path):
        definition = load_definition(simple_workflow)
        pricing = _get_pricing("us-east-1")
        count = _count_lambda_invocations(definition, pricing)
        assert count == 3

    def test_parallel_workflow(self, parallel_workflow: Path):
        definition = load_definition(parallel_workflow)
        pricing = _get_pricing("us-east-1")
        count = _count_lambda_invocations(definition, pricing)
        # 1 Init + 2 branch tasks = 3
        assert count == 3

    def test_choice_workflow_counts_all_paths(self, choice_workflow: Path):
        definition = load_definition(choice_workflow)
        pricing = _get_pricing("us-east-1")
        count = _count_lambda_invocations(definition, pricing)
        # 2 task states total (HighPath + LowPath)
        assert count == 2


class TestCountDynamoDBOperations:
    """Tests for _count_dynamodb_operations function."""

    def test_no_tables_returns_zero(self, simple_workflow: Path):
        definition = load_definition(simple_workflow)
        pricing = _get_pricing("us-east-1")
        reads, writes = _count_dynamodb_operations(definition, pricing)
        assert reads == 0
        assert writes == 0

    def test_with_table_returns_operations(self, dynamo_workflow: Path):
        definition = load_definition(dynamo_workflow)
        pricing = _get_pricing("us-east-1")
        reads, writes = _count_dynamodb_operations(definition, pricing)
        assert reads > 0
        assert writes > 0


class TestCalculateLambdaCost:
    """Tests for _calculate_lambda_cost function."""

    def test_basic_cost_calculation(self):
        pricing = _get_pricing("us-east-1")
        cost = _calculate_lambda_cost(10000, 3, pricing)
        assert cost > 0
        assert isinstance(cost, float)

    def test_zero_invocations_zero_cost(self):
        pricing = _get_pricing("us-east-1")
        cost = _calculate_lambda_cost(0, 3, pricing)
        assert cost == 0.0

    def test_more_tasks_higher_cost(self):
        pricing = _get_pricing("us-east-1")
        cost_few = _calculate_lambda_cost(10000, 2, pricing)
        cost_many = _calculate_lambda_cost(10000, 5, pricing)
        assert cost_many > cost_few


class TestCalculateDynamoDBCost:
    """Tests for _calculate_dynamodb_cost function."""

    def test_zero_operations_zero_cost(self):
        pricing = _get_pricing("us-east-1")
        cost = _calculate_dynamodb_cost(10000, 0, 0, pricing)
        assert cost == 0.0

    def test_with_operations_positive_cost(self):
        pricing = _get_pricing("us-east-1")
        cost = _calculate_dynamodb_cost(10000, 2, 2, pricing)
        assert cost > 0


class TestCalculateDataTransferCost:
    """Tests for _calculate_data_transfer_cost function."""

    def test_small_transfer_within_free_tier(self):
        pricing = _get_pricing("us-east-1")
        # 1000 invocations * 3 tasks * 1KB = 3KB, well within 1GB free tier
        cost = _calculate_data_transfer_cost(1000, 3, pricing)
        assert cost == 0.0

    def test_large_transfer_exceeds_free_tier(self):
        pricing = _get_pricing("us-east-1")
        # 100M invocations would exceed free tier
        cost = _calculate_data_transfer_cost(100_000_000, 3, pricing)
        assert cost > 0


class TestCalculateTriggerCost:
    """Tests for _calculate_trigger_cost function."""

    def test_no_triggers_zero_cost(self, simple_workflow: Path):
        definition = load_definition(simple_workflow)
        pricing = _get_pricing("us-east-1")
        cost = _calculate_trigger_cost(definition, 10000, pricing)
        assert cost == 0.0

    def test_sqs_trigger_cost(self, tmp_path: Path):
        wf = tmp_path / "workflow.yaml"
        wf.write_text(
            textwrap.dedent("""\
            rsf_version: "1.0"
            StartAt: Process
            States:
              Process:
                Type: Task
                End: true
            triggers:
              - type: sqs
                queue_name: my-queue
        """)
        )
        definition = load_definition(wf)
        pricing = _get_pricing("us-east-1")
        cost = _calculate_trigger_cost(definition, 1_000_000, pricing)
        assert cost == pytest.approx(0.40, abs=0.01)

    def test_eventbridge_trigger_cost(self, tmp_path: Path):
        wf = tmp_path / "workflow.yaml"
        wf.write_text(
            textwrap.dedent("""\
            rsf_version: "1.0"
            StartAt: Process
            States:
              Process:
                Type: Task
                End: true
            triggers:
              - type: eventbridge
                schedule_expression: "rate(1 minute)"
        """)
        )
        definition = load_definition(wf)
        pricing = _get_pricing("us-east-1")
        cost = _calculate_trigger_cost(definition, 1_000_000, pricing)
        assert cost == pytest.approx(1.00, abs=0.01)


class TestCostCommand:
    """Tests for the main cost CLI command integration."""

    def test_cost_with_valid_workflow(self, simple_workflow: Path, capsys):
        """Cost command with valid workflow prints table output."""
        from rsf.cli.cost_cmd import cost as cost_cmd

        # Use --json for easier assertion
        cost_cmd(workflow=simple_workflow, invocations=10000, region="us-east-1", output_json=True)
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["monthly_invocations"] == 10000
        assert result["tasks_per_execution"] == 3
        assert result["total_monthly_cost"] > 0
        assert len(result["services"]) >= 2  # At least Lambda + Data Transfer

    def test_cost_json_output(self, simple_workflow: Path, capsys):
        """JSON output has correct structure."""
        from rsf.cli.cost_cmd import cost as cost_cmd

        cost_cmd(workflow=simple_workflow, invocations=1000, region="us-east-1", output_json=True)
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert "workflow" in result
        assert "region" in result
        assert "services" in result
        assert "total_monthly_cost" in result

    def test_cost_with_region_override(self, simple_workflow: Path, capsys):
        """Region override affects pricing."""
        from rsf.cli.cost_cmd import cost as cost_cmd

        cost_cmd(workflow=simple_workflow, invocations=10000, region="us-east-1", output_json=True)
        captured_us = capsys.readouterr()
        result_us = json.loads(captured_us.out)

        cost_cmd(workflow=simple_workflow, invocations=10000, region="eu-west-1", output_json=True)
        captured_eu = capsys.readouterr()
        result_eu = json.loads(captured_eu.out)

        assert result_eu["total_monthly_cost"] > result_us["total_monthly_cost"]

    def test_cost_invalid_workflow_exits(self, tmp_path: Path):
        """Invalid workflow file prints error and exits."""
        from click.exceptions import Exit

        from rsf.cli.cost_cmd import cost as cost_cmd

        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("not: a: valid: workflow")
        with pytest.raises((SystemExit, Exit)):
            cost_cmd(workflow=bad_file, invocations=1000, region="us-east-1", output_json=False)

    def test_cost_default_invocations(self, simple_workflow: Path, capsys):
        """Default invocations is 1000."""
        from rsf.cli.cost_cmd import cost as cost_cmd

        cost_cmd(workflow=simple_workflow, invocations=1000, region="us-east-1", output_json=True)
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["monthly_invocations"] == 1000

    def test_cost_total_matches_sum(self, simple_workflow: Path, capsys):
        """Total cost matches sum of individual service costs."""
        from rsf.cli.cost_cmd import cost as cost_cmd

        cost_cmd(workflow=simple_workflow, invocations=10000, region="us-east-1", output_json=True)
        captured = capsys.readouterr()
        result = json.loads(captured.out)

        service_sum = sum(s["monthly_cost"] for s in result["services"])
        assert abs(result["total_monthly_cost"] - service_sum) < 0.001

    def test_cost_services_have_required_fields(self, simple_workflow: Path, capsys):
        """Each service entry has service, monthly_cost, and detail."""
        from rsf.cli.cost_cmd import cost as cost_cmd

        cost_cmd(workflow=simple_workflow, invocations=10000, region="us-east-1", output_json=True)
        captured = capsys.readouterr()
        result = json.loads(captured.out)

        for svc in result["services"]:
            assert "service" in svc
            assert "monthly_cost" in svc
            assert "detail" in svc

    def test_cost_dynamo_workflow_includes_dynamodb(self, dynamo_workflow: Path, capsys):
        """Workflow with DynamoDB tables includes DynamoDB in services."""
        from rsf.cli.cost_cmd import cost as cost_cmd

        cost_cmd(workflow=dynamo_workflow, invocations=10000, region="us-east-1", output_json=True)
        captured = capsys.readouterr()
        result = json.loads(captured.out)

        service_names = [s["service"] for s in result["services"]]
        assert "DynamoDB" in service_names
