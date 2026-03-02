"""Tests for CDKProvider implementation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from rsf.providers.base import InfrastructureProvider, PrerequisiteCheck, ProviderContext
from rsf.providers.cdk import CDKProvider
from rsf.providers.metadata import WorkflowMetadata


@pytest.fixture()
def provider() -> CDKProvider:
    """Return a CDKProvider instance."""
    return CDKProvider()


@pytest.fixture()
def minimal_metadata() -> WorkflowMetadata:
    """Return a minimal WorkflowMetadata for testing."""
    return WorkflowMetadata(workflow_name="test-workflow")


@pytest.fixture()
def minimal_ctx(minimal_metadata: WorkflowMetadata, tmp_path: Path) -> ProviderContext:
    """Return a minimal ProviderContext for testing."""
    return ProviderContext(
        metadata=minimal_metadata,
        output_dir=tmp_path / "cdk",
        stage=None,
        workflow_path=tmp_path / "workflow.yaml",
    )


class TestCDKProviderInterface:
    """Tests for CDKProvider ABC compliance."""

    def test_is_infrastructure_provider(self, provider: CDKProvider) -> None:
        """CDKProvider() is an instance of InfrastructureProvider."""
        assert isinstance(provider, InfrastructureProvider)

    def test_no_type_error_on_instantiation(self) -> None:
        """CDKProvider can be instantiated without TypeError (all abstract methods implemented)."""
        p = CDKProvider()
        assert p is not None

    def test_has_all_abstract_methods(self, provider: CDKProvider) -> None:
        """CDKProvider implements all 5 abstract methods."""
        assert hasattr(provider, "generate")
        assert hasattr(provider, "deploy")
        assert hasattr(provider, "teardown")
        assert hasattr(provider, "check_prerequisites")
        assert hasattr(provider, "validate_config")


class TestCDKProviderGenerate:
    """Tests for CDKProvider.generate()."""

    def test_generate_delegates_to_generator(
        self, provider: CDKProvider, minimal_ctx: ProviderContext
    ) -> None:
        """generate() calls generate_cdk with correct config."""
        with patch("rsf.providers.cdk.generate_cdk") as mock_gen:
            mock_gen.return_value = MagicMock(generated_files=[], skipped_files=[])
            provider.generate(minimal_ctx)

        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args
        config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config.workflow_name == "test-workflow"
        output_dir = call_kwargs.kwargs.get("output_dir") or call_kwargs[1].get("output_dir")
        assert output_dir == minimal_ctx.output_dir


class TestCDKProviderDeploy:
    """Tests for CDKProvider.deploy()."""

    def test_deploy_calls_streaming_subprocess(
        self, provider: CDKProvider, minimal_ctx: ProviderContext
    ) -> None:
        """deploy() invokes npx aws-cdk@latest deploy."""
        with (
            patch.object(provider, "_check_bootstrap_or_warn"),
            patch.object(provider, "run_provider_command_streaming") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)
            provider.deploy(minimal_ctx)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[:2] == ["npx", "aws-cdk@latest"]
        assert "deploy" in cmd

    def test_deploy_auto_approve_adds_flag(
        self, provider: CDKProvider, minimal_metadata: WorkflowMetadata, tmp_path: Path
    ) -> None:
        """With auto_approve=True, deploy command includes --require-approval never."""
        ctx = ProviderContext(
            metadata=minimal_metadata,
            output_dir=tmp_path / "cdk",
            stage=None,
            workflow_path=tmp_path / "workflow.yaml",
            auto_approve=True,
        )
        with (
            patch.object(provider, "_check_bootstrap_or_warn"),
            patch.object(provider, "run_provider_command_streaming") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)
            provider.deploy(ctx)

        cmd = mock_run.call_args[0][0]
        assert "--require-approval" in cmd
        approval_idx = cmd.index("--require-approval")
        assert cmd[approval_idx + 1] == "never"

    def test_deploy_stage_adds_context(
        self, provider: CDKProvider, minimal_metadata: WorkflowMetadata, tmp_path: Path
    ) -> None:
        """With stage="prod", deploy command includes -c stage=prod."""
        ctx = ProviderContext(
            metadata=minimal_metadata,
            output_dir=tmp_path / "cdk",
            stage="prod",
            workflow_path=tmp_path / "workflow.yaml",
        )
        with (
            patch.object(provider, "_check_bootstrap_or_warn"),
            patch.object(provider, "run_provider_command_streaming") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)
            provider.deploy(ctx)

        cmd = mock_run.call_args[0][0]
        assert "-c" in cmd
        c_idx = cmd.index("-c")
        assert cmd[c_idx + 1] == "stage=prod"

    def test_deploy_checks_bootstrap_first(
        self, provider: CDKProvider, minimal_ctx: ProviderContext
    ) -> None:
        """deploy() calls _check_bootstrap_or_warn before running cdk deploy."""
        call_order = []

        with (
            patch.object(
                provider,
                "_check_bootstrap_or_warn",
                side_effect=lambda ctx: call_order.append("bootstrap"),
            ),
            patch.object(
                provider,
                "run_provider_command_streaming",
                side_effect=lambda *a, **kw: call_order.append("deploy"),
            ),
        ):
            provider.deploy(minimal_ctx)

        assert call_order == ["bootstrap", "deploy"]


class TestCDKProviderBootstrap:
    """Tests for CDK bootstrap detection."""

    def test_bootstrap_missing_raises(
        self, provider: CDKProvider, minimal_ctx: ProviderContext
    ) -> None:
        """When CDKToolkit stack is missing, raises SystemExit with bootstrap command."""
        from botocore.exceptions import ClientError

        mock_cf = MagicMock()
        mock_cf.describe_stacks.side_effect = ClientError(
            {"Error": {"Code": "ValidationError", "Message": "Stack with id CDKToolkit does not exist"}},
            "DescribeStacks",
        )

        with (
            patch("rsf.providers.cdk.boto3") as mock_boto3,
            patch.object(provider, "_get_account_and_region", return_value=("123456789012", "us-east-2")),
        ):
            mock_boto3.client.return_value = mock_cf
            with pytest.raises(SystemExit, match="CDKToolkit"):
                provider._check_bootstrap_or_warn(minimal_ctx)

    def test_bootstrap_present_continues(
        self, provider: CDKProvider, minimal_ctx: ProviderContext
    ) -> None:
        """When CDKToolkit stack exists, _check_bootstrap_or_warn returns quietly."""
        mock_cf = MagicMock()
        mock_cf.describe_stacks.return_value = {"Stacks": [{"StackName": "CDKToolkit"}]}

        with patch("rsf.providers.cdk.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_cf
            # Should not raise
            provider._check_bootstrap_or_warn(minimal_ctx)

    def test_bootstrap_error_message_includes_command(
        self, provider: CDKProvider, minimal_ctx: ProviderContext
    ) -> None:
        """Bootstrap error message includes the exact cdk bootstrap command."""
        from botocore.exceptions import ClientError

        mock_cf = MagicMock()
        mock_cf.describe_stacks.side_effect = ClientError(
            {"Error": {"Code": "ValidationError", "Message": "Stack with id CDKToolkit does not exist"}},
            "DescribeStacks",
        )

        with (
            patch("rsf.providers.cdk.boto3") as mock_boto3,
            patch.object(provider, "_get_account_and_region", return_value=("111222333444", "eu-west-1")),
        ):
            mock_boto3.client.return_value = mock_cf
            with pytest.raises(SystemExit, match=r"cdk bootstrap aws://111222333444/eu-west-1"):
                provider._check_bootstrap_or_warn(minimal_ctx)


class TestCDKProviderTeardown:
    """Tests for CDKProvider.teardown()."""

    def test_teardown_calls_destroy(
        self, provider: CDKProvider, minimal_ctx: ProviderContext
    ) -> None:
        """teardown() invokes cdk destroy --force."""
        with patch.object(provider, "run_provider_command_streaming") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.teardown(minimal_ctx)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[:2] == ["npx", "aws-cdk@latest"]
        assert "destroy" in cmd
        assert "--force" in cmd

    def test_teardown_stage_adds_context(
        self, provider: CDKProvider, minimal_metadata: WorkflowMetadata, tmp_path: Path
    ) -> None:
        """With stage, teardown command includes -c stage=X."""
        ctx = ProviderContext(
            metadata=minimal_metadata,
            output_dir=tmp_path / "cdk",
            stage="staging",
            workflow_path=tmp_path / "workflow.yaml",
        )
        with patch.object(provider, "run_provider_command_streaming") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.teardown(ctx)

        cmd = mock_run.call_args[0][0]
        assert "-c" in cmd
        c_idx = cmd.index("-c")
        assert cmd[c_idx + 1] == "stage=staging"


class TestCDKProviderPrereqs:
    """Tests for CDKProvider.check_prerequisites()."""

    def test_npx_found(
        self, provider: CDKProvider, minimal_ctx: ProviderContext
    ) -> None:
        """check_prerequisites() returns pass for npx when found."""
        with patch("rsf.providers.cdk.shutil.which", side_effect=lambda x: "/usr/bin/npx" if x == "npx" else None):
            checks = provider.check_prerequisites(minimal_ctx)

        npx_check = next(c for c in checks if c.name == "node/npx")
        assert npx_check.status == "pass"

    def test_npx_missing(
        self, provider: CDKProvider, minimal_ctx: ProviderContext
    ) -> None:
        """check_prerequisites() returns fail for missing npx."""
        with patch("rsf.providers.cdk.shutil.which", return_value=None):
            checks = provider.check_prerequisites(minimal_ctx)

        npx_check = next(c for c in checks if c.name == "node/npx")
        assert npx_check.status == "fail"
        assert "nodejs" in npx_check.message.lower() or "node" in npx_check.message.lower()

    def test_cdk_found(
        self, provider: CDKProvider, minimal_ctx: ProviderContext
    ) -> None:
        """check_prerequisites() returns pass for cdk binary when found."""
        with patch("rsf.providers.cdk.shutil.which", return_value="/usr/bin/mock"):
            checks = provider.check_prerequisites(minimal_ctx)

        cdk_check = next(c for c in checks if c.name == "cdk")
        assert cdk_check.status == "pass"

    def test_cdk_missing_is_warn_not_fail(
        self, provider: CDKProvider, minimal_ctx: ProviderContext
    ) -> None:
        """check_prerequisites() returns warn (not fail) for missing cdk binary."""
        with patch("rsf.providers.cdk.shutil.which", side_effect=lambda x: "/usr/bin/npx" if x == "npx" else None):
            checks = provider.check_prerequisites(minimal_ctx)

        cdk_check = next(c for c in checks if c.name == "cdk")
        assert cdk_check.status == "warn"
        assert "npm install" in cdk_check.message

    def test_returns_both_checks(
        self, provider: CDKProvider, minimal_ctx: ProviderContext
    ) -> None:
        """check_prerequisites() returns checks for both npx and cdk."""
        with patch("rsf.providers.cdk.shutil.which", return_value="/usr/bin/mock"):
            checks = provider.check_prerequisites(minimal_ctx)

        check_names = {c.name for c in checks}
        assert "node/npx" in check_names
        assert "cdk" in check_names


class TestCDKProviderValidateConfig:
    """Tests for CDKProvider.validate_config()."""

    def test_validate_config_noop(
        self, provider: CDKProvider, minimal_ctx: ProviderContext
    ) -> None:
        """validate_config() is a no-op (Pydantic handles validation)."""
        # Should not raise
        result = provider.validate_config(minimal_ctx)
        assert result is None


class TestCDKProviderStreaming:
    """Tests for streaming subprocess execution."""

    def test_streaming_subprocess_no_capture(
        self, provider: CDKProvider
    ) -> None:
        """run_provider_command_streaming does not use capture_output."""
        with patch("rsf.providers.cdk.subprocess.run") as mock_run:
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

    def test_streaming_merges_env(self, provider: CDKProvider) -> None:
        """run_provider_command_streaming merges env with os.environ."""
        with patch("rsf.providers.cdk.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.run_provider_command_streaming(
                ["echo"], env={"MY_VAR": "test"}
            )

        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["env"]["MY_VAR"] == "test"
