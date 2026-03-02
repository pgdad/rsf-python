"""Tests for the rsf validate subcommand."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from rsf.cli.main import app

runner = CliRunner()

# ── Minimal valid workflow YAML ────────────────────────────────────────────────
VALID_WORKFLOW = """\
rsf_version: "1.0"
StartAt: ProcessData
States:
  ProcessData:
    Type: Task
    End: true
"""

# ── Valid workflow with infrastructure block ──────────────────────────────────
VALID_WORKFLOW_WITH_INFRA = """\
rsf_version: "1.0"
StartAt: ProcessData
infrastructure:
  provider: terraform
States:
  ProcessData:
    Type: Task
    End: true
"""

# ── Workflow with unknown provider ───────────────────────────────────────────
UNKNOWN_PROVIDER_WORKFLOW = """\
rsf_version: "1.0"
StartAt: ProcessData
infrastructure:
  provider: pulumi
States:
  ProcessData:
    Type: Task
    End: true
"""

# ── Workflow with unknown infra field (Pydantic extra=forbid catches this) ───
UNKNOWN_INFRA_FIELD_WORKFLOW = """\
rsf_version: "1.0"
StartAt: ProcessData
infrastructure:
  provider: terraform
  bad_field: something
States:
  ProcessData:
    Type: Task
    End: true
"""

# ── Invalid YAML (bad indentation / parse error) ──────────────────────────────
MALFORMED_YAML = """\
StartAt: Foo
States:
  Foo:
    Type: Task
      End: true
"""

# ── Missing required field (no StartAt) ─────────────────────────────────────
MISSING_START_AT = """\
rsf_version: "1.0"
States:
  Done:
    Type: Succeed
"""

# ── Semantically invalid: dangling Next reference ─────────────────────────────
DANGLING_NEXT = """\
rsf_version: "1.0"
StartAt: ProcessData
States:
  ProcessData:
    Type: Task
    Next: DoesNotExist
  Done:
    Type: Succeed
"""


class TestValidateSubcommand:
    """Tests for `rsf validate`."""

    def test_valid_workflow_exits_0(self, tmp_path: Path) -> None:
        """A well-formed workflow.yaml produces exit code 0 and 'Valid' output."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(VALID_WORKFLOW, encoding="utf-8")

        result = runner.invoke(app, ["validate", str(wf)])

        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"
        assert "Valid" in result.output

    def test_file_not_found_exits_1(self, tmp_path: Path) -> None:
        """A missing file produces exit code 1 and a 'not found' message."""
        missing = tmp_path / "nonexistent.yaml"

        result = runner.invoke(app, ["validate", str(missing)])

        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "Error" in result.output

    def test_malformed_yaml_exits_1(self, tmp_path: Path) -> None:
        """Malformed YAML (parse error) produces exit code 1."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(MALFORMED_YAML, encoding="utf-8")

        result = runner.invoke(app, ["validate", str(wf)])

        assert result.exit_code == 1

    def test_missing_start_at_exits_1_with_field_path(self, tmp_path: Path) -> None:
        """A workflow missing StartAt produces exit code 1 and mentions the field."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(MISSING_START_AT, encoding="utf-8")

        result = runner.invoke(app, ["validate", str(wf)])

        assert result.exit_code == 1
        # Should mention the missing field (Pydantic uses "start_at" or "StartAt")
        output_lower = result.output.lower()
        assert "start_at" in output_lower or "startat" in output_lower or "error" in output_lower

    def test_dangling_next_exits_1_with_state_name(self, tmp_path: Path) -> None:
        """A semantically invalid workflow prints the bad state name and exits 1."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(DANGLING_NEXT, encoding="utf-8")

        result = runner.invoke(app, ["validate", str(wf)])

        assert result.exit_code == 1
        # The bad reference 'DoesNotExist' should appear in the error output
        assert "DoesNotExist" in result.output

    def test_validate_does_not_create_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Running rsf validate must never create any files in the output directory."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(VALID_WORKFLOW, encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        files_before = set(tmp_path.rglob("*"))
        runner.invoke(app, ["validate", str(wf)])
        files_after = set(tmp_path.rglob("*"))

        new_files = files_after - files_before
        assert len(new_files) == 0, f"validate created unexpected files: {new_files}"

    def test_validate_uses_fixture_file(self) -> None:
        """rsf validate works against the project's valid fixture files."""
        fixture = Path(__file__).parent.parent.parent / "fixtures" / "valid" / "all_state_types.yaml"
        if not fixture.exists():
            pytest.skip("Fixture file not found")

        result = runner.invoke(app, ["validate", str(fixture)])

        assert result.exit_code == 0, f"Expected exit 0 for valid fixture: {result.output}"
        assert "Valid" in result.output

    def test_validate_invalid_semantic_fixture(self) -> None:
        """rsf validate reports errors for a semantic-invalid fixture."""
        fixture = Path(__file__).parent.parent.parent / "fixtures" / "invalid" / "semantic" / "bad_reference.yaml"
        if not fixture.exists():
            pytest.skip("Fixture file not found")

        result = runner.invoke(app, ["validate", str(fixture)])

        assert result.exit_code == 1


class TestInfrastructureValidation:
    """Tests for infrastructure config validation in rsf validate."""

    def test_validate_with_valid_infra_block_passes(self, tmp_path: Path) -> None:
        """Workflow with valid infrastructure: {provider: terraform} passes validation."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(VALID_WORKFLOW_WITH_INFRA, encoding="utf-8")

        result = runner.invoke(app, ["validate", str(wf)])

        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"
        assert "Valid" in result.output

    def test_validate_with_unknown_provider_fails(self, tmp_path: Path) -> None:
        """Workflow with unknown provider name exits 1 with provider error."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(UNKNOWN_PROVIDER_WORKFLOW, encoding="utf-8")

        result = runner.invoke(app, ["validate", str(wf)])

        assert result.exit_code == 1
        assert "pulumi" in result.output
        assert "infrastructure.provider" in result.output

    def test_validate_with_unknown_infra_field_fails(self, tmp_path: Path) -> None:
        """Workflow with extra field in infrastructure block exits 1 (Pydantic catches)."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(UNKNOWN_INFRA_FIELD_WORKFLOW, encoding="utf-8")

        result = runner.invoke(app, ["validate", str(wf)])

        assert result.exit_code == 1

    def test_validate_no_infra_block_still_passes(self, tmp_path: Path) -> None:
        """Workflow with no infrastructure block still passes (backward compat)."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(VALID_WORKFLOW, encoding="utf-8")

        result = runner.invoke(app, ["validate", str(wf)])

        assert result.exit_code == 0
        assert "Valid" in result.output

    def test_validate_rsf_toml_valid_passes(self, tmp_path: Path) -> None:
        """Workflow + valid rsf.toml with [infrastructure] passes validation."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(VALID_WORKFLOW, encoding="utf-8")
        toml = tmp_path / "rsf.toml"
        toml.write_text('[infrastructure]\nprovider = "terraform"\n', encoding="utf-8")

        result = runner.invoke(app, ["validate", str(wf)])

        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"
        assert "Valid" in result.output

    def test_validate_rsf_toml_unknown_provider_fails(self, tmp_path: Path) -> None:
        """rsf.toml with unknown provider exits 1."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(VALID_WORKFLOW, encoding="utf-8")
        toml = tmp_path / "rsf.toml"
        toml.write_text('[infrastructure]\nprovider = "unknown"\n', encoding="utf-8")

        result = runner.invoke(app, ["validate", str(wf)])

        assert result.exit_code == 1
        assert "unknown" in result.output
        assert "infrastructure.provider" in result.output

    def test_validate_rsf_toml_invalid_field_fails(self, tmp_path: Path) -> None:
        """rsf.toml with extra field in [infrastructure] exits 1."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(VALID_WORKFLOW, encoding="utf-8")
        toml = tmp_path / "rsf.toml"
        toml.write_text('[infrastructure]\nbad_field = "oops"\n', encoding="utf-8")

        result = runner.invoke(app, ["validate", str(wf)])

        assert result.exit_code == 1

    def test_validate_error_format_uses_field_path(self, tmp_path: Path) -> None:
        """Error output contains infrastructure.provider field path format."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(UNKNOWN_PROVIDER_WORKFLOW, encoding="utf-8")

        result = runner.invoke(app, ["validate", str(wf)])

        assert result.exit_code == 1
        assert "infrastructure.provider" in result.output
        # Should mention available providers
        assert "terraform" in result.output
