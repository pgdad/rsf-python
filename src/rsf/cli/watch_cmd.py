"""RSF watch subcommand — auto-validate and regenerate on file changes."""

from __future__ import annotations

import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

import typer
import yaml
from pydantic import ValidationError as PydanticValidationError
from rich.console import Console

from rsf.codegen.generator import generate as codegen_generate
from rsf.dsl import parser as dsl_parser
from rsf.dsl.validator import validate_definition

console = Console()


def _format_timestamp() -> str:
    """Return current time as [HH:MM:SS]."""
    return datetime.now().strftime("[%H:%M:%S]")


def _get_watch_paths(workflow: Path) -> list[Path]:
    """Return the list of paths to monitor for changes."""
    paths = [workflow]
    handlers_dir = workflow.parent / "handlers"
    if handlers_dir.exists():
        paths.append(handlers_dir)
    return paths


def run_cycle(
    workflow: Path,
    deploy: bool = False,
    tf_dir: Path | None = None,
    stage: str | None = None,
) -> tuple[bool, str]:
    """Run one validate + generate cycle.

    Returns (success, message) where message is a compact status string.
    """
    ts = _format_timestamp()

    # Step 1: YAML parse
    try:
        data = dsl_parser.load_yaml(workflow)
    except yaml.YAMLError as exc:
        return False, f"{ts} YAML error: {exc}"

    if not isinstance(data, dict):
        return False, f"{ts} Invalid workflow: must be a YAML mapping"

    # Step 2: Pydantic structural validation
    try:
        definition = dsl_parser.parse_definition(data)
    except PydanticValidationError as exc:
        error_count = len(exc.errors())
        return False, f"{ts} {error_count} validation error(s)"

    # Step 3: Semantic validation
    errors = validate_definition(definition)
    real_errors = [e for e in errors if e.severity == "error"]
    if real_errors:
        return False, f"{ts} {len(real_errors)} error(s) \u2014 see above"

    # Step 4: Code generation
    try:
        codegen_generate(
            definition=definition,
            dsl_path=workflow,
            output_dir=workflow.parent,
        )
    except Exception as exc:
        return False, f"{ts} Generation failed: {exc}"

    # Step 5: Optional deploy
    if deploy:
        effective_tf_dir = tf_dir or (workflow.parent / "terraform")
        if stage:
            effective_tf_dir = effective_tf_dir / stage

        if not shutil.which("terraform"):
            return False, f"{ts} Valid + regenerated, but deploy failed: terraform not found"

        if not effective_tf_dir.exists():
            return False, f"{ts} Valid + regenerated, but deploy failed: {effective_tf_dir} not found"

        stage_var_file = None
        if stage:
            stage_var_file = workflow.parent / "stages" / f"{stage}.tfvars"

        try:
            targeted_cmd = [
                "terraform",
                "apply",
                "-target=aws_lambda_function.*",
                "-auto-approve",
            ]
            if stage_var_file and stage_var_file.exists():
                targeted_cmd.extend(["-var-file", str(stage_var_file.resolve())])

            subprocess.run(
                targeted_cmd,
                cwd=effective_tf_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            return True, f"{ts} Valid + regenerated + deployed"
        except subprocess.CalledProcessError as exc:
            return False, f"{ts} Valid + regenerated, but deploy failed (exit {exc.returncode})"

    return True, f"{ts} Valid + regenerated"


def watch(
    workflow: Path = typer.Argument("workflow.yaml", help="Path to workflow YAML file"),
    deploy: bool = typer.Option(False, "--deploy", help="Auto-deploy code changes after validation"),
    tf_dir: Path = typer.Option("terraform", "--tf-dir", help="Terraform output directory"),
    stage: str | None = typer.Option(None, "--stage", help="Deployment stage for --deploy"),
) -> None:
    """Watch workflow files and auto-validate + regenerate on changes.

    Monitors workflow.yaml and the handlers/ directory. On each change,
    validates the workflow and regenerates orchestrator.py if valid.
    Use --deploy to also push code changes to AWS automatically.
    Press Ctrl+C to stop.
    """
    if not workflow.exists():
        console.print(f"[red]Error:[/red] Workflow file not found: [bold]{workflow}[/bold]")
        raise typer.Exit(code=1)

    watch_paths = _get_watch_paths(workflow)
    watch_dirs = [str(p) for p in watch_paths]

    mode_label = "watch + validate + generate"
    if deploy:
        mode_label += " + deploy"

    console.print(f"[bold]RSF Watch[/bold] \u2014 {mode_label}")
    console.print(f"[dim]Watching: {', '.join(str(p) for p in watch_paths)}[/dim]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    # Run initial cycle
    success, message = run_cycle(workflow, deploy=deploy, tf_dir=tf_dir, stage=stage)
    if success:
        console.print(f"[green]{message}[/green]")
    else:
        console.print(f"[red]{message}[/red]")

    # Try watchfiles first, fall back to polling
    try:
        from watchfiles import watch as watchfiles_watch

        try:
            for changes in watchfiles_watch(*watch_dirs):
                # Filter for relevant file types
                relevant = any(str(path).endswith((".yaml", ".yml", ".py")) for _, path in changes)
                if not relevant:
                    continue

                success, message = run_cycle(workflow, deploy=deploy, tf_dir=tf_dir, stage=stage)
                if success:
                    console.print(f"[green]{message}[/green]")
                else:
                    console.print(f"[red]{message}[/red]")
        except KeyboardInterrupt:
            console.print("\n[dim]Watch stopped[/dim]")

    except ImportError:
        # Fallback: simple polling
        console.print(
            "[dim]watchfiles not installed \u2014 using polling (pip install rsf[watch] for better performance)[/dim]"
        )
        _poll_loop(workflow, watch_paths, deploy, tf_dir, stage)


def _poll_loop(
    workflow: Path,
    watch_paths: list[Path],
    deploy: bool,
    tf_dir: Path,
    stage: str | None,
) -> None:
    """Simple polling fallback when watchfiles is not available."""
    last_mtimes: dict[str, float] = {}

    def _get_mtimes() -> dict[str, float]:
        mtimes: dict[str, float] = {}
        for p in watch_paths:
            if p.is_file():
                mtimes[str(p)] = p.stat().st_mtime
            elif p.is_dir():
                for f in p.rglob("*"):
                    if f.suffix in (".yaml", ".yml", ".py"):
                        mtimes[str(f)] = f.stat().st_mtime
        return mtimes

    last_mtimes = _get_mtimes()

    try:
        while True:
            time.sleep(1)  # 1-second poll interval
            current_mtimes = _get_mtimes()

            if current_mtimes != last_mtimes:
                last_mtimes = current_mtimes
                success, message = run_cycle(workflow, deploy=deploy, tf_dir=tf_dir, stage=stage)
                if success:
                    console.print(f"[green]{message}[/green]")
                else:
                    console.print(f"[red]{message}[/red]")
    except KeyboardInterrupt:
        console.print("\n[dim]Watch stopped[/dim]")
