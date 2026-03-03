"""Tests for rsf diff subcommand."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from rsf.dsl.parser import parse_definition
from rsf.cli.diff_cmd import DiffEntry, compute_diff


def _make_definition(states_yaml: dict, start_at: str = "Start", **kwargs):
    """Helper to create a StateMachineDefinition from a dict."""
    data = {
        "StartAt": start_at,
        "States": states_yaml,
        **kwargs,
    }
    return parse_definition(data)


class TestWorkflowDiffEngine:
    """Tests for the compute_diff engine."""

    def test_identical_definitions_produce_empty_diff(self):
        """Two identical definitions should produce no changes."""
        defn = _make_definition(
            {"Start": {"Type": "Task", "End": True}},
        )
        diffs = compute_diff(defn, defn)
        assert diffs == []

    def test_state_added_shows_as_added(self):
        """State present in local but not deployed shows as 'added'."""
        local = _make_definition({
            "Start": {"Type": "Task", "Next": "NewState"},
            "NewState": {"Type": "Pass", "End": True},
        })
        deployed = _make_definition({
            "Start": {"Type": "Task", "End": True},
        })
        diffs = compute_diff(local, deployed)
        state_diffs = [d for d in diffs if d.component == "State" and d.name == "NewState"]
        assert len(state_diffs) == 1
        assert state_diffs[0].change == "added"
        assert state_diffs[0].local == "Pass"

    def test_state_removed_shows_as_removed(self):
        """State present in deployed but not local shows as 'removed'."""
        local = _make_definition({
            "Start": {"Type": "Task", "End": True},
        })
        deployed = _make_definition({
            "Start": {"Type": "Task", "Next": "OldState"},
            "OldState": {"Type": "Pass", "End": True},
        })
        diffs = compute_diff(local, deployed)
        state_diffs = [d for d in diffs if d.component == "State" and d.name == "OldState"]
        assert len(state_diffs) == 1
        assert state_diffs[0].change == "removed"

    def test_state_type_changed_shows_as_changed(self):
        """State with different type shows as 'changed'."""
        local = _make_definition({
            "Start": {"Type": "Pass", "End": True},
        })
        deployed = _make_definition({
            "Start": {"Type": "Task", "End": True},
        })
        diffs = compute_diff(local, deployed)
        state_diffs = [d for d in diffs if d.component == "State" and d.name == "Start"]
        assert len(state_diffs) == 1
        assert state_diffs[0].change == "changed"
        assert "Pass" in state_diffs[0].local
        assert "Task" in state_diffs[0].deployed

    def test_transition_changed_detected(self):
        """State with different Next target shows as transition change."""
        local = _make_definition({
            "Start": {"Type": "Task", "Next": "StateB"},
            "StateA": {"Type": "Pass", "End": True},
            "StateB": {"Type": "Pass", "End": True},
        })
        deployed = _make_definition({
            "Start": {"Type": "Task", "Next": "StateA"},
            "StateA": {"Type": "Pass", "End": True},
            "StateB": {"Type": "Pass", "End": True},
        })
        diffs = compute_diff(local, deployed)
        transition_diffs = [d for d in diffs if d.component == "Transition" and d.name == "Start"]
        assert len(transition_diffs) == 1
        assert transition_diffs[0].change == "changed"
        assert "StateB" in transition_diffs[0].local
        assert "StateA" in transition_diffs[0].deployed

    def test_start_at_changed_detected(self):
        """Different StartAt shows as top-level config change."""
        local = _make_definition(
            {
                "Start": {"Type": "Task", "End": True},
                "Alt": {"Type": "Pass", "End": True},
            },
            start_at="Alt",
        )
        deployed = _make_definition(
            {
                "Start": {"Type": "Task", "End": True},
                "Alt": {"Type": "Pass", "End": True},
            },
            start_at="Start",
        )
        diffs = compute_diff(local, deployed)
        config_diffs = [d for d in diffs if d.component == "Config" and d.name == "StartAt"]
        assert len(config_diffs) == 1
        assert config_diffs[0].change == "changed"
        assert config_diffs[0].local == "Alt"
        assert config_diffs[0].deployed == "Start"

    def test_handler_added_detected(self):
        """Adding a Task state should also report a handler addition."""
        local = _make_definition({
            "Start": {"Type": "Task", "Next": "Process"},
            "Process": {"Type": "Task", "End": True},
        })
        deployed = _make_definition({
            "Start": {"Type": "Task", "End": True},
        })
        diffs = compute_diff(local, deployed)
        handler_diffs = [d for d in diffs if d.component == "Handler" and d.name == "Process"]
        assert len(handler_diffs) == 1
        assert handler_diffs[0].change == "added"

    def test_multiple_changes_all_reported(self):
        """Multiple changes in same workflow should all be reported."""
        local = _make_definition({
            "Start": {"Type": "Pass", "Next": "NewState"},
            "NewState": {"Type": "Task", "End": True},
        })
        deployed = _make_definition({
            "Start": {"Type": "Task", "Next": "OldState"},
            "OldState": {"Type": "Pass", "End": True},
        })
        diffs = compute_diff(local, deployed)
        # Should have changes for: Start type change, Start transition change,
        # NewState added (+ handler), OldState removed
        assert len(diffs) >= 4

    def test_none_deployed_treats_all_as_added(self):
        """None deployed definition means everything is new."""
        local = _make_definition({
            "Start": {"Type": "Task", "Next": "Process"},
            "Process": {"Type": "Pass", "End": True},
        })
        diffs = compute_diff(local, None)
        state_diffs = [d for d in diffs if d.component == "State"]
        assert len(state_diffs) == 2
        assert all(d.change == "added" for d in state_diffs)
        # Task state should also have a handler entry
        handler_diffs = [d for d in diffs if d.component == "Handler"]
        assert len(handler_diffs) == 1
        assert handler_diffs[0].name == "Start"

    def test_timeout_change_detected(self):
        """TimeoutSeconds change detected as top-level change."""
        local = _make_definition(
            {"Start": {"Type": "Task", "End": True}},
            TimeoutSeconds=300,
        )
        deployed = _make_definition(
            {"Start": {"Type": "Task", "End": True}},
            TimeoutSeconds=600,
        )
        diffs = compute_diff(local, deployed)
        config_diffs = [d for d in diffs if d.component == "Config" and d.name == "TimeoutSeconds"]
        assert len(config_diffs) == 1
        assert config_diffs[0].change == "changed"
        assert "300" in config_diffs[0].local
        assert "600" in config_diffs[0].deployed


# --- Helper for CLI tests ---


def _write_diff_workflow(tmp_path: Path) -> Path:
    """Write a minimal workflow.yaml file and return the path."""
    workflow = tmp_path / "workflow.yaml"
    data = {"StartAt": "Start", "States": {"Start": {"Type": "Task", "End": True}}}
    workflow.write_text(yaml.dump(data), encoding="utf-8")
    return workflow


# --- Provider-aware diff tests ---


class TestProviderAwareDiff:
    """Tests for provider-aware diff behavior."""

    def test_non_terraform_provider_shows_message_and_exits_0(self, tmp_path: Path) -> None:
        """Non-terraform provider shows message and exits 0."""
        workflow = _write_diff_workflow(tmp_path)

        mock_config = MagicMock()
        mock_config.provider = "cdk"

        from typer.testing import CliRunner
        from rsf.cli.main import app

        with patch("rsf.cli.diff_cmd.resolve_infra_config", return_value=mock_config):
            runner = CliRunner()
            result = runner.invoke(app, ["diff", str(workflow)])
            assert result.exit_code == 0
            assert "not available" in result.output.lower()
            assert "cdk" in result.output

    def test_terraform_provider_proceeds_normally(self, tmp_path: Path) -> None:
        """Terraform provider proceeds normally (shows all as new)."""
        workflow = _write_diff_workflow(tmp_path)

        mock_config = MagicMock()
        mock_config.provider = "terraform"

        from typer.testing import CliRunner
        from rsf.cli.main import app

        with patch("rsf.cli.diff_cmd.resolve_infra_config", return_value=mock_config):
            runner = CliRunner()
            result = runner.invoke(app, ["diff", str(workflow)])
            assert result.exit_code == 1  # Differences found (all new)
            assert "not available" not in result.output.lower()

    def test_provider_detection_failure_defaults_to_terraform(self, tmp_path: Path) -> None:
        """Provider detection failure defaults to terraform behavior."""
        workflow = _write_diff_workflow(tmp_path)

        from typer.testing import CliRunner
        from rsf.cli.main import app

        with patch("rsf.cli.diff_cmd.resolve_infra_config", side_effect=Exception("config error")):
            runner = CliRunner()
            result = runner.invoke(app, ["diff", str(workflow)])
            assert result.exit_code == 1  # Proceeds as terraform
            assert "not available" not in result.output.lower()

    def test_custom_provider_shows_provider_name_in_message(self, tmp_path: Path) -> None:
        """Custom provider name appears in the not-available message."""
        workflow = _write_diff_workflow(tmp_path)

        mock_config = MagicMock()
        mock_config.provider = "custom"

        from typer.testing import CliRunner
        from rsf.cli.main import app

        with patch("rsf.cli.diff_cmd.resolve_infra_config", return_value=mock_config):
            runner = CliRunner()
            result = runner.invoke(app, ["diff", str(workflow)])
            assert result.exit_code == 0
            assert "custom" in result.output
