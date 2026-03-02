"""RSF cost subcommand — estimate monthly AWS costs from workflow structure."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from rsf.dsl.parser import load_definition
from rsf.dsl.models import StateMachineDefinition

console = Console()

# Default pricing (us-east-1, on-demand)
DEFAULT_PRICING: dict[str, float] = {
    "lambda_request_per_million": 0.20,
    "lambda_gb_second": 0.0000166667,
    "lambda_default_memory_mb": 128,
    "lambda_default_duration_ms": 200,
    "dynamodb_write_per_million": 1.25,
    "dynamodb_read_per_million": 0.25,
    "dynamodb_reads_per_invocation": 2,
    "dynamodb_writes_per_invocation": 2,
    "data_transfer_per_gb": 0.09,
    "data_transfer_free_gb": 1.0,
    "estimated_payload_kb": 1,
    "sqs_per_million": 0.40,
    "sns_per_million": 0.50,
    "eventbridge_per_million": 1.00,
    "map_default_items": 10,
}

# Regional pricing multipliers relative to us-east-1
REGION_MULTIPLIERS: dict[str, float] = {
    "us-east-1": 1.0,
    "us-east-2": 1.0,
    "us-west-1": 1.0,
    "us-west-2": 1.0,
    "eu-west-1": 1.10,
    "eu-west-2": 1.10,
    "eu-central-1": 1.15,
    "ap-southeast-1": 1.10,
    "ap-northeast-1": 1.15,
}


def _get_pricing(region: str) -> dict[str, float]:
    """Return pricing dict adjusted for the given AWS region.

    Unknown regions use the same pricing as us-east-1 (multiplier 1.0).
    """
    multiplier = REGION_MULTIPLIERS.get(region, 1.0)
    pricing = dict(DEFAULT_PRICING)
    # Apply multiplier to cost fields only, not counts/sizes
    cost_fields = [
        "lambda_request_per_million",
        "lambda_gb_second",
        "dynamodb_write_per_million",
        "dynamodb_read_per_million",
        "data_transfer_per_gb",
        "sqs_per_million",
        "sns_per_million",
        "eventbridge_per_million",
    ]
    for field in cost_fields:
        pricing[field] = DEFAULT_PRICING[field] * multiplier
    return pricing


def _count_states_recursive(states: dict[str, Any]) -> dict[str, int]:
    """Count state types in a state machine, recursing into Parallel/Map branches.

    Returns a dict mapping state types to counts, plus special keys:
    - 'task_count': number of Task states (Lambda invocations per execution)
    - 'parallel_branches': total branches in Parallel states
    - 'map_states': number of Map states
    """
    counts: dict[str, int] = {
        "task_count": 0,
        "parallel_branches": 0,
        "map_states": 0,
        "total_states": 0,
    }

    for _name, state in states.items():
        if not isinstance(state, dict):
            # Pydantic model — get type from attribute
            state_type = getattr(state, "type", None)
            state_dict: dict[str, Any] = {}
            if hasattr(state, "model_dump"):
                state_dict = state.model_dump(by_alias=True)
            else:
                state_dict = {}
        else:
            state_type = state.get("Type")
            state_dict = state

        counts["total_states"] += 1

        if state_type == "Task":
            counts["task_count"] += 1

        elif state_type == "Parallel":
            branches = getattr(state, "branches", None) or state_dict.get("Branches", [])
            counts["parallel_branches"] += len(branches) if branches else 0
            for branch in branches or []:
                if hasattr(branch, "states"):
                    branch_states = branch.states
                else:
                    branch_states = branch.get("States", {})
                sub_counts = _count_states_recursive(branch_states)
                counts["task_count"] += sub_counts["task_count"]
                counts["parallel_branches"] += sub_counts["parallel_branches"]
                counts["map_states"] += sub_counts["map_states"]

        elif state_type == "Map":
            counts["map_states"] += 1
            item_processor = getattr(state, "item_processor", None) or state_dict.get("ItemProcessor")
            if item_processor:
                if hasattr(item_processor, "states"):
                    proc_states = item_processor.states
                else:
                    proc_states = item_processor.get("States", {})
                sub_counts = _count_states_recursive(proc_states)
                counts["task_count"] += sub_counts["task_count"]
                counts["parallel_branches"] += sub_counts["parallel_branches"]
                counts["map_states"] += sub_counts["map_states"]

    return counts


def _count_lambda_invocations(definition: StateMachineDefinition, pricing: dict[str, float]) -> int:
    """Count the expected Lambda invocations per workflow execution.

    Walks the state machine counting Task states. For Map states,
    multiplies by the default item count assumption.
    """
    counts = _count_states_recursive(definition.states)
    task_count = counts["task_count"]
    map_states = counts["map_states"]

    # Each map state multiplies its tasks by the default item count
    map_multiplier = int(pricing.get("map_default_items", 10))
    if map_states > 0:
        task_count += map_states * (map_multiplier - 1)

    return max(task_count, 1)


def _count_dynamodb_operations(
    definition: StateMachineDefinition, pricing: dict[str, float]
) -> tuple[int, int]:
    """Count estimated DynamoDB reads and writes per invocation.

    Returns (reads_per_invocation, writes_per_invocation).
    If no DynamoDB tables are defined, returns (0, 0).
    """
    tables = definition.dynamodb_tables
    if not tables:
        return (0, 0)

    reads = int(pricing.get("dynamodb_reads_per_invocation", 2)) * len(tables)
    writes = int(pricing.get("dynamodb_writes_per_invocation", 2)) * len(tables)
    return (reads, writes)


def _calculate_lambda_cost(
    invocations: int, tasks_per_execution: int, pricing: dict[str, float]
) -> float:
    """Calculate monthly Lambda cost.

    Includes request cost and compute cost (GB-seconds).
    """
    total_requests = invocations * tasks_per_execution

    # Request cost
    request_cost = (total_requests / 1_000_000) * pricing["lambda_request_per_million"]

    # Compute cost (GB-seconds)
    memory_gb = pricing["lambda_default_memory_mb"] / 1024
    duration_sec = pricing["lambda_default_duration_ms"] / 1000
    gb_seconds = total_requests * memory_gb * duration_sec
    compute_cost = gb_seconds * pricing["lambda_gb_second"]

    return request_cost + compute_cost


def _calculate_dynamodb_cost(
    invocations: int,
    reads_per: int,
    writes_per: int,
    pricing: dict[str, float],
) -> float:
    """Calculate monthly DynamoDB cost for on-demand mode."""
    if reads_per == 0 and writes_per == 0:
        return 0.0

    total_reads = invocations * reads_per
    total_writes = invocations * writes_per

    read_cost = (total_reads / 1_000_000) * pricing["dynamodb_read_per_million"]
    write_cost = (total_writes / 1_000_000) * pricing["dynamodb_write_per_million"]

    return read_cost + write_cost


def _calculate_data_transfer_cost(
    invocations: int, tasks_per_execution: int, pricing: dict[str, float]
) -> float:
    """Calculate monthly data transfer cost estimate."""
    total_requests = invocations * tasks_per_execution
    payload_kb = pricing["estimated_payload_kb"]
    total_gb = (total_requests * payload_kb) / (1024 * 1024)

    # Subtract free tier
    billable_gb = max(0, total_gb - pricing["data_transfer_free_gb"])
    return billable_gb * pricing["data_transfer_per_gb"]


def _calculate_trigger_cost(
    definition: StateMachineDefinition, invocations: int, pricing: dict[str, float]
) -> float:
    """Calculate monthly trigger cost based on configured event sources."""
    triggers = definition.triggers
    if not triggers:
        return 0.0

    total = 0.0
    for trigger in triggers:
        trigger_type = getattr(trigger, "type", None)
        if trigger_type == "sqs":
            total += (invocations / 1_000_000) * pricing["sqs_per_million"]
        elif trigger_type == "sns":
            total += (invocations / 1_000_000) * pricing["sns_per_million"]
        elif trigger_type == "eventbridge":
            total += (invocations / 1_000_000) * pricing["eventbridge_per_million"]

    return total


def cost(
    workflow: Path = typer.Argument("workflow.yaml", help="Path to workflow YAML file"),
    invocations: int = typer.Option(
        1000, "--invocations", "-n", help="Expected monthly invocations"
    ),
    region: str = typer.Option(
        "us-east-1", "--region", help="AWS region for pricing"
    ),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Estimate monthly AWS costs for a workflow based on structure and invocation count.

    Analyzes the workflow YAML to count Lambda functions, DynamoDB tables,
    parallel branches, and map iterations, then calculates estimated costs.
    No deployment required — purely static analysis.
    """
    try:
        definition = load_definition(workflow)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to load workflow: {e}")
        raise typer.Exit(code=1)

    pricing = _get_pricing(region)

    # Calculate costs
    tasks_per_exec = _count_lambda_invocations(definition, pricing)
    reads_per, writes_per = _count_dynamodb_operations(definition, pricing)

    lambda_cost = _calculate_lambda_cost(invocations, tasks_per_exec, pricing)
    dynamodb_cost = _calculate_dynamodb_cost(invocations, reads_per, writes_per, pricing)
    transfer_cost = _calculate_data_transfer_cost(invocations, tasks_per_exec, pricing)
    trigger_cost = _calculate_trigger_cost(definition, invocations, pricing)

    total = lambda_cost + dynamodb_cost + transfer_cost + trigger_cost

    # Build cost breakdown
    services: list[dict[str, Any]] = []
    services.append(
        {
            "service": "Lambda",
            "monthly_cost": round(lambda_cost, 4),
            "detail": f"{invocations:,} invocations x {tasks_per_exec} tasks/exec",
        }
    )
    if reads_per > 0 or writes_per > 0:
        services.append(
            {
                "service": "DynamoDB",
                "monthly_cost": round(dynamodb_cost, 4),
                "detail": f"{reads_per} reads + {writes_per} writes per invocation",
            }
        )
    services.append(
        {
            "service": "Data Transfer",
            "monthly_cost": round(transfer_cost, 4),
            "detail": f"~{pricing['estimated_payload_kb']:.0f}KB per task invocation",
        }
    )
    if trigger_cost > 0:
        services.append(
            {
                "service": "Triggers",
                "monthly_cost": round(trigger_cost, 4),
                "detail": "Event source trigger costs",
            }
        )

    if output_json:
        result = {
            "workflow": str(workflow),
            "region": region,
            "monthly_invocations": invocations,
            "tasks_per_execution": tasks_per_exec,
            "services": services,
            "total_monthly_cost": round(total, 4),
        }
        typer.echo(json.dumps(result, indent=2))
        return

    # Rich table output
    console.print()
    console.print(f"[bold]Cost Estimate:[/bold] {workflow}")
    console.print(f"Region: {region} | Monthly invocations: {invocations:,}")
    console.print(f"Tasks per execution: {tasks_per_exec}")
    console.print()

    table = Table(title="Monthly Cost Breakdown")
    table.add_column("Service", style="bold")
    table.add_column("Monthly Cost", justify="right")
    table.add_column("Detail", style="dim")

    for svc in services:
        table.add_row(
            svc["service"],
            f"${svc['monthly_cost']:.4f}",
            svc["detail"],
        )
    table.add_row("", "", "")
    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]${total:.4f}[/bold]",
        "estimated monthly",
    )

    console.print(table)
    console.print()
