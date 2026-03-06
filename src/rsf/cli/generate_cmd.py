"""rsf generate subcommand — validates and generates orchestrator + handler stubs."""

from __future__ import annotations

from pathlib import Path

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console

from rsf import __version__
from rsf.codegen.generator import generate as codegen_generate
from rsf.dsl import parser as dsl_parser
from rsf.dsl.validator import validate_definition

console = Console()


def generate(
    workflow: Path = typer.Argument("workflow.yaml", help="Path to workflow YAML file"),
    output_dir: Path = typer.Option(
        "src/generated",
        "--output",
        "-o",
        help="Output directory for orchestrator.py",
    ),
    handlers_dir_opt: Path = typer.Option(
        None,
        "--handlers-dir",
        help="Output directory for handler stubs (default: src/handlers or OUTPUT/handlers)",
    ),
    no_infra: bool = typer.Option(
        False,
        "--no-infra",
        help="Generate code only, skip infrastructure files",
    ),
) -> None:
    """Generate orchestrator.py and handler stubs from a workflow YAML.

    Validates the workflow first (structural + semantic).  On success, writes
    orchestrator.py to OUTPUT_DIR and handler stubs to HANDLERS_DIR.
    Existing handler stubs without the generated marker are preserved
    (Generation Gap pattern).
    """
    if no_infra:
        console.print("[dim]--no-infra: infrastructure generation skipped[/dim]")
    # 1. File existence check
    if not workflow.exists():
        console.print(f"[red]Error:[/red] File not found: {workflow}")
        raise typer.Exit(code=1)

    # 2. YAML parse check
    try:
        data = dsl_parser.load_yaml(workflow)
    except yaml.YAMLError as exc:
        console.print(f"[red]Error:[/red] Invalid YAML in {workflow}: {exc}")
        raise typer.Exit(code=1)

    if not isinstance(data, dict):
        console.print(f"[red]Error:[/red] Workflow file must be a YAML mapping, got: {type(data).__name__}")
        raise typer.Exit(code=1)

    # 3. Pydantic structural validation
    try:
        definition = dsl_parser.parse_definition(data)
    except ValidationError as exc:
        console.print(f"[red]Validation errors in[/red] {workflow}:")
        for error in exc.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            console.print(f"  [yellow]{field_path}[/yellow]: {error['msg']}")
        raise typer.Exit(code=1)

    # 4. Semantic validation
    errors = validate_definition(definition)
    if errors:
        console.print(f"[red]Semantic errors in[/red] {workflow}:")
        for error in errors:
            if error.path:
                console.print(f"  [yellow]{error.path}[/yellow]: {error.message}")
            else:
                console.print(f"  {error.message}")
        raise typer.Exit(code=1)

    # 5. Generate code
    output_dir.mkdir(parents=True, exist_ok=True)
    # Default handlers_dir: sibling of output_dir (src/handlers when output is src/generated)
    handlers_dir = handlers_dir_opt or output_dir.parent / "handlers"
    handlers_dir.mkdir(parents=True, exist_ok=True)
    result = codegen_generate(
        definition=definition,
        dsl_path=workflow,
        output_dir=output_dir,
        handlers_dir=handlers_dir,
        rsf_version=__version__,
    )

    # 6. Print summary
    console.print(f"[green]Generated:[/green] {result.orchestrator_path}")

    for handler_path in result.handler_paths:
        console.print(f"  [green]Created:[/green] {handler_path}")

    for skipped_path in result.skipped_handlers:
        console.print(f"  [yellow]Skipped:[/yellow] {skipped_path} (already exists, not overwritten)")

    total_handlers = len(result.handler_paths)
    total_skipped = len(result.skipped_handlers)
    console.print(
        f"\n[bold]Summary:[/bold] orchestrator written, {total_handlers} handler(s) created, {total_skipped} skipped."
    )
