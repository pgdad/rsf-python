"""Tests for semantic cross-state validation (BFS)."""

import pytest

from rsf.dsl import StateMachineDefinition
from rsf.dsl.validator import validate_definition


def _validate(data: dict) -> list:
    sm = StateMachineDefinition.model_validate(data)
    return validate_definition(sm)


class TestReferenceResolution:
    def test_valid_references(self):
        errors = _validate(
            {
                "StartAt": "A",
                "States": {
                    "A": {"Type": "Task", "Next": "B"},
                    "B": {"Type": "Succeed"},
                },
            }
        )
        assert len(errors) == 0

    def test_invalid_next(self):
        errors = _validate(
            {
                "StartAt": "A",
                "States": {
                    "A": {"Type": "Task", "Next": "NonExistent"},
                    "B": {"Type": "Succeed"},
                },
            }
        )
        assert any("NonExistent" in e.message for e in errors)

    def test_invalid_startat(self):
        errors = _validate(
            {
                "StartAt": "Missing",
                "States": {"A": {"Type": "Succeed"}},
            }
        )
        assert any("StartAt" in e.path for e in errors)

    def test_invalid_choice_default(self):
        errors = _validate(
            {
                "StartAt": "C",
                "States": {
                    "C": {
                        "Type": "Choice",
                        "Choices": [
                            {"Variable": "$.x", "NumericEquals": 1, "Next": "A"},
                        ],
                        "Default": "BadRef",
                    },
                    "A": {"Type": "Succeed"},
                },
            }
        )
        assert any("BadRef" in e.message for e in errors)

    def test_invalid_catch_next(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {
                    "T": {
                        "Type": "Task",
                        "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "Missing"}],
                        "End": True,
                    },
                },
            }
        )
        assert any("Missing" in e.message for e in errors)


class TestReachability:
    def test_all_reachable(self):
        errors = _validate(
            {
                "StartAt": "A",
                "States": {
                    "A": {"Type": "Task", "Next": "B"},
                    "B": {"Type": "Succeed"},
                },
            }
        )
        assert len(errors) == 0

    def test_unreachable_state(self):
        errors = _validate(
            {
                "StartAt": "A",
                "States": {
                    "A": {"Type": "Succeed"},
                    "Orphan": {"Type": "Succeed"},
                },
            }
        )
        assert any("Orphan" in e.message and "reachable" in e.message for e in errors)

    def test_reachable_via_choice(self):
        errors = _validate(
            {
                "StartAt": "C",
                "States": {
                    "C": {
                        "Type": "Choice",
                        "Choices": [
                            {"Variable": "$.x", "NumericEquals": 1, "Next": "A"},
                        ],
                        "Default": "B",
                    },
                    "A": {"Type": "Succeed"},
                    "B": {"Type": "Succeed"},
                },
            }
        )
        assert len(errors) == 0

    def test_reachable_via_catch(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {
                    "T": {
                        "Type": "Task",
                        "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "Err"}],
                        "Next": "Done",
                    },
                    "Done": {"Type": "Succeed"},
                    "Err": {"Type": "Fail", "Error": "E"},
                },
            }
        )
        assert len(errors) == 0


class TestTerminalState:
    def test_has_terminal(self):
        errors = _validate(
            {
                "StartAt": "A",
                "States": {"A": {"Type": "Succeed"}},
            }
        )
        assert len(errors) == 0

    def test_end_true_is_terminal(self):
        errors = _validate(
            {
                "StartAt": "A",
                "States": {"A": {"Type": "Task", "End": True}},
            }
        )
        assert len(errors) == 0

    def test_no_terminal(self):
        errors = _validate(
            {
                "StartAt": "A",
                "States": {
                    "A": {"Type": "Task", "Next": "B"},
                    "B": {"Type": "Task", "Next": "A"},
                },
            }
        )
        assert any("terminal" in e.message for e in errors)


class TestStatesAllOrdering:
    def test_states_all_last_is_ok(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {
                    "T": {
                        "Type": "Task",
                        "Retry": [
                            {"ErrorEquals": ["Custom"], "MaxAttempts": 1},
                            {"ErrorEquals": ["States.ALL"], "MaxAttempts": 2},
                        ],
                        "End": True,
                    },
                },
            }
        )
        assert not any("States.ALL" in e.message for e in errors)

    def test_states_all_not_last_is_error(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {
                    "T": {
                        "Type": "Task",
                        "Retry": [
                            {"ErrorEquals": ["States.ALL"], "MaxAttempts": 2},
                            {"ErrorEquals": ["Custom"], "MaxAttempts": 1},
                        ],
                        "End": True,
                    },
                },
            }
        )
        assert any("States.ALL" in e.message for e in errors)


class TestRecursiveBranchValidation:
    def test_parallel_branch_validation(self):
        errors = _validate(
            {
                "StartAt": "P",
                "States": {
                    "P": {
                        "Type": "Parallel",
                        "Branches": [
                            {
                                "StartAt": "A",
                                "States": {
                                    "A": {"Type": "Task", "Next": "Missing"},
                                    "B": {"Type": "Succeed"},
                                },
                            }
                        ],
                        "End": True,
                    }
                },
            }
        )
        assert any("Missing" in e.message for e in errors)

    def test_map_item_processor_validation(self):
        errors = _validate(
            {
                "StartAt": "M",
                "States": {
                    "M": {
                        "Type": "Map",
                        "ItemProcessor": {
                            "StartAt": "X",
                            "States": {
                                "X": {"Type": "Task", "Next": "Ghost"},
                                "Y": {"Type": "Succeed"},
                            },
                        },
                        "End": True,
                    }
                },
            }
        )
        assert any("Ghost" in e.message for e in errors)
