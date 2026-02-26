"""RSF CLI entry point — Typer application with subcommand registration."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from rsf import __version__

console = Console()

app = typer.Typer(
    name="rsf",
    help="RSF — Replacement for Step Functions",
    no_args_is_help=True,
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Print the RSF version string and exit."""
    if value:
        typer.echo(f"rsf {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show the RSF version and exit.",
    ),
) -> None:
    """RSF — Replacement for Step Functions."""


# Import and register subcommands
from rsf.cli import deploy_cmd, import_cmd, init_cmd, validate_cmd  # noqa: E402

app.command(name="init")(init_cmd.init)
app.command(name="deploy")(deploy_cmd.deploy)
app.command(name="validate")(validate_cmd.validate)
app.command(name="import")(import_cmd.import_asl)


if __name__ == "__main__":
    app()
