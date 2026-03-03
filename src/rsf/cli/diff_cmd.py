"""RSF diff subcommand — compare local workflow with deployed state."""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from rsf.config import resolve_infra_config
from rsf.dsl.models import StateMachineDefinition, TaskState
from rsf.dsl.parser import load_definition

console = Console()


@dataclass
class DiffEntry:
    """A single difference between local and deployed workflow."""

    component: str  # "State", "Transition", "Handler", "Config"
    name: str  # State name or config field
    change: str  # "added", "removed", "changed"
    local: str  # Local value description
    deployed: str  # Deployed value description


def compute_diff(
    local_def: StateMachineDefinition,
    deployed_def: StateMachineDefinition | None,
) -> list[DiffEntry]:
    """Compare two workflow definitions and return a list of differences."""
    diffs: list[DiffEntry] = []

    if deployed_def is None:
        # Everything is new
        for name, state in local_def.states.items():
            state_type = getattr(state, "type", "Unknown")
            diffs.append(
                DiffEntry(
                    component="State",
                    name=name,
                    change="added",
                    local=state_type,
                    deployed="\u2014",
                )
            )
            if isinstance(state, TaskState):
                diffs.append(
                    DiffEntry(
                        component="Handler",
                        name=name,
                        change="added",
                        local="handler function",
                        deployed="\u2014",
                    )
                )
        return diffs

    # Compare StartAt
    if local_def.start_at != deployed_def.start_at:
        diffs.append(
            DiffEntry(
                component="Config",
                name="StartAt",
                change="changed",
                local=local_def.start_at,
                deployed=deployed_def.start_at,
            )
        )

    # Compare TimeoutSeconds
    if local_def.timeout_seconds != deployed_def.timeout_seconds:
        diffs.append(
            DiffEntry(
                component="Config",
                name="TimeoutSeconds",
                change="changed",
                local=str(local_def.timeout_seconds or "none"),
                deployed=str(deployed_def.timeout_seconds or "none"),
            )
        )

    # Compare states
    local_names = set(local_def.states.keys())
    deployed_names = set(deployed_def.states.keys())

    # Added states
    for name in sorted(local_names - deployed_names):
        state = local_def.states[name]
        state_type = getattr(state, "type", "Unknown")
        diffs.append(
            DiffEntry(
                component="State",
                name=name,
                change="added",
                local=state_type,
                deployed="\u2014",
            )
        )
        if isinstance(state, TaskState):
            diffs.append(
                DiffEntry(
                    component="Handler",
                    name=name,
                    change="added",
                    local="handler function",
                    deployed="\u2014",
                )
            )

    # Removed states
    for name in sorted(deployed_names - local_names):
        state = deployed_def.states[name]
        state_type = getattr(state, "type", "Unknown")
        diffs.append(
            DiffEntry(
                component="State",
                name=name,
                change="removed",
                local="\u2014",
                deployed=state_type,
            )
        )
        if isinstance(state, TaskState):
            diffs.append(
                DiffEntry(
                    component="Handler",
                    name=name,
                    change="removed",
                    local="\u2014",
                    deployed="handler function",
                )
            )

    # Changed states (present in both)
    for name in sorted(local_names & deployed_names):
        local_state = local_def.states[name]
        deployed_state = deployed_def.states[name]

        local_type = getattr(local_state, "type", "Unknown")
        deployed_type = getattr(deployed_state, "type", "Unknown")

        if local_type != deployed_type:
            diffs.append(
                DiffEntry(
                    component="State",
                    name=name,
                    change="changed",
                    local=f"Type: {local_type}",
                    deployed=f"Type: {deployed_type}",
                )
            )

        # Compare transitions (Next field)
        local_next = getattr(local_state, "next", None)
        deployed_next = getattr(deployed_state, "next", None)
        if local_next != deployed_next:
            diffs.append(
                DiffEntry(
                    component="Transition",
                    name=name,
                    change="changed",
                    local=f"Next: {local_next or 'End'}",
                    deployed=f"Next: {deployed_next or 'End'}",
                )
            )

        # Compare End field
        local_end = getattr(local_state, "end", None)
        deployed_end = getattr(deployed_state, "end", None)
        if local_end != deployed_end:
            diffs.append(
                DiffEntry(
                    component="Transition",
                    name=name,
                    change="changed",
                    local=f"End: {local_end}",
                    deployed=f"End: {deployed_end}",
                )
            )

    return diffs


def _load_deployed_definition(
    tf_dir: Path,
) -> StateMachineDefinition | None:
    """Load the deployed workflow definition from the Terraform directory.

    Looks for a workflow.yaml in the terraform directory that was used
    during the last deploy. Returns None if not found.
    """
    # Look for workflow.yaml alongside terraform files
    for candidate in [
        tf_dir / "workflow.yaml",
        tf_dir / "workflow.yml",
        tf_dir.parent / "workflow.yaml",
        tf_dir.parent / "workflow.yml",
    ]:
        if candidate.exists():
            try:
                return load_definition(candidate)
            except Exception:
                continue

    # Check if terraform state exists at all
    if not (tf_dir / "terraform.tfstate").exists():
        return None

    # Try to extract from terraform state file
    try:
        state_data = json.loads((tf_dir / "terraform.tfstate").read_text())
        # Look through resources for any that contain workflow definition data
        for resource in state_data.get("resources", []):
            if resource.get("type") == "aws_lambda_function":
                # Lambda exists but we can't extract workflow definition from it
                return None
    except Exception:
        pass

    return None


def _render_table(diffs: list[DiffEntry]) -> Table:
    """Render diff entries as a Rich table with color coding."""
    table = Table(title="Workflow Diff", show_lines=True)
    table.add_column("Component", style="bold")
    table.add_column("Name")
    table.add_column("Change")
    table.add_column("Local")
    table.add_column("Deployed")

    for entry in diffs:
        if entry.change == "added":
            style = "green"
        elif entry.change == "removed":
            style = "red"
        else:
            style = "yellow"

        table.add_row(
            entry.component,
            entry.name,
            f"[{style}]{entry.change}[/{style}]",
            entry.local,
            entry.deployed,
            style=style,
        )

    return table


def _render_raw_diff(local_path: Path, deployed_path: Path | None) -> str:
    """Render a raw YAML diff between local and deployed definitions."""
    local_text = local_path.read_text(encoding="utf-8")

    if deployed_path is None or not deployed_path.exists():
        # Show everything as additions
        lines = local_text.splitlines()
        return "\n".join(f"+ {line}" for line in lines)

    deployed_text = deployed_path.read_text(encoding="utf-8")

    diff_lines = difflib.unified_diff(
        deployed_text.splitlines(),
        local_text.splitlines(),
        fromfile="deployed",
        tofile="local",
        lineterm="",
    )
    return "\n".join(diff_lines)


def diff(
    workflow: Path = typer.Argument("workflow.yaml", help="Path to workflow YAML file"),
    tf_dir: Path = typer.Option("terraform", "--tf-dir", help="Terraform output directory"),
    stage: str | None = typer.Option(None, "--stage", help="Deployment stage to diff against"),
    raw: bool = typer.Option(False, "--raw", help="Show full YAML diff instead of semantic table"),
) -> None:
    """Compare local workflow with deployed state.

    Shows a structured diff of states, transitions, and handler signatures.
    Exit code 1 if differences exist (like git diff --exit-code).
    """
    # Check workflow file exists
    if not workflow.exists():
        console.print(f"[red]Error:[/red] Workflow file not found: [bold]{workflow}[/bold]")
        raise typer.Exit(code=1)

    # Stage handling: adjust tf_dir
    effective_tf_dir = tf_dir
    if stage:
        effective_tf_dir = tf_dir / stage

    # Load local definition
    try:
        local_def = load_definition(workflow)
    except Exception as exc:
        console.print(f"[red]Error:[/red] Invalid local workflow: {exc}")
        raise typer.Exit(code=1)

    # Detect configured provider
    try:
        infra_config = resolve_infra_config(local_def, workflow.parent)
        provider_name = infra_config.provider
    except Exception:
        provider_name = "terraform"

    # Diff only works with Terraform state -- gracefully decline for other providers
    if provider_name != "terraform":
        console.print(
            f"[yellow]Diff is not available for the {provider_name} provider.[/yellow]\n"
            f"The diff command compares local workflow definitions against Terraform state.\n"
            f"Your active provider ({provider_name}) does not use Terraform state."
        )
        raise typer.Exit(code=0)

    # Raw diff mode
    if raw:
        deployed_path = None
        for candidate in [
            effective_tf_dir / "workflow.yaml",
            effective_tf_dir / "workflow.yml",
            effective_tf_dir.parent / "workflow.yaml",
            effective_tf_dir.parent / "workflow.yml",
        ]:
            if candidate.exists():
                deployed_path = candidate
                break

        raw_output = _render_raw_diff(workflow, deployed_path)
        if not raw_output.strip():
            console.print("[green]No differences found.[/green]")
            raise typer.Exit(code=0)
        console.print(raw_output)
        raise typer.Exit(code=1)

    # Load deployed definition
    deployed_def = _load_deployed_definition(effective_tf_dir)

    # Compute diff
    diffs = compute_diff(local_def, deployed_def)

    if not diffs:
        console.print("[green]No differences found.[/green]")
        raise typer.Exit(code=0)

    # Display results
    if deployed_def is None:
        console.print("[yellow]No deployed state found \u2014 showing all as new[/yellow]\n")

    table = _render_table(diffs)
    console.print(table)

    console.print(f"\n[bold]{len(diffs)}[/bold] difference(s) found.")
    raise typer.Exit(code=1)
