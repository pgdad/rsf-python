"""Error handling models — RetryPolicy and Catcher."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from rsf.dsl.types import JitterStrategy


class RetryPolicy(BaseModel):
    """Retry policy with exponential backoff and optional jitter."""

    model_config = {"extra": "forbid", "populate_by_name": True}

    error_equals: list[str] = Field(alias="ErrorEquals")
    interval_seconds: int = Field(default=1, alias="IntervalSeconds", ge=0)
    max_attempts: int = Field(default=3, alias="MaxAttempts", ge=0)
    backoff_rate: float = Field(default=2.0, alias="BackoffRate", ge=1.0)
    max_delay_seconds: int | None = Field(default=None, alias="MaxDelaySeconds", ge=0)
    jitter_strategy: JitterStrategy | None = Field(
        default=None, alias="JitterStrategy"
    )


class Catcher(BaseModel):
    """Error catcher that routes errors to a recovery state."""

    model_config = {"extra": "forbid", "populate_by_name": True}

    error_equals: list[str] = Field(alias="ErrorEquals")
    next: str = Field(alias="Next")
    result_path: str | None = Field(default=None, alias="ResultPath")
    comment: str | None = Field(default=None, alias="Comment")
