"""Tests for CustomProviderConfig Pydantic model and InfrastructureConfig.custom type."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from rsf.dsl.models import CustomProviderConfig, InfrastructureConfig


class TestCustomProviderConfigBasics:
    """Tests for CustomProviderConfig field validation."""

    def test_minimal_config_requires_program(self) -> None:
        """CustomProviderConfig(program=...) creates valid config."""
        config = CustomProviderConfig(program="/usr/bin/deploy")
        assert config.program == "/usr/bin/deploy"

    def test_program_is_required(self) -> None:
        """CustomProviderConfig() without program raises ValidationError."""
        with pytest.raises(ValidationError):
            CustomProviderConfig()  # type: ignore[call-arg]

    def test_args_defaults_to_empty_list(self) -> None:
        """Config without args has args == []."""
        config = CustomProviderConfig(program="/usr/bin/deploy")
        assert config.args == []

    def test_metadata_transport_defaults_to_file(self) -> None:
        """Config without metadata_transport has metadata_transport == 'file'."""
        config = CustomProviderConfig(program="/usr/bin/deploy")
        assert config.metadata_transport == "file"

    def test_teardown_args_defaults_to_none(self) -> None:
        """Config without teardown_args has teardown_args is None."""
        config = CustomProviderConfig(program="/usr/bin/deploy")
        assert config.teardown_args is None

    def test_env_defaults_to_none(self) -> None:
        """Config without env has env is None."""
        config = CustomProviderConfig(program="/usr/bin/deploy")
        assert config.env is None

    def test_timeout_defaults_to_none(self) -> None:
        """Config without timeout has timeout is None."""
        config = CustomProviderConfig(program="/usr/bin/deploy")
        assert config.timeout is None


class TestCustomProviderConfigMetadataTransport:
    """Tests for metadata_transport Literal validation."""

    def test_metadata_transport_accepts_file(self) -> None:
        """metadata_transport='file' is valid."""
        config = CustomProviderConfig(program="/bin/sh", metadata_transport="file")
        assert config.metadata_transport == "file"

    def test_metadata_transport_accepts_env(self) -> None:
        """metadata_transport='env' is valid."""
        config = CustomProviderConfig(program="/bin/sh", metadata_transport="env")
        assert config.metadata_transport == "env"

    def test_metadata_transport_accepts_args(self) -> None:
        """metadata_transport='args' is valid."""
        config = CustomProviderConfig(program="/bin/sh", metadata_transport="args")
        assert config.metadata_transport == "args"

    def test_metadata_transport_rejects_invalid(self) -> None:
        """metadata_transport='invalid' raises ValidationError."""
        with pytest.raises(ValidationError):
            CustomProviderConfig(program="/bin/sh", metadata_transport="invalid")  # type: ignore[arg-type]


class TestCustomProviderConfigExtraFields:
    """Tests for extra field rejection."""

    def test_extra_fields_rejected(self) -> None:
        """extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError):
            CustomProviderConfig(program="/bin/sh", unknown_field="value")  # type: ignore[call-arg]


class TestCustomProviderConfigFull:
    """Tests for full config with all fields."""

    def test_full_config(self) -> None:
        """Config with all fields populated works correctly."""
        config = CustomProviderConfig(
            program="/opt/deploy/my-infra.sh",
            args=["deploy", "--env", "{stage}", "--workflow", "{workflow_name}"],
            teardown_args=["teardown", "--env", "{stage}"],
            metadata_transport="env",
            env={"DEPLOY_TOKEN": "secret123"},
            timeout=300,
        )
        assert config.program == "/opt/deploy/my-infra.sh"
        assert config.args == ["deploy", "--env", "{stage}", "--workflow", "{workflow_name}"]
        assert config.teardown_args == ["teardown", "--env", "{stage}"]
        assert config.metadata_transport == "env"
        assert config.env == {"DEPLOY_TOKEN": "secret123"}
        assert config.timeout == 300


class TestInfrastructureConfigCustom:
    """Tests for InfrastructureConfig.custom typed field."""

    def test_infrastructure_config_accepts_custom(self) -> None:
        """InfrastructureConfig with provider='custom' and CustomProviderConfig works."""
        config = InfrastructureConfig(
            provider="custom",
            custom=CustomProviderConfig(program="/usr/bin/deploy"),
        )
        assert config.provider == "custom"
        assert config.custom is not None
        assert config.custom.program == "/usr/bin/deploy"

    def test_infrastructure_config_custom_none_by_default(self) -> None:
        """InfrastructureConfig().custom is None."""
        config = InfrastructureConfig()
        assert config.custom is None

    def test_infrastructure_config_yaml_round_trip(self) -> None:
        """Dict with nested custom block validates to proper types."""
        data = {
            "provider": "custom",
            "custom": {
                "program": "/opt/deploy/script.sh",
                "args": ["deploy", "--env", "{stage}"],
                "metadata_transport": "file",
            },
        }
        config = InfrastructureConfig.model_validate(data)
        assert config.provider == "custom"
        assert isinstance(config.custom, CustomProviderConfig)
        assert config.custom.program == "/opt/deploy/script.sh"
        assert config.custom.args == ["deploy", "--env", "{stage}"]
        assert config.custom.metadata_transport == "file"
