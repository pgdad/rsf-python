"""Integration tests for custom provider end-to-end flow.

Tests the full custom provider flow: registration, config parsing,
transport selection, and subprocess invocation through the provider
interface.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rsf.dsl.models import CustomProviderConfig, InfrastructureConfig
from rsf.providers.base import ProviderContext
from rsf.providers.custom import CustomProvider
from rsf.providers.metadata import WorkflowMetadata


@pytest.fixture()
def minimal_metadata() -> WorkflowMetadata:
    """Return a minimal WorkflowMetadata for testing."""
    return WorkflowMetadata(workflow_name="test-workflow", stage="dev")


@pytest.fixture()
def executable_script(tmp_path: Path) -> Path:
    """Create a real executable script and return its path."""
    script = tmp_path / "deploy.sh"
    script.write_text("#!/bin/sh\nexit 0\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def _make_definition(
    program: str,
    args: list[str] | None = None,
    teardown_args: list[str] | None = None,
    metadata_transport: str = "file",
    env: dict[str, str] | None = None,
) -> MagicMock:
    """Create a mock definition with CustomProviderConfig."""
    custom_config = CustomProviderConfig(
        program=program,
        args=args or [],
        teardown_args=teardown_args,
        metadata_transport=metadata_transport,  # type: ignore[arg-type]
        env=env,
    )
    infra_config = InfrastructureConfig(provider="custom", custom=custom_config)
    definition = MagicMock()
    definition.infrastructure = infra_config
    return definition


class TestCustomProviderRegistration:
    """Tests for custom provider registration via __init__.py."""

    def test_custom_provider_registered(self) -> None:
        """'custom' appears in list_providers() after __init__ import."""
        # Force re-import to trigger registration
        from rsf.providers import list_providers

        assert "custom" in list_providers()

    def test_get_custom_provider(self) -> None:
        """get_provider('custom') returns CustomProvider instance."""
        from rsf.providers import get_provider

        provider = get_provider("custom")
        assert isinstance(provider, CustomProvider)

    def test_custom_provider_importable(self) -> None:
        """CustomProvider is importable from rsf.providers."""
        from rsf.providers import CustomProvider as CP

        assert CP is CustomProvider


class TestCustomDeployFileTransportEndToEnd:
    """End-to-end tests with file metadata transport."""

    def test_deploy_file_transport(
        self,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """Full deploy flow with file transport: program invoked, metadata file created."""
        definition = _make_definition(
            program=str(executable_script),
            args=["deploy"],
            metadata_transport="file",
        )
        ctx = ProviderContext(
            metadata=minimal_metadata,
            output_dir=tmp_path / "output",
            stage="dev",
            workflow_path=tmp_path / "workflow.yaml",
            definition=definition,
        )

        provider = CustomProvider()
        with patch.object(provider, "run_provider_command_streaming") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.deploy(ctx)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        call_kwargs = mock_run.call_args[1]

        # Program path is first in command
        assert cmd[0] == str(executable_script)
        # deploy arg is present
        assert "deploy" in cmd
        # RSF_METADATA_FILE is in env (file transport)
        env = call_kwargs.get("env", {})
        assert "RSF_METADATA_FILE" in env
        # shell=False is enforced by run_provider_command_streaming


class TestCustomDeployEnvTransportEndToEnd:
    """End-to-end tests with env metadata transport."""

    def test_deploy_env_transport(
        self,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """Full deploy flow with env transport: RSF_* env vars set."""
        definition = _make_definition(
            program=str(executable_script),
            args=["deploy"],
            metadata_transport="env",
        )
        ctx = ProviderContext(
            metadata=minimal_metadata,
            output_dir=tmp_path / "output",
            stage="dev",
            workflow_path=tmp_path / "workflow.yaml",
            definition=definition,
        )

        provider = CustomProvider()
        with patch.object(provider, "run_provider_command_streaming") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.deploy(ctx)

        call_kwargs = mock_run.call_args[1]
        env = call_kwargs.get("env", {})
        assert env.get("RSF_WORKFLOW_NAME") == "test-workflow"
        assert env.get("RSF_STAGE") == "dev"
        assert "RSF_METADATA_JSON" in env


class TestCustomDeployArgsTransportEndToEnd:
    """End-to-end tests with args metadata transport."""

    def test_deploy_args_transport(
        self,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """Full deploy flow with args transport: placeholders substituted in command."""
        definition = _make_definition(
            program=str(executable_script),
            args=["deploy", "--workflow {workflow_name}", "--stage {stage}"],
            metadata_transport="args",
        )
        ctx = ProviderContext(
            metadata=minimal_metadata,
            output_dir=tmp_path / "output",
            stage="dev",
            workflow_path=tmp_path / "workflow.yaml",
            definition=definition,
        )

        provider = CustomProvider()
        with patch.object(provider, "run_provider_command_streaming") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.deploy(ctx)

        cmd = mock_run.call_args[0][0]
        # ArgsTransport returns substituted args which are appended
        # Original args are also in the command (un-substituted templates)
        # But the extra_args from transport have the substituted values
        cmd_str = " ".join(cmd)
        assert "test-workflow" in cmd_str
        assert "dev" in cmd_str


class TestCustomDeploySecurityEndToEnd:
    """End-to-end security verification tests."""

    def test_rejects_relative_program(
        self,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
    ) -> None:
        """Deploy rejects relative program path."""
        definition = _make_definition(program="relative/path.sh")
        ctx = ProviderContext(
            metadata=minimal_metadata,
            output_dir=tmp_path / "output",
            stage="dev",
            workflow_path=tmp_path / "workflow.yaml",
            definition=definition,
        )

        provider = CustomProvider()
        with pytest.raises(ValueError, match="absolute path"):
            provider.deploy(ctx)

    def test_validates_executable(
        self,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
    ) -> None:
        """Deploy validates program is executable."""
        # Create file without execute permission
        script = tmp_path / "not_exec.sh"
        script.write_text("#!/bin/sh\nexit 0\n")
        script.chmod(stat.S_IRUSR | stat.S_IWUSR)  # No execute

        definition = _make_definition(program=str(script))
        ctx = ProviderContext(
            metadata=minimal_metadata,
            output_dir=tmp_path / "output",
            stage="dev",
            workflow_path=tmp_path / "workflow.yaml",
            definition=definition,
        )

        provider = CustomProvider()
        with pytest.raises(PermissionError, match="not executable"):
            provider.deploy(ctx)

    def test_shell_false_enforced(
        self,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """subprocess.run is called with shell=False."""
        definition = _make_definition(program=str(executable_script))
        ctx = ProviderContext(
            metadata=minimal_metadata,
            output_dir=tmp_path / "output",
            stage="dev",
            workflow_path=tmp_path / "workflow.yaml",
            definition=definition,
        )

        provider = CustomProvider()
        with patch("rsf.providers.custom.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.deploy(ctx)

        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["shell"] is False


class TestCustomTeardownEndToEnd:
    """End-to-end teardown tests."""

    def test_teardown_with_args(
        self,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """Teardown with teardown_args invokes program."""
        definition = _make_definition(
            program=str(executable_script),
            teardown_args=["teardown", "--force"],
        )
        ctx = ProviderContext(
            metadata=minimal_metadata,
            output_dir=tmp_path / "output",
            stage="dev",
            workflow_path=tmp_path / "workflow.yaml",
            definition=definition,
        )

        provider = CustomProvider()
        with patch.object(provider, "run_provider_command_streaming") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.teardown(ctx)

        cmd = mock_run.call_args[0][0]
        assert "teardown" in cmd
        assert "--force" in cmd

    def test_teardown_without_args_raises(
        self,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """Teardown without teardown_args raises NotImplementedError."""
        definition = _make_definition(program=str(executable_script))
        ctx = ProviderContext(
            metadata=minimal_metadata,
            output_dir=tmp_path / "output",
            stage="dev",
            workflow_path=tmp_path / "workflow.yaml",
            definition=definition,
        )

        provider = CustomProvider()
        with pytest.raises(NotImplementedError, match="teardown not configured"):
            provider.teardown(ctx)
