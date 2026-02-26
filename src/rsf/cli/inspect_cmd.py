"""RSF CLI inspect subcommand — launches the execution inspector FastAPI server."""

from __future__ import annotations

import subprocess
from pathlib import Path

import typer
from rich.console import Console

console = Console()


def inspect(
    arn: str = typer.Option(None, "--arn", help="Lambda function ARN to inspect"),
    port: int = typer.Option(8766, "--port", "-p", help="Port to serve on"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't auto-open browser"),
    tf_dir: Path = typer.Option("terraform", "--tf-dir", help="Terraform directory for ARN discovery"),
) -> None:
    """Launch the RSF Execution Inspector in your browser.

    Connects to a deployed Lambda Durable Function and shows live execution
    history and state machine progress. Press Ctrl+C to stop the server.

    If --arn is not provided, attempts to discover the ARN from Terraform output.
    """
    from rsf.inspect.server import launch

    resolved_arn = arn

    if resolved_arn is None:
        # Attempt ARN discovery from Terraform state
        tf_state = tf_dir / "terraform.tfstate"
        if tf_state.exists():
            try:
                proc = subprocess.run(
                    ["terraform", "output", "-raw", "function_arn"],
                    cwd=tf_dir,
                    capture_output=True,
                    text=True,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    resolved_arn = proc.stdout.strip()
                else:
                    resolved_arn = None
            except Exception:
                resolved_arn = None

    if resolved_arn is None:
        console.print(
            "[red]Error:[/red] No --arn provided and could not discover ARN from Terraform state. "
            "Use --arn <function-arn>."
        )
        raise typer.Exit(code=1)

    console.print(f"[blue]Starting RSF Inspector on port {port}...[/blue]")
    console.print(f"[dim]Inspecting: {resolved_arn}[/dim]")

    try:
        launch(function_name=resolved_arn, port=port, open_browser=not no_browser)
    except KeyboardInterrupt:
        console.print("[dim]Server stopped[/dim]")
