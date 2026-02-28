"""Tests for the rsf generate subcommand."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from rsf.cli.main import app

runner = CliRunner()

# ── Valid workflow with one Task state and one terminal state ─────────────────
VALID_WORKFLOW = """\
rsf_version: "1.0"
StartAt: ProcessData
States:
  ProcessData:
    Type: Task
    Next: Done
  Done:
    Type: Succeed
"""

# ── Valid workflow with two Task states ───────────────────────────────────────
VALID_WORKFLOW_MULTI_TASK = """\
rsf_version: "1.0"
StartAt: StepOne
States:
  StepOne:
    Type: Task
    Next: StepTwo
  StepTwo:
    Type: Task
    Next: Done
  Done:
    Type: Succeed
"""

# ── Invalid: Pydantic error (missing StartAt) ─────────────────────────────────
INVALID_MISSING_START_AT = """\
rsf_version: "1.0"
States:
  Done:
    Type: Succeed
"""

# ── Invalid: semantic error (dangling Next reference) ─────────────────────────
INVALID_DANGLING_NEXT = """\
rsf_version: "1.0"
StartAt: ProcessData
States:
  ProcessData:
    Type: Task
    Next: Nonexistent
  Done:
    Type: Succeed
"""


class TestGenerateSubcommand:
    """Tests for `rsf generate`."""

    def test_generate_creates_orchestrator_and_handler(self, tmp_path: Path) -> None:
        """rsf generate creates orchestrator.py and handler stubs for Task states."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(VALID_WORKFLOW, encoding="utf-8")
        out = tmp_path / "out"

        result = runner.invoke(app, ["generate", str(wf), "--output", str(out)])

        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"
        assert (out / "orchestrator.py").exists(), "orchestrator.py should be created"
        assert (out / "handlers" / "process_data.py").exists(), "handler stub should be created"

    def test_generate_skips_existing_handler_on_second_run(self, tmp_path: Path) -> None:
        """Running generate twice skips handlers that were modified (Generation Gap)."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(VALID_WORKFLOW, encoding="utf-8")
        out = tmp_path / "out"

        # First run — creates handler
        result1 = runner.invoke(app, ["generate", str(wf), "--output", str(out)])
        assert result1.exit_code == 0, f"First generate failed: {result1.output}"

        handler = out / "handlers" / "process_data.py"
        assert handler.exists()

        # Simulate user editing the handler (remove generated marker)
        handler.write_text("# user-modified content\ndef process_data(event, context): pass\n")
        mtime_after_edit = handler.stat().st_mtime

        # Second run — should skip the user-modified handler
        result2 = runner.invoke(app, ["generate", str(wf), "--output", str(out)])
        assert result2.exit_code == 0, f"Second generate failed: {result2.output}"
        assert "Skipped" in result2.output or "skipped" in result2.output.lower()

        # Handler content must not be overwritten
        assert handler.stat().st_mtime == mtime_after_edit or "user-modified" in handler.read_text(encoding="utf-8")

    def test_generate_invalid_workflow_exits_1_no_files(self, tmp_path: Path) -> None:
        """rsf generate with an invalid workflow exits 1 and creates no files."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(INVALID_MISSING_START_AT, encoding="utf-8")
        out = tmp_path / "out"

        result = runner.invoke(app, ["generate", str(wf), "--output", str(out)])

        assert result.exit_code == 1
        assert not out.exists(), "No output directory should be created on failure"

    def test_generate_semantic_error_exits_1(self, tmp_path: Path) -> None:
        """rsf generate with a semantically invalid workflow exits 1."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(INVALID_DANGLING_NEXT, encoding="utf-8")
        out = tmp_path / "out"

        result = runner.invoke(app, ["generate", str(wf), "--output", str(out)])

        assert result.exit_code == 1
        assert "Nonexistent" in result.output

    def test_generate_file_not_found_exits_1(self, tmp_path: Path) -> None:
        """rsf generate with a missing file exits 1 with a clear error message."""
        missing = tmp_path / "nonexistent.yaml"

        result = runner.invoke(app, ["generate", str(missing)])

        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "Error" in result.output

    def test_generate_default_workflow_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """rsf generate with no argument defaults to workflow.yaml in cwd."""
        monkeypatch.chdir(tmp_path)
        wf = tmp_path / "workflow.yaml"
        wf.write_text(VALID_WORKFLOW, encoding="utf-8")

        # No explicit workflow argument — defaults to "workflow.yaml"
        result = runner.invoke(app, ["generate"])

        # If cwd has workflow.yaml, it should succeed
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"
        assert (
            (tmp_path / "orchestrator.py").exists()
            or (tmp_path / "out" / "orchestrator.py").exists()
            or any(p.name == "orchestrator.py" for p in tmp_path.rglob("orchestrator.py"))
        )

    def test_generate_multi_task_creates_multiple_handlers(self, tmp_path: Path) -> None:
        """rsf generate creates one handler stub per Task state."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(VALID_WORKFLOW_MULTI_TASK, encoding="utf-8")
        out = tmp_path / "out"

        result = runner.invoke(app, ["generate", str(wf), "--output", str(out)])

        assert result.exit_code == 0, f"Expected exit 0: {result.output}"
        assert (out / "orchestrator.py").exists()
        assert (out / "handlers" / "step_one.py").exists(), "step_one handler should be created"
        assert (out / "handlers" / "step_two.py").exists(), "step_two handler should be created"

    def test_generate_output_mentions_handler_count(self, tmp_path: Path) -> None:
        """rsf generate prints a summary mentioning how many handlers were created/skipped."""
        wf = tmp_path / "workflow.yaml"
        wf.write_text(VALID_WORKFLOW, encoding="utf-8")
        out = tmp_path / "out"

        result = runner.invoke(app, ["generate", str(wf), "--output", str(out)])

        assert result.exit_code == 0
        # Summary line must mention handler count
        assert "handler" in result.output.lower()
