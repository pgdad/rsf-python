"""Tests for semantic cross-state validation (BFS)."""

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


class TestDynamoDBValidation:
    """Tests for semantic validation of DynamoDB table configurations."""

    def test_valid_pay_per_request_no_errors(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
                "dynamodb_tables": [
                    {
                        "table_name": "orders",
                        "partition_key": {"name": "order_id", "type": "S"},
                    }
                ],
            }
        )
        assert not any("dynamodb" in e.message.lower() for e in errors if e.severity == "error")

    def test_valid_provisioned_with_capacities_no_errors(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
                "dynamodb_tables": [
                    {
                        "table_name": "orders",
                        "partition_key": {"name": "id", "type": "S"},
                        "billing_mode": "PROVISIONED",
                        "read_capacity": 5,
                        "write_capacity": 5,
                    }
                ],
            }
        )
        assert not any("capacity" in e.message.lower() for e in errors if e.severity == "error")

    def test_provisioned_without_capacity_produces_error(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
                "dynamodb_tables": [
                    {
                        "table_name": "orders",
                        "partition_key": {"name": "id", "type": "S"},
                        "billing_mode": "PROVISIONED",
                    }
                ],
            }
        )
        capacity_errors = [e for e in errors if "capacity" in e.message.lower() and e.severity == "error"]
        assert len(capacity_errors) >= 1

    def test_duplicate_table_names_produce_error(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
                "dynamodb_tables": [
                    {
                        "table_name": "orders",
                        "partition_key": {"name": "id", "type": "S"},
                    },
                    {
                        "table_name": "orders",
                        "partition_key": {"name": "pk", "type": "S"},
                    },
                ],
            }
        )
        dup_errors = [e for e in errors if "duplicate" in e.message.lower() and e.severity == "error"]
        assert len(dup_errors) >= 1

    def test_empty_dynamodb_tables_warning(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
                "dynamodb_tables": [],
            }
        )
        warnings = [e for e in errors if e.severity == "warning" and "dynamodb" in e.message.lower()]
        assert len(warnings) >= 1


class TestSubWorkflowValidation:
    """Tests for semantic validation of sub-workflow references."""

    def test_valid_sub_workflow_reference(self):
        errors = _validate(
            {
                "StartAt": "T",
                "sub_workflows": [{"name": "payment-processor"}],
                "States": {
                    "T": {
                        "Type": "Task",
                        "SubWorkflow": "payment-processor",
                        "End": True,
                    }
                },
            }
        )
        assert not any("SubWorkflow" in e.message or "sub_workflow" in e.message.lower() for e in errors if e.severity == "error")

    def test_undeclared_sub_workflow_produces_error(self):
        errors = _validate(
            {
                "StartAt": "T",
                "sub_workflows": [{"name": "payment-processor"}],
                "States": {
                    "T": {
                        "Type": "Task",
                        "SubWorkflow": "unknown-workflow",
                        "End": True,
                    }
                },
            }
        )
        sub_errors = [e for e in errors if "unknown-workflow" in e.message and e.severity == "error"]
        assert len(sub_errors) >= 1

    def test_unused_sub_workflow_produces_warning(self):
        errors = _validate(
            {
                "StartAt": "T",
                "sub_workflows": [
                    {"name": "payment-processor"},
                    {"name": "unused-workflow"},
                ],
                "States": {
                    "T": {
                        "Type": "Task",
                        "SubWorkflow": "payment-processor",
                        "End": True,
                    }
                },
            }
        )
        warnings = [e for e in errors if e.severity == "warning" and "unused-workflow" in e.message]
        assert len(warnings) >= 1

    def test_no_sub_workflows_no_errors(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
            }
        )
        assert not any("sub_workflow" in e.message.lower() for e in errors)


class TestTriggerValidation:
    """Tests for semantic validation of trigger configurations."""

    def test_valid_eventbridge_trigger_no_errors(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
                "triggers": [
                    {"type": "eventbridge", "schedule_expression": "rate(5 minutes)"}
                ],
            }
        )
        assert not any(
            "trigger" in e.message.lower()
            for e in errors
            if e.severity == "error"
        )

    def test_valid_sqs_trigger_no_errors(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
                "triggers": [{"type": "sqs", "queue_name": "my-queue"}],
            }
        )
        assert not any(
            "trigger" in e.message.lower()
            for e in errors
            if e.severity == "error"
        )

    def test_valid_sns_trigger_no_errors(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
                "triggers": [
                    {
                        "type": "sns",
                        "topic_arn": "arn:aws:sns:us-east-1:123456789012:MyTopic",
                    }
                ],
            }
        )
        assert not any(
            "trigger" in e.message.lower()
            for e in errors
            if e.severity == "error"
        )

    def test_eventbridge_missing_both_produces_error(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
                "triggers": [{"type": "eventbridge"}],
            }
        )
        trigger_errors = [
            e
            for e in errors
            if "schedule_expression" in e.message or "event_pattern" in e.message
        ]
        assert len(trigger_errors) >= 1

    def test_sqs_large_batch_size_warning(self):
        """SQS batch_size above 10 produces a warning (Pydantic enforces le=10000)."""
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
                "triggers": [
                    {"type": "sqs", "queue_name": "my-queue", "batch_size": 10000}
                ],
            }
        )
        warnings = [
            e
            for e in errors
            if e.severity == "warning" and "batch_size" in e.message
        ]
        assert len(warnings) >= 1

    def test_empty_triggers_list_warning(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
                "triggers": [],
            }
        )
        warnings = [
            e
            for e in errors
            if e.severity == "warning" and "trigger" in e.message.lower()
        ]
        assert len(warnings) >= 1


class TestTimeoutValidation:
    """Tests for semantic validation of timeout values."""

    def test_valid_timeout_no_warning(self):
        errors = _validate(
            {
                "StartAt": "T",
                "TimeoutSeconds": 300,
                "States": {"T": {"Type": "Task", "End": True}},
            }
        )
        assert len(errors) == 0

    def test_no_timeout_no_warning(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
            }
        )
        assert len(errors) == 0

    def test_extremely_large_timeout_warning(self):
        errors = _validate(
            {
                "StartAt": "T",
                "TimeoutSeconds": 2592001,  # >30 days
                "States": {"T": {"Type": "Task", "End": True}},
            }
        )
        warnings = [e for e in errors if e.severity == "warning"]
        assert len(warnings) == 1
        assert "30 days" in warnings[0].message


class TestAlarmValidation:
    """Tests for semantic validation of alarm configurations."""

    def test_valid_error_rate_alarm_no_errors(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
                "alarms": [{"type": "error_rate", "threshold": 5, "period": 300}],
            }
        )
        assert not any("alarm" in e.message.lower() for e in errors if e.severity == "error")

    def test_valid_duration_alarm_no_errors(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
                "alarms": [{"type": "duration", "threshold": 5000}],
            }
        )
        assert not any("alarm" in e.message.lower() for e in errors if e.severity == "error")

    def test_valid_throttle_alarm_no_errors(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
                "alarms": [{"type": "throttle", "threshold": 10}],
            }
        )
        assert not any("alarm" in e.message.lower() for e in errors if e.severity == "error")

    def test_error_rate_threshold_over_100_produces_warning(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
                "alarms": [{"type": "error_rate", "threshold": 150}],
            }
        )
        warnings = [e for e in errors if e.severity == "warning" and "100%" in e.message]
        assert len(warnings) >= 1

    def test_empty_alarms_list_produces_warning(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
                "alarms": [],
            }
        )
        warnings = [e for e in errors if e.severity == "warning" and "alarm" in e.message.lower()]
        assert len(warnings) >= 1

    def test_duplicate_alarm_types_produce_warning(self):
        errors = _validate(
            {
                "StartAt": "T",
                "States": {"T": {"Type": "Task", "End": True}},
                "alarms": [
                    {"type": "error_rate", "threshold": 5},
                    {"type": "error_rate", "threshold": 10},
                ],
            }
        )
        warnings = [e for e in errors if e.severity == "warning" and "multiple" in e.message.lower()]
        assert len(warnings) >= 1
