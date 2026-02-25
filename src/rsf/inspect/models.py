"""Data models for the RSF execution inspector.

Pydantic v2 models for durable execution data returned by the Lambda
control plane APIs: execution summaries, details, history events, and
timestamp normalization utilities.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ExecutionStatus(str, Enum):
    """Status of a durable Lambda execution."""

    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    STOPPED = "STOPPED"


# Statuses that indicate the execution has finished.
TERMINAL_STATUSES = frozenset({
    ExecutionStatus.SUCCEEDED,
    ExecutionStatus.FAILED,
    ExecutionStatus.TIMED_OUT,
    ExecutionStatus.STOPPED,
})


def normalize_timestamp(value: Any) -> datetime:
    """Normalize an AWS timestamp to a UTC-aware datetime.

    AWS may return timestamps as epoch seconds (int/float), naive
    datetime objects, or already-aware datetimes.  This function
    normalizes all of them to UTC.
    """
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    raise TypeError(f"Cannot normalize timestamp of type {type(value).__name__}")


def _ts_validator(v: Any) -> datetime | None:
    """Pydantic field validator that normalizes timestamps."""
    if v is None:
        return None
    return normalize_timestamp(v)


class ExecutionSummary(BaseModel):
    """Summary of a single durable execution (list view)."""

    execution_id: str
    name: str = ""
    status: ExecutionStatus
    function_name: str
    start_time: datetime
    end_time: datetime | None = None

    validate_start_time = field_validator("start_time", mode="before")(_ts_validator)
    validate_end_time = field_validator("end_time", mode="before")(_ts_validator)

    model_config = {"ser_json_timedelta": "float"}


class ExecutionError(BaseModel):
    """Error information for a failed execution."""

    error: str = ""
    cause: str = ""


class ExecutionDetail(ExecutionSummary):
    """Full detail of a single execution including I/O and history."""

    input_payload: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error: ExecutionError | None = None
    history: list[HistoryEvent] = Field(default_factory=list)


class HistoryEvent(BaseModel):
    """A single event in the execution history timeline."""

    event_id: int
    timestamp: datetime
    event_type: str
    sub_type: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)

    validate_timestamp = field_validator("timestamp", mode="before")(_ts_validator)


# Rebuild ExecutionDetail now that HistoryEvent is defined.
ExecutionDetail.model_rebuild()


class ExecutionListResponse(BaseModel):
    """Response for the execution list endpoint with pagination."""

    executions: list[ExecutionSummary]
    next_token: str | None = None
