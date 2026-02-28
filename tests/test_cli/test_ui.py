"""Tests for the RSF ui subcommand."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from rsf.cli.main import app

runner = CliRunner()


def test_ui_calls_launch_with_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf ui calls launch with default workflow.yaml and port 8765."""
    monkeypatch.chdir(tmp_path)

    with patch("rsf.editor.server.launch") as mock_launch:
        result = runner.invoke(app, ["ui"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    mock_launch.assert_called_once()
    call_kwargs = mock_launch.call_args

    assert call_kwargs.kwargs.get("port", call_kwargs.args[1] if len(call_kwargs.args) > 1 else None) == 8765 or (
        call_kwargs.kwargs.get("port") == 8765
    )
    assert "Starting RSF Graph Editor" in result.output


def test_ui_custom_port_and_no_browser(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf ui my-workflow.yaml --port 9000 --no-browser passes correct args."""
    monkeypatch.chdir(tmp_path)

    with patch("rsf.editor.server.launch") as mock_launch:
        result = runner.invoke(app, ["ui", "my-workflow.yaml", "--port", "9000", "--no-browser"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    mock_launch.assert_called_once_with(
        workflow_path="my-workflow.yaml",
        port=9000,
        open_browser=False,
    )


def test_ui_open_browser_true_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf ui calls launch with open_browser=True by default."""
    monkeypatch.chdir(tmp_path)

    with patch("rsf.editor.server.launch") as mock_launch:
        result = runner.invoke(app, ["ui"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    mock_launch.assert_called_once()
    _, kwargs = mock_launch.call_args
    assert kwargs.get("open_browser") is True


def test_ui_no_browser_flag_passes_false(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf ui --no-browser calls launch with open_browser=False."""
    monkeypatch.chdir(tmp_path)

    with patch("rsf.editor.server.launch") as mock_launch:
        result = runner.invoke(app, ["ui", "--no-browser"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    mock_launch.assert_called_once()
    _, kwargs = mock_launch.call_args
    assert kwargs.get("open_browser") is False
