"""Tests for CustomProvider implementation."""

from __future__ import annotations

import stat
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rsf.dsl.models import CustomProviderConfig, InfrastructureConfig
from rsf.providers.base import InfrastructureProvider, ProviderContext
from rsf.providers.custom import CustomProvider
from rsf.providers.metadata import WorkflowMetadata
from rsf.providers.transports import ArgsTransport, EnvTransport, FileTransport


@pytest.fixture()
def provider() -> CustomProvider:
    """Return a CustomProvider instance."""
    return CustomProvider()


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


@pytest.fixture()
def non_executable_file(tmp_path: Path) -> Path:
    """Create a file that is NOT executable."""
    script = tmp_path / "not_exec.sh"
    script.write_text("#!/bin/sh\nexit 0\n")
    # Explicitly remove execute permission
    script.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return script


def _make_ctx(
    metadata: WorkflowMetadata,
    tmp_path: Path,
    program: str,
    args: list[str] | None = None,
    teardown_args: list[str] | None = None,
    metadata_transport: str = "file",
    env: dict[str, str] | None = None,
) -> ProviderContext:
    """Create a ProviderContext with a valid definition carrying CustomProviderConfig."""
    custom_config = CustomProviderConfig(
        program=program,
        args=args or [],
        teardown_args=teardown_args,
        metadata_transport=metadata_transport,  # type: ignore[arg-type]
        env=env,
    )
    infra_config = InfrastructureConfig(provider="custom", custom=custom_config)

    # Create a minimal StateMachineDefinition with infrastructure
    definition = MagicMock()
    definition.infrastructure = infra_config

    return ProviderContext(
        metadata=metadata,
        output_dir=tmp_path / "output",
        stage=metadata.stage,
        workflow_path=tmp_path / "workflow.yaml",
        definition=definition,
    )


class TestCustomProviderInterface:
    """Tests for CustomProvider ABC compliance."""

    def test_is_infrastructure_provider(self, provider: CustomProvider) -> None:
        """CustomProvider() is an instance of InfrastructureProvider."""
        assert isinstance(provider, InfrastructureProvider)

    def test_no_type_error_on_instantiation(self) -> None:
        """CustomProvider can be instantiated without TypeError (all abstract methods)."""
        p = CustomProvider()
        assert p is not None

    def test_has_all_abstract_methods(self, provider: CustomProvider) -> None:
        """CustomProvider implements all 5 abstract methods."""
        assert hasattr(provider, "generate")
        assert hasattr(provider, "deploy")
        assert hasattr(provider, "teardown")
        assert hasattr(provider, "check_prerequisites")
        assert hasattr(provider, "validate_config")


class TestCustomProviderGenerate:
    """Tests for CustomProvider.generate()."""

    def test_generate_is_noop(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """generate() returns None, doesn't raise."""
        ctx = _make_ctx(minimal_metadata, tmp_path, str(executable_script))
        result = provider.generate(ctx)
        assert result is None


class TestCustomProviderDeploy:
    """Tests for CustomProvider.deploy()."""

    def test_deploy_invokes_program(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """deploy() calls subprocess.run with correct program path."""
        ctx = _make_ctx(
            minimal_metadata, tmp_path, str(executable_script), args=["deploy"]
        )
        with patch.object(provider, "run_provider_command_streaming") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.deploy(ctx)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == str(executable_script)
        assert "deploy" in cmd

    def test_deploy_uses_shell_false(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """subprocess.run is called with shell=False."""
        ctx = _make_ctx(minimal_metadata, tmp_path, str(executable_script))
        with patch("rsf.providers.custom.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.deploy(ctx)

        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs.get("shell") is False

    def test_deploy_passes_args(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """Configured args appear in the command list."""
        ctx = _make_ctx(
            minimal_metadata,
            tmp_path,
            str(executable_script),
            args=["deploy", "--env", "dev"],
        )
        with patch.object(provider, "run_provider_command_streaming") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.deploy(ctx)

        cmd = mock_run.call_args[0][0]
        assert cmd[1:4] == ["deploy", "--env", "dev"]

    def test_deploy_file_transport_sets_env(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """With metadata_transport='file', RSF_METADATA_FILE is set in env."""
        ctx = _make_ctx(
            minimal_metadata,
            tmp_path,
            str(executable_script),
            metadata_transport="file",
        )
        with patch.object(provider, "run_provider_command_streaming") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.deploy(ctx)

        call_kwargs = mock_run.call_args[1]  # keyword args
        env = call_kwargs.get("env", {})
        assert "RSF_METADATA_FILE" in env

    def test_deploy_env_transport_sets_vars(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """With metadata_transport='env', RSF_WORKFLOW_NAME/RSF_STAGE/RSF_METADATA_JSON set."""
        ctx = _make_ctx(
            minimal_metadata,
            tmp_path,
            str(executable_script),
            metadata_transport="env",
        )
        with patch.object(provider, "run_provider_command_streaming") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.deploy(ctx)

        call_kwargs = mock_run.call_args[1]
        env = call_kwargs.get("env", {})
        assert "RSF_WORKFLOW_NAME" in env
        assert "RSF_STAGE" in env
        assert "RSF_METADATA_JSON" in env

    def test_deploy_args_transport_appends_args(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """With metadata_transport='args', extra args from transport appear in command."""
        ctx = _make_ctx(
            minimal_metadata,
            tmp_path,
            str(executable_script),
            args=["--workflow {workflow_name}"],
            metadata_transport="args",
        )
        with patch.object(provider, "run_provider_command_streaming") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.deploy(ctx)

        cmd = mock_run.call_args[0][0]
        # ArgsTransport substitutes {workflow_name} and returns as extra args
        # The original args template is in config.args, extra_args come from transport
        assert "test-workflow" in " ".join(cmd)

    def test_deploy_custom_env_merged(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """config.env vars appear in subprocess env."""
        ctx = _make_ctx(
            minimal_metadata,
            tmp_path,
            str(executable_script),
            env={"DEPLOY_TOKEN": "secret123"},
        )
        with patch.object(provider, "run_provider_command_streaming") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.deploy(ctx)

        call_kwargs = mock_run.call_args[1]
        env = call_kwargs.get("env", {})
        assert env.get("DEPLOY_TOKEN") == "secret123"

    def test_deploy_cwd_is_workflow_parent(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """subprocess cwd is ctx.workflow_path.parent."""
        ctx = _make_ctx(minimal_metadata, tmp_path, str(executable_script))
        with patch.object(provider, "run_provider_command_streaming") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.deploy(ctx)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == ctx.workflow_path.parent

    def test_deploy_validates_program_before_invoke(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
    ) -> None:
        """Non-existent program raises FileNotFoundError."""
        ctx = _make_ctx(
            minimal_metadata, tmp_path, "/nonexistent/program/deploy.sh"
        )
        with pytest.raises(FileNotFoundError, match="not found"):
            provider.deploy(ctx)

    def test_deploy_validates_absolute_path(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
    ) -> None:
        """Relative path raises ValueError."""
        ctx = _make_ctx(minimal_metadata, tmp_path, "relative/path.sh")
        with pytest.raises(ValueError, match="absolute path"):
            provider.deploy(ctx)

    def test_deploy_validates_executable(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        non_executable_file: Path,
    ) -> None:
        """Non-executable file raises PermissionError."""
        ctx = _make_ctx(minimal_metadata, tmp_path, str(non_executable_file))
        with pytest.raises(PermissionError, match="not executable"):
            provider.deploy(ctx)

    def test_deploy_transport_cleanup_on_success(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """transport.cleanup() called on success."""
        ctx = _make_ctx(
            minimal_metadata,
            tmp_path,
            str(executable_script),
            metadata_transport="file",
        )
        with (
            patch.object(provider, "run_provider_command_streaming") as mock_run,
            patch("rsf.providers.custom.FileTransport") as MockTransport,
        ):
            mock_instance = MagicMock()
            mock_instance.prepare.return_value = []
            MockTransport.return_value = mock_instance
            mock_run.return_value = MagicMock(returncode=0)

            provider.deploy(ctx)

        mock_instance.cleanup.assert_called_once()

    def test_deploy_transport_cleanup_on_error(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """transport.cleanup() called even when subprocess fails."""
        ctx = _make_ctx(
            minimal_metadata,
            tmp_path,
            str(executable_script),
            metadata_transport="file",
        )
        import subprocess as sp

        with (
            patch.object(
                provider,
                "run_provider_command_streaming",
                side_effect=sp.CalledProcessError(1, "deploy"),
            ),
            patch("rsf.providers.custom.FileTransport") as MockTransport,
        ):
            mock_instance = MagicMock()
            mock_instance.prepare.return_value = []
            MockTransport.return_value = mock_instance

            with pytest.raises(sp.CalledProcessError):
                provider.deploy(ctx)

        mock_instance.cleanup.assert_called_once()


class TestCustomProviderTeardown:
    """Tests for CustomProvider.teardown()."""

    def test_teardown_with_args(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """teardown() with teardown_args configured invokes program with those args."""
        ctx = _make_ctx(
            minimal_metadata,
            tmp_path,
            str(executable_script),
            teardown_args=["teardown", "--force"],
        )
        with patch.object(provider, "run_provider_command_streaming") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.teardown(ctx)

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == str(executable_script)
        assert "teardown" in cmd
        assert "--force" in cmd

    def test_teardown_without_args_raises(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """teardown() without teardown_args raises NotImplementedError."""
        ctx = _make_ctx(
            minimal_metadata,
            tmp_path,
            str(executable_script),
            teardown_args=None,
        )
        with pytest.raises(NotImplementedError, match="teardown not configured"):
            provider.teardown(ctx)

    def test_teardown_uses_shell_false(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """subprocess.run is called with shell=False during teardown."""
        ctx = _make_ctx(
            minimal_metadata,
            tmp_path,
            str(executable_script),
            teardown_args=["teardown"],
        )
        with patch("rsf.providers.custom.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.teardown(ctx)

        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs.get("shell") is False


class TestCustomProviderPrerequisites:
    """Tests for CustomProvider.check_prerequisites()."""

    def test_prereqs_program_exists_and_executable(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """Returns pass checks when program exists and is executable."""
        ctx = _make_ctx(minimal_metadata, tmp_path, str(executable_script))
        checks = provider.check_prerequisites(ctx)

        program_check = next(c for c in checks if c.name == "custom-program")
        assert program_check.status == "pass"

        exec_check = next(c for c in checks if c.name == "custom-program-executable")
        assert exec_check.status == "pass"

    def test_prereqs_program_not_found(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
    ) -> None:
        """Returns fail check when program doesn't exist."""
        ctx = _make_ctx(minimal_metadata, tmp_path, "/nonexistent/program.sh")
        checks = provider.check_prerequisites(ctx)

        program_check = next(c for c in checks if c.name == "custom-program")
        assert program_check.status == "fail"
        assert "not found" in program_check.message

    def test_prereqs_program_not_executable(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        non_executable_file: Path,
    ) -> None:
        """Returns fail check when program exists but is not executable."""
        ctx = _make_ctx(minimal_metadata, tmp_path, str(non_executable_file))
        checks = provider.check_prerequisites(ctx)

        exec_check = next(c for c in checks if c.name == "custom-program-executable")
        assert exec_check.status == "fail"
        assert "not executable" in exec_check.message


class TestCustomProviderValidateConfig:
    """Tests for CustomProvider.validate_config()."""

    def test_validate_config_valid(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """Valid config doesn't raise."""
        ctx = _make_ctx(minimal_metadata, tmp_path, str(executable_script))
        result = provider.validate_config(ctx)
        assert result is None

    def test_validate_config_relative_path_raises(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
    ) -> None:
        """Relative path raises ValueError."""
        ctx = _make_ctx(minimal_metadata, tmp_path, "relative/path.sh")
        with pytest.raises(ValueError, match="absolute path"):
            provider.validate_config(ctx)

    def test_validate_config_args_transport_validates_templates(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """Invalid placeholder in args raises ValueError."""
        ctx = _make_ctx(
            minimal_metadata,
            tmp_path,
            str(executable_script),
            args=["--bad {nonexistent}"],
            metadata_transport="args",
        )
        with pytest.raises(ValueError, match="Invalid placeholder"):
            provider.validate_config(ctx)


class TestCustomProviderGetConfig:
    """Tests for CustomProvider._get_config()."""

    def test_get_config_returns_custom_config(
        self,
        provider: CustomProvider,
        minimal_metadata: WorkflowMetadata,
        tmp_path: Path,
        executable_script: Path,
    ) -> None:
        """Extracts CustomProviderConfig from ctx.definition."""
        ctx = _make_ctx(minimal_metadata, tmp_path, str(executable_script))
        config = provider._get_config(ctx)
        assert isinstance(config, CustomProviderConfig)
        assert config.program == str(executable_script)

    def test_get_config_no_definition_raises(
        self, provider: CustomProvider, minimal_metadata: WorkflowMetadata, tmp_path: Path
    ) -> None:
        """ctx.definition=None raises ValueError."""
        ctx = ProviderContext(
            metadata=minimal_metadata,
            output_dir=tmp_path / "output",
            stage=None,
            workflow_path=tmp_path / "workflow.yaml",
            definition=None,
        )
        with pytest.raises(ValueError, match="requires workflow definition"):
            provider._get_config(ctx)

    def test_get_config_no_custom_config_raises(
        self, provider: CustomProvider, minimal_metadata: WorkflowMetadata, tmp_path: Path
    ) -> None:
        """Definition without custom block raises ValueError."""
        definition = MagicMock()
        definition.infrastructure = InfrastructureConfig(provider="custom")
        # custom is None by default

        ctx = ProviderContext(
            metadata=minimal_metadata,
            output_dir=tmp_path / "output",
            stage=None,
            workflow_path=tmp_path / "workflow.yaml",
            definition=definition,
        )
        with pytest.raises(ValueError, match="requires 'custom' block"):
            provider._get_config(ctx)


class TestCustomProviderCreateTransport:
    """Tests for CustomProvider._create_transport()."""

    def test_create_transport_file(self, provider: CustomProvider) -> None:
        """Returns FileTransport instance for 'file'."""
        config = CustomProviderConfig(program="/bin/sh", metadata_transport="file")
        transport = provider._create_transport(config)
        assert isinstance(transport, FileTransport)

    def test_create_transport_env(self, provider: CustomProvider) -> None:
        """Returns EnvTransport instance for 'env'."""
        config = CustomProviderConfig(program="/bin/sh", metadata_transport="env")
        transport = provider._create_transport(config)
        assert isinstance(transport, EnvTransport)

    def test_create_transport_args(self, provider: CustomProvider) -> None:
        """Returns ArgsTransport instance for 'args'."""
        config = CustomProviderConfig(
            program="/bin/sh",
            args=["--workflow {workflow_name}"],
            metadata_transport="args",
        )
        transport = provider._create_transport(config)
        assert isinstance(transport, ArgsTransport)


class TestCustomProviderStreaming:
    """Tests for streaming subprocess execution."""

    def test_streaming_subprocess_no_capture(self, provider: CustomProvider) -> None:
        """run_provider_command_streaming does not use capture_output."""
        with patch("rsf.providers.custom.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.run_provider_command_streaming(["echo", "test"])

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args.kwargs
        # capture_output must NOT be present (or be False)
        assert call_kwargs.get("capture_output") is not True
        # shell must be False
        assert call_kwargs.get("shell") is False
        # check must be True
        assert call_kwargs.get("check") is True

    def test_streaming_merges_env(self, provider: CustomProvider) -> None:
        """run_provider_command_streaming merges env with os.environ."""
        with patch("rsf.providers.custom.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.run_provider_command_streaming(
                ["echo"], env={"MY_VAR": "test"}
            )

        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["env"]["MY_VAR"] == "test"
