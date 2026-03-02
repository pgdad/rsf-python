"""Tests for rsf diff subcommand."""

from __future__ import annotations

import pytest

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
