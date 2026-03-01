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
    no_infra: bool = typer.Option(False, "--no-infra", help="Generate and deploy code only, skip Terraform"),
) -> None:
    """Deploy an RSF workflow to AWS via Terraform.

    Generates Terraform files, then runs terraform init and terraform apply.
    Use --code-only to re-package Lambda code without a full Terraform apply.
    Use --no-infra to skip Terraform generation entirely.
    """
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

    # --no-infra: skip all Terraform steps, return after code generation
    if no_infra:
        console.print("[green]Code generated (infrastructure skipped).[/green]")
        return

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
    # Build lambda_url config from DSL definition
    lambda_url_enabled = False
    lambda_url_auth_type = "NONE"
    if hasattr(definition, "lambda_url") and definition.lambda_url is not None and definition.lambda_url.enabled:
        lambda_url_enabled = True
        lambda_url_auth_type = definition.lambda_url.auth_type.value

    # Build trigger config from DSL definition
    triggers_config: list[dict] = []
    if hasattr(definition, "triggers") and definition.triggers:
        for trigger in definition.triggers:
            trigger_dict: dict = {"type": trigger.type}
            if trigger.type == "eventbridge":
                trigger_dict["schedule_expression"] = trigger.schedule_expression
                trigger_dict["event_pattern"] = trigger.event_pattern
            elif trigger.type == "sqs":
                trigger_dict["queue_name"] = trigger.queue_name
                trigger_dict["batch_size"] = trigger.batch_size
            elif trigger.type == "sns":
                trigger_dict["topic_arn"] = trigger.topic_arn
            triggers_config.append(trigger_dict)
    has_sqs = any(t["type"] == "sqs" for t in triggers_config)

    # Build DynamoDB config from DSL definition
    dynamodb_config: list[dict] = []
    if hasattr(definition, "dynamodb_tables") and definition.dynamodb_tables:
        for table in definition.dynamodb_tables:
            table_dict: dict = {
                "table_name": table.table_name,
                "partition_key": {"name": table.partition_key.name, "type": table.partition_key.type.value},
                "billing_mode": table.billing_mode.value,
            }
            if table.sort_key:
                table_dict["sort_key"] = {"name": table.sort_key.name, "type": table.sort_key.type.value}
            if table.read_capacity is not None:
                table_dict["read_capacity"] = table.read_capacity
            if table.write_capacity is not None:
                table_dict["write_capacity"] = table.write_capacity
            dynamodb_config.append(table_dict)

    # Build alarm config from DSL definition
    alarms_config: list[dict] = []
    if hasattr(definition, "alarms") and definition.alarms:
        for alarm in definition.alarms:
            alarm_dict: dict = {
                "type": alarm.type,
                "threshold": alarm.threshold,
                "period": alarm.period,
                "evaluation_periods": alarm.evaluation_periods,
                "sns_topic_arn": alarm.sns_topic_arn,
            }
            alarms_config.append(alarm_dict)

    # Build DLQ config from DSL definition
    dlq_enabled = False
    dlq_max_receive_count = 3
    dlq_queue_name = None
    if hasattr(definition, "dead_letter_queue") and definition.dead_letter_queue is not None:
        if definition.dead_letter_queue.enabled:
            dlq_enabled = True
            dlq_max_receive_count = definition.dead_letter_queue.max_receive_count
            dlq_queue_name = definition.dead_letter_queue.queue_name

    with Status("[bold]Generating Terraform files...[/bold]", console=console):
        tf_result = generate_terraform(
            config=TerraformConfig(
                workflow_name=workflow_name,
                lambda_url_enabled=lambda_url_enabled,
                lambda_url_auth_type=lambda_url_auth_type,
                triggers=triggers_config,
                has_sqs_triggers=has_sqs,
                dynamodb_tables=dynamodb_config,
                has_dynamodb_tables=bool(dynamodb_config),
                alarms=alarms_config,
                has_alarms=bool(alarms_config),
                dlq_enabled=dlq_enabled,
                dlq_max_receive_count=dlq_max_receive_count,
                dlq_queue_name=dlq_queue_name,
            ),
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
