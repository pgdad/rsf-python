"""Tests for the BFS state mapper."""

from rsf.dsl.parser import parse_definition
from rsf.codegen.state_mappers import map_states


def _parse(data):
    """Helper to parse a dict into a StateMachineDefinition."""
    return parse_definition(data)


class TestMapStatesBasic:
    def test_single_task(self):
        sm = _parse(
            {
                "StartAt": "DoWork",
                "States": {
                    "DoWork": {"Type": "Task", "End": True},
                },
            }
        )
        mappings = map_states(sm)
        assert len(mappings) == 1
        assert mappings[0].state_name == "DoWork"
        assert mappings[0].state_type == "Task"
        assert mappings[0].sdk_primitive == "context.step"

    def test_task_chain(self):
        sm = _parse(
            {
                "StartAt": "Step1",
                "States": {
                    "Step1": {"Type": "Task", "Next": "Step2"},
                    "Step2": {"Type": "Task", "Next": "Step3"},
                    "Step3": {"Type": "Task", "End": True},
                },
            }
        )
        mappings = map_states(sm)
        assert len(mappings) == 3
        names = [m.state_name for m in mappings]
        assert names == ["Step1", "Step2", "Step3"]

    def test_bfs_order(self):
        """BFS visits states in breadth-first order."""
        sm = _parse(
            {
                "StartAt": "Start",
                "States": {
                    "Start": {"Type": "Task", "Next": "Middle"},
                    "Middle": {"Type": "Task", "Next": "End"},
                    "End": {"Type": "Succeed"},
                },
            }
        )
        mappings = map_states(sm)
        names = [m.state_name for m in mappings]
        assert names == ["Start", "Middle", "End"]


class TestMapAllStateTypes:
    def test_pass_state(self):
        sm = _parse(
            {
                "StartAt": "Inject",
                "States": {
                    "Inject": {
                        "Type": "Pass",
                        "Result": {"key": "value"},
                        "ResultPath": "$.data",
                        "End": True,
                    },
                },
            }
        )
        mappings = map_states(sm)
        assert mappings[0].state_type == "Pass"
        assert mappings[0].sdk_primitive == "passthrough"
        assert mappings[0].params["result"] == {"key": "value"}
        assert mappings[0].params["result_path"] == "$.data"

    def test_choice_state(self):
        sm = _parse(
            {
                "StartAt": "Route",
                "States": {
                    "Route": {
                        "Type": "Choice",
                        "Choices": [
                            {"Variable": "$.x", "NumericGreaterThan": 10, "Next": "Big"},
                        ],
                        "Default": "Small",
                    },
                    "Big": {"Type": "Succeed"},
                    "Small": {"Type": "Succeed"},
                },
            }
        )
        mappings = map_states(sm)
        choice = mappings[0]
        assert choice.state_type == "Choice"
        assert choice.sdk_primitive == "conditional"
        assert len(choice.params["rules"]) == 1
        assert choice.params["default"] == "Small"

    def test_wait_state(self):
        sm = _parse(
            {
                "StartAt": "Delay",
                "States": {
                    "Delay": {"Type": "Wait", "Seconds": 30, "End": True},
                },
            }
        )
        mappings = map_states(sm)
        assert mappings[0].state_type == "Wait"
        assert mappings[0].sdk_primitive == "context.wait"
        assert mappings[0].params["seconds"] == 30

    def test_succeed_state(self):
        sm = _parse(
            {
                "StartAt": "Done",
                "States": {"Done": {"Type": "Succeed"}},
            }
        )
        mappings = map_states(sm)
        assert mappings[0].state_type == "Succeed"
        assert mappings[0].sdk_primitive == "return"

    def test_fail_state(self):
        sm = _parse(
            {
                "StartAt": "DoWork",
                "States": {
                    "DoWork": {"Type": "Task", "Next": "Boom"},
                    "Boom": {"Type": "Fail", "Error": "Kaboom", "Cause": "it broke"},
                },
            }
        )
        mappings = map_states(sm)
        fail = [m for m in mappings if m.state_type == "Fail"][0]
        assert fail.sdk_primitive == "raise"
        assert fail.params["error"] == "Kaboom"
        assert fail.params["cause"] == "it broke"

    def test_parallel_state(self):
        sm = _parse(
            {
                "StartAt": "Both",
                "States": {
                    "Both": {
                        "Type": "Parallel",
                        "Branches": [
                            {"StartAt": "A", "States": {"A": {"Type": "Task", "End": True}}},
                            {"StartAt": "B", "States": {"B": {"Type": "Task", "End": True}}},
                        ],
                        "End": True,
                    },
                },
            }
        )
        mappings = map_states(sm)
        par = mappings[0]
        assert par.state_type == "Parallel"
        assert par.sdk_primitive == "context.parallel"
        assert len(par.params["branches"]) == 2

    def test_map_state(self):
        sm = _parse(
            {
                "StartAt": "Iterate",
                "States": {
                    "Iterate": {
                        "Type": "Map",
                        "ItemsPath": "$.items",
                        "MaxConcurrency": 5,
                        "ItemProcessor": {
                            "StartAt": "Process",
                            "States": {"Process": {"Type": "Task", "End": True}},
                        },
                        "End": True,
                    },
                },
            }
        )
        mappings = map_states(sm)
        m = mappings[0]
        assert m.state_type == "Map"
        assert m.sdk_primitive == "context.map"
        assert m.params["items_path"] == "$.items"
        assert m.params["max_concurrency"] == 5


class TestBFSTraversal:
    def test_choice_branches_included(self):
        sm = _parse(
            {
                "StartAt": "Route",
                "States": {
                    "Route": {
                        "Type": "Choice",
                        "Choices": [
                            {"Variable": "$.x", "BooleanEquals": True, "Next": "BranchA"},
                        ],
                        "Default": "BranchB",
                    },
                    "BranchA": {"Type": "Succeed"},
                    "BranchB": {"Type": "Succeed"},
                },
            }
        )
        mappings = map_states(sm)
        names = {m.state_name for m in mappings}
        assert names == {"Route", "BranchA", "BranchB"}

    def test_catch_targets_included(self):
        sm = _parse(
            {
                "StartAt": "Risky",
                "States": {
                    "Risky": {
                        "Type": "Task",
                        "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "HandleErr"}],
                        "Next": "Done",
                    },
                    "Done": {"Type": "Succeed"},
                    "HandleErr": {"Type": "Fail", "Error": "Caught"},
                },
            }
        )
        mappings = map_states(sm)
        names = {m.state_name for m in mappings}
        assert names == {"Risky", "Done", "HandleErr"}

    def test_loop_back_states(self):
        sm = _parse(
            {
                "StartAt": "Start",
                "States": {
                    "Start": {"Type": "Task", "Next": "Check"},
                    "Check": {
                        "Type": "Choice",
                        "Choices": [
                            {"Variable": "$.done", "BooleanEquals": True, "Next": "End"},
                        ],
                        "Default": "Start",  # Loop back
                    },
                    "End": {"Type": "Succeed"},
                },
            }
        )
        mappings = map_states(sm)
        names = {m.state_name for m in mappings}
        assert names == {"Start", "Check", "End"}


class TestTaskParams:
    def test_retry_params(self):
        sm = _parse(
            {
                "StartAt": "Do",
                "States": {
                    "Do": {
                        "Type": "Task",
                        "Retry": [
                            {
                                "ErrorEquals": ["TransientError"],
                                "IntervalSeconds": 2,
                                "MaxAttempts": 3,
                                "BackoffRate": 2.0,
                            }
                        ],
                        "End": True,
                    },
                },
            }
        )
        mappings = map_states(sm)
        assert mappings[0].params["has_retry"] is True
        assert len(mappings[0].params["retry_policies"]) == 1

    def test_catch_params(self):
        sm = _parse(
            {
                "StartAt": "Do",
                "States": {
                    "Do": {
                        "Type": "Task",
                        "Catch": [
                            {
                                "ErrorEquals": ["States.ALL"],
                                "Next": "Fail",
                                "ResultPath": "$.error",
                            }
                        ],
                        "Next": "Done",
                    },
                    "Done": {"Type": "Succeed"},
                    "Fail": {"Type": "Fail", "Error": "Caught"},
                },
            }
        )
        mappings = map_states(sm)
        task = mappings[0]
        assert task.params["has_catch"] is True
        assert task.params["catch_policies"][0]["next"] == "Fail"
        assert task.params["catch_policies"][0]["result_path"] == "$.error"

    def test_timeout_params(self):
        sm = _parse(
            {
                "StartAt": "Do",
                "States": {
                    "Do": {
                        "Type": "Task",
                        "TimeoutSeconds": 300,
                        "HeartbeatSeconds": 60,
                        "End": True,
                    },
                },
            }
        )
        mappings = map_states(sm)
        assert mappings[0].params["timeout_seconds"] == 300
        assert mappings[0].params["heartbeat_seconds"] == 60


class TestChoiceRuleMapping:
    def test_boolean_and_rule(self):
        sm = _parse(
            {
                "StartAt": "Route",
                "States": {
                    "Route": {
                        "Type": "Choice",
                        "Choices": [
                            {
                                "And": [
                                    {"Variable": "$.x", "NumericGreaterThan": 0},
                                    {"Variable": "$.y", "StringEquals": "yes"},
                                ],
                                "Next": "Match",
                            }
                        ],
                        "Default": "NoMatch",
                    },
                    "Match": {"Type": "Succeed"},
                    "NoMatch": {"Type": "Succeed"},
                },
            }
        )
        mappings = map_states(sm)
        rule = mappings[0].params["rules"][0]
        assert rule["type"] == "and"
        assert len(rule["conditions"]) == 2

    def test_boolean_not_rule(self):
        sm = _parse(
            {
                "StartAt": "Route",
                "States": {
                    "Route": {
                        "Type": "Choice",
                        "Choices": [
                            {
                                "Not": {"Variable": "$.flag", "BooleanEquals": False},
                                "Next": "Match",
                            }
                        ],
                        "Default": "NoMatch",
                    },
                    "Match": {"Type": "Succeed"},
                    "NoMatch": {"Type": "Succeed"},
                },
            }
        )
        mappings = map_states(sm)
        rule = mappings[0].params["rules"][0]
        assert rule["type"] == "not"
        assert rule["condition"]["type"] == "data_test"
