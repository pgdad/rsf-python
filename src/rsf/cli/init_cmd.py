"""RSF init subcommand — scaffold a new RSF project."""

from __future__ import annotations

import typer

app_ref = None  # Will be set after main.py creates the app


def init(
    project_name: str = typer.Argument(..., help="Name of the project to create"),
) -> None:
    """Scaffold a new RSF project directory."""
    raise NotImplementedError("init command not yet implemented")
