"""RSF CLI import subcommand — converts ASL JSON to RSF YAML with handler stubs."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()


def import_asl(
    asl_file: Path = typer.Argument(..., help="Path to ASL JSON file"),
    output: Path = typer.Option("workflow.yaml", "--output", "-o", help="Output YAML file path"),
    handlers_dir: Path = typer.Option("handlers", "--handlers", help="Handler stubs output directory"),
) -> None:
    """Convert an ASL JSON state machine definition to RSF YAML format.

    Generates a workflow.yaml and handler stubs for Task states found
    in the ASL definition.
    """
    from rsf.importer.converter import import_asl as _import_asl

    # Check source file exists
    if not asl_file.exists():
        console.print(f"[red]Error:[/red] ASL file not found: {asl_file}")
        raise typer.Exit(code=1)

    # Warn if output already exists (overwrite is intentional)
    if output.exists():
        console.print(f"[yellow]Warning:[/yellow] Output file already exists and will be overwritten: {output}")

    try:
        result = _import_asl(
            source=asl_file,
            output_path=output,
            handlers_dir=handlers_dir,
        )
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    # Print any conversion warnings
    for warning in result.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning.message}")

    # Print success summary
    stub_count = len(result.task_state_names)
    console.print(f"[green]Success:[/green] Converted ASL to {output}")
    if stub_count > 0:
        console.print(f"  Handler stubs: {stub_count} created in {handlers_dir}/")
        for name in result.task_state_names:
            console.print(f"    - {name}")
    else:
        console.print("  No Task states found — no handler stubs created.")
