"""RSF deploy subcommand -- generates infrastructure and deploys to AWS.

Routes deployment through the pluggable provider interface. The default
provider is Terraform, with zero-config backward compatibility for v2.0
workflows that have no ``infrastructure:`` block.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.status import Status

from rsf.codegen.generator import generate as codegen_generate
from rsf.config import resolve_infra_config
from rsf.dsl.parser import load_definition
from rsf.providers import ProviderNotFoundError, get_provider
from rsf.providers.base import ProviderContext
from rsf.providers.metadata import create_metadata, derive_workflow_name

console = Console()


def deploy(
    workflow: Path = typer.Argument("workflow.yaml", help="Path to workflow YAML file"),
    code_only: bool = typer.Option(False, "--code-only", help="Re-package and update Lambda code only"),
    auto_approve: bool = typer.Option(False, "--auto-approve", "-y", help="Skip confirmation prompt"),
    output_dir: Path = typer.Option("terraform", "--output-dir", help="Infrastructure output directory"),
    tf_dir: Path = typer.Option(None, "--tf-dir", hidden=True, help="[deprecated] Alias for --output-dir"),
    no_infra: bool = typer.Option(False, "--no-infra", help="Generate and deploy code only, skip infrastructure"),
    stage: str | None = typer.Option(None, "--stage", help="Deployment stage (e.g., dev, staging, prod)"),
    teardown: bool = typer.Option(False, "--teardown", help="Destroy all deployed infrastructure (runs provider teardown)"),
) -> None:
    """Deploy an RSF workflow to AWS via the configured infrastructure provider.

    Generates infrastructure files, then deploys. Default provider is Terraform.
    Use --code-only to re-package Lambda code without a full infrastructure deploy.
    Use --no-infra to skip infrastructure generation entirely.
    Use --stage to deploy to a named stage with stage-specific variable overrides.
    Use --teardown to destroy all deployed infrastructure.
    """
    # Handle --tf-dir alias (deprecated, hidden)
    if tf_dir is not None:
        output_dir = tf_dir

    # Check mutual exclusion: --teardown with --code-only or --no-infra
    if teardown and (code_only or no_infra):
        console.print("[red]Error:[/red] --teardown is mutually exclusive with --code-only and --no-infra")
        raise typer.Exit(code=1)

    # Check mutual exclusion: --no-infra and --code-only
    if no_infra and code_only:
        console.print("[red]Error:[/red] --no-infra and --code-only are mutually exclusive")
        raise typer.Exit(code=1)

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
    # Output into src/generated/ to match Terraform template's archive_file source_dir
    codegen_output = workflow.parent / "src" / "generated"
    codegen_output.mkdir(parents=True, exist_ok=True)
    with Status("[bold]Generating code...[/bold]", console=console):
        codegen_result = codegen_generate(
            definition=definition,
            dsl_path=workflow,
            output_dir=codegen_output,
            handlers_dir=workflow.parent / "src" / "handlers",
        )

    console.print(
        f"[green]Code generated:[/green] {codegen_result.orchestrator_path.name} "
        f"+ {len(codegen_result.handler_paths)} handler(s) "
        f"({len(codegen_result.skipped_handlers)} skipped)"
    )

    # --no-infra: skip all infrastructure steps, return after code generation
    if no_infra:
        console.print("[green]Code generated (infrastructure skipped).[/green]")
        return

    # Step 4: Resolve infrastructure config (YAML > rsf.toml > default)
    infra_config = resolve_infra_config(definition, workflow.parent)

    # Step 5: Get provider
    try:
        provider = get_provider(infra_config.provider)
    except ProviderNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    # Step 6: Check --code-only constraint (Terraform-specific)
    if code_only and infra_config.provider != "terraform":
        console.print(
            "[red]Error:[/red] --code-only is only supported with the terraform provider"
        )
        raise typer.Exit(code=1)

    # Step 7: Derive workflow name
    workflow_name = derive_workflow_name(definition, workflow)

    # Stage handling: isolate output_dir and resolve stage variable file
    stage_var_file: Path | None = None
    if stage:
        output_dir = output_dir / stage  # e.g., terraform/prod/
        stage_var_file = workflow.parent / "stages" / f"{stage}.tfvars"
        if not stage_var_file.exists():
            console.print(
                f"[red]Error:[/red] Stage variable file not found: [bold]{stage_var_file}[/bold]\n"
                "Create it with stage-specific overrides. Example:\n"
                '  name_prefix = "rsf-prod"\n'
                "  timeout     = 300\n"
                "  memory_size = 512"
            )
            raise typer.Exit(code=1)

    # Step 8: Ensure resolved infra config is available on definition
    # (rsf.toml config must be accessible via ctx.definition.infrastructure
    # for providers like CustomProvider that read their config from it)
    if definition.infrastructure is None:
        definition.infrastructure = infra_config

    # Step 9: Create metadata and provider context
    metadata = create_metadata(definition, workflow_name, stage=stage)
    ctx = ProviderContext(
        metadata=metadata,
        output_dir=output_dir,
        stage=stage,
        workflow_path=workflow,
        definition=definition,
        auto_approve=auto_approve,
        stage_var_file=stage_var_file,
    )

    # Teardown dispatch (must be after ctx creation, before deploy)
    if teardown:
        _teardown_infra(provider, ctx)
        return

    if code_only:
        _deploy_code_only(ctx)
    else:
        _deploy_full(provider, ctx)


def _deploy_full(provider: object, ctx: ProviderContext) -> None:
    """Run the full provider deploy pipeline: check prerequisites -> generate -> deploy."""
    # Check provider prerequisites (replaces hardcoded terraform binary check)
    prereq_checks = provider.check_prerequisites(ctx)
    failed_checks = [c for c in prereq_checks if c.status == "fail"]
    if failed_checks:
        for check in failed_checks:
            console.print(f"[red]Error:[/red] {check.name}: {check.message}")
        raise typer.Exit(code=1)

    # Generate infrastructure files
    with Status("[bold]Generating infrastructure files...[/bold]", console=console):
        provider.generate(ctx)

    console.print(
        f"[green]Infrastructure generated[/green] in [bold]{ctx.output_dir}[/bold]"
    )

    # Deploy via provider
    console.print("\n[bold]Deploying infrastructure...[/bold]")
    try:
        provider.deploy(ctx)
    except subprocess.CalledProcessError as exc:
        console.print(
            f"[red]Error:[/red] Infrastructure deploy failed (exit {exc.returncode})"
        )
        if exc.stderr:
            console.print(f"[dim]{exc.stderr.strip()}[/dim]")
        if exc.stdout:
            console.print(f"[dim]{exc.stdout.strip()}[/dim]")
        raise typer.Exit(code=1)

    console.print("\n[green]Deploy complete[/green]")


def _teardown_infra(provider: object, ctx: ProviderContext) -> None:
    """Destroy all deployed infrastructure via the provider's teardown method."""
    console.print("[bold]Tearing down infrastructure...[/bold]")
    try:
        provider.teardown(ctx)
    except subprocess.CalledProcessError as exc:
        console.print(
            f"[red]Error:[/red] Infrastructure teardown failed (exit {exc.returncode})"
        )
        raise typer.Exit(code=1)
    except NotImplementedError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)
    console.print("[green]Teardown complete[/green]")


def _deploy_code_only(ctx: ProviderContext) -> None:
    """Re-package Lambda code and update it via targeted Terraform apply.

    This remains Terraform-specific since --code-only is only supported
    with the terraform provider (enforced in deploy() above).
    """
    # Check terraform binary
    if not shutil.which("terraform"):
        console.print(
            "[red]Error:[/red] terraform binary not found. "
            "Install from https://terraform.io"
        )
        raise typer.Exit(code=1)

    # Check output_dir has terraform state
    if not ctx.output_dir.exists():
        console.print(
            f"[red]Error:[/red] Terraform directory not found: [bold]{ctx.output_dir}[/bold]\n"
            "Run [bold]rsf deploy[/bold] first to initialise the infrastructure."
        )
        raise typer.Exit(code=1)

    # Run targeted terraform apply for Lambda only
    console.print(
        "\n[bold]Running targeted terraform apply (Lambda code update)...[/bold]"
    )
    targeted_cmd = [
        "terraform",
        "apply",
        "-target=aws_lambda_function.*",
        "-auto-approve",
    ]
    if ctx.stage_var_file:
        targeted_cmd.extend(["-var-file", str(ctx.stage_var_file.resolve())])
    try:
        subprocess.run(
            targeted_cmd,
            cwd=ctx.output_dir,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        console.print(
            f"[red]Error:[/red] terraform apply --code-only failed (exit {exc.returncode})"
        )
        raise typer.Exit(code=1)

    console.print("\n[green]Code update complete[/green]")
