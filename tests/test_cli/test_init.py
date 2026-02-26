"""Tests for the RSF init scaffold subcommand."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from rsf.cli.main import app
from rsf.dsl.parser import load_yaml

runner = CliRunner()


def test_init_creates_all_expected_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf init my-project creates all required scaffold files."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "my-project"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"

    project = tmp_path / "my-project"
    assert project.is_dir(), "Project directory should be created"

    expected_files = [
        "workflow.yaml",
        "handlers/__init__.py",
        "handlers/example_handler.py",
        "pyproject.toml",
        ".gitignore",
        "tests/__init__.py",
        "tests/test_example.py",
    ]
    for rel_path in expected_files:
        assert (project / rel_path).exists(), f"Missing file: {rel_path}"


def test_init_twice_fails_with_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf init my-project twice should fail on the second run with exit code 1."""
    monkeypatch.chdir(tmp_path)

    # First run — should succeed
    result1 = runner.invoke(app, ["init", "my-project"])
    assert result1.exit_code == 0, f"First init failed: {result1.output}"

    # Second run — should fail with exit code 1
    result2 = runner.invoke(app, ["init", "my-project"])
    assert result2.exit_code == 1, f"Second init should fail, but got: {result2.output}"
    assert "Error" in result2.output or "already exists" in result2.output


def test_init_workflow_yaml_is_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Created workflow.yaml should be valid YAML parseable by rsf.dsl.parser.load_yaml."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "my-project"])
    assert result.exit_code == 0

    workflow_path = tmp_path / "my-project" / "workflow.yaml"
    assert workflow_path.exists()

    data = load_yaml(workflow_path)
    assert isinstance(data, dict)
    assert "StartAt" in data
    assert "States" in data


def test_init_pyproject_contains_project_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Created pyproject.toml should contain the project name."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "my-cool-project"])
    assert result.exit_code == 0

    pyproject_path = tmp_path / "my-cool-project" / "pyproject.toml"
    assert pyproject_path.exists()

    content = pyproject_path.read_text(encoding="utf-8")
    assert "my-cool-project" in content
