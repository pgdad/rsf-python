"""Tests for the RSF CLI main entry point."""

from __future__ import annotations

from typer.testing import CliRunner

from rsf import __version__
from rsf.cli.main import app

runner = CliRunner()


def test_version_flag_prints_version() -> None:
    """rsf --version should print the version string and exit with code 0."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"rsf {__version__}" in result.output


def test_help_flag_shows_subcommands() -> None:
    """rsf --help should show 'RSF' and available subcommand names."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "RSF" in result.output
    assert "init" in result.output


def test_no_args_shows_help() -> None:
    """rsf with no arguments should show help (no_args_is_help=True).

    Typer's no_args_is_help=True triggers help display with exit code 0 or 2
    depending on version. We accept either — the important thing is help is shown.
    """
    result = runner.invoke(app, [])
    # no_args_is_help=True shows help; exit code may be 0 or 2 depending on Typer version
    assert result.exit_code in (0, 2)
    assert "RSF" in result.output
