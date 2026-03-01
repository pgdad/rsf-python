"""Tests for DSL state models — all 8 state types, validation, and parsing."""

import pytest
from pydantic import ValidationError

from rsf.dsl import (
    StateMachineDefinition,
    TaskState,
    PassState,
    ChoiceState,
    SucceedState,
    FailState,
    ParallelState,
    MapState,
    DataTestRule,
    BooleanAndRule,
    BooleanNotRule,
    LambdaUrlAuthType,
)


class TestTaskState:
    def test_basic_task(self):
        sm = StateMachineDefinition.model_validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
            }
        )
        assert isinstance(sm.states["T"], TaskState)
        assert sm.states["T"].end is True

    def test_task_with_io(self):
        sm = StateMachineDefinition.model_validate(
            {
                "StartAt": "T",
                "States": {
                    "T": {
                        "Type": "Task",
                        "InputPath": "$.input",
                        "Parameters": {"key.$": "$.val"},
                        "ResultSelector": {"out.$": "$.data"},
                        "ResultPath": "$.result",
                        "OutputPath": "$.result",
                        "End": True,
                    }
                },
            }
        )
        t = sm.states["T"]
        assert t.input_path == "$.input"
        assert t.parameters == {"key.$": "$.val"}
        assert t.result_selector == {"out.$": "$.data"}
        assert t.result_path == "$.result"

    def test_task_with_retry_catch(self):
        sm = StateMachineDefinition.model_validate(
            {
                "StartAt": "T",
                "States": {
                    "T": {
                        "Type": "Task",
                        "Retry": [
                            {
                                "ErrorEquals": ["TransientError"],
                                "IntervalSeconds": 2,
                                "MaxAttempts": 3,
                                "BackoffRate": 2.0,
                            }
                        ],
                        "Catch": [
                            {
                                "ErrorEquals": ["States.ALL"],
                                "Next": "Err",
                                "ResultPath": "$.error",
                            }
                        ],
                        "Next": "Done",
                    },
                    "Err": {"Type": "Fail", "Error": "E"},
                    "Done": {"Type": "Succeed"},
                },
            }
        )
        t = sm.states["T"]
        assert len(t.retry) == 1
        assert t.retry[0].error_equals == ["TransientError"]
        assert len(t.catch) == 1
        assert t.catch[0].next == "Err"

    def test_timeout_mutual_exclusion(self):
        with pytest.raises(ValidationError, match="TimeoutSeconds.*TimeoutSecondsPath"):
            StateMachineDefinition.model_validate(
                {
                    "StartAt": "T",
                    "States": {
                        "T": {
                            "Type": "Task",
                            "TimeoutSeconds": 10,
                            "TimeoutSecondsPath": "$.t",
                            "End": True,
                        }
                    },
                }
            )

    def test_heartbeat_mutual_exclusion(self):
        with pytest.raises(ValidationError, match="HeartbeatSeconds.*HeartbeatSecondsPath"):
            StateMachineDefinition.model_validate(
                {
                    "StartAt": "T",
                    "States": {
                        "T": {
                            "Type": "Task",
                            "HeartbeatSeconds": 10,
                            "HeartbeatSecondsPath": "$.h",
                            "End": True,
                        }
                    },
                }
            )

    def test_heartbeat_must_be_less_than_timeout(self):
        with pytest.raises(ValidationError, match="HeartbeatSeconds must be less"):
            StateMachineDefinition.model_validate(
                {
                    "StartAt": "T",
                    "States": {
                        "T": {
                            "Type": "Task",
                            "TimeoutSeconds": 10,
                            "HeartbeatSeconds": 15,
                            "End": True,
                        }
                    },
                }
            )

    def test_next_xor_end(self):
        with pytest.raises(ValidationError, match="Next.*End"):
            StateMachineDefinition.model_validate(
                {
                    "StartAt": "T",
                    "States": {
                        "T": {"Type": "Task", "Next": "X", "End": True},
                        "X": {"Type": "Succeed"},
                    },
                }
            )

    def test_must_have_next_or_end(self):
        with pytest.raises(ValidationError, match="Next.*End"):
            StateMachineDefinition.model_validate(
                {
                    "StartAt": "T",
                    "States": {"T": {"Type": "Task"}},
                }
            )


class TestPassState:
    def test_pass_with_result(self):
        sm = StateMachineDefinition.model_validate(
            {
                "StartAt": "P",
                "States": {
                    "P": {
                        "Type": "Pass",
                        "Result": {"status": "ok"},
                        "ResultPath": "$.injected",
                        "End": True,
                    }
                },
            }
        )
        assert isinstance(sm.states["P"], PassState)
        assert sm.states["P"].result == {"status": "ok"}

    def test_pass_minimal(self):
        sm = StateMachineDefinition.model_validate(
            {
                "StartAt": "P",
                "States": {"P": {"Type": "Pass", "End": True}},
            }
        )
        assert sm.states["P"].result is None


class TestChoiceState:
    def test_choice_with_data_test_rules(self):
        sm = StateMachineDefinition.model_validate(
            {
                "StartAt": "C",
                "States": {
                    "C": {
                        "Type": "Choice",
                        "Choices": [
                            {"Variable": "$.x", "NumericGreaterThan": 100, "Next": "High"},
                            {"Variable": "$.y", "StringEquals": "yes", "Next": "Yes"},
                        ],
                        "Default": "Other",
                    },
                    "High": {"Type": "Succeed"},
                    "Yes": {"Type": "Succeed"},
                    "Other": {"Type": "Succeed"},
                },
            }
        )
        assert isinstance(sm.states["C"], ChoiceState)
        assert len(sm.states["C"].choices) == 2

    def test_choice_with_boolean_and(self):
        sm = StateMachineDefinition.model_validate(
            {
                "StartAt": "C",
                "States": {
                    "C": {
                        "Type": "Choice",
                        "Choices": [
                            {
                                "And": [
                                    {"Variable": "$.a", "BooleanEquals": True},
                                    {"Variable": "$.b", "NumericEquals": 1},
                                ],
                                "Next": "Both",
                            }
                        ],
                        "Default": "Other",
                    },
                    "Both": {"Type": "Succeed"},
                    "Other": {"Type": "Succeed"},
                },
            }
        )
        rule = sm.states["C"].choices[0]
        assert isinstance(rule, BooleanAndRule)
        assert len(rule.and_) == 2

    def test_choice_with_not(self):
        sm = StateMachineDefinition.model_validate(
            {
                "StartAt": "C",
                "States": {
                    "C": {
                        "Type": "Choice",
                        "Choices": [
                            {
                                "Not": {"Variable": "$.x", "IsNull": True},
                                "Next": "NotNull",
                            }
                        ],
                        "Default": "D",
                    },
                    "NotNull": {"Type": "Succeed"},
                    "D": {"Type": "Succeed"},
                },
            }
        )
        rule = sm.states["C"].choices[0]
        assert isinstance(rule, BooleanNotRule)

    def test_data_test_rule_exactly_one_operator(self):
        with pytest.raises(ValidationError, match="exactly one comparison operator"):
            DataTestRule.model_validate(
                {
                    "Variable": "$.x",
                    "StringEquals": "a",
                    "NumericEquals": 1,
                }
            )

    def test_data_test_rule_no_operator(self):
        with pytest.raises(ValidationError, match="exactly one comparison operator"):
            DataTestRule.model_validate({"Variable": "$.x"})


class TestWaitState:
    def test_wait_seconds(self):
        sm = StateMachineDefinition.model_validate(
            {
                "StartAt": "W",
                "States": {
                    "W": {"Type": "Wait", "Seconds": 300, "Next": "D"},
                    "D": {"Type": "Succeed"},
                },
            }
        )
        assert sm.states["W"].seconds == 300

    def test_wait_exactly_one_spec(self):
        with pytest.raises(ValidationError, match="exactly one"):
            StateMachineDefinition.model_validate(
                {
                    "StartAt": "W",
                    "States": {
                        "W": {
                            "Type": "Wait",
                            "Seconds": 10,
                            "Timestamp": "2024-01-01T00:00:00Z",
                            "Next": "D",
                        },
                        "D": {"Type": "Succeed"},
                    },
                }
            )

    def test_wait_no_spec(self):
        with pytest.raises(ValidationError, match="exactly one"):
            StateMachineDefinition.model_validate(
                {
                    "StartAt": "W",
                    "States": {
                        "W": {"Type": "Wait", "Next": "D"},
                        "D": {"Type": "Succeed"},
                    },
                }
            )


class TestSucceedState:
    def test_succeed(self):
        sm = StateMachineDefinition.model_validate(
            {
                "StartAt": "S",
                "States": {"S": {"Type": "Succeed"}},
            }
        )
        assert isinstance(sm.states["S"], SucceedState)


class TestFailState:
    def test_fail(self):
        sm = StateMachineDefinition.model_validate(
            {
                "StartAt": "F",
                "States": {"F": {"Type": "Fail", "Error": "E", "Cause": "C"}},
            }
        )
        assert isinstance(sm.states["F"], FailState)
        assert sm.states["F"].error == "E"
        assert sm.states["F"].cause == "C"

    def test_fail_error_mutual_exclusion(self):
        with pytest.raises(ValidationError, match="Error.*ErrorPath"):
            StateMachineDefinition.model_validate(
                {
                    "StartAt": "F",
                    "States": {"F": {"Type": "Fail", "Error": "E", "ErrorPath": "$.e"}},
                }
            )

    def test_fail_cause_mutual_exclusion(self):
        with pytest.raises(ValidationError, match="Cause.*CausePath"):
            StateMachineDefinition.model_validate(
                {
                    "StartAt": "F",
                    "States": {"F": {"Type": "Fail", "Cause": "C", "CausePath": "$.c"}},
                }
            )

    def test_fail_no_io_fields(self):
        with pytest.raises(ValidationError):
            StateMachineDefinition.model_validate(
                {
                    "StartAt": "F",
                    "States": {"F": {"Type": "Fail", "InputPath": "$.x"}},
                }
            )


class TestParallelState:
    def test_parallel(self):
        sm = StateMachineDefinition.model_validate(
            {
                "StartAt": "P",
                "States": {
                    "P": {
                        "Type": "Parallel",
                        "Branches": [
                            {"StartAt": "A", "States": {"A": {"Type": "Task", "End": True}}},
                            {"StartAt": "B", "States": {"B": {"Type": "Task", "End": True}}},
                        ],
                        "End": True,
                    }
                },
            }
        )
        assert isinstance(sm.states["P"], ParallelState)
        assert len(sm.states["P"].branches) == 2


class TestMapState:
    def test_map(self):
        sm = StateMachineDefinition.model_validate(
            {
                "StartAt": "M",
                "States": {
                    "M": {
                        "Type": "Map",
                        "ItemsPath": "$.items",
                        "ItemProcessor": {
                            "StartAt": "Process",
                            "States": {"Process": {"Type": "Task", "End": True}},
                        },
                        "MaxConcurrency": 5,
                        "End": True,
                    }
                },
            }
        )
        assert isinstance(sm.states["M"], MapState)
        assert sm.states["M"].max_concurrency == 5


class TestExtraFieldRejection:
    def test_unknown_field_at_root(self):
        with pytest.raises(ValidationError):
            StateMachineDefinition.model_validate(
                {
                    "StartAt": "A",
                    "States": {"A": {"Type": "Succeed"}},
                    "UnknownField": "bad",
                }
            )

    def test_unknown_field_on_state(self):
        with pytest.raises(ValidationError):
            StateMachineDefinition.model_validate(
                {
                    "StartAt": "A",
                    "States": {"A": {"Type": "Task", "End": True, "Resource": "arn:bad"}},
                }
            )


class TestStateMachineDefinition:
    def test_rsf_version_default(self):
        sm = StateMachineDefinition.model_validate(
            {
                "StartAt": "A",
                "States": {"A": {"Type": "Succeed"}},
            }
        )
        assert sm.rsf_version == "1.0"

    def test_all_optional_fields(self):
        sm = StateMachineDefinition.model_validate(
            {
                "rsf_version": "2.0",
                "Comment": "test",
                "StartAt": "A",
                "States": {"A": {"Type": "Succeed"}},
                "Version": "1.0",
                "TimeoutSeconds": 3600,
                "QueryLanguage": "JSONPath",
            }
        )
        assert sm.comment == "test"
        assert sm.version == "1.0"
        assert sm.timeout_seconds == 3600


class TestLambdaUrlConfig:
    """Tests for lambda_url DSL field parsing, validation, and backward compatibility."""

    def _base(self, **extra):
        """Create minimal valid workflow dict with optional extra fields."""
        data = {
            "StartAt": "S",
            "States": {"S": {"Type": "Succeed"}},
        }
        data.update(extra)
        return data

    def test_lambda_url_none_auth(self):
        sm = StateMachineDefinition.model_validate(
            self._base(lambda_url={"enabled": True, "auth_type": "NONE"})
        )
        assert sm.lambda_url is not None
        assert sm.lambda_url.enabled is True
        assert sm.lambda_url.auth_type == LambdaUrlAuthType.NONE

    def test_lambda_url_aws_iam_auth(self):
        sm = StateMachineDefinition.model_validate(
            self._base(lambda_url={"enabled": True, "auth_type": "AWS_IAM"})
        )
        assert sm.lambda_url is not None
        assert sm.lambda_url.auth_type == LambdaUrlAuthType.AWS_IAM

    def test_lambda_url_disabled(self):
        sm = StateMachineDefinition.model_validate(
            self._base(lambda_url={"enabled": False, "auth_type": "NONE"})
        )
        assert sm.lambda_url is not None
        assert sm.lambda_url.enabled is False

    def test_lambda_url_omitted_backward_compat(self):
        sm = StateMachineDefinition.model_validate(self._base())
        assert sm.lambda_url is None

    def test_lambda_url_rejects_invalid_auth_type(self):
        with pytest.raises(ValidationError):
            StateMachineDefinition.model_validate(
                self._base(lambda_url={"enabled": True, "auth_type": "BASIC"})
            )

    def test_lambda_url_rejects_missing_auth_type(self):
        with pytest.raises(ValidationError):
            StateMachineDefinition.model_validate(
                self._base(lambda_url={"enabled": True})
            )

    def test_lambda_url_rejects_missing_enabled(self):
        with pytest.raises(ValidationError):
            StateMachineDefinition.model_validate(
                self._base(lambda_url={"auth_type": "NONE"})
            )

    def test_lambda_url_rejects_extra_fields(self):
        with pytest.raises(ValidationError):
            StateMachineDefinition.model_validate(
                self._base(
                    lambda_url={
                        "enabled": True,
                        "auth_type": "NONE",
                        "cors": True,
                    }
                )
            )
