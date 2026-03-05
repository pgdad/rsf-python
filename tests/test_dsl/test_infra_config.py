"""Tests for InfrastructureConfig and TerraformProviderConfig Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from rsf.dsl.models import InfrastructureConfig, TerraformProviderConfig


class TestTerraformProviderConfig:
    """Tests for TerraformProviderConfig model."""

    def test_defaults(self) -> None:
        """TerraformProviderConfig with no args has tf_dir='terraform'."""
        config = TerraformProviderConfig()
        assert config.tf_dir == "terraform"
        assert config.backend_bucket is None
        assert config.backend_key is None
        assert config.backend_dynamodb_table is None

    def test_custom_values(self) -> None:
        """TerraformProviderConfig accepts custom tf_dir and backend settings."""
        config = TerraformProviderConfig(
            tf_dir="custom",
            backend_bucket="my-bucket",
            backend_key="my-key",
            backend_dynamodb_table="my-table",
        )
        assert config.tf_dir == "custom"
        assert config.backend_bucket == "my-bucket"
        assert config.backend_key == "my-key"
        assert config.backend_dynamodb_table == "my-table"

    def test_extra_forbid(self) -> None:
        """TerraformProviderConfig rejects unknown fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            TerraformProviderConfig(bad_field="x")


class TestInfrastructureConfig:
    """Tests for InfrastructureConfig model."""

    def test_defaults(self) -> None:
        """InfrastructureConfig with no args defaults to provider='terraform'."""
        config = InfrastructureConfig()
        assert config.provider == "terraform"
        assert config.terraform is None
        assert config.cdk is None
        assert config.custom is None

    def test_terraform_provider_with_config(self) -> None:
        """InfrastructureConfig with terraform provider-specific config."""
        config = InfrastructureConfig(
            provider="terraform",
            terraform=TerraformProviderConfig(tf_dir="custom"),
        )
        assert config.provider == "terraform"
        assert config.terraform is not None
        assert config.terraform.tf_dir == "custom"

    def test_cdk_provider_with_dict_config(self) -> None:
        """InfrastructureConfig accepts cdk as dict (forward compat for Phase 53)."""
        config = InfrastructureConfig(
            provider="cdk",
            cdk={"app_dir": "cdk_app"},
        )
        assert config.provider == "cdk"
        assert config.cdk == {"app_dir": "cdk_app"}

    def test_custom_provider_with_dict_config(self) -> None:
        """InfrastructureConfig accepts custom as dict (forward compat for Phase 54)."""
        config = InfrastructureConfig(
            provider="custom",
            custom={"program": "/usr/bin/deploy.sh"},
        )
        assert config.provider == "custom"
        assert config.custom.program == "/usr/bin/deploy.sh"

    def test_extra_forbid(self) -> None:
        """InfrastructureConfig rejects unknown fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            InfrastructureConfig(unknown_field="x")

    def test_from_dict(self) -> None:
        """InfrastructureConfig can be created from dict (model_validate)."""
        config = InfrastructureConfig.model_validate({
            "provider": "terraform",
            "terraform": {"tf_dir": "custom", "backend_bucket": "my-bucket"},
        })
        assert config.provider == "terraform"
        assert config.terraform.tf_dir == "custom"
        assert config.terraform.backend_bucket == "my-bucket"


class TestStateMachineDefinitionInfrastructure:
    """Tests for infrastructure field on StateMachineDefinition."""

    def test_no_infrastructure_field(self) -> None:
        """Workflow YAML with no infrastructure: key -> definition.infrastructure is None."""
        from rsf.dsl.parser import parse_definition

        data = {
            "rsf_version": "1.0",
            "Comment": "test",
            "StartAt": "Hello",
            "States": {
                "Hello": {"Type": "Pass", "End": True},
            },
        }
        definition = parse_definition(data)
        assert definition.infrastructure is None

    def test_infrastructure_terraform(self) -> None:
        """Workflow YAML with infrastructure: {provider: terraform} parses correctly."""
        from rsf.dsl.parser import parse_definition

        data = {
            "rsf_version": "1.0",
            "Comment": "test",
            "StartAt": "Hello",
            "States": {
                "Hello": {"Type": "Pass", "End": True},
            },
            "infrastructure": {
                "provider": "terraform",
            },
        }
        definition = parse_definition(data)
        assert definition.infrastructure is not None
        assert definition.infrastructure.provider == "terraform"

    def test_infrastructure_with_nested_terraform_config(self) -> None:
        """Workflow YAML with infrastructure: {provider: terraform, terraform: {tf_dir: custom}} parses."""
        from rsf.dsl.parser import parse_definition

        data = {
            "rsf_version": "1.0",
            "Comment": "test",
            "StartAt": "Hello",
            "States": {
                "Hello": {"Type": "Pass", "End": True},
            },
            "infrastructure": {
                "provider": "terraform",
                "terraform": {
                    "tf_dir": "custom",
                    "backend_bucket": "my-bucket",
                },
            },
        }
        definition = parse_definition(data)
        assert definition.infrastructure is not None
        assert definition.infrastructure.terraform is not None
        assert definition.infrastructure.terraform.tf_dir == "custom"
        assert definition.infrastructure.terraform.backend_bucket == "my-bucket"

    def test_infrastructure_unknown_field_rejected(self) -> None:
        """Workflow YAML with infrastructure: {bad_field: x} -> ValidationError."""
        from rsf.dsl.parser import parse_definition

        data = {
            "rsf_version": "1.0",
            "Comment": "test",
            "StartAt": "Hello",
            "States": {
                "Hello": {"Type": "Pass", "End": True},
            },
            "infrastructure": {
                "provider": "terraform",
                "bad_field": "x",
            },
        }
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            parse_definition(data)
