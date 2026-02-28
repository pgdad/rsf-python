"""Tests for the RSF import subcommand."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from rsf.cli.main import app

runner = CliRunner()

# Minimal valid ASL JSON for testing
_MINIMAL_ASL = {
    "StartAt": "MyTask",
    "States": {
        "MyTask": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:us-east-1:123:function:my-fn",
            "End": True,
        }
    },
}


def _write_asl(path: Path, data: dict | None = None) -> Path:
    """Write ASL JSON to a file. Uses minimal valid ASL if data is None."""
    data = data if data is not None else _MINIMAL_ASL
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_import_produces_workflow_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf import asl.json produces workflow.yaml in current directory."""
    monkeypatch.chdir(tmp_path)
    asl_file = tmp_path / "asl.json"
    _write_asl(asl_file)

    result = runner.invoke(app, ["import", str(asl_file)])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    assert (tmp_path / "workflow.yaml").exists(), "workflow.yaml should be created"
    assert "Success" in result.output


def test_import_custom_output_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf import asl.json --output custom.yaml writes to the specified path."""
    monkeypatch.chdir(tmp_path)
    asl_file = tmp_path / "asl.json"
    _write_asl(asl_file)
    custom_output = tmp_path / "custom.yaml"

    result = runner.invoke(app, ["import", str(asl_file), "--output", str(custom_output)])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    assert custom_output.exists(), "custom.yaml should be created"
    assert (tmp_path / "workflow.yaml").exists() is False, "Default workflow.yaml should NOT be created"


def test_import_file_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf import on a missing file exits with code 1."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["import", "nonexistent.json"])

    assert result.exit_code == 1
    assert "Error" in result.output
    assert "not found" in result.output.lower() or "nonexistent" in result.output


def test_import_malformed_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf import on malformed JSON prints a clear error, not a stack trace."""
    monkeypatch.chdir(tmp_path)
    asl_file = tmp_path / "bad.json"
    asl_file.write_text("{this is not valid json}", encoding="utf-8")

    result = runner.invoke(app, ["import", str(asl_file)])

    assert result.exit_code == 1
    # Should show a user-friendly error, not a raw traceback
    assert "Error" in result.output
    assert "Traceback" not in result.output
    assert "ValueError" not in result.output


def test_import_shows_warnings_for_resource_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf import shows warnings for Resource fields that were stripped."""
    monkeypatch.chdir(tmp_path)
    asl_file = tmp_path / "asl.json"
    _write_asl(asl_file)  # The minimal ASL has a Resource field on MyTask

    result = runner.invoke(app, ["import", str(asl_file)])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    # The Resource field should trigger a warning
    assert "Warning" in result.output
    assert "Resource" in result.output


def test_import_handler_stubs_created(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf import creates handler stub files for Task states."""
    monkeypatch.chdir(tmp_path)
    asl_file = tmp_path / "asl.json"
    _write_asl(asl_file)

    result = runner.invoke(app, ["import", str(asl_file)])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    handlers_dir = tmp_path / "handlers"
    assert handlers_dir.exists(), "handlers/ directory should be created"
    stub_files = list(handlers_dir.glob("*.py"))
    assert len(stub_files) >= 1, "At least one handler stub should be created"


def test_import_output_already_exists_warns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf import warns but overwrites if output file already exists."""
    monkeypatch.chdir(tmp_path)
    asl_file = tmp_path / "asl.json"
    _write_asl(asl_file)
    output = tmp_path / "workflow.yaml"
    output.write_text("# existing content", encoding="utf-8")

    result = runner.invoke(app, ["import", str(asl_file)])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    assert "Warning" in result.output
    assert "overwritten" in result.output
    # File should have been overwritten with real content
    content = output.read_text(encoding="utf-8")
    assert "rsf_version" in content
