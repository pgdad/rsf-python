"""rsf validate subcommand — validates a workflow YAML without generating code."""

from __future__ import annotations

from pathlib import Path

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console

from rsf.config import load_project_config
from rsf.dsl import parser as dsl_parser
from rsf.dsl.validator import validate_definition
from rsf.providers import ProviderNotFoundError, get_provider, list_providers

console = Console()


def validate(
    workflow: Path = typer.Argument("workflow.yaml", help="Path to workflow YAML file"),
) -> None:
    """Validate a workflow YAML file without generating any code.

    Checks structural (Pydantic), semantic (cross-state reference), and
    infrastructure configuration constraints. Prints field-path-specific
    errors on failure.
    """
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

    # 5. Infrastructure config validation (workflow YAML)
    if definition.infrastructure is not None:
        try:
            get_provider(definition.infrastructure.provider)
        except ProviderNotFoundError:
            available = list_providers()
            console.print(f"[red]Validation errors in[/red] {workflow}:")
            console.print(
                f"  [yellow]infrastructure.provider[/yellow]: "
                f"Unknown provider '{definition.infrastructure.provider}'. "
                f"Available: {available}"
            )
            raise typer.Exit(code=1)

    # 6. Infrastructure config validation (rsf.toml)
    try:
        toml_config = load_project_config(workflow.parent)
        if toml_config is not None:
            try:
                get_provider(toml_config.provider)
            except ProviderNotFoundError:
                available = list_providers()
                console.print("[red]Validation errors in[/red] rsf.toml:")
                console.print(
                    f"  [yellow]infrastructure.provider[/yellow]: "
                    f"Unknown provider '{toml_config.provider}'. "
                    f"Available: {available}"
                )
                raise typer.Exit(code=1)
    except ValidationError as exc:
        console.print("[red]Validation errors in[/red] rsf.toml:")
        for error in exc.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            console.print(f"  [yellow]infrastructure.{field_path}[/yellow]: {error['msg']}")
        raise typer.Exit(code=1)

    # 7. All checks passed
    console.print(f"[green]Valid:[/green] {workflow}")
