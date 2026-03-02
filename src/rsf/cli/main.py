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
from rsf.cli import deploy_cmd, diff_cmd, doctor_cmd, export_cmd, generate_cmd, import_cmd, init_cmd, inspect_cmd, logs_cmd, test_cmd, ui_cmd, validate_cmd, watch_cmd  # noqa: E402

app.command(name="init")(init_cmd.init)
app.command(name="deploy")(deploy_cmd.deploy)
app.command(name="diff")(diff_cmd.diff)
app.command(name="doctor")(doctor_cmd.doctor)
app.command(name="export")(export_cmd.export_workflow)
app.command(name="logs")(logs_cmd.logs)
app.command(name="test")(test_cmd.test_workflow)
app.command(name="watch")(watch_cmd.watch)
app.command(name="validate")(validate_cmd.validate)
app.command(name="generate")(generate_cmd.generate)
app.command(name="import")(import_cmd.import_asl)
app.command(name="ui")(ui_cmd.ui)
app.command(name="inspect")(inspect_cmd.inspect)


if __name__ == "__main__":
    app()
