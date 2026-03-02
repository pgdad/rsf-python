"""Tests for InfrastructureProvider ABC, ProviderContext, and PrerequisiteCheck."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from rsf.providers.base import (
    InfrastructureProvider,
    PrerequisiteCheck,
    ProviderContext,
)


# --- Test fixtures ---


@dataclass
class _StubMetadata:
    """Minimal metadata stub for ProviderContext tests."""

    workflow_name: str = "test-workflow"


class _CompleteProvider(InfrastructureProvider):
    """Concrete provider that implements all abstract methods."""

    def generate(self, ctx: ProviderContext) -> None:
        pass

    def deploy(self, ctx: ProviderContext) -> None:
        pass

    def teardown(self, ctx: ProviderContext) -> None:
        pass

    def check_prerequisites(self, ctx: ProviderContext) -> list[PrerequisiteCheck]:
        return []

    def validate_config(self, ctx: ProviderContext) -> None:
        pass


# --- ABC enforcement tests ---


class TestInfrastructureProviderABC:
    """Verify ABC contract enforcement."""

    def test_complete_subclass_instantiates(self) -> None:
        """Subclass with all methods implements successfully."""
        provider = _CompleteProvider()
        assert isinstance(provider, InfrastructureProvider)

    def test_missing_deploy_raises_type_error(self) -> None:
        """Omitting deploy() raises TypeError."""

        class _Bad(InfrastructureProvider):
            def generate(self, ctx: ProviderContext) -> None:
                pass

            def teardown(self, ctx: ProviderContext) -> None:
                pass

            def check_prerequisites(self, ctx: ProviderContext) -> list[PrerequisiteCheck]:
                return []

            def validate_config(self, ctx: ProviderContext) -> None:
                pass

        with pytest.raises(TypeError):
            _Bad()

    def test_missing_generate_raises_type_error(self) -> None:
        """Omitting generate() raises TypeError."""

        class _Bad(InfrastructureProvider):
            def deploy(self, ctx: ProviderContext) -> None:
                pass

            def teardown(self, ctx: ProviderContext) -> None:
                pass

            def check_prerequisites(self, ctx: ProviderContext) -> list[PrerequisiteCheck]:
                return []

            def validate_config(self, ctx: ProviderContext) -> None:
                pass

        with pytest.raises(TypeError):
            _Bad()

    def test_missing_teardown_raises_type_error(self) -> None:
        """Omitting teardown() raises TypeError."""

        class _Bad(InfrastructureProvider):
            def generate(self, ctx: ProviderContext) -> None:
                pass

            def deploy(self, ctx: ProviderContext) -> None:
                pass

            def check_prerequisites(self, ctx: ProviderContext) -> list[PrerequisiteCheck]:
                return []

            def validate_config(self, ctx: ProviderContext) -> None:
                pass

        with pytest.raises(TypeError):
            _Bad()

    def test_missing_check_prerequisites_raises_type_error(self) -> None:
        """Omitting check_prerequisites() raises TypeError."""

        class _Bad(InfrastructureProvider):
            def generate(self, ctx: ProviderContext) -> None:
                pass

            def deploy(self, ctx: ProviderContext) -> None:
                pass

            def teardown(self, ctx: ProviderContext) -> None:
                pass

            def validate_config(self, ctx: ProviderContext) -> None:
                pass

        with pytest.raises(TypeError):
            _Bad()

    def test_missing_validate_config_raises_type_error(self) -> None:
        """Omitting validate_config() raises TypeError."""

        class _Bad(InfrastructureProvider):
            def generate(self, ctx: ProviderContext) -> None:
                pass

            def deploy(self, ctx: ProviderContext) -> None:
                pass

            def teardown(self, ctx: ProviderContext) -> None:
                pass

            def check_prerequisites(self, ctx: ProviderContext) -> list[PrerequisiteCheck]:
                return []

        with pytest.raises(TypeError):
            _Bad()


# --- ProviderContext tests ---


class TestProviderContext:
    """Verify ProviderContext dataclass fields."""

    def test_required_fields(self, tmp_path: Path) -> None:
        """ProviderContext has metadata, output_dir, stage, workflow_path."""
        meta = _StubMetadata()
        ctx = ProviderContext(
            metadata=meta,
            output_dir=tmp_path,
            stage="dev",
            workflow_path=tmp_path / "workflow.yaml",
        )
        assert ctx.metadata is meta
        assert ctx.output_dir == tmp_path
        assert ctx.stage == "dev"
        assert ctx.workflow_path == tmp_path / "workflow.yaml"

    def test_definition_defaults_to_none(self, tmp_path: Path) -> None:
        """ProviderContext.definition defaults to None."""
        ctx = ProviderContext(
            metadata=_StubMetadata(),
            output_dir=tmp_path,
            stage=None,
            workflow_path=tmp_path / "workflow.yaml",
        )
        assert ctx.definition is None

    def test_definition_can_be_set(self, tmp_path: Path) -> None:
        """ProviderContext.definition can be explicitly set."""
        mock_def = MagicMock()
        ctx = ProviderContext(
            metadata=_StubMetadata(),
            output_dir=tmp_path,
            stage="prod",
            workflow_path=tmp_path / "workflow.yaml",
            definition=mock_def,
        )
        assert ctx.definition is mock_def

    def test_stage_can_be_none(self, tmp_path: Path) -> None:
        """ProviderContext.stage accepts None."""
        ctx = ProviderContext(
            metadata=_StubMetadata(),
            output_dir=tmp_path,
            stage=None,
            workflow_path=tmp_path / "workflow.yaml",
        )
        assert ctx.stage is None


# --- PrerequisiteCheck tests ---


class TestPrerequisiteCheck:
    """Verify PrerequisiteCheck dataclass fields."""

    def test_fields(self) -> None:
        """PrerequisiteCheck has name, status, message."""
        check = PrerequisiteCheck(name="terraform", status="pass", message="v1.5.7")
        assert check.name == "terraform"
        assert check.status == "pass"
        assert check.message == "v1.5.7"

    def test_status_values(self) -> None:
        """PrerequisiteCheck accepts pass, warn, fail statuses."""
        for status in ("pass", "warn", "fail"):
            check = PrerequisiteCheck(name="test", status=status, message="msg")  # type: ignore[arg-type]
            assert check.status == status


# --- run_provider_command tests ---


class TestRunProviderCommand:
    """Verify run_provider_command() behavior."""

    @patch("rsf.providers.base.subprocess.run")
    def test_calls_subprocess_with_shell_false(self, mock_run: MagicMock) -> None:
        """run_provider_command() calls subprocess.run with shell=False."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo", "hello"], returncode=0, stdout="hello\n", stderr=""
        )
        provider = _CompleteProvider()
        result = provider.run_provider_command(["echo", "hello"])

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs["shell"] is False

    @patch("rsf.providers.base.subprocess.run")
    def test_returns_completed_process(self, mock_run: MagicMock) -> None:
        """run_provider_command() returns CompletedProcess."""
        expected = subprocess.CompletedProcess(
            args=["echo", "hello"], returncode=0, stdout="hello\n", stderr=""
        )
        mock_run.return_value = expected
        provider = _CompleteProvider()
        result = provider.run_provider_command(["echo", "hello"])
        assert result is expected

    @patch("rsf.providers.base.subprocess.run")
    def test_raises_on_nonzero_exit(self, mock_run: MagicMock) -> None:
        """run_provider_command() raises CalledProcessError on failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["bad-cmd"]
        )
        provider = _CompleteProvider()
        with pytest.raises(subprocess.CalledProcessError):
            provider.run_provider_command(["bad-cmd"])

    @patch("rsf.providers.base.subprocess.run")
    def test_merges_env_with_os_environ(self, mock_run: MagicMock) -> None:
        """run_provider_command() merges provided env with os.environ."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo"], returncode=0, stdout="", stderr=""
        )
        provider = _CompleteProvider()
        custom_env = {"MY_VAR": "my_value"}
        provider.run_provider_command(["echo"], env=custom_env)

        call_kwargs = mock_run.call_args.kwargs
        passed_env = call_kwargs["env"]
        # Custom var should be present
        assert passed_env["MY_VAR"] == "my_value"
        # OS environ vars should also be present (PATH at minimum)
        assert "PATH" in passed_env

    @patch("rsf.providers.base.subprocess.run")
    def test_passes_cwd(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """run_provider_command() passes cwd to subprocess."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo"], returncode=0, stdout="", stderr=""
        )
        provider = _CompleteProvider()
        provider.run_provider_command(["echo"], cwd=tmp_path)

        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["cwd"] == tmp_path

    @patch("rsf.providers.base.subprocess.run")
    def test_captures_output_as_text(self, mock_run: MagicMock) -> None:
        """run_provider_command() captures output as text."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo"], returncode=0, stdout="output", stderr=""
        )
        provider = _CompleteProvider()
        provider.run_provider_command(["echo"])

        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["capture_output"] is True
        assert call_kwargs["text"] is True
