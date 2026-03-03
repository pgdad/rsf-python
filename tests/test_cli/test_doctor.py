"""Tests for rsf doctor CLI command."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


from rsf.cli.doctor_cmd import (
    CheckResult,
    _check_aws_credentials,
    _check_boto3,
    _check_directory,
    _check_python,
    _check_terraform,
    _check_workflow,
    run_all_checks,
)


# --- CheckResult tests ---


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_dataclass_fields(self) -> None:
        """Test 1: CheckResult holds all expected fields."""
        result = CheckResult(
            name="Python",
            status="PASS",
            version="3.12.3",
            message="Python 3.12.3",
            fix_hint=None,
        )
        assert result.name == "Python"
        assert result.status == "PASS"
        assert result.version == "3.12.3"
        assert result.message == "Python 3.12.3"
        assert result.fix_hint is None


# --- Python check tests ---


class TestCheckPython:
    """Tests for _check_python."""

    def test_pass_for_310_plus(self) -> None:
        """Test 2: Returns PASS when sys.version_info >= (3, 10)."""
        with patch.object(sys, "version_info", (3, 12, 3, "final", 0)):
            result = _check_python()
            assert result.status == "PASS"
            assert result.version == "3.12.3"

    def test_warn_for_38_39(self) -> None:
        """Test 3: Returns WARN when version is 3.8 or 3.9."""
        with patch.object(sys, "version_info", (3, 9, 1, "final", 0)):
            result = _check_python()
            assert result.status == "WARN"
            assert "3.10" in result.message


# --- Terraform check tests ---


class TestCheckTerraform:
    """Tests for _check_terraform."""

    def test_pass_when_found_and_version_ge_1(self) -> None:
        """Test 4: Returns PASS when binary found and version >= 1.0."""
        mock_proc = MagicMock()
        mock_proc.stdout = "Terraform v1.5.7\n"

        with (
            patch("shutil.which", return_value="/usr/bin/terraform"),
            patch("subprocess.run", return_value=mock_proc),
        ):
            result = _check_terraform()
            assert result.status == "PASS"
            assert result.version == "1.5.7"

    def test_fail_when_not_found(self) -> None:
        """Test 5: Returns FAIL with fix hint when not found."""
        with patch("shutil.which", return_value=None):
            result = _check_terraform()
            assert result.status == "FAIL"
            assert result.fix_hint is not None
            assert "terraform" in result.fix_hint.lower()


# --- AWS credentials check tests ---


class TestCheckAwsCredentials:
    """Tests for _check_aws_credentials."""

    def test_pass_when_valid(self) -> None:
        """Test 6: Returns PASS when boto3 session has valid credentials."""
        mock_frozen = MagicMock()
        mock_frozen.access_key = "AKIA..."

        mock_credentials = MagicMock()
        mock_credentials.get_frozen_credentials.return_value = mock_frozen

        mock_session = MagicMock()
        mock_session.get_credentials.return_value = mock_credentials

        with patch("boto3.Session", return_value=mock_session):
            result = _check_aws_credentials()
            assert result.status == "PASS"

    def test_fail_when_no_credentials(self) -> None:
        """Test 7: Returns FAIL when no credentials available."""
        mock_session = MagicMock()
        mock_session.get_credentials.return_value = None

        with patch("boto3.Session", return_value=mock_session):
            result = _check_aws_credentials()
            assert result.status == "FAIL"


# --- boto3 check tests ---


class TestCheckBoto3:
    """Tests for _check_boto3."""

    def test_pass_when_importable(self) -> None:
        """Test 8: Returns PASS with version when importable."""
        result = _check_boto3()
        assert result.status == "PASS"
        assert result.version is not None


# --- Workflow check tests ---


class TestCheckWorkflow:
    """Tests for _check_workflow."""

    def test_pass_when_valid(self, tmp_path: Path) -> None:
        """Test 9: Returns PASS when workflow.yaml exists and is valid."""
        workflow = tmp_path / "workflow.yaml"
        workflow.write_text(
            """
StartAt: First
States:
  First:
    Type: Task
    End: true
"""
        )
        result = _check_workflow(workflow)
        assert result.status == "PASS"

    def test_fail_when_missing(self, tmp_path: Path) -> None:
        """Test 10: Returns FAIL when workflow.yaml doesn't exist."""
        result = _check_workflow(tmp_path / "nonexistent.yaml")
        assert result.status == "FAIL"

    def test_warn_when_invalid(self, tmp_path: Path) -> None:
        """Test 11: Returns WARN when workflow.yaml exists but is invalid."""
        workflow = tmp_path / "workflow.yaml"
        workflow.write_text("not a valid workflow: true\n")
        result = _check_workflow(workflow)
        assert result.status == "WARN"
        assert "invalid" in result.message.lower()


# --- Directory check tests ---


class TestCheckDirectory:
    """Tests for _check_directory."""

    def test_pass_when_exists(self, tmp_path: Path) -> None:
        """Test 12: Returns PASS when directory exists."""
        d = tmp_path / "terraform"
        d.mkdir()
        result = _check_directory("terraform/", d)
        assert result.status == "PASS"

    def test_warn_when_missing(self, tmp_path: Path) -> None:
        """Test 12b: Returns WARN when directory missing."""
        result = _check_directory("terraform/", tmp_path / "terraform")
        assert result.status == "WARN"


# --- run_all_checks tests ---


class TestRunAllChecks:
    """Tests for run_all_checks."""

    def test_always_includes_environment_checks(self) -> None:
        """Test 13: Returns all environment checks always present."""
        results = run_all_checks()
        names = {r.name for r in results}
        assert "Python" in names
        assert "Terraform" in names
        assert "AWS Credentials" in names
        assert "boto3 SDK" in names
        assert "AWS CLI" in names

    def test_includes_project_checks_when_path_exists(self, tmp_path: Path) -> None:
        """Test 14: Includes project checks when workflow.yaml path exists."""
        workflow = tmp_path / "workflow.yaml"
        workflow.write_text(
            """
StartAt: First
States:
  First:
    Type: Task
    End: true
"""
        )
        tf_dir = tmp_path / "terraform"
        tf_dir.mkdir()
        handlers_dir = tmp_path / "handlers"

        results = run_all_checks(
            workflow_path=workflow,
            tf_dir=tf_dir,
            handlers_dir=handlers_dir,
        )
        names = {r.name for r in results}
        assert "workflow.yaml" in names
        assert "terraform/" in names
        assert "handlers/" in names


# --- CLI command tests ---


class TestDoctorCommand:
    """Tests for the doctor CLI command."""

    def test_exit_0_when_all_pass(self) -> None:
        """Test 15: All PASS checks exits with code 0."""
        from typer.testing import CliRunner
        from rsf.cli.main import app

        all_pass = [
            CheckResult(name="Python", status="PASS", version="3.12.3"),
            CheckResult(name="Terraform", status="PASS", version="1.5.7"),
            CheckResult(name="AWS Credentials", status="PASS"),
            CheckResult(name="boto3 SDK", status="PASS", version="1.34.0"),
            CheckResult(name="AWS CLI", status="PASS", version="2.15.0"),
        ]

        with patch("rsf.cli.doctor_cmd.run_all_checks", return_value=all_pass):
            runner = CliRunner()
            result = runner.invoke(app, ["doctor", "--no-color"])
            assert result.exit_code == 0

    def test_exit_1_when_any_fail(self) -> None:
        """Test 16: Any FAIL check exits with code 1."""
        from typer.testing import CliRunner
        from rsf.cli.main import app

        with_fail = [
            CheckResult(name="Python", status="PASS", version="3.12.3"),
            CheckResult(name="Terraform", status="FAIL", message="Not found"),
            CheckResult(name="AWS Credentials", status="PASS"),
            CheckResult(name="boto3 SDK", status="PASS"),
            CheckResult(name="AWS CLI", status="PASS"),
        ]

        with patch("rsf.cli.doctor_cmd.run_all_checks", return_value=with_fail):
            runner = CliRunner()
            result = runner.invoke(app, ["doctor", "--no-color"])
            assert result.exit_code == 1

    def test_exit_0_when_only_warn(self) -> None:
        """Test 17: Only WARN checks (no FAIL) exits with code 0."""
        from typer.testing import CliRunner
        from rsf.cli.main import app

        with_warn = [
            CheckResult(name="Python", status="PASS", version="3.12.3"),
            CheckResult(name="Terraform", status="WARN", message="Old version"),
            CheckResult(name="AWS Credentials", status="PASS"),
            CheckResult(name="boto3 SDK", status="PASS"),
            CheckResult(name="AWS CLI", status="WARN", message="Not found"),
        ]

        with patch("rsf.cli.doctor_cmd.run_all_checks", return_value=with_warn):
            runner = CliRunner()
            result = runner.invoke(app, ["doctor", "--no-color"])
            assert result.exit_code == 0

    def test_shows_status_symbols(self) -> None:
        """Test 18: Outputs check names with PASS/WARN/FAIL status."""
        from typer.testing import CliRunner
        from rsf.cli.main import app

        results = [
            CheckResult(name="Python", status="PASS", version="3.12.3"),
            CheckResult(name="Terraform", status="FAIL", message="Not found", fix_hint="Install terraform"),
            CheckResult(name="AWS Credentials", status="PASS"),
            CheckResult(name="boto3 SDK", status="PASS"),
            CheckResult(name="AWS CLI", status="WARN", message="Not found"),
        ]

        with patch("rsf.cli.doctor_cmd.run_all_checks", return_value=results):
            runner = CliRunner()
            result = runner.invoke(app, ["doctor", "--no-color"])
            assert "PASS" in result.output
            assert "FAIL" in result.output
            assert "WARN" in result.output

    def test_json_output(self) -> None:
        """Test 19: --json outputs a valid JSON report."""
        from typer.testing import CliRunner
        from rsf.cli.main import app

        results = [
            CheckResult(name="Python", status="PASS", version="3.12.3", message="Python 3.12.3"),
            CheckResult(name="Terraform", status="PASS", version="1.5.7", message="Terraform 1.5.7"),
            CheckResult(name="AWS Credentials", status="PASS", message="Credentials available"),
            CheckResult(name="boto3 SDK", status="PASS", version="1.34.0", message="boto3 1.34.0"),
            CheckResult(name="AWS CLI", status="PASS", version="2.15.0", message="AWS CLI 2.15.0"),
        ]

        with patch("rsf.cli.doctor_cmd.run_all_checks", return_value=results):
            runner = CliRunner()
            result = runner.invoke(app, ["doctor", "--json"])
            parsed = json.loads(result.output)
            assert "checks" in parsed
            assert "summary" in parsed
            assert len(parsed["checks"]) == 5
            assert parsed["summary"]["total"] == 5
            assert parsed["summary"]["pass"] == 5

    def test_no_color_plain_text(self) -> None:
        """Test 20: --no-color outputs plain text."""
        from typer.testing import CliRunner
        from rsf.cli.main import app

        results = [
            CheckResult(name="Python", status="PASS", version="3.12.3"),
            CheckResult(name="Terraform", status="PASS", version="1.5.7"),
            CheckResult(name="AWS Credentials", status="PASS"),
            CheckResult(name="boto3 SDK", status="PASS"),
            CheckResult(name="AWS CLI", status="PASS"),
        ]

        with patch("rsf.cli.doctor_cmd.run_all_checks", return_value=results):
            runner = CliRunner()
            result = runner.invoke(app, ["doctor", "--no-color"])
            # Should not contain Rich markup
            assert "[green]" not in result.output
            assert "[red]" not in result.output

    def test_shows_fix_hints(self) -> None:
        """Test 21: Shows fix hints for failed checks."""
        from typer.testing import CliRunner
        from rsf.cli.main import app

        results = [
            CheckResult(name="Python", status="PASS", version="3.12.3"),
            CheckResult(name="Terraform", status="FAIL", message="Not found", fix_hint="Install terraform"),
            CheckResult(name="AWS Credentials", status="PASS"),
            CheckResult(name="boto3 SDK", status="PASS"),
            CheckResult(name="AWS CLI", status="PASS"),
        ]

        with patch("rsf.cli.doctor_cmd.run_all_checks", return_value=results):
            runner = CliRunner()
            result = runner.invoke(app, ["doctor", "--no-color"])
            assert "Fix: Install terraform" in result.output

    def test_shows_section_headers(self) -> None:
        """Test 22: Shows Environment and Project section headers."""
        from typer.testing import CliRunner
        from rsf.cli.main import app

        results = [
            CheckResult(name="Python", status="PASS", version="3.12.3"),
            CheckResult(name="Terraform", status="PASS", version="1.5.7"),
            CheckResult(name="AWS Credentials", status="PASS"),
            CheckResult(name="boto3 SDK", status="PASS"),
            CheckResult(name="AWS CLI", status="PASS"),
            CheckResult(name="workflow.yaml", status="PASS"),
        ]

        with patch("rsf.cli.doctor_cmd.run_all_checks", return_value=results):
            runner = CliRunner()
            result = runner.invoke(app, ["doctor", "--no-color"])
            assert "Environment" in result.output
            assert "Project" in result.output


# --- Provider-aware doctor tests ---


class TestProviderAwareDoctor:
    """Tests for provider-aware doctor behavior."""

    def test_terraform_check_warn_when_not_active_provider(self) -> None:
        """Terraform check returns WARN (not FAIL) when not the active provider."""
        with patch("shutil.which", return_value=None):
            result = _check_terraform(is_active=False)
            assert result.status == "WARN"
            assert "not the active provider" in result.message

    def test_terraform_dir_skipped_for_non_terraform_provider(self, tmp_path: Path) -> None:
        """terraform/ directory check is skipped when provider is not terraform."""
        workflow = tmp_path / "workflow.yaml"
        workflow.write_text(
            "StartAt: First\nStates:\n  First:\n    Type: Task\n    End: true\n"
        )
        tf_dir = tmp_path / "terraform"
        tf_dir.mkdir()

        results = run_all_checks(
            workflow_path=workflow,
            tf_dir=tf_dir,
            handlers_dir=tmp_path / "handlers",
            provider_name="cdk",
        )
        names = {r.name for r in results}
        assert "terraform/" not in names

    def test_terraform_dir_included_for_terraform_provider(self, tmp_path: Path) -> None:
        """terraform/ directory check is included when provider is terraform."""
        workflow = tmp_path / "workflow.yaml"
        workflow.write_text(
            "StartAt: First\nStates:\n  First:\n    Type: Task\n    End: true\n"
        )
        tf_dir = tmp_path / "terraform"
        tf_dir.mkdir()

        results = run_all_checks(
            workflow_path=workflow,
            tf_dir=tf_dir,
            handlers_dir=tmp_path / "handlers",
            provider_name="terraform",
        )
        names = {r.name for r in results}
        assert "terraform/" in names

    def test_json_output_includes_provider_field(self) -> None:
        """JSON output includes a 'provider' field."""
        from typer.testing import CliRunner
        from rsf.cli.main import app

        results = [
            CheckResult(name="Python", status="PASS", version="3.12.3"),
            CheckResult(name="Terraform", status="WARN", message="Not found (not the active provider)"),
            CheckResult(name="AWS Credentials", status="PASS"),
            CheckResult(name="boto3 SDK", status="PASS"),
            CheckResult(name="AWS CLI", status="PASS"),
        ]

        with (
            patch("rsf.cli.doctor_cmd.run_all_checks", return_value=results),
            patch("rsf.cli.doctor_cmd._detect_provider", return_value="cdk"),
        ):
            runner = CliRunner()
            result = runner.invoke(app, ["doctor", "--json"])
            parsed = json.loads(result.output)
            assert "provider" in parsed
            assert parsed["provider"] == "cdk"

    def test_provider_label_shown_for_non_terraform(self) -> None:
        """Provider label is shown in output for non-terraform providers."""
        from typer.testing import CliRunner
        from rsf.cli.main import app

        results = [
            CheckResult(name="Python", status="PASS", version="3.12.3"),
            CheckResult(name="Terraform", status="WARN", message="Not found (not the active provider)"),
            CheckResult(name="AWS Credentials", status="PASS"),
            CheckResult(name="boto3 SDK", status="PASS"),
            CheckResult(name="AWS CLI", status="PASS"),
        ]

        with (
            patch("rsf.cli.doctor_cmd.run_all_checks", return_value=results),
            patch("rsf.cli.doctor_cmd._detect_provider", return_value="cdk"),
        ):
            runner = CliRunner()
            result = runner.invoke(app, ["doctor", "--no-color"])
            assert "provider: cdk" in result.output
