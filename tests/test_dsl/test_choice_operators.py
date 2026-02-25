"""Exhaustive tests for all 39 Choice comparison operators and boolean combinators.

Tests both valid parsing and the DataTestRule exactly-one-operator constraint.
"""

import pytest
from pydantic import ValidationError

from rsf.dsl import StateMachineDefinition
from rsf.dsl.choice import (
    BooleanAndRule,
    BooleanNotRule,
    BooleanOrRule,
    ConditionRule,
    DataTestRule,
)


def _choice_sm(rules: list[dict], default: str = "Fallback") -> StateMachineDefinition:
    """Helper: build a StateMachineDefinition with a Choice state and terminal targets."""
    targets = set()
    for rule in rules:
        if "Next" in rule:
            targets.add(rule["Next"])
        # Handle And/Or/Not top-level rules
        for key in ("And", "Or"):
            if key in rule:
                for sub in rule[key]:
                    if "Next" in sub:
                        targets.add(sub["Next"])
        if "Not" in rule and isinstance(rule["Not"], dict) and "Next" in rule:
            targets.add(rule["Next"])

    targets.add(default)
    states = {
        "Route": {
            "Type": "Choice",
            "Choices": rules,
            "Default": default,
        }
    }
    for t in targets:
        states[t] = {"Type": "Succeed"}

    return StateMachineDefinition.model_validate({
        "StartAt": "Route",
        "States": states,
    })


# -----------------------------------------------------------------------
# String operators (11)
# -----------------------------------------------------------------------


class TestStringOperators:
    def test_string_equals(self):
        sm = _choice_sm([{"Variable": "$.name", "StringEquals": "Alice", "Next": "Match"}])
        rule = sm.states["Route"].choices[0]
        assert isinstance(rule, DataTestRule)
        op, val = rule.get_operator()
        assert op == "StringEquals"
        assert val == "Alice"

    def test_string_equals_path(self):
        sm = _choice_sm([{"Variable": "$.a", "StringEqualsPath": "$.b", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "StringEqualsPath"
        assert val == "$.b"

    def test_string_greater_than(self):
        sm = _choice_sm([{"Variable": "$.a", "StringGreaterThan": "bbb", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "StringGreaterThan"

    def test_string_greater_than_path(self):
        sm = _choice_sm([{"Variable": "$.a", "StringGreaterThanPath": "$.b", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "StringGreaterThanPath"

    def test_string_greater_than_equals(self):
        sm = _choice_sm([{"Variable": "$.a", "StringGreaterThanEquals": "aaa", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "StringGreaterThanEquals"

    def test_string_greater_than_equals_path(self):
        sm = _choice_sm([{"Variable": "$.a", "StringGreaterThanEqualsPath": "$.b", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "StringGreaterThanEqualsPath"

    def test_string_less_than(self):
        sm = _choice_sm([{"Variable": "$.a", "StringLessThan": "zzz", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "StringLessThan"

    def test_string_less_than_path(self):
        sm = _choice_sm([{"Variable": "$.a", "StringLessThanPath": "$.b", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "StringLessThanPath"

    def test_string_less_than_equals(self):
        sm = _choice_sm([{"Variable": "$.a", "StringLessThanEquals": "mmm", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "StringLessThanEquals"

    def test_string_less_than_equals_path(self):
        sm = _choice_sm([{"Variable": "$.a", "StringLessThanEqualsPath": "$.b", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "StringLessThanEqualsPath"

    def test_string_matches(self):
        sm = _choice_sm([{"Variable": "$.a", "StringMatches": "*.txt", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "StringMatches"
        assert val == "*.txt"

    def test_string_matches_path(self):
        sm = _choice_sm([{"Variable": "$.a", "StringMatchesPath": "$.pattern", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "StringMatchesPath"


# -----------------------------------------------------------------------
# Numeric operators (10)
# -----------------------------------------------------------------------


class TestNumericOperators:
    def test_numeric_equals(self):
        sm = _choice_sm([{"Variable": "$.x", "NumericEquals": 42, "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "NumericEquals"
        assert val == 42

    def test_numeric_equals_path(self):
        sm = _choice_sm([{"Variable": "$.x", "NumericEqualsPath": "$.y", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "NumericEqualsPath"

    def test_numeric_greater_than(self):
        sm = _choice_sm([{"Variable": "$.x", "NumericGreaterThan": 100, "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "NumericGreaterThan"

    def test_numeric_greater_than_path(self):
        sm = _choice_sm([{"Variable": "$.x", "NumericGreaterThanPath": "$.y", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "NumericGreaterThanPath"

    def test_numeric_greater_than_equals(self):
        sm = _choice_sm([{"Variable": "$.x", "NumericGreaterThanEquals": 50, "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "NumericGreaterThanEquals"

    def test_numeric_greater_than_equals_path(self):
        sm = _choice_sm([{"Variable": "$.x", "NumericGreaterThanEqualsPath": "$.y", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "NumericGreaterThanEqualsPath"

    def test_numeric_less_than(self):
        sm = _choice_sm([{"Variable": "$.x", "NumericLessThan": 10, "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "NumericLessThan"

    def test_numeric_less_than_path(self):
        sm = _choice_sm([{"Variable": "$.x", "NumericLessThanPath": "$.y", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "NumericLessThanPath"

    def test_numeric_less_than_equals(self):
        sm = _choice_sm([{"Variable": "$.x", "NumericLessThanEquals": 99, "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "NumericLessThanEquals"

    def test_numeric_less_than_equals_path(self):
        sm = _choice_sm([{"Variable": "$.x", "NumericLessThanEqualsPath": "$.y", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "NumericLessThanEqualsPath"

    def test_numeric_float(self):
        sm = _choice_sm([{"Variable": "$.x", "NumericEquals": 3.14, "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert val == 3.14


# -----------------------------------------------------------------------
# Boolean operators (2)
# -----------------------------------------------------------------------


class TestBooleanOperators:
    def test_boolean_equals_true(self):
        sm = _choice_sm([{"Variable": "$.flag", "BooleanEquals": True, "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "BooleanEquals"
        assert val is True

    def test_boolean_equals_false(self):
        sm = _choice_sm([{"Variable": "$.flag", "BooleanEquals": False, "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert val is False

    def test_boolean_equals_path(self):
        sm = _choice_sm([{"Variable": "$.flag", "BooleanEqualsPath": "$.other", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "BooleanEqualsPath"


# -----------------------------------------------------------------------
# Timestamp operators (10)
# -----------------------------------------------------------------------


class TestTimestampOperators:
    def test_timestamp_equals(self):
        sm = _choice_sm([{"Variable": "$.ts", "TimestampEquals": "2025-01-01T00:00:00Z", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "TimestampEquals"
        assert val == "2025-01-01T00:00:00Z"

    def test_timestamp_equals_path(self):
        sm = _choice_sm([{"Variable": "$.ts", "TimestampEqualsPath": "$.other_ts", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "TimestampEqualsPath"

    def test_timestamp_greater_than(self):
        sm = _choice_sm([{"Variable": "$.ts", "TimestampGreaterThan": "2025-06-15T00:00:00Z", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "TimestampGreaterThan"

    def test_timestamp_greater_than_path(self):
        sm = _choice_sm([{"Variable": "$.ts", "TimestampGreaterThanPath": "$.ref", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "TimestampGreaterThanPath"

    def test_timestamp_greater_than_equals(self):
        sm = _choice_sm([{"Variable": "$.ts", "TimestampGreaterThanEquals": "2025-01-01T00:00:00Z", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "TimestampGreaterThanEquals"

    def test_timestamp_greater_than_equals_path(self):
        sm = _choice_sm([{"Variable": "$.ts", "TimestampGreaterThanEqualsPath": "$.ref", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "TimestampGreaterThanEqualsPath"

    def test_timestamp_less_than(self):
        sm = _choice_sm([{"Variable": "$.ts", "TimestampLessThan": "2030-12-31T23:59:59Z", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "TimestampLessThan"

    def test_timestamp_less_than_path(self):
        sm = _choice_sm([{"Variable": "$.ts", "TimestampLessThanPath": "$.deadline", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "TimestampLessThanPath"

    def test_timestamp_less_than_equals(self):
        sm = _choice_sm([{"Variable": "$.ts", "TimestampLessThanEquals": "2025-12-31T23:59:59Z", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "TimestampLessThanEquals"

    def test_timestamp_less_than_equals_path(self):
        sm = _choice_sm([{"Variable": "$.ts", "TimestampLessThanEqualsPath": "$.ref", "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "TimestampLessThanEqualsPath"


# -----------------------------------------------------------------------
# Type checking operators (6)
# -----------------------------------------------------------------------


class TestTypeCheckOperators:
    def test_is_boolean_true(self):
        sm = _choice_sm([{"Variable": "$.val", "IsBoolean": True, "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "IsBoolean"
        assert val is True

    def test_is_boolean_false(self):
        sm = _choice_sm([{"Variable": "$.val", "IsBoolean": False, "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert val is False

    def test_is_null(self):
        sm = _choice_sm([{"Variable": "$.val", "IsNull": True, "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "IsNull"

    def test_is_numeric(self):
        sm = _choice_sm([{"Variable": "$.val", "IsNumeric": True, "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "IsNumeric"

    def test_is_present(self):
        sm = _choice_sm([{"Variable": "$.val", "IsPresent": True, "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "IsPresent"

    def test_is_string(self):
        sm = _choice_sm([{"Variable": "$.val", "IsString": True, "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "IsString"

    def test_is_timestamp(self):
        sm = _choice_sm([{"Variable": "$.val", "IsTimestamp": True, "Next": "Match"}])
        op, val = sm.states["Route"].choices[0].get_operator()
        assert op == "IsTimestamp"


# -----------------------------------------------------------------------
# Boolean combinators (And, Or, Not, Condition)
# -----------------------------------------------------------------------


class TestBooleanCombinators:
    def test_and_with_two_rules(self):
        sm = _choice_sm([{
            "And": [
                {"Variable": "$.x", "NumericGreaterThan": 0},
                {"Variable": "$.y", "StringEquals": "yes"},
            ],
            "Next": "Match",
        }])
        rule = sm.states["Route"].choices[0]
        assert isinstance(rule, BooleanAndRule)
        assert len(rule.and_) == 2

    def test_and_with_three_rules(self):
        sm = _choice_sm([{
            "And": [
                {"Variable": "$.a", "BooleanEquals": True},
                {"Variable": "$.b", "NumericEquals": 1},
                {"Variable": "$.c", "StringEquals": "ok"},
            ],
            "Next": "Match",
        }])
        assert len(sm.states["Route"].choices[0].and_) == 3

    def test_or_combinator(self):
        sm = _choice_sm([{
            "Or": [
                {"Variable": "$.x", "NumericEquals": 0},
                {"Variable": "$.x", "NumericEquals": 1},
            ],
            "Next": "Match",
        }])
        rule = sm.states["Route"].choices[0]
        assert isinstance(rule, BooleanOrRule)
        assert len(rule.or_) == 2

    def test_not_combinator(self):
        sm = _choice_sm([{
            "Not": {"Variable": "$.flag", "BooleanEquals": False},
            "Next": "Match",
        }])
        rule = sm.states["Route"].choices[0]
        assert isinstance(rule, BooleanNotRule)
        inner = rule.not_
        assert isinstance(inner, DataTestRule)

    def test_nested_and_or(self):
        sm = _choice_sm([{
            "And": [
                {"Or": [
                    {"Variable": "$.a", "NumericEquals": 1},
                    {"Variable": "$.a", "NumericEquals": 2},
                ]},
                {"Variable": "$.b", "BooleanEquals": True},
            ],
            "Next": "Match",
        }])
        outer = sm.states["Route"].choices[0]
        assert isinstance(outer, BooleanAndRule)
        inner_or = outer.and_[0]
        assert isinstance(inner_or, BooleanOrRule)

    def test_nested_not_in_and(self):
        sm = _choice_sm([{
            "And": [
                {"Not": {"Variable": "$.x", "IsNull": True}},
                {"Variable": "$.y", "NumericGreaterThan": 0},
            ],
            "Next": "Match",
        }])
        outer = sm.states["Route"].choices[0]
        assert isinstance(outer, BooleanAndRule)
        assert isinstance(outer.and_[0], BooleanNotRule)

    def test_condition_rule(self):
        sm = _choice_sm([{
            "Condition": "$$.input.value > 100",
            "Next": "Match",
        }])
        rule = sm.states["Route"].choices[0]
        assert isinstance(rule, ConditionRule)
        assert rule.condition == "$$.input.value > 100"


# -----------------------------------------------------------------------
# Validation edge cases
# -----------------------------------------------------------------------


class TestChoiceValidation:
    def test_data_test_rule_requires_variable(self):
        with pytest.raises(ValidationError, match="Variable"):
            DataTestRule.model_validate({"StringEquals": "test"})

    def test_two_operators_rejected(self):
        with pytest.raises(ValidationError, match="exactly one"):
            DataTestRule.model_validate({
                "Variable": "$.x",
                "StringEquals": "a",
                "NumericEquals": 1,
            })

    def test_no_operator_rejected(self):
        with pytest.raises(ValidationError, match="exactly one"):
            DataTestRule.model_validate({"Variable": "$.x"})

    def test_three_operators_rejected(self):
        with pytest.raises(ValidationError, match="exactly one"):
            DataTestRule.model_validate({
                "Variable": "$.x",
                "StringEquals": "a",
                "NumericEquals": 1,
                "BooleanEquals": True,
            })

    def test_choice_state_empty_choices_has_no_rules(self):
        """Empty choices list is structurally valid but produces no rules."""
        sm = StateMachineDefinition.model_validate({
            "StartAt": "C",
            "States": {
                "C": {"Type": "Choice", "Choices": [], "Default": "D"},
                "D": {"Type": "Succeed"},
            },
        })
        assert len(sm.states["C"].choices) == 0

    def test_all_39_operators_parseable(self):
        """Verify all 39 operators can be parsed individually."""
        from rsf.dsl.types import COMPARISON_OPERATORS

        operator_values = {
            "StringEquals": "test",
            "StringEqualsPath": "$.x",
            "StringGreaterThan": "test",
            "StringGreaterThanPath": "$.x",
            "StringGreaterThanEquals": "test",
            "StringGreaterThanEqualsPath": "$.x",
            "StringLessThan": "test",
            "StringLessThanPath": "$.x",
            "StringLessThanEquals": "test",
            "StringLessThanEqualsPath": "$.x",
            "StringMatches": "*.txt",
            "StringMatchesPath": "$.x",
            "NumericEquals": 42,
            "NumericEqualsPath": "$.x",
            "NumericGreaterThan": 42,
            "NumericGreaterThanPath": "$.x",
            "NumericGreaterThanEquals": 42,
            "NumericGreaterThanEqualsPath": "$.x",
            "NumericLessThan": 42,
            "NumericLessThanPath": "$.x",
            "NumericLessThanEquals": 42,
            "NumericLessThanEqualsPath": "$.x",
            "BooleanEquals": True,
            "BooleanEqualsPath": "$.x",
            "TimestampEquals": "2025-01-01T00:00:00Z",
            "TimestampEqualsPath": "$.x",
            "TimestampGreaterThan": "2025-01-01T00:00:00Z",
            "TimestampGreaterThanPath": "$.x",
            "TimestampGreaterThanEquals": "2025-01-01T00:00:00Z",
            "TimestampGreaterThanEqualsPath": "$.x",
            "TimestampLessThan": "2025-01-01T00:00:00Z",
            "TimestampLessThanPath": "$.x",
            "TimestampLessThanEquals": "2025-01-01T00:00:00Z",
            "TimestampLessThanEqualsPath": "$.x",
            "IsBoolean": True,
            "IsNull": True,
            "IsNumeric": True,
            "IsPresent": True,
            "IsString": True,
            "IsTimestamp": True,
        }

        assert len(operator_values) == len(COMPARISON_OPERATORS), (
            f"Expected {len(COMPARISON_OPERATORS)} operators, test covers {len(operator_values)}"
        )

        for op_name, op_value in operator_values.items():
            rule = DataTestRule.model_validate({
                "Variable": "$.test",
                op_name: op_value,
            })
            parsed_op, parsed_val = rule.get_operator()
            assert parsed_op == op_name, f"Failed for operator {op_name}"
            assert parsed_val == op_value, f"Value mismatch for {op_name}"
