"""DSL type definitions and constants."""

from __future__ import annotations

from enum import Enum


class QueryLanguage(str, Enum):
    """Supported query languages."""

    JSONPATH = "JSONPath"
    JSONATA = "JSONata"


class JitterStrategy(str, Enum):
    """Jitter strategies for retry backoff."""

    FULL = "FULL"
    NONE = "NONE"


class ProcessorMode(str, Enum):
    """Map state processor modes."""

    INLINE = "INLINE"
    DISTRIBUTED = "DISTRIBUTED"


# All 39 comparison operators for Choice rules
COMPARISON_OPERATORS: frozenset[str] = frozenset(
    {
        # String equality
        "StringEquals",
        "StringEqualsPath",
        # String ordering
        "StringGreaterThan",
        "StringGreaterThanPath",
        "StringGreaterThanEquals",
        "StringGreaterThanEqualsPath",
        "StringLessThan",
        "StringLessThanPath",
        "StringLessThanEquals",
        "StringLessThanEqualsPath",
        # String pattern
        "StringMatches",
        "StringMatchesPath",
        # Numeric equality
        "NumericEquals",
        "NumericEqualsPath",
        # Numeric ordering
        "NumericGreaterThan",
        "NumericGreaterThanPath",
        "NumericGreaterThanEquals",
        "NumericGreaterThanEqualsPath",
        "NumericLessThan",
        "NumericLessThanPath",
        "NumericLessThanEquals",
        "NumericLessThanEqualsPath",
        # Boolean equality
        "BooleanEquals",
        "BooleanEqualsPath",
        # Timestamp equality
        "TimestampEquals",
        "TimestampEqualsPath",
        # Timestamp ordering
        "TimestampGreaterThan",
        "TimestampGreaterThanPath",
        "TimestampGreaterThanEquals",
        "TimestampGreaterThanEqualsPath",
        "TimestampLessThan",
        "TimestampLessThanPath",
        "TimestampLessThanEquals",
        "TimestampLessThanEqualsPath",
        # Type checking
        "IsBoolean",
        "IsNull",
        "IsNumeric",
        "IsPresent",
        "IsString",
        "IsTimestamp",
    }
)
