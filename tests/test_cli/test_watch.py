"""Tests for rsf watch subcommand (auto-validate and regenerate)."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from rsf.cli.watch_cmd import _format_timestamp, _get_watch_paths, run_cycle


def _write_valid_workflow(path: Path) -> None:
    """Write a minimal valid workflow.yaml for testing."""
    data = {
        "StartAt": "Start",
        "States": {
            "Start": {"Type": "Task", "End": True},
        },
    }
    path.write_text(yaml.dump(data), encoding="utf-8")


def _write_invalid_yaml(path: Path) -> None:
    """Write invalid YAML content."""
    path.write_text("invalid: [\nyaml: broken", encoding="utf-8")


def _write_invalid_workflow(path: Path) -> None:
    """Write YAML that fails Pydantic validation."""
    data = {
        "StartAt": "Start",
        "States": {
            "Start": {"Type": "InvalidType", "End": True},
        },
    }
    path.write_text(yaml.dump(data), encoding="utf-8")


def _write_semantic_error_workflow(path: Path) -> None:
    """Write a workflow with semantic validation errors."""
    data = {
        "StartAt": "Start",
        "States": {
            "Start": {"Type": "Task", "Next": "NonExistent"},
        },
    }
    path.write_text(yaml.dump(data), encoding="utf-8")


class TestWatchCycle:
    """Tests for the run_cycle function."""

    def test_valid_workflow_returns_success(self, tmp_path):
        """run_cycle with valid workflow.yaml returns success."""
        workflow = tmp_path / "workflow.yaml"
        _write_valid_workflow(workflow)

        success, message = run_cycle(workflow)

        assert success is True
        assert "Valid + regenerated" in message

    def test_invalid_yaml_returns_error(self, tmp_path):
        """run_cycle with invalid YAML returns error."""
        workflow = tmp_path / "workflow.yaml"
        _write_invalid_yaml(workflow)

        success, message = run_cycle(workflow)

        assert success is False
        assert "YAML error" in message or "validation error" in message

    def test_pydantic_validation_error_returns_count(self, tmp_path):
        """run_cycle with Pydantic validation error returns error count."""
        workflow = tmp_path / "workflow.yaml"
        _write_invalid_workflow(workflow)

        success, message = run_cycle(workflow)

        assert success is False
        assert "validation error" in message or "error" in message.lower()

    def test_semantic_validation_error_returns_count(self, tmp_path):
        """run_cycle with semantic validation errors returns error count."""
        workflow = tmp_path / "workflow.yaml"
        _write_semantic_error_workflow(workflow)

        success, message = run_cycle(workflow)

        assert success is False
        assert "error" in message.lower()

    def test_generates_orchestrator_on_success(self, tmp_path):
        """run_cycle generates orchestrator.py on success."""
        workflow = tmp_path / "workflow.yaml"
        _write_valid_workflow(workflow)

        success, message = run_cycle(workflow)

        assert success is True
        assert (tmp_path / "orchestrator.py").exists()

    def test_deploy_calls_provider_interface(self, tmp_path):
        """run_cycle with --deploy routes through the provider interface."""
        workflow = tmp_path / "workflow.yaml"
        _write_valid_workflow(workflow)

        tf_dir = tmp_path / "terraform"
        tf_dir.mkdir()

        mock_config = MagicMock()
        mock_config.provider = "terraform"

        mock_provider = MagicMock()

        with (
            patch("rsf.cli.watch_cmd.resolve_infra_config", return_value=mock_config),
            patch("rsf.cli.watch_cmd.get_provider", return_value=mock_provider),
        ):
            success, message = run_cycle(workflow, deploy=True, tf_dir=tf_dir)

            assert success is True
            assert "deployed" in message
            mock_provider.generate.assert_called_once()
            mock_provider.deploy.assert_called_once()

    def test_deploy_failure_returns_error(self, tmp_path):
        """run_cycle with --deploy failure returns deploy error."""
        workflow = tmp_path / "workflow.yaml"
        _write_valid_workflow(workflow)

        tf_dir = tmp_path / "terraform"
        tf_dir.mkdir()

        import subprocess

        mock_config = MagicMock()
        mock_config.provider = "terraform"

        mock_provider = MagicMock()
        mock_provider.deploy.side_effect = subprocess.CalledProcessError(1, "terraform")

        with (
            patch("rsf.cli.watch_cmd.resolve_infra_config", return_value=mock_config),
            patch("rsf.cli.watch_cmd.get_provider", return_value=mock_provider),
        ):
            success, message = run_cycle(workflow, deploy=True, tf_dir=tf_dir)

            assert success is False
            assert "deploy failed" in message

    def test_deploy_with_cdk_provider(self, tmp_path):
        """run_cycle with --deploy works with CDK provider."""
        workflow = tmp_path / "workflow.yaml"
        _write_valid_workflow(workflow)

        tf_dir = tmp_path / "terraform"
        tf_dir.mkdir()

        mock_config = MagicMock()
        mock_config.provider = "cdk"

        mock_provider = MagicMock()

        with (
            patch("rsf.cli.watch_cmd.resolve_infra_config", return_value=mock_config),
            patch("rsf.cli.watch_cmd.get_provider", return_value=mock_provider),
        ):
            success, message = run_cycle(workflow, deploy=True, tf_dir=tf_dir)

            assert success is True
            assert "cdk" in message
            mock_provider.generate.assert_called_once()
            mock_provider.deploy.assert_called_once()

    def test_deploy_provider_not_found_returns_error(self, tmp_path):
        """run_cycle with unknown provider returns error."""
        from rsf.providers import ProviderNotFoundError

        workflow = tmp_path / "workflow.yaml"
        _write_valid_workflow(workflow)

        tf_dir = tmp_path / "terraform"
        tf_dir.mkdir()

        mock_config = MagicMock()
        mock_config.provider = "nonexistent"

        with (
            patch("rsf.cli.watch_cmd.resolve_infra_config", return_value=mock_config),
            patch("rsf.cli.watch_cmd.get_provider", side_effect=ProviderNotFoundError("nonexistent")),
        ):
            success, message = run_cycle(workflow, deploy=True, tf_dir=tf_dir)

            assert success is False
            assert "deploy failed" in message

    def test_deploy_creates_provider_context_with_auto_approve(self, tmp_path):
        """run_cycle deploy creates ProviderContext with auto_approve=True."""
        workflow = tmp_path / "workflow.yaml"
        _write_valid_workflow(workflow)

        tf_dir = tmp_path / "terraform"
        tf_dir.mkdir()

        mock_config = MagicMock()
        mock_config.provider = "terraform"

        mock_provider = MagicMock()

        with (
            patch("rsf.cli.watch_cmd.resolve_infra_config", return_value=mock_config),
            patch("rsf.cli.watch_cmd.get_provider", return_value=mock_provider),
        ):
            run_cycle(workflow, deploy=True, tf_dir=tf_dir)

            # Get the ProviderContext passed to deploy
            ctx = mock_provider.deploy.call_args[0][0]
            assert ctx.auto_approve is True

    def test_format_timestamp_returns_bracketed_time(self):
        """_format_timestamp returns [HH:MM:SS] format."""
        ts = _format_timestamp()
        assert re.match(r"\[\d{2}:\d{2}:\d{2}\]", ts)

    def test_get_watch_paths_returns_workflow_and_handlers(self, tmp_path):
        """_get_watch_paths returns workflow file and handlers directory."""
        workflow = tmp_path / "workflow.yaml"
        workflow.touch()
        handlers_dir = tmp_path / "handlers"
        handlers_dir.mkdir()

        paths = _get_watch_paths(workflow)

        assert workflow in paths
        assert handlers_dir in paths

    def test_get_watch_paths_without_handlers_dir(self, tmp_path):
        """_get_watch_paths returns only workflow when handlers/ doesn't exist."""
        workflow = tmp_path / "workflow.yaml"
        workflow.touch()

        paths = _get_watch_paths(workflow)

        assert workflow in paths
        assert len(paths) == 1
