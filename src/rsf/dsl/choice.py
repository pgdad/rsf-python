"""Choice rule models — 39 comparison operators and boolean combinators."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Discriminator, Field, Tag, model_validator

from rsf.dsl.types import COMPARISON_OPERATORS


class DataTestRule(BaseModel):
    """A single comparison rule with a Variable and exactly one operator."""

    model_config = {"extra": "forbid", "populate_by_name": True}

    variable: str = Field(alias="Variable")
    next: str | None = Field(default=None, alias="Next")

    # String operators
    string_equals: str | None = Field(default=None, alias="StringEquals")
    string_equals_path: str | None = Field(default=None, alias="StringEqualsPath")
    string_greater_than: str | None = Field(default=None, alias="StringGreaterThan")
    string_greater_than_path: str | None = Field(
        default=None, alias="StringGreaterThanPath"
    )
    string_greater_than_equals: str | None = Field(
        default=None, alias="StringGreaterThanEquals"
    )
    string_greater_than_equals_path: str | None = Field(
        default=None, alias="StringGreaterThanEqualsPath"
    )
    string_less_than: str | None = Field(default=None, alias="StringLessThan")
    string_less_than_path: str | None = Field(
        default=None, alias="StringLessThanPath"
    )
    string_less_than_equals: str | None = Field(
        default=None, alias="StringLessThanEquals"
    )
    string_less_than_equals_path: str | None = Field(
        default=None, alias="StringLessThanEqualsPath"
    )
    string_matches: str | None = Field(default=None, alias="StringMatches")
    string_matches_path: str | None = Field(default=None, alias="StringMatchesPath")

    # Numeric operators
    numeric_equals: int | float | None = Field(default=None, alias="NumericEquals")
    numeric_equals_path: str | None = Field(default=None, alias="NumericEqualsPath")
    numeric_greater_than: int | float | None = Field(
        default=None, alias="NumericGreaterThan"
    )
    numeric_greater_than_path: str | None = Field(
        default=None, alias="NumericGreaterThanPath"
    )
    numeric_greater_than_equals: int | float | None = Field(
        default=None, alias="NumericGreaterThanEquals"
    )
    numeric_greater_than_equals_path: str | None = Field(
        default=None, alias="NumericGreaterThanEqualsPath"
    )
    numeric_less_than: int | float | None = Field(
        default=None, alias="NumericLessThan"
    )
    numeric_less_than_path: str | None = Field(
        default=None, alias="NumericLessThanPath"
    )
    numeric_less_than_equals: int | float | None = Field(
        default=None, alias="NumericLessThanEquals"
    )
    numeric_less_than_equals_path: str | None = Field(
        default=None, alias="NumericLessThanEqualsPath"
    )

    # Boolean operator
    boolean_equals: bool | None = Field(default=None, alias="BooleanEquals")
    boolean_equals_path: str | None = Field(default=None, alias="BooleanEqualsPath")

    # Timestamp operators
    timestamp_equals: str | None = Field(default=None, alias="TimestampEquals")
    timestamp_equals_path: str | None = Field(
        default=None, alias="TimestampEqualsPath"
    )
    timestamp_greater_than: str | None = Field(
        default=None, alias="TimestampGreaterThan"
    )
    timestamp_greater_than_path: str | None = Field(
        default=None, alias="TimestampGreaterThanPath"
    )
    timestamp_greater_than_equals: str | None = Field(
        default=None, alias="TimestampGreaterThanEquals"
    )
    timestamp_greater_than_equals_path: str | None = Field(
        default=None, alias="TimestampGreaterThanEqualsPath"
    )
    timestamp_less_than: str | None = Field(default=None, alias="TimestampLessThan")
    timestamp_less_than_path: str | None = Field(
        default=None, alias="TimestampLessThanPath"
    )
    timestamp_less_than_equals: str | None = Field(
        default=None, alias="TimestampLessThanEquals"
    )
    timestamp_less_than_equals_path: str | None = Field(
        default=None, alias="TimestampLessThanEqualsPath"
    )

    # Type checking operators
    is_boolean: bool | None = Field(default=None, alias="IsBoolean")
    is_null: bool | None = Field(default=None, alias="IsNull")
    is_numeric: bool | None = Field(default=None, alias="IsNumeric")
    is_present: bool | None = Field(default=None, alias="IsPresent")
    is_string: bool | None = Field(default=None, alias="IsString")
    is_timestamp: bool | None = Field(default=None, alias="IsTimestamp")

    @model_validator(mode="after")
    def exactly_one_operator(self) -> DataTestRule:
        """Ensure exactly one comparison operator is set."""
        # Map alias -> field name for all operator fields
        operator_fields = {
            "StringEquals": "string_equals",
            "StringEqualsPath": "string_equals_path",
            "StringGreaterThan": "string_greater_than",
            "StringGreaterThanPath": "string_greater_than_path",
            "StringGreaterThanEquals": "string_greater_than_equals",
            "StringGreaterThanEqualsPath": "string_greater_than_equals_path",
            "StringLessThan": "string_less_than",
            "StringLessThanPath": "string_less_than_path",
            "StringLessThanEquals": "string_less_than_equals",
            "StringLessThanEqualsPath": "string_less_than_equals_path",
            "StringMatches": "string_matches",
            "StringMatchesPath": "string_matches_path",
            "NumericEquals": "numeric_equals",
            "NumericEqualsPath": "numeric_equals_path",
            "NumericGreaterThan": "numeric_greater_than",
            "NumericGreaterThanPath": "numeric_greater_than_path",
            "NumericGreaterThanEquals": "numeric_greater_than_equals",
            "NumericGreaterThanEqualsPath": "numeric_greater_than_equals_path",
            "NumericLessThan": "numeric_less_than",
            "NumericLessThanPath": "numeric_less_than_path",
            "NumericLessThanEquals": "numeric_less_than_equals",
            "NumericLessThanEqualsPath": "numeric_less_than_equals_path",
            "BooleanEquals": "boolean_equals",
            "BooleanEqualsPath": "boolean_equals_path",
            "TimestampEquals": "timestamp_equals",
            "TimestampEqualsPath": "timestamp_equals_path",
            "TimestampGreaterThan": "timestamp_greater_than",
            "TimestampGreaterThanPath": "timestamp_greater_than_path",
            "TimestampGreaterThanEquals": "timestamp_greater_than_equals",
            "TimestampGreaterThanEqualsPath": "timestamp_greater_than_equals_path",
            "TimestampLessThan": "timestamp_less_than",
            "TimestampLessThanPath": "timestamp_less_than_path",
            "TimestampLessThanEquals": "timestamp_less_than_equals",
            "TimestampLessThanEqualsPath": "timestamp_less_than_equals_path",
            "IsBoolean": "is_boolean",
            "IsNull": "is_null",
            "IsNumeric": "is_numeric",
            "IsPresent": "is_present",
            "IsString": "is_string",
            "IsTimestamp": "is_timestamp",
        }
        set_operators = [
            alias
            for alias, field_name in operator_fields.items()
            if getattr(self, field_name) is not None
        ]
        if len(set_operators) == 0:
            raise ValueError("DataTestRule must have exactly one comparison operator")
        if len(set_operators) > 1:
            raise ValueError(
                f"DataTestRule must have exactly one comparison operator, "
                f"got: {', '.join(set_operators)}"
            )
        return self

    def get_operator(self) -> tuple[str, Any]:
        """Return (operator_alias, value) for the set operator."""
        operator_fields = {
            "StringEquals": "string_equals",
            "StringEqualsPath": "string_equals_path",
            "StringGreaterThan": "string_greater_than",
            "StringGreaterThanPath": "string_greater_than_path",
            "StringGreaterThanEquals": "string_greater_than_equals",
            "StringGreaterThanEqualsPath": "string_greater_than_equals_path",
            "StringLessThan": "string_less_than",
            "StringLessThanPath": "string_less_than_path",
            "StringLessThanEquals": "string_less_than_equals",
            "StringLessThanEqualsPath": "string_less_than_equals_path",
            "StringMatches": "string_matches",
            "StringMatchesPath": "string_matches_path",
            "NumericEquals": "numeric_equals",
            "NumericEqualsPath": "numeric_equals_path",
            "NumericGreaterThan": "numeric_greater_than",
            "NumericGreaterThanPath": "numeric_greater_than_path",
            "NumericGreaterThanEquals": "numeric_greater_than_equals",
            "NumericGreaterThanEqualsPath": "numeric_greater_than_equals_path",
            "NumericLessThan": "numeric_less_than",
            "NumericLessThanPath": "numeric_less_than_path",
            "NumericLessThanEquals": "numeric_less_than_equals",
            "NumericLessThanEqualsPath": "numeric_less_than_equals_path",
            "BooleanEquals": "boolean_equals",
            "BooleanEqualsPath": "boolean_equals_path",
            "TimestampEquals": "timestamp_equals",
            "TimestampEqualsPath": "timestamp_equals_path",
            "TimestampGreaterThan": "timestamp_greater_than",
            "TimestampGreaterThanPath": "timestamp_greater_than_path",
            "TimestampGreaterThanEquals": "timestamp_greater_than_equals",
            "TimestampGreaterThanEqualsPath": "timestamp_greater_than_equals_path",
            "TimestampLessThan": "timestamp_less_than",
            "TimestampLessThanPath": "timestamp_less_than_path",
            "TimestampLessThanEquals": "timestamp_less_than_equals",
            "TimestampLessThanEqualsPath": "timestamp_less_than_equals_path",
            "IsBoolean": "is_boolean",
            "IsNull": "is_null",
            "IsNumeric": "is_numeric",
            "IsPresent": "is_present",
            "IsString": "is_string",
            "IsTimestamp": "is_timestamp",
        }
        for alias, field_name in operator_fields.items():
            val = getattr(self, field_name)
            if val is not None:
                return (alias, val)
        raise ValueError("No operator set")


class BooleanAndRule(BaseModel):
    """Boolean AND combinator — all child rules must match."""

    model_config = {"extra": "forbid", "populate_by_name": True}

    and_: list[ChoiceRule] = Field(alias="And")
    next: str | None = Field(default=None, alias="Next")


class BooleanOrRule(BaseModel):
    """Boolean OR combinator — at least one child rule must match."""

    model_config = {"extra": "forbid", "populate_by_name": True}

    or_: list[ChoiceRule] = Field(alias="Or")
    next: str | None = Field(default=None, alias="Next")


class BooleanNotRule(BaseModel):
    """Boolean NOT combinator — inverts child rule."""

    model_config = {"extra": "forbid", "populate_by_name": True}

    not_: ChoiceRule = Field(alias="Not")
    next: str | None = Field(default=None, alias="Next")


class ConditionRule(BaseModel):
    """JSONata condition-based rule."""

    model_config = {"extra": "forbid", "populate_by_name": True}

    condition: str = Field(alias="Condition")
    next: str | None = Field(default=None, alias="Next")


def discriminate_choice_rule(data: Any) -> str:
    """Discriminator function for choice rules — inspects keys to determine type."""
    if isinstance(data, dict):
        if "And" in data:
            return "and"
        if "Or" in data:
            return "or"
        if "Not" in data:
            return "not"
        if "Condition" in data:
            return "condition"
        return "data_test"
    # If it's already a model instance
    if isinstance(data, BooleanAndRule):
        return "and"
    if isinstance(data, BooleanOrRule):
        return "or"
    if isinstance(data, BooleanNotRule):
        return "not"
    if isinstance(data, ConditionRule):
        return "condition"
    return "data_test"


# The ChoiceRule union type with callable discriminator
ChoiceRule = Annotated[
    Union[
        Annotated[DataTestRule, Tag("data_test")],
        Annotated[BooleanAndRule, Tag("and")],
        Annotated[BooleanOrRule, Tag("or")],
        Annotated[BooleanNotRule, Tag("not")],
        Annotated[ConditionRule, Tag("condition")],
    ],
    Discriminator(discriminate_choice_rule),
]

# Rebuild models that reference ChoiceRule to resolve forward refs
BooleanAndRule.model_rebuild()
BooleanOrRule.model_rebuild()
BooleanNotRule.model_rebuild()
