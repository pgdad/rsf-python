"""Tests for JSON Schema generation and CLI export command.

Tests cover:
- generate_json_schema() output correctness
- write_json_schema() file creation
- v2.0 DSL field coverage
- rsf schema export CLI command
- SchemaStore catalog entry validity
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from rsf.cli.main import app
from rsf.schema.generate import generate_json_schema, write_json_schema

runner = CliRunner()


# ---------------------------------------------------------------------------
# Schema generation tests
# ---------------------------------------------------------------------------


def test_schema_has_draft_2020_12() -> None:
    """generate_json_schema() returns a dict with $schema set to Draft 2020-12 URI."""
    schema = generate_json_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_schema_has_id_with_github_url() -> None:
    """generate_json_schema() includes $id with GitHub raw URL pattern."""
    schema = generate_json_schema()
    assert "$id" in schema
    assert "raw.githubusercontent.com" in schema["$id"]
    assert "rsf-python" in schema["$id"]


def test_schema_title() -> None:
    """Schema title is 'RSF Workflow Definition'."""
    schema = generate_json_schema()
    assert schema["title"] == "RSF Workflow Definition"


def test_schema_v2_fields_present() -> None:
    """Schema properties include all v2.0 top-level fields."""
    schema = generate_json_schema()
    props = schema.get("properties", {})
    v2_fields = [
        "triggers",
        "sub_workflows",
        "dynamodb_tables",
        "alarms",
        "dead_letter_queue",
        "TimeoutSeconds",
    ]
    for field in v2_fields:
        assert field in props, f"Missing v2.0 field: {field}"


def test_schema_has_states_property() -> None:
    """Schema includes 'States' property (core DSL)."""
    schema = generate_json_schema()
    props = schema.get("properties", {})
    assert "States" in props


def test_schema_has_start_at_property() -> None:
    """Schema includes 'StartAt' property (core DSL)."""
    schema = generate_json_schema()
    props = schema.get("properties", {})
    assert "StartAt" in props


def test_write_json_schema_creates_file(tmp_path: Path) -> None:
    """write_json_schema() creates a valid JSON file at the specified path."""
    out = tmp_path / "test-schema.json"
    result = write_json_schema(out)
    assert result == out
    assert out.exists()
    # Verify it's valid JSON
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "$schema" in data


def test_schema_meta_validation() -> None:
    """The generated schema is valid JSON Schema (validates against meta-schema)."""
    try:
        import jsonschema  # noqa: F401

        schema = generate_json_schema()
        jsonschema.Draft202012Validator.check_schema(schema)
    except ImportError:
        pytest.skip("jsonschema not installed — skipping meta-schema validation")


def test_schema_description_present() -> None:
    """Schema description field is present and non-empty."""
    schema = generate_json_schema()
    assert "description" in schema
    assert len(schema["description"]) > 0


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def test_schema_export_creates_default_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf schema export creates rsf-workflow.json in current directory by default."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["schema"])
    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    assert (tmp_path / "rsf-workflow.json").exists()


def test_schema_export_custom_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf schema export --output custom.json writes to the specified path."""
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "custom.json"
    result = runner.invoke(app, ["schema", "--output", str(out)])
    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    assert out.exists()
    data = json.loads(out.read_text())
    assert "$schema" in data


def test_schema_export_stdout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf schema export --stdout prints schema to stdout (valid JSON)."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["schema", "--stdout"])
    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    # Output should be valid JSON
    data = json.loads(result.output)
    assert "$schema" in data
    assert "$id" in data


def test_schema_export_exits_0(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf schema export exits 0 on success."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["schema"])
    assert result.exit_code == 0


def test_schema_export_output_has_required_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Schema export output contains $schema and $id fields."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["schema", "--stdout"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "$schema" in data
    assert "$id" in data
    assert "title" in data


def test_schemastore_catalog_entry_valid() -> None:
    """SchemaStore catalog entry JSON is valid and contains fileMatch with workflow.yaml."""
    catalog_path = Path("schemas/schemastore-catalog-entry.json")
    assert catalog_path.exists(), "Catalog entry file not found"

    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert "name" in data
    assert "fileMatch" in data
    assert "workflow.yaml" in data["fileMatch"]
    assert "url" in data
    assert "raw.githubusercontent.com" in data["url"]
