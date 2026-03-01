"""Tests for the RSF deploy subcommand."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from rsf.cli.main import app

runner = CliRunner()

# Minimal valid workflow YAML
MINIMAL_WORKFLOW_YAML = """\
rsf_version: "1.0"
Comment: test-workflow
StartAt: Hello
States:
  Hello:
    Type: Pass
    End: true
"""


@pytest.fixture()
def workflow_dir(tmp_path: Path) -> Path:
    """Create a tmp directory with a valid workflow.yaml."""
    wf = tmp_path / "workflow.yaml"
    wf.write_text(MINIMAL_WORKFLOW_YAML, encoding="utf-8")
    return tmp_path


def test_deploy_full_happy_path(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy with valid workflow and mocked terraform exits 0, calls init then apply."""
    monkeypatch.chdir(workflow_dir)

    with (
        patch("rsf.cli.deploy_cmd.shutil.which", return_value="/usr/bin/terraform"),
        patch("rsf.cli.deploy_cmd.subprocess.run") as mock_run,
        patch("rsf.cli.deploy_cmd.generate_terraform") as mock_tf,
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        # Set up mocks
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )
        mock_tf.return_value = MagicMock(generated_files=[], skipped_files=[])
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(app, ["deploy", "workflow.yaml"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    assert "Deploy complete" in result.output

    # Verify subprocess.run called with terraform init then terraform apply (no -auto-approve)
    calls = mock_run.call_args_list
    assert len(calls) == 2
    init_call = calls[0]
    apply_call = calls[1]
    assert init_call[0][0] == ["terraform", "init"]
    assert apply_call[0][0] == ["terraform", "apply"]


def test_deploy_auto_approve(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy --auto-approve passes -auto-approve flag to terraform apply."""
    monkeypatch.chdir(workflow_dir)

    with (
        patch("rsf.cli.deploy_cmd.shutil.which", return_value="/usr/bin/terraform"),
        patch("rsf.cli.deploy_cmd.subprocess.run") as mock_run,
        patch("rsf.cli.deploy_cmd.generate_terraform") as mock_tf,
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )
        mock_tf.return_value = MagicMock(generated_files=[], skipped_files=[])
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(app, ["deploy", "--auto-approve", "workflow.yaml"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"

    calls = mock_run.call_args_list
    assert len(calls) == 2
    apply_call = calls[1]
    assert apply_call[0][0] == ["terraform", "apply", "-auto-approve"]


def test_deploy_auto_approve_short_flag(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy -y is an alias for --auto-approve."""
    monkeypatch.chdir(workflow_dir)

    with (
        patch("rsf.cli.deploy_cmd.shutil.which", return_value="/usr/bin/terraform"),
        patch("rsf.cli.deploy_cmd.subprocess.run") as mock_run,
        patch("rsf.cli.deploy_cmd.generate_terraform") as mock_tf,
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )
        mock_tf.return_value = MagicMock(generated_files=[], skipped_files=[])
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(app, ["deploy", "-y", "workflow.yaml"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    calls = mock_run.call_args_list
    assert len(calls) == 2
    apply_call = calls[1]
    assert "-auto-approve" in apply_call[0][0]


def test_deploy_code_only(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy --code-only uses -target flag and skips full Terraform apply."""
    monkeypatch.chdir(workflow_dir)
    # Create tf_dir so it exists
    tf_dir = workflow_dir / "terraform"
    tf_dir.mkdir()

    with (
        patch("rsf.cli.deploy_cmd.shutil.which", return_value="/usr/bin/terraform"),
        patch("rsf.cli.deploy_cmd.subprocess.run") as mock_run,
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(app, ["deploy", "--code-only", "workflow.yaml"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    assert "Code update complete" in result.output

    # Only one subprocess call (targeted apply — no init)
    calls = mock_run.call_args_list
    assert len(calls) == 1
    targeted_call = calls[0]
    cmd = targeted_call[0][0]
    assert cmd[0] == "terraform"
    assert cmd[1] == "apply"
    assert any("-target" in arg for arg in cmd)
    assert "-auto-approve" in cmd


def test_deploy_no_workflow_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy with no workflow.yaml exits 1 with an error message."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["deploy", "workflow.yaml"])

    assert result.exit_code == 1, f"Expected exit 1, got: {result.exit_code}"
    assert "Error" in result.output
    assert "workflow.yaml" in result.output


def test_deploy_terraform_not_in_path(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy exits 1 and mentions terraform when terraform binary not found."""
    monkeypatch.chdir(workflow_dir)

    with (
        patch("rsf.cli.deploy_cmd.shutil.which", return_value=None),
        patch("rsf.cli.deploy_cmd.generate_terraform") as mock_tf,
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )
        mock_tf.return_value = MagicMock(generated_files=[], skipped_files=[])

        result = runner.invoke(app, ["deploy", "workflow.yaml"])

    assert result.exit_code == 1, f"Expected exit 1, got: {result.exit_code}"
    assert "terraform" in result.output.lower()


def test_deploy_subprocess_error(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy exits 1 when terraform subprocess fails with CalledProcessError."""
    monkeypatch.chdir(workflow_dir)

    with (
        patch("rsf.cli.deploy_cmd.shutil.which", return_value="/usr/bin/terraform"),
        patch("rsf.cli.deploy_cmd.subprocess.run") as mock_run,
        patch("rsf.cli.deploy_cmd.generate_terraform") as mock_tf,
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )
        mock_tf.return_value = MagicMock(generated_files=[], skipped_files=[])
        mock_run.side_effect = subprocess.CalledProcessError(1, "terraform init")

        result = runner.invoke(app, ["deploy", "workflow.yaml"])

    assert result.exit_code == 1, f"Expected exit 1, got: {result.exit_code}"
    assert "Error" in result.output


def test_deploy_code_only_no_terraform_dir(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy --code-only exits 1 when tf_dir doesn't exist."""
    monkeypatch.chdir(workflow_dir)
    # Note: do NOT create tf_dir

    with (
        patch("rsf.cli.deploy_cmd.shutil.which", return_value="/usr/bin/terraform"),
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )

        result = runner.invoke(app, ["deploy", "--code-only", "workflow.yaml"])

    assert result.exit_code == 1, f"Expected exit 1, got: {result.exit_code}"
    assert "Error" in result.output


def test_deploy_help_shows_all_options(monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy --help shows --code-only, --auto-approve, and --tf-dir options."""
    result = runner.invoke(app, ["deploy", "--help"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    # Strip ANSI escape codes — Typer/Rich inserts them in CI
    import re

    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--code-only" in plain
    assert "--auto-approve" in plain
    assert "--tf-dir" in plain


# ── --no-infra flag tests ─────────────────────────────────────────────────────


def test_deploy_no_infra_skips_terraform(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy --no-infra generates code but does NOT call terraform."""
    monkeypatch.chdir(workflow_dir)

    with (
        patch("rsf.cli.deploy_cmd.subprocess.run") as mock_run,
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )

        result = runner.invoke(app, ["deploy", "--no-infra", "workflow.yaml"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    # subprocess.run should NOT have been called (no terraform)
    mock_run.assert_not_called()
    # Output should mention infra was skipped
    assert "skipped" in result.output.lower() or "no-infra" in result.output.lower()


def test_deploy_no_infra_and_code_only_mutually_exclusive(
    workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """rsf deploy --no-infra --code-only exits 1 with a mutual exclusion error."""
    monkeypatch.chdir(workflow_dir)

    result = runner.invoke(app, ["deploy", "--no-infra", "--code-only", "workflow.yaml"])

    assert result.exit_code == 1, f"Expected exit 1, got: {result.exit_code}: {result.output}"
    assert "mutually exclusive" in result.output.lower() or "no-infra" in result.output.lower()


def test_deploy_without_no_infra_still_calls_terraform(
    workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """rsf deploy (without --no-infra) still calls terraform as before."""
    monkeypatch.chdir(workflow_dir)

    with (
        patch("rsf.cli.deploy_cmd.shutil.which", return_value="/usr/bin/terraform"),
        patch("rsf.cli.deploy_cmd.subprocess.run") as mock_run,
        patch("rsf.cli.deploy_cmd.generate_terraform") as mock_tf,
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )
        mock_tf.return_value = MagicMock(generated_files=[], skipped_files=[])
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(app, ["deploy", "workflow.yaml"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    # terraform should have been called (init + apply)
    assert mock_run.call_count == 2


def test_deploy_help_shows_no_infra_option() -> None:
    """rsf deploy --help shows --no-infra option."""
    result = runner.invoke(app, ["deploy", "--help"])

    assert result.exit_code == 0
    import re

    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--no-infra" in plain


# ── --stage flag tests ───────────────────────────────────────────────────────


class TestStageDeployment:
    """Tests for multi-stage deployment via --stage option."""

    def test_deploy_stage_prod_uses_stage_var_file(
        self, workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """rsf deploy --stage prod looks for stages/prod.tfvars file."""
        monkeypatch.chdir(workflow_dir)
        # Create stage var file
        stages_dir = workflow_dir / "stages"
        stages_dir.mkdir()
        (stages_dir / "prod.tfvars").write_text('name_prefix = "rsf-prod"\n')

        with (
            patch("rsf.cli.deploy_cmd.shutil.which", return_value="/usr/bin/terraform"),
            patch("rsf.cli.deploy_cmd.subprocess.run") as mock_run,
            patch("rsf.cli.deploy_cmd.generate_terraform") as mock_tf,
            patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
        ):
            mock_codegen.return_value = MagicMock(
                orchestrator_path=workflow_dir / "orchestrator.py",
                handler_paths=[],
                skipped_handlers=[],
            )
            mock_tf.return_value = MagicMock(generated_files=[], skipped_files=[])
            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(app, ["deploy", "--stage", "prod", "workflow.yaml"])

        assert result.exit_code == 0, f"Unexpected exit: {result.output}"
        assert "Deploy complete" in result.output

    def test_deploy_stage_dev_uses_stage_var_file(
        self, workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """rsf deploy --stage dev looks for stages/dev.tfvars file."""
        monkeypatch.chdir(workflow_dir)
        stages_dir = workflow_dir / "stages"
        stages_dir.mkdir()
        (stages_dir / "dev.tfvars").write_text('name_prefix = "rsf-dev"\n')

        with (
            patch("rsf.cli.deploy_cmd.shutil.which", return_value="/usr/bin/terraform"),
            patch("rsf.cli.deploy_cmd.subprocess.run") as mock_run,
            patch("rsf.cli.deploy_cmd.generate_terraform") as mock_tf,
            patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
        ):
            mock_codegen.return_value = MagicMock(
                orchestrator_path=workflow_dir / "orchestrator.py",
                handler_paths=[],
                skipped_handlers=[],
            )
            mock_tf.return_value = MagicMock(generated_files=[], skipped_files=[])
            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(app, ["deploy", "--stage", "dev", "workflow.yaml"])

        assert result.exit_code == 0, f"Unexpected exit: {result.output}"

    def test_deploy_without_stage_no_var_file(
        self, workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """rsf deploy without --stage works as before (no -var-file passed)."""
        monkeypatch.chdir(workflow_dir)

        with (
            patch("rsf.cli.deploy_cmd.shutil.which", return_value="/usr/bin/terraform"),
            patch("rsf.cli.deploy_cmd.subprocess.run") as mock_run,
            patch("rsf.cli.deploy_cmd.generate_terraform") as mock_tf,
            patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
        ):
            mock_codegen.return_value = MagicMock(
                orchestrator_path=workflow_dir / "orchestrator.py",
                handler_paths=[],
                skipped_handlers=[],
            )
            mock_tf.return_value = MagicMock(generated_files=[], skipped_files=[])
            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(app, ["deploy", "workflow.yaml"])

        assert result.exit_code == 0, f"Unexpected exit: {result.output}"
        # Verify no -var-file in any terraform command
        for call in mock_run.call_args_list:
            cmd = call[0][0]
            assert "-var-file" not in cmd

    def test_deploy_stage_missing_var_file_errors(
        self, workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """rsf deploy --stage prod with missing prod.tfvars prints error and exits."""
        monkeypatch.chdir(workflow_dir)
        # Do NOT create stages/prod.tfvars

        with (
            patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
        ):
            mock_codegen.return_value = MagicMock(
                orchestrator_path=workflow_dir / "orchestrator.py",
                handler_paths=[],
                skipped_handlers=[],
            )

            result = runner.invoke(app, ["deploy", "--stage", "prod", "workflow.yaml"])

        assert result.exit_code == 1, f"Expected exit 1, got: {result.exit_code}"
        assert "Stage variable file not found" in result.output

    def test_deploy_stage_passes_var_file_to_terraform_apply(
        self, workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """rsf deploy --stage prod passes -var-file=stages/prod.tfvars to terraform apply."""
        monkeypatch.chdir(workflow_dir)
        stages_dir = workflow_dir / "stages"
        stages_dir.mkdir()
        (stages_dir / "prod.tfvars").write_text('name_prefix = "rsf-prod"\n')

        with (
            patch("rsf.cli.deploy_cmd.shutil.which", return_value="/usr/bin/terraform"),
            patch("rsf.cli.deploy_cmd.subprocess.run") as mock_run,
            patch("rsf.cli.deploy_cmd.generate_terraform") as mock_tf,
            patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
        ):
            mock_codegen.return_value = MagicMock(
                orchestrator_path=workflow_dir / "orchestrator.py",
                handler_paths=[],
                skipped_handlers=[],
            )
            mock_tf.return_value = MagicMock(generated_files=[], skipped_files=[])
            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(app, ["deploy", "--stage", "prod", "workflow.yaml"])

        assert result.exit_code == 0, f"Unexpected exit: {result.output}"
        # Check terraform apply call has -var-file
        calls = mock_run.call_args_list
        apply_call = calls[1]  # second call is terraform apply
        cmd = apply_call[0][0]
        assert "-var-file" in cmd
        # The var file path should contain prod.tfvars
        var_file_idx = cmd.index("-var-file")
        assert "prod.tfvars" in cmd[var_file_idx + 1]

    def test_deploy_stage_no_var_file_in_terraform_init(
        self, workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """rsf deploy --stage does NOT pass -var-file to terraform init (init doesn't support it)."""
        monkeypatch.chdir(workflow_dir)
        stages_dir = workflow_dir / "stages"
        stages_dir.mkdir()
        (stages_dir / "prod.tfvars").write_text('name_prefix = "rsf-prod"\n')

        with (
            patch("rsf.cli.deploy_cmd.shutil.which", return_value="/usr/bin/terraform"),
            patch("rsf.cli.deploy_cmd.subprocess.run") as mock_run,
            patch("rsf.cli.deploy_cmd.generate_terraform") as mock_tf,
            patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
        ):
            mock_codegen.return_value = MagicMock(
                orchestrator_path=workflow_dir / "orchestrator.py",
                handler_paths=[],
                skipped_handlers=[],
            )
            mock_tf.return_value = MagicMock(generated_files=[], skipped_files=[])
            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(app, ["deploy", "--stage", "prod", "workflow.yaml"])

        assert result.exit_code == 0, f"Unexpected exit: {result.output}"
        # First call is terraform init — should NOT have -var-file
        init_call = mock_run.call_args_list[0]
        init_cmd = init_call[0][0]
        assert init_cmd == ["terraform", "init"]

    def test_deploy_stage_with_no_infra_ignores_stage(
        self, workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """rsf deploy --stage prod --no-infra generates code only, ignores stage."""
        monkeypatch.chdir(workflow_dir)
        # No stages dir needed — --no-infra returns before stage var file check

        with (
            patch("rsf.cli.deploy_cmd.subprocess.run") as mock_run,
            patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
        ):
            mock_codegen.return_value = MagicMock(
                orchestrator_path=workflow_dir / "orchestrator.py",
                handler_paths=[],
                skipped_handlers=[],
            )

            result = runner.invoke(app, ["deploy", "--stage", "prod", "--no-infra", "workflow.yaml"])

        assert result.exit_code == 0, f"Unexpected exit: {result.output}"
        mock_run.assert_not_called()

    def test_deploy_stage_isolates_tf_dir(
        self, workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """rsf deploy --stage prod uses terraform/prod/ directory for isolation."""
        monkeypatch.chdir(workflow_dir)
        stages_dir = workflow_dir / "stages"
        stages_dir.mkdir()
        (stages_dir / "prod.tfvars").write_text('name_prefix = "rsf-prod"\n')

        with (
            patch("rsf.cli.deploy_cmd.shutil.which", return_value="/usr/bin/terraform"),
            patch("rsf.cli.deploy_cmd.subprocess.run") as mock_run,
            patch("rsf.cli.deploy_cmd.generate_terraform") as mock_tf,
            patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
        ):
            mock_codegen.return_value = MagicMock(
                orchestrator_path=workflow_dir / "orchestrator.py",
                handler_paths=[],
                skipped_handlers=[],
            )
            mock_tf.return_value = MagicMock(generated_files=[], skipped_files=[])
            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(app, ["deploy", "--stage", "prod", "workflow.yaml"])

        assert result.exit_code == 0, f"Unexpected exit: {result.output}"
        # Verify generate_terraform was called with output_dir ending in /prod
        tf_call = mock_tf.call_args
        output_dir = tf_call.kwargs.get("output_dir") or tf_call[1].get("output_dir")
        assert str(output_dir).endswith("prod"), f"Expected tf_dir to end with 'prod', got: {output_dir}"
