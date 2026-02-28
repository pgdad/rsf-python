"""RSF deploy subcommand — generates Terraform and deploys to AWS."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.status import Status

from rsf.codegen.generator import generate as codegen_generate
from rsf.dsl.parser import load_definition
from rsf.terraform.generator import TerraformConfig, generate_terraform

console = Console()


def deploy(
    workflow: Path = typer.Argument("workflow.yaml", help="Path to workflow YAML file"),
    code_only: bool = typer.Option(False, "--code-only", help="Re-package and update Lambda code only"),
    auto_approve: bool = typer.Option(False, "--auto-approve", "-y", help="Skip Terraform confirmation prompt"),
    tf_dir: Path = typer.Option("terraform", "--tf-dir", help="Terraform output directory"),
) -> None:
    """Deploy an RSF workflow to AWS via Terraform.

    Generates Terraform files, then runs terraform init and terraform apply.
    Use --code-only to re-package Lambda code without a full Terraform apply.
    """
    # Step 1: Check workflow file exists
    if not workflow.exists():
        console.print(
            f"[red]Error:[/red] Workflow file not found: [bold]{workflow}[/bold]\n"
            "Create one with [bold]rsf init <project>[/bold] or specify a path."
        )
        raise typer.Exit(code=1)

    # Step 2: Load and validate the workflow
    with Status("[bold]Loading workflow...[/bold]", console=console):
        try:
            definition = load_definition(workflow)
        except (ValueError, ValidationError) as exc:
            console.print(f"[red]Error:[/red] Invalid workflow: {exc}")
            raise typer.Exit(code=1)
        except Exception as exc:
            console.print(f"[red]Error:[/red] Failed to load workflow: {exc}")
            raise typer.Exit(code=1)

    # Step 3: Generate orchestrator + handlers via codegen
    with Status("[bold]Generating code...[/bold]", console=console):
        codegen_result = codegen_generate(
            definition=definition,
            dsl_path=workflow,
            output_dir=workflow.parent,
        )

    console.print(
        f"[green]Code generated:[/green] {codegen_result.orchestrator_path.name} "
        f"+ {len(codegen_result.handler_paths)} handler(s) "
        f"({len(codegen_result.skipped_handlers)} skipped)"
    )

    # Step 4: Derive workflow name
    workflow_name = definition.comment if definition.comment else workflow.stem.replace("_", "-").replace(" ", "-")

    if code_only:
        _deploy_code_only(definition, workflow, workflow_name, tf_dir)
    else:
        _deploy_full(definition, workflow, workflow_name, tf_dir, auto_approve)


def _deploy_full(
    definition: object,
    workflow: Path,
    workflow_name: str,
    tf_dir: Path,
    auto_approve: bool,
) -> None:
    """Run the full Terraform deploy pipeline."""
    # Step 5: Generate Terraform files
    with Status("[bold]Generating Terraform files...[/bold]", console=console):
        tf_result = generate_terraform(
            config=TerraformConfig(workflow_name=workflow_name),
            output_dir=tf_dir,
        )

    console.print(
        f"[green]Terraform generated:[/green] {len(tf_result.generated_files)} file(s) "
        f"in [bold]{tf_dir}[/bold] ({len(tf_result.skipped_files)} skipped)"
    )

    # Step 6: Check terraform binary
    if not shutil.which("terraform"):
        console.print("[red]Error:[/red] terraform binary not found. Install from https://terraform.io")
        raise typer.Exit(code=1)

    # Step 7: terraform init
    console.print("\n[bold]Running terraform init...[/bold]")
    try:
        subprocess.run(
            ["terraform", "init"],
            cwd=tf_dir,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Error:[/red] terraform init failed (exit {exc.returncode})")
        raise typer.Exit(code=1)

    # Step 8 + 9: terraform apply
    apply_cmd = ["terraform", "apply"]
    if auto_approve:
        apply_cmd.append("-auto-approve")

    console.print("\n[bold]Running terraform apply...[/bold]")
    try:
        subprocess.run(apply_cmd, cwd=tf_dir, check=True)
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Error:[/red] terraform apply failed (exit {exc.returncode})")
        raise typer.Exit(code=1)

    # Step 11: Success
    console.print("\n[green]Deploy complete[/green]")


def _deploy_code_only(
    definition: object,
    workflow: Path,
    workflow_name: str,
    tf_dir: Path,
) -> None:
    """Re-package Lambda code and update it via targeted Terraform apply."""
    # Step 4 (code-only): Check terraform binary
    if not shutil.which("terraform"):
        console.print("[red]Error:[/red] terraform binary not found. Install from https://terraform.io")
        raise typer.Exit(code=1)

    # Step 5 (code-only): Check tf_dir has terraform state
    if not tf_dir.exists():
        console.print(
            f"[red]Error:[/red] Terraform directory not found: [bold]{tf_dir}[/bold]\n"
            "Run [bold]rsf deploy[/bold] first to initialise the infrastructure."
        )
        raise typer.Exit(code=1)

    # Step 5 (code-only): Run targeted terraform apply for Lambda only
    console.print("\n[bold]Running targeted terraform apply (Lambda code update)...[/bold]")
    try:
        subprocess.run(
            [
                "terraform",
                "apply",
                "-target=aws_lambda_function.*",
                "-auto-approve",
            ],
            cwd=tf_dir,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Error:[/red] terraform apply --code-only failed (exit {exc.returncode})")
        raise typer.Exit(code=1)

    console.print("\n[green]Code update complete[/green]")
