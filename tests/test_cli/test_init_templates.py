"""Tests for RSF init --template scaffolding."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from rsf.cli.main import app

runner = CliRunner()


# ─── Template Listing ────────────────────────────────────────────────────────


def test_template_list_shows_all_templates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf init --template list shows both available templates."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--template", "list"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    assert "api-gateway-crud" in result.output
    assert "s3-event-pipeline" in result.output


def test_template_list_shows_descriptions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf init --template list shows descriptions for each template."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--template", "list"])

    assert result.exit_code == 0
    assert "DynamoDB" in result.output or "CRUD" in result.output
    assert "S3" in result.output or "pipeline" in result.output


# ─── API Gateway CRUD Template ──────────────────────────────────────────────


def test_api_gateway_crud_creates_complete_scaffold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf init --template api-gateway-crud creates all expected files."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--template", "api-gateway-crud", "my-api"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"

    project = tmp_path / "my-api"
    assert project.is_dir()

    expected_files = [
        "workflow.yaml",
        "handlers/__init__.py",
        "handlers/create_item.py",
        "handlers/get_item.py",
        "handlers/update_item.py",
        "handlers/delete_item.py",
        "handlers/list_items.py",
        "tests/__init__.py",
        "tests/test_handlers.py",
        "pyproject.toml",
        ".gitignore",
        "terraform.tf",
        "README.md",
    ]
    for rel_path in expected_files:
        assert (project / rel_path).exists(), f"Missing file: {rel_path}"


def test_api_gateway_crud_default_project_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf init --template api-gateway-crud without project name defaults to template name."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--template", "api-gateway-crud"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    assert (tmp_path / "api-gateway-crud").is_dir()
    assert (tmp_path / "api-gateway-crud" / "workflow.yaml").exists()


# ─── S3 Event Pipeline Template ─────────────────────────────────────────────


def test_s3_event_pipeline_creates_complete_scaffold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf init --template s3-event-pipeline creates all expected files."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--template", "s3-event-pipeline", "my-pipeline"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"

    project = tmp_path / "my-pipeline"
    assert project.is_dir()

    expected_files = [
        "workflow.yaml",
        "handlers/__init__.py",
        "handlers/validate_file.py",
        "handlers/transform_data.py",
        "handlers/process_upload.py",
        "handlers/notify_complete.py",
        "tests/__init__.py",
        "tests/test_handlers.py",
        "pyproject.toml",
        ".gitignore",
        "terraform.tf",
        "README.md",
    ]
    for rel_path in expected_files:
        assert (project / rel_path).exists(), f"Missing file: {rel_path}"


def test_s3_event_pipeline_default_project_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf init --template s3-event-pipeline without project name defaults to template name."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--template", "s3-event-pipeline"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    assert (tmp_path / "s3-event-pipeline").is_dir()
    assert (tmp_path / "s3-event-pipeline" / "workflow.yaml").exists()


# ─── Error Handling ──────────────────────────────────────────────────────────


def test_invalid_template_shows_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf init --template nonexistent exits 1 with available templates."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--template", "nonexistent"])

    assert result.exit_code == 1, f"Expected exit 1, got: {result.exit_code}"
    assert "nonexistent" in result.output or "Unknown" in result.output
    # Should mention available templates
    assert "api-gateway-crud" in result.output
    assert "s3-event-pipeline" in result.output


def test_no_project_name_no_template_shows_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf init without project name or template shows error."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init"])

    assert result.exit_code == 1, f"Expected exit 1, got: {result.exit_code}"
    assert "project name" in result.output.lower() or "Error" in result.output


# ─── Backward Compatibility ──────────────────────────────────────────────────


def test_default_init_still_works(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf init my-project (no --template) still creates HelloWorld scaffold."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "my-project"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"

    project = tmp_path / "my-project"
    assert (project / "workflow.yaml").exists()
    assert (project / "src" / "handlers" / "example_handler.py").exists()
    assert (project / "tests" / "test_example.py").exists()

    # Default scaffold should NOT have template-specific files
    assert not (project / "src" / "handlers" / "create_item.py").exists()
    assert not (project / "src" / "handlers" / "validate_file.py").exists()


# ─── Content Validity ────────────────────────────────────────────────────────


@pytest.mark.parametrize("template", ["api-gateway-crud", "s3-event-pipeline"])
def test_template_workflow_yaml_is_valid(template: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scaffolded workflow.yaml is valid YAML with StartAt and States fields."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--template", template, f"test-{template}"])
    assert result.exit_code == 0

    workflow_path = tmp_path / f"test-{template}" / "workflow.yaml"
    assert workflow_path.exists()

    data = yaml.safe_load(workflow_path.read_text())
    assert isinstance(data, dict)
    assert "StartAt" in data
    assert "States" in data
    assert len(data["States"]) > 0


@pytest.mark.parametrize("template", ["api-gateway-crud", "s3-event-pipeline"])
def test_template_pyproject_has_project_name(template: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scaffolded pyproject.toml contains the correct project name."""
    monkeypatch.chdir(tmp_path)
    project_name = f"my-{template}-project"
    result = runner.invoke(app, ["init", "--template", template, project_name])
    assert result.exit_code == 0

    pyproject_path = tmp_path / project_name / "pyproject.toml"
    assert pyproject_path.exists()

    content = pyproject_path.read_text()
    assert project_name in content


@pytest.mark.parametrize("template", ["api-gateway-crud", "s3-event-pipeline"])
def test_template_gitignore_created(template: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scaffolded project has .gitignore (renamed from gitignore)."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--template", template, f"test-{template}"])
    assert result.exit_code == 0

    gitignore_path = tmp_path / f"test-{template}" / ".gitignore"
    assert gitignore_path.exists()
    content = gitignore_path.read_text()
    assert "__pycache__" in content


@pytest.mark.parametrize("template", ["api-gateway-crud", "s3-event-pipeline"])
def test_template_has_handlers_and_tests_dirs(template: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scaffolded project has handlers/ and tests/ subdirectories."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--template", template, f"test-{template}"])
    assert result.exit_code == 0

    project = tmp_path / f"test-{template}"
    assert (project / "handlers").is_dir()
    assert (project / "tests").is_dir()


def test_template_scaffold_twice_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scaffolding the same template twice should fail with exit code 1."""
    monkeypatch.chdir(tmp_path)

    result1 = runner.invoke(app, ["init", "--template", "api-gateway-crud", "my-api"])
    assert result1.exit_code == 0

    result2 = runner.invoke(app, ["init", "--template", "api-gateway-crud", "my-api"])
    assert result2.exit_code == 1
    assert "already exists" in result2.output
