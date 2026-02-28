"""Async Lambda client for the RSF execution inspector.

Wraps synchronous boto3 Lambda calls with ``asyncio.to_thread`` and
enforces a token-bucket rate limiter (12 req/s ceiling) to stay under
the 15 req/s Lambda control-plane limit.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import boto3

from rsf.inspect.models import (
    ExecutionDetail,
    ExecutionError,
    ExecutionListResponse,
    ExecutionStatus,
    ExecutionSummary,
    HistoryEvent,
    normalize_timestamp,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token-bucket rate limiter
# ---------------------------------------------------------------------------


class TokenBucketRateLimiter:
    """Async-safe token-bucket rate limiter.

    Defaults to 12 tokens/s with a bucket capacity of 12, ensuring we
    never exceed the 15 req/s Lambda control-plane limit even under
    sustained load.
    """

    def __init__(self, rate: float = 12.0, capacity: float = 12.0) -> None:
        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a token is available, then consume it."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
            self._last_refill = now

            if self._tokens < 1.0:
                wait_time = (1.0 - self._tokens) / self._rate
                await asyncio.sleep(wait_time)
                self._tokens = 0.0
                self._last_refill = time.monotonic()
            else:
                self._tokens -= 1.0


# ---------------------------------------------------------------------------
# Lambda inspect client
# ---------------------------------------------------------------------------


class LambdaInspectClient:
    """Async wrapper around boto3 Lambda durable-execution APIs.

    Args:
        function_name: The Lambda function name or ARN to inspect.
        region_name: AWS region (defaults to session default).
        rate_limiter: Optional custom rate limiter instance.
    """

    def __init__(
        self,
        function_name: str,
        region_name: str | None = None,
        rate_limiter: TokenBucketRateLimiter | None = None,
    ) -> None:
        self.function_name = function_name
        self._client = boto3.client("lambda", region_name=region_name)
        self._limiter = rate_limiter or TokenBucketRateLimiter()

    # -- Public API ---------------------------------------------------------

    async def list_executions(
        self,
        status: ExecutionStatus | None = None,
        max_items: int = 50,
        next_token: str | None = None,
    ) -> ExecutionListResponse:
        """List durable executions for the configured function.

        Args:
            status: Optional status filter.
            max_items: Maximum number of results (default 50).
            next_token: Pagination token from a previous response.

        Returns:
            ExecutionListResponse with summaries and optional next_token.
        """
        kwargs: dict[str, Any] = {
            "FunctionName": self.function_name,
            "MaxItems": max_items,
        }
        if status is not None:
            kwargs["StatusFilter"] = status.value
        if next_token is not None:
            kwargs["NextToken"] = next_token

        await self._limiter.acquire()
        raw = await asyncio.to_thread(self._client.list_durable_executions_by_function, **kwargs)

        executions = [self._parse_summary(item) for item in raw.get("DurableExecutions", [])]

        return ExecutionListResponse(
            executions=executions,
            next_token=raw.get("NextToken"),
        )

    async def get_execution(self, execution_id: str) -> ExecutionDetail:
        """Get full detail (including history) for one execution.

        Args:
            execution_id: The durable-execution identifier.

        Returns:
            ExecutionDetail with history events.
        """
        await self._limiter.acquire()
        raw = await asyncio.to_thread(
            self._client.get_durable_execution,
            FunctionName=self.function_name,
            ExecutionId=execution_id,
        )

        return self._parse_detail(raw)

    async def close(self) -> None:
        """Close the underlying boto3 client."""
        await asyncio.to_thread(self._client.close)

    # -- Internal helpers ---------------------------------------------------

    def _parse_summary(self, item: dict[str, Any]) -> ExecutionSummary:
        """Parse a raw API execution summary into our model."""
        return ExecutionSummary(
            execution_id=item.get("ExecutionId", ""),
            name=item.get("ExecutionName", item.get("ExecutionId", "")),
            status=ExecutionStatus(item.get("Status", "RUNNING")),
            function_name=item.get("FunctionName", self.function_name),
            start_time=normalize_timestamp(item.get("StartTime", 0)),
            end_time=(normalize_timestamp(item["EndTime"]) if item.get("EndTime") is not None else None),
        )

    def _parse_detail(self, raw: dict[str, Any]) -> ExecutionDetail:
        """Parse a raw API execution detail into our model."""
        exec_data = raw.get("DurableExecution", raw)

        # Parse input/result payloads (may be JSON strings).
        input_payload = self._try_parse_json(exec_data.get("Input"))
        result = self._try_parse_json(exec_data.get("Output"))

        error_info = None
        if exec_data.get("Error") or exec_data.get("Cause"):
            error_info = ExecutionError(
                error=exec_data.get("Error", ""),
                cause=exec_data.get("Cause", ""),
            )

        # Parse history events.
        history = [self._parse_history_event(evt) for evt in exec_data.get("Events", [])]

        return ExecutionDetail(
            execution_id=exec_data.get("ExecutionId", ""),
            name=exec_data.get("ExecutionName", exec_data.get("ExecutionId", "")),
            status=ExecutionStatus(exec_data.get("Status", "RUNNING")),
            function_name=exec_data.get("FunctionName", self.function_name),
            start_time=normalize_timestamp(exec_data.get("StartTime", 0)),
            end_time=(normalize_timestamp(exec_data["EndTime"]) if exec_data.get("EndTime") is not None else None),
            input_payload=input_payload,
            result=result,
            error=error_info,
            history=history,
        )

    def _parse_history_event(self, evt: dict[str, Any]) -> HistoryEvent:
        """Parse a single history event from the API response."""
        return HistoryEvent(
            event_id=evt.get("EventId", 0),
            timestamp=normalize_timestamp(evt.get("Timestamp", 0)),
            event_type=evt.get("EventType", ""),
            sub_type=evt.get("SubType"),
            details=evt.get("Details", {}),
        )

    @staticmethod
    def _try_parse_json(value: Any) -> dict[str, Any] | None:
        """Try to parse a value as JSON; return dict or None."""
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {"value": parsed}
            except (json.JSONDecodeError, TypeError):
                return {"raw": value}
        return {"value": value}
