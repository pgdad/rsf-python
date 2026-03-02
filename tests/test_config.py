"""Tests for rsf.config — rsf.toml loading and config resolution."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from rsf.config import load_project_config, resolve_infra_config
from rsf.dsl.models import InfrastructureConfig


class TestLoadProjectConfig:
    """Tests for load_project_config()."""

    def test_no_toml_file_returns_none(self, tmp_path: Path) -> None:
        """Directory with no rsf.toml returns None."""
        result = load_project_config(tmp_path)
        assert result is None

    def test_toml_no_infrastructure_returns_none(self, tmp_path: Path) -> None:
        """rsf.toml without [infrastructure] table returns None."""
        (tmp_path / "rsf.toml").write_text('[other]\nkey = "value"\n')
        result = load_project_config(tmp_path)
        assert result is None

    def test_toml_with_valid_infrastructure(self, tmp_path: Path) -> None:
        """rsf.toml with [infrastructure] returns InfrastructureConfig."""
        (tmp_path / "rsf.toml").write_text(
            '[infrastructure]\nprovider = "terraform"\n'
        )
        result = load_project_config(tmp_path)
        assert result is not None
        assert isinstance(result, InfrastructureConfig)
        assert result.provider == "terraform"

    def test_toml_with_nested_terraform_config(self, tmp_path: Path) -> None:
        """rsf.toml with [infrastructure.terraform] parses nested config."""
        (tmp_path / "rsf.toml").write_text(
            '[infrastructure]\n'
            'provider = "terraform"\n'
            '\n'
            '[infrastructure.terraform]\n'
            'tf_dir = "custom"\n'
            'backend_bucket = "my-bucket"\n'
        )
        result = load_project_config(tmp_path)
        assert result is not None
        assert result.provider == "terraform"
        assert result.terraform is not None
        assert result.terraform.tf_dir == "custom"
        assert result.terraform.backend_bucket == "my-bucket"

    def test_toml_with_invalid_field_raises(self, tmp_path: Path) -> None:
        """rsf.toml with unknown field in [infrastructure] raises ValidationError."""
        (tmp_path / "rsf.toml").write_text(
            '[infrastructure]\nprovider = "terraform"\nbad_field = "x"\n'
        )
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            load_project_config(tmp_path)

    def test_toml_default_provider(self, tmp_path: Path) -> None:
        """rsf.toml [infrastructure] without provider key defaults to 'terraform'."""
        (tmp_path / "rsf.toml").write_text("[infrastructure]\n")
        result = load_project_config(tmp_path)
        assert result is not None
        assert result.provider == "terraform"


class TestResolveInfraConfig:
    """Tests for resolve_infra_config() cascade."""

    def test_yaml_infrastructure_wins(self, tmp_path: Path) -> None:
        """Workflow YAML infrastructure: block takes precedence over rsf.toml."""
        from rsf.dsl.parser import parse_definition

        # Write rsf.toml with cdk provider
        (tmp_path / "rsf.toml").write_text(
            '[infrastructure]\nprovider = "cdk"\n'
        )

        # Workflow YAML has terraform provider
        data = {
            "rsf_version": "1.0",
            "Comment": "test",
            "StartAt": "Hello",
            "States": {"Hello": {"Type": "Pass", "End": True}},
            "infrastructure": {"provider": "terraform"},
        }
        definition = parse_definition(data)

        result = resolve_infra_config(definition, tmp_path)
        assert result.provider == "terraform"  # YAML wins over rsf.toml

    def test_toml_when_no_yaml(self, tmp_path: Path) -> None:
        """rsf.toml used when workflow YAML has no infrastructure: block."""
        from rsf.dsl.parser import parse_definition

        # Write rsf.toml
        (tmp_path / "rsf.toml").write_text(
            '[infrastructure]\nprovider = "cdk"\n'
        )

        # Workflow YAML has no infrastructure block
        data = {
            "rsf_version": "1.0",
            "Comment": "test",
            "StartAt": "Hello",
            "States": {"Hello": {"Type": "Pass", "End": True}},
        }
        definition = parse_definition(data)

        result = resolve_infra_config(definition, tmp_path)
        assert result.provider == "cdk"  # rsf.toml used

    def test_default_when_no_yaml_no_toml(self, tmp_path: Path) -> None:
        """Default InfrastructureConfig (terraform) when no YAML or rsf.toml."""
        from rsf.dsl.parser import parse_definition

        # No rsf.toml, no infrastructure: block
        data = {
            "rsf_version": "1.0",
            "Comment": "test",
            "StartAt": "Hello",
            "States": {"Hello": {"Type": "Pass", "End": True}},
        }
        definition = parse_definition(data)

        result = resolve_infra_config(definition, tmp_path)
        assert result.provider == "terraform"  # hardcoded default

    def test_default_returns_infrastructure_config(self, tmp_path: Path) -> None:
        """Default result is an InfrastructureConfig instance."""
        from rsf.dsl.parser import parse_definition

        data = {
            "rsf_version": "1.0",
            "Comment": "test",
            "StartAt": "Hello",
            "States": {"Hello": {"Type": "Pass", "End": True}},
        }
        definition = parse_definition(data)

        result = resolve_infra_config(definition, tmp_path)
        assert isinstance(result, InfrastructureConfig)
