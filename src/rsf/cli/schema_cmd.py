"""RSF CLI schema export command."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from rsf.schema.generate import generate_json_schema, write_json_schema

console = Console()


def schema_export(
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: rsf-workflow.json in current directory)",
    ),
    stdout: bool = typer.Option(
        False,
        "--stdout",
        help="Print schema to stdout instead of writing to a file",
    ),
) -> None:
    """Export the RSF workflow JSON Schema.

    Generates the full JSON Schema for workflow.yaml definitions
    covering all DSL fields. Use --stdout to pipe to other tools.
    """
    if stdout:
        schema = generate_json_schema()
        sys.stdout.write(json.dumps(schema, indent=2) + "\n")
        return

    out_path = output or Path("rsf-workflow.json")
    written = write_json_schema(out_path)
    console.print(f"[green]Schema written to:[/green] {written}")
