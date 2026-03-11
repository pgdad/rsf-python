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


def _mock_provider(*, prereq_pass: bool = True):
    """Create a mock provider with generate, deploy, and check_prerequisites.

    Args:
        prereq_pass: When True (default), check_prerequisites returns all-pass.
                     When False, returns a failing prerequisite check.
    """
    from rsf.providers.base import PrerequisiteCheck

    mock = MagicMock()
    mock.generate.return_value = None
    mock.deploy.return_value = None

    if prereq_pass:
        mock.check_prerequisites.return_value = [
            PrerequisiteCheck("terraform", "pass", "terraform found"),
        ]
    else:
        mock.check_prerequisites.return_value = [
            PrerequisiteCheck("terraform", "fail", "terraform not found"),
        ]
    return mock


def test_deploy_full_happy_path(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy with valid workflow and mocked provider exits 0."""
    monkeypatch.chdir(workflow_dir)

    mock_provider = _mock_provider()
    with (
        patch("rsf.cli.deploy_cmd.get_provider", return_value=mock_provider),
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )

        result = runner.invoke(app, ["deploy", "workflow.yaml"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    assert "Deploy complete" in result.output

    # Verify provider methods called
    mock_provider.generate.assert_called_once()
    mock_provider.deploy.assert_called_once()


def test_deploy_auto_approve(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy --auto-approve passes auto_approve=True in ProviderContext."""
    monkeypatch.chdir(workflow_dir)

    mock_provider = _mock_provider()
    with (
        patch("rsf.cli.deploy_cmd.get_provider", return_value=mock_provider),
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )

        result = runner.invoke(app, ["deploy", "--auto-approve", "workflow.yaml"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"

    # Check ProviderContext passed to deploy has auto_approve=True
    ctx = mock_provider.deploy.call_args[0][0]
    assert ctx.auto_approve is True


def test_deploy_auto_approve_short_flag(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy -y is an alias for --auto-approve."""
    monkeypatch.chdir(workflow_dir)

    mock_provider = _mock_provider()
    with (
        patch("rsf.cli.deploy_cmd.get_provider", return_value=mock_provider),
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )

        result = runner.invoke(app, ["deploy", "-y", "workflow.yaml"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    ctx = mock_provider.deploy.call_args[0][0]
    assert ctx.auto_approve is True


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

    # Only one subprocess call (targeted apply -- no init)
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


def test_deploy_provider_prerequisite_failure(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy exits 1 when provider prerequisite check fails."""
    monkeypatch.chdir(workflow_dir)

    mock_provider = _mock_provider(prereq_pass=False)
    with (
        patch("rsf.cli.deploy_cmd.get_provider", return_value=mock_provider),
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )

        result = runner.invoke(app, ["deploy", "workflow.yaml"])

    assert result.exit_code == 1, f"Expected exit 1, got: {result.exit_code}"
    assert "terraform" in result.output.lower()


def test_deploy_subprocess_error(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy exits 1 when provider deploy fails with CalledProcessError."""
    monkeypatch.chdir(workflow_dir)

    mock_provider = _mock_provider()
    mock_provider.deploy.side_effect = subprocess.CalledProcessError(1, "terraform apply")
    with (
        patch("rsf.cli.deploy_cmd.get_provider", return_value=mock_provider),
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )

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
    """rsf deploy --help shows --code-only, --auto-approve, and --output-dir options."""
    result = runner.invoke(app, ["deploy", "--help"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    # Strip ANSI escape codes -- Typer/Rich inserts them in CI
    import re

    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--code-only" in plain
    assert "--auto-approve" in plain
    assert "--output-dir" in plain


# -- --no-infra flag tests --


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


def test_deploy_no_infra_and_code_only_mutually_exclusive(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy --no-infra --code-only exits 1 with a mutual exclusion error."""
    monkeypatch.chdir(workflow_dir)

    result = runner.invoke(app, ["deploy", "--no-infra", "--code-only", "workflow.yaml"])

    assert result.exit_code == 1, f"Expected exit 1, got: {result.exit_code}: {result.output}"
    assert "mutually exclusive" in result.output.lower() or "no-infra" in result.output.lower()


def test_deploy_without_no_infra_still_calls_provider(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy (without --no-infra) still calls provider as before."""
    monkeypatch.chdir(workflow_dir)

    mock_provider = _mock_provider()
    with (
        patch("rsf.cli.deploy_cmd.get_provider", return_value=mock_provider),
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )

        result = runner.invoke(app, ["deploy", "workflow.yaml"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    # provider should have been called (generate + deploy)
    assert mock_provider.generate.call_count == 1
    assert mock_provider.deploy.call_count == 1


def test_deploy_help_shows_no_infra_option() -> None:
    """rsf deploy --help shows --no-infra option."""
    result = runner.invoke(app, ["deploy", "--help"])

    assert result.exit_code == 0
    import re

    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--no-infra" in plain


# -- --output-dir and --tf-dir tests --


def test_deploy_output_dir_option(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy --output-dir custom uses custom output directory."""
    monkeypatch.chdir(workflow_dir)

    mock_provider = _mock_provider()
    with (
        patch("rsf.cli.deploy_cmd.get_provider", return_value=mock_provider),
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )

        result = runner.invoke(app, ["deploy", "--output-dir", "custom_tf", "workflow.yaml"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    ctx = mock_provider.generate.call_args[0][0]
    assert str(ctx.output_dir).endswith("custom_tf")


def test_deploy_tf_dir_alias_still_works(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy --tf-dir custom still works as hidden alias."""
    monkeypatch.chdir(workflow_dir)

    mock_provider = _mock_provider()
    with (
        patch("rsf.cli.deploy_cmd.get_provider", return_value=mock_provider),
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )

        result = runner.invoke(app, ["deploy", "--tf-dir", "legacy_tf", "workflow.yaml"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    ctx = mock_provider.generate.call_args[0][0]
    assert str(ctx.output_dir).endswith("legacy_tf")


# -- Provider dispatch tests --


def test_deploy_code_only_non_terraform_errors(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy --code-only with non-terraform provider errors."""
    monkeypatch.chdir(workflow_dir)
    # Write workflow with CDK provider
    wf = workflow_dir / "workflow.yaml"
    wf.write_text(
        MINIMAL_WORKFLOW_YAML + "infrastructure:\n  provider: cdk\n",
        encoding="utf-8",
    )

    mock_provider = _mock_provider()
    with (
        patch("rsf.cli.deploy_cmd.get_provider", return_value=mock_provider),
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )

        result = runner.invoke(app, ["deploy", "--code-only", "workflow.yaml"])

    assert result.exit_code == 1, f"Expected exit 1, got: {result.exit_code}"
    assert "--code-only" in result.output
    assert "terraform" in result.output.lower()


def test_deploy_unknown_provider_errors(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy with unknown provider in infrastructure: block errors."""
    monkeypatch.chdir(workflow_dir)
    # Write workflow with unknown provider
    wf = workflow_dir / "workflow.yaml"
    wf.write_text(
        MINIMAL_WORKFLOW_YAML + "infrastructure:\n  provider: pulumi\n",
        encoding="utf-8",
    )

    with (
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )

        result = runner.invoke(app, ["deploy", "workflow.yaml"])

    assert result.exit_code == 1, f"Expected exit 1, got: {result.exit_code}"
    assert "Error" in result.output


# -- --stage flag tests --


class TestStageDeployment:
    """Tests for multi-stage deployment via --stage option."""

    def test_deploy_stage_prod_uses_stage_var_file(self, workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """rsf deploy --stage prod looks for stages/prod.tfvars file."""
        monkeypatch.chdir(workflow_dir)
        # Create stage var file
        stages_dir = workflow_dir / "stages"
        stages_dir.mkdir()
        (stages_dir / "prod.tfvars").write_text('name_prefix = "rsf-prod"\n')

        mock_provider = _mock_provider()
        with (
            patch("rsf.cli.deploy_cmd.get_provider", return_value=mock_provider),
            patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
        ):
            mock_codegen.return_value = MagicMock(
                orchestrator_path=workflow_dir / "orchestrator.py",
                handler_paths=[],
                skipped_handlers=[],
            )

            result = runner.invoke(app, ["deploy", "--stage", "prod", "workflow.yaml"])

        assert result.exit_code == 0, f"Unexpected exit: {result.output}"
        assert "Deploy complete" in result.output

    def test_deploy_stage_dev_uses_stage_var_file(self, workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """rsf deploy --stage dev looks for stages/dev.tfvars file."""
        monkeypatch.chdir(workflow_dir)
        stages_dir = workflow_dir / "stages"
        stages_dir.mkdir()
        (stages_dir / "dev.tfvars").write_text('name_prefix = "rsf-dev"\n')

        mock_provider = _mock_provider()
        with (
            patch("rsf.cli.deploy_cmd.get_provider", return_value=mock_provider),
            patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
        ):
            mock_codegen.return_value = MagicMock(
                orchestrator_path=workflow_dir / "orchestrator.py",
                handler_paths=[],
                skipped_handlers=[],
            )

            result = runner.invoke(app, ["deploy", "--stage", "dev", "workflow.yaml"])

        assert result.exit_code == 0, f"Unexpected exit: {result.output}"

    def test_deploy_without_stage_no_var_file(self, workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """rsf deploy without --stage works as before (no -var-file passed)."""
        monkeypatch.chdir(workflow_dir)

        mock_provider = _mock_provider()
        with (
            patch("rsf.cli.deploy_cmd.get_provider", return_value=mock_provider),
            patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
        ):
            mock_codegen.return_value = MagicMock(
                orchestrator_path=workflow_dir / "orchestrator.py",
                handler_paths=[],
                skipped_handlers=[],
            )

            result = runner.invoke(app, ["deploy", "workflow.yaml"])

        assert result.exit_code == 0, f"Unexpected exit: {result.output}"
        # Verify no stage_var_file in ProviderContext
        ctx = mock_provider.deploy.call_args[0][0]
        assert ctx.stage_var_file is None

    def test_deploy_stage_missing_var_file_errors(self, workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    def test_deploy_stage_passes_stage_var_file_to_provider(
        self, workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """rsf deploy --stage prod passes stage_var_file in ProviderContext."""
        monkeypatch.chdir(workflow_dir)
        stages_dir = workflow_dir / "stages"
        stages_dir.mkdir()
        (stages_dir / "prod.tfvars").write_text('name_prefix = "rsf-prod"\n')

        mock_provider = _mock_provider()
        with (
            patch("rsf.cli.deploy_cmd.get_provider", return_value=mock_provider),
            patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
        ):
            mock_codegen.return_value = MagicMock(
                orchestrator_path=workflow_dir / "orchestrator.py",
                handler_paths=[],
                skipped_handlers=[],
            )

            result = runner.invoke(app, ["deploy", "--stage", "prod", "workflow.yaml"])

        assert result.exit_code == 0, f"Unexpected exit: {result.output}"
        # Check ProviderContext has stage_var_file
        ctx = mock_provider.deploy.call_args[0][0]
        assert ctx.stage_var_file is not None
        assert "prod.tfvars" in str(ctx.stage_var_file)

    def test_deploy_stage_no_var_file_in_terraform_init(
        self, workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """rsf deploy --stage prod passes stage info through ProviderContext (not init)."""
        monkeypatch.chdir(workflow_dir)
        stages_dir = workflow_dir / "stages"
        stages_dir.mkdir()
        (stages_dir / "prod.tfvars").write_text('name_prefix = "rsf-prod"\n')

        mock_provider = _mock_provider()
        with (
            patch("rsf.cli.deploy_cmd.get_provider", return_value=mock_provider),
            patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
        ):
            mock_codegen.return_value = MagicMock(
                orchestrator_path=workflow_dir / "orchestrator.py",
                handler_paths=[],
                skipped_handlers=[],
            )

            result = runner.invoke(app, ["deploy", "--stage", "prod", "workflow.yaml"])

        assert result.exit_code == 0, f"Unexpected exit: {result.output}"
        # Provider handles init/apply internally -- we just verify it was called
        mock_provider.deploy.assert_called_once()

    def test_deploy_stage_with_no_infra_ignores_stage(
        self, workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """rsf deploy --stage prod --no-infra generates code only, ignores stage."""
        monkeypatch.chdir(workflow_dir)
        # No stages dir needed -- --no-infra returns before stage var file check

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

    def test_deploy_stage_isolates_output_dir(self, workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """rsf deploy --stage prod uses terraform/prod/ directory for isolation."""
        monkeypatch.chdir(workflow_dir)
        stages_dir = workflow_dir / "stages"
        stages_dir.mkdir()
        (stages_dir / "prod.tfvars").write_text('name_prefix = "rsf-prod"\n')

        mock_provider = _mock_provider()
        with (
            patch("rsf.cli.deploy_cmd.get_provider", return_value=mock_provider),
            patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
        ):
            mock_codegen.return_value = MagicMock(
                orchestrator_path=workflow_dir / "orchestrator.py",
                handler_paths=[],
                skipped_handlers=[],
            )

            result = runner.invoke(app, ["deploy", "--stage", "prod", "workflow.yaml"])

        assert result.exit_code == 0, f"Unexpected exit: {result.output}"
        # Verify provider received output_dir ending in /prod
        ctx = mock_provider.generate.call_args[0][0]
        assert str(ctx.output_dir).endswith("prod"), f"Expected output_dir to end with 'prod', got: {ctx.output_dir}"


# -- --teardown flag tests --


def test_deploy_teardown_calls_provider_teardown(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy --teardown calls provider.teardown(ctx) and exits 0 with 'Teardown complete'."""
    monkeypatch.chdir(workflow_dir)

    mock_provider = _mock_provider()
    mock_provider.teardown.return_value = None
    with (
        patch("rsf.cli.deploy_cmd.get_provider", return_value=mock_provider),
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )

        result = runner.invoke(app, ["deploy", "--teardown", "workflow.yaml"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    assert "Teardown complete" in result.output
    mock_provider.teardown.assert_called_once()


def test_deploy_teardown_exits_nonzero_on_subprocess_error(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """provider.teardown() raises CalledProcessError -> exit 1 with 'Infrastructure teardown failed'."""
    monkeypatch.chdir(workflow_dir)

    mock_provider = _mock_provider()
    mock_provider.teardown.side_effect = subprocess.CalledProcessError(1, "terraform destroy")
    with (
        patch("rsf.cli.deploy_cmd.get_provider", return_value=mock_provider),
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )

        result = runner.invoke(app, ["deploy", "--teardown", "workflow.yaml"])

    assert result.exit_code == 1, f"Expected exit 1, got: {result.exit_code}"
    assert "teardown failed" in result.output.lower() or "Infrastructure teardown failed" in result.output


def test_deploy_teardown_not_implemented_errors_gracefully(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """provider.teardown() raises NotImplementedError -> exit 1 with error message."""
    monkeypatch.chdir(workflow_dir)

    mock_provider = _mock_provider()
    mock_provider.teardown.side_effect = NotImplementedError("teardown not supported")
    with (
        patch("rsf.cli.deploy_cmd.get_provider", return_value=mock_provider),
        patch("rsf.cli.deploy_cmd.codegen_generate") as mock_codegen,
    ):
        mock_codegen.return_value = MagicMock(
            orchestrator_path=workflow_dir / "orchestrator.py",
            handler_paths=[],
            skipped_handlers=[],
        )

        result = runner.invoke(app, ["deploy", "--teardown", "workflow.yaml"])

    assert result.exit_code == 1, f"Expected exit 1, got: {result.exit_code}"
    assert "Error" in result.output or "not supported" in result.output.lower()


def test_deploy_teardown_mutually_exclusive_with_code_only(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy --teardown --code-only -> exit 1 with mutual exclusion error."""
    monkeypatch.chdir(workflow_dir)

    result = runner.invoke(app, ["deploy", "--teardown", "--code-only", "workflow.yaml"])

    assert result.exit_code == 1, f"Expected exit 1, got: {result.exit_code}"
    assert "mutually exclusive" in result.output.lower() or "teardown" in result.output.lower()


def test_deploy_teardown_mutually_exclusive_with_no_infra(workflow_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """rsf deploy --teardown --no-infra -> exit 1 with mutual exclusion error."""
    monkeypatch.chdir(workflow_dir)

    result = runner.invoke(app, ["deploy", "--teardown", "--no-infra", "workflow.yaml"])

    assert result.exit_code == 1, f"Expected exit 1, got: {result.exit_code}"
    assert "mutually exclusive" in result.output.lower() or "teardown" in result.output.lower()


def test_deploy_help_shows_teardown_option() -> None:
    """rsf deploy --help output contains '--teardown'."""
    result = runner.invoke(app, ["deploy", "--help"])

    assert result.exit_code == 0
    import re

    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--teardown" in plain
