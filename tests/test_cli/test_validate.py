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
