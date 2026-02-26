"""RSF CLI ui subcommand — launches the graph editor FastAPI server."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()


def ui(
    workflow: Path = typer.Argument("workflow.yaml", help="Path to workflow YAML file"),
    port: int = typer.Option(8765, "--port", "-p", help="Port to serve on"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't auto-open browser"),
) -> None:
    """Launch the RSF Graph Editor in your browser.

    Starts a local FastAPI server and opens the visual workflow editor.
    Press Ctrl+C to stop the server.
    """
    from rsf.editor.server import launch

    console.print(f"[blue]Starting RSF Graph Editor on port {port}...[/blue]")

    try:
        launch(workflow_path=str(workflow), port=port, open_browser=not no_browser)
    except KeyboardInterrupt:
        console.print("[dim]Server stopped[/dim]")
