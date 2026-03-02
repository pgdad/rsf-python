"""Tests for TerraformProvider implementation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rsf.providers.base import PrerequisiteCheck, ProviderContext
from rsf.providers.metadata import WorkflowMetadata
from rsf.providers.terraform import TerraformProvider


@pytest.fixture()
def provider() -> TerraformProvider:
    """Return a TerraformProvider instance."""
    return TerraformProvider()


@pytest.fixture()
def minimal_metadata() -> WorkflowMetadata:
    """Return a minimal WorkflowMetadata for testing."""
    return WorkflowMetadata(workflow_name="test-workflow")


@pytest.fixture()
def full_metadata() -> WorkflowMetadata:
    """Return a WorkflowMetadata with all infra features enabled."""
    return WorkflowMetadata(
        workflow_name="full-workflow",
        stage="prod",
        handler_count=3,
        timeout_seconds=300,
        triggers=[{"type": "sqs", "queue_name": "my-queue", "batch_size": 10}],
        dynamodb_tables=[
            {
                "table_name": "my-table",
                "partition_key": {"name": "pk", "type": "S"},
                "billing_mode": "PAY_PER_REQUEST",
            }
        ],
        alarms=[
            {
                "type": "error_rate",
                "threshold": 5,
                "period": 300,
                "evaluation_periods": 1,
                "sns_topic_arn": "arn:aws:sns:us-east-1:123456:alerts",
            }
        ],
        dlq_enabled=True,
        dlq_max_receive_count=5,
        dlq_queue_name="my-dlq",
        lambda_url_enabled=True,
        lambda_url_auth_type="AWS_IAM",
    )


@pytest.fixture()
def minimal_ctx(minimal_metadata: WorkflowMetadata, tmp_path: Path) -> ProviderContext:
    """Return a minimal ProviderContext for testing."""
    return ProviderContext(
        metadata=minimal_metadata,
        output_dir=tmp_path / "terraform",
        stage=None,
        workflow_path=tmp_path / "workflow.yaml",
    )


class TestTerraformProviderGenerate:
    """Tests for TerraformProvider.generate()."""

    def test_generate_calls_generate_terraform(
        self, provider: TerraformProvider, minimal_ctx: ProviderContext
    ) -> None:
        """generate() delegates to generate_terraform() with correct config."""
        with patch("rsf.providers.terraform.generate_terraform") as mock_gen:
            mock_gen.return_value = MagicMock(generated_files=[], skipped_files=[])
            provider.generate(minimal_ctx)

        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args
        config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config.workflow_name == "test-workflow"
        output_dir = call_kwargs.kwargs.get("output_dir") or call_kwargs[1].get("output_dir")
        assert output_dir == minimal_ctx.output_dir

    def test_generate_maps_all_metadata_fields(
        self, provider: TerraformProvider, full_metadata: WorkflowMetadata, tmp_path: Path
    ) -> None:
        """generate() maps all WorkflowMetadata fields to TerraformConfig."""
        ctx = ProviderContext(
            metadata=full_metadata,
            output_dir=tmp_path / "terraform",
            stage="prod",
            workflow_path=tmp_path / "workflow.yaml",
        )
        with patch("rsf.providers.terraform.generate_terraform") as mock_gen:
            mock_gen.return_value = MagicMock(generated_files=[], skipped_files=[])
            provider.generate(ctx)

        config = mock_gen.call_args.kwargs.get("config") or mock_gen.call_args[1].get("config")
        assert config.workflow_name == "full-workflow"
        assert config.triggers == full_metadata.triggers
        assert config.has_sqs_triggers is True
        assert config.dynamodb_tables == full_metadata.dynamodb_tables
        assert config.has_dynamodb_tables is True
        assert config.alarms == full_metadata.alarms
        assert config.has_alarms is True
        assert config.dlq_enabled is True
        assert config.dlq_max_receive_count == 5
        assert config.dlq_queue_name == "my-dlq"
        assert config.lambda_url_enabled is True
        assert config.lambda_url_auth_type == "AWS_IAM"
        assert config.stage == "prod"


class TestTerraformProviderDeploy:
    """Tests for TerraformProvider.deploy()."""

    def test_deploy_runs_init_then_apply(
        self, provider: TerraformProvider, minimal_ctx: ProviderContext
    ) -> None:
        """deploy() calls terraform init then terraform apply."""
        with patch.object(provider, "run_provider_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.deploy(minimal_ctx)

        assert mock_run.call_count == 2
        init_call = mock_run.call_args_list[0]
        apply_call = mock_run.call_args_list[1]
        assert init_call[0][0] == ["terraform", "init"]
        assert apply_call[0][0] == ["terraform", "apply"]

    def test_deploy_with_auto_approve(
        self, provider: TerraformProvider, minimal_metadata: WorkflowMetadata, tmp_path: Path
    ) -> None:
        """deploy() includes -auto-approve when auto_approve=True."""
        ctx = ProviderContext(
            metadata=minimal_metadata,
            output_dir=tmp_path / "terraform",
            stage=None,
            workflow_path=tmp_path / "workflow.yaml",
            auto_approve=True,
        )
        with patch.object(provider, "run_provider_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.deploy(ctx)

        apply_call = mock_run.call_args_list[1]
        assert "-auto-approve" in apply_call[0][0]

    def test_deploy_with_stage_var_file(
        self, provider: TerraformProvider, minimal_metadata: WorkflowMetadata, tmp_path: Path
    ) -> None:
        """deploy() includes -var-file when stage_var_file is set."""
        var_file = tmp_path / "stages" / "prod.tfvars"
        ctx = ProviderContext(
            metadata=minimal_metadata,
            output_dir=tmp_path / "terraform",
            stage="prod",
            workflow_path=tmp_path / "workflow.yaml",
            stage_var_file=var_file,
        )
        with patch.object(provider, "run_provider_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.deploy(ctx)

        apply_call = mock_run.call_args_list[1]
        apply_cmd = apply_call[0][0]
        assert "-var-file" in apply_cmd
        assert str(var_file) in apply_cmd


class TestTerraformProviderTeardown:
    """Tests for TerraformProvider.teardown()."""

    def test_teardown_runs_destroy(
        self, provider: TerraformProvider, minimal_ctx: ProviderContext
    ) -> None:
        """teardown() calls terraform destroy -auto-approve."""
        with patch.object(provider, "run_provider_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.teardown(minimal_ctx)

        mock_run.assert_called_once()
        destroy_cmd = mock_run.call_args[0][0]
        assert destroy_cmd == ["terraform", "destroy", "-auto-approve"]


class TestTerraformProviderPrereqs:
    """Tests for TerraformProvider.check_prerequisites()."""

    def test_terraform_found(
        self, provider: TerraformProvider, minimal_ctx: ProviderContext
    ) -> None:
        """check_prerequisites() returns pass when terraform binary found."""
        with patch("rsf.providers.terraform.shutil.which", return_value="/usr/bin/terraform"):
            checks = provider.check_prerequisites(minimal_ctx)

        assert len(checks) == 1
        assert checks[0].status == "pass"
        assert checks[0].name == "terraform"

    def test_terraform_missing(
        self, provider: TerraformProvider, minimal_ctx: ProviderContext
    ) -> None:
        """check_prerequisites() returns warn when terraform binary not found."""
        with patch("rsf.providers.terraform.shutil.which", return_value=None):
            checks = provider.check_prerequisites(minimal_ctx)

        assert len(checks) == 1
        assert checks[0].status == "warn"
        assert checks[0].name == "terraform"


class TestTerraformProviderValidateConfig:
    """Tests for TerraformProvider.validate_config()."""

    def test_validate_config_noop(
        self, provider: TerraformProvider, minimal_ctx: ProviderContext
    ) -> None:
        """validate_config() is a no-op (Pydantic handles validation)."""
        # Should not raise
        provider.validate_config(minimal_ctx)


class TestProviderRegistration:
    """Tests for TerraformProvider registration in provider registry."""

    def test_get_provider_terraform(self) -> None:
        """get_provider('terraform') returns a TerraformProvider instance."""
        from rsf.providers.registry import get_provider, register_provider

        # Ensure registration (registry may have been cleared by other tests)
        register_provider("terraform", TerraformProvider)
        provider = get_provider("terraform")
        assert isinstance(provider, TerraformProvider)

    def test_list_providers_includes_terraform(self) -> None:
        """list_providers() includes 'terraform'."""
        from rsf.providers.registry import list_providers, register_provider

        # Ensure registration (registry may have been cleared by other tests)
        register_provider("terraform", TerraformProvider)
        providers = list_providers()
        assert "terraform" in providers
