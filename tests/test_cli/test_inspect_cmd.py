"""Tests for the RSF inspect subcommand."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from rsf.cli.main import app

runner = CliRunner()

_SAMPLE_ARN = "arn:aws:lambda:us-east-2:123456789:function:my-fn"


def test_inspect_with_arn_calls_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """rsf inspect --arn <arn> calls launch with the given ARN."""
    monkeypatch.chdir(tmp_path)

    with patch("rsf.inspect.server.launch") as mock_launch:
        result = runner.invoke(app, ["inspect", "--arn", _SAMPLE_ARN])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    mock_launch.assert_called_once()
    _, kwargs = mock_launch.call_args
    assert kwargs.get("function_name") == _SAMPLE_ARN
    assert "Starting RSF Inspector" in result.output
    assert _SAMPLE_ARN in result.output


def test_inspect_no_arn_no_terraform_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """rsf inspect with no --arn and no terraform state exits with code 1."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["inspect"])

    assert result.exit_code == 1
    assert "Error" in result.output
    assert "--arn" in result.output


def test_inspect_discovers_arn_from_terraform(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """rsf inspect with terraform state available reads ARN from terraform output."""
    monkeypatch.chdir(tmp_path)

    # Create a fake terraform directory with terraform.tfstate
    tf_dir = tmp_path / "terraform"
    tf_dir.mkdir()
    (tf_dir / "terraform.tfstate").write_text(
        json.dumps({"version": 4, "outputs": {}}), encoding="utf-8"
    )

    with patch("subprocess.run") as mock_run, \
         patch("rsf.inspect.server.launch") as mock_launch:
        # Mock terraform output returning the ARN
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = _SAMPLE_ARN
        mock_run.return_value = mock_proc

        result = runner.invoke(app, ["inspect"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    mock_launch.assert_called_once()
    _, kwargs = mock_launch.call_args
    assert kwargs.get("function_name") == _SAMPLE_ARN


def test_inspect_terraform_fails_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """rsf inspect exits 1 when terraform output fails even if tfstate exists."""
    monkeypatch.chdir(tmp_path)

    tf_dir = tmp_path / "terraform"
    tf_dir.mkdir()
    (tf_dir / "terraform.tfstate").write_text(
        json.dumps({"version": 4, "outputs": {}}), encoding="utf-8"
    )

    with patch("subprocess.run") as mock_run:
        # Mock terraform output failure
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_run.return_value = mock_proc

        result = runner.invoke(app, ["inspect"])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_inspect_port_and_no_browser_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """rsf inspect --arn <arn> --port 9001 --no-browser passes correct args."""
    monkeypatch.chdir(tmp_path)

    with patch("rsf.inspect.server.launch") as mock_launch:
        result = runner.invoke(
            app,
            ["inspect", "--arn", _SAMPLE_ARN, "--port", "9001", "--no-browser"],
        )

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    mock_launch.assert_called_once_with(
        function_name=_SAMPLE_ARN,
        port=9001,
        open_browser=False,
    )


def test_inspect_default_port_and_open_browser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """rsf inspect uses port 8766 and open_browser=True by default."""
    monkeypatch.chdir(tmp_path)

    with patch("rsf.inspect.server.launch") as mock_launch:
        result = runner.invoke(app, ["inspect", "--arn", _SAMPLE_ARN])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    mock_launch.assert_called_once()
    _, kwargs = mock_launch.call_args
    assert kwargs.get("port") == 8766
    assert kwargs.get("open_browser") is True
