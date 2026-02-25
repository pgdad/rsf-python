"""Tests for the Lambda inspect client and token bucket rate limiter."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from rsf.inspect.client import LambdaInspectClient, TokenBucketRateLimiter
from rsf.inspect.models import ExecutionStatus


# -----------------------------------------------------------------------
# TokenBucketRateLimiter
# -----------------------------------------------------------------------


class TestTokenBucketRateLimiter:
    @pytest.mark.asyncio
    async def test_initial_tokens_available(self):
        """First requests should be served immediately."""
        limiter = TokenBucketRateLimiter(rate=12.0, capacity=12.0)
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.05  # Should be nearly instant

    @pytest.mark.asyncio
    async def test_burst_within_capacity(self):
        """Multiple requests within capacity should not block."""
        limiter = TokenBucketRateLimiter(rate=12.0, capacity=12.0)
        start = time.monotonic()
        for _ in range(10):
            await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1  # Should be fast for 10 tokens from 12 capacity

    @pytest.mark.asyncio
    async def test_rate_limiting_kicks_in(self):
        """Exhausting all tokens should cause a delay."""
        limiter = TokenBucketRateLimiter(rate=100.0, capacity=2.0)
        # Exhaust the bucket
        await limiter.acquire()
        await limiter.acquire()
        # Third request should wait
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.005  # Should wait for token refill

    @pytest.mark.asyncio
    async def test_tokens_refill_over_time(self):
        """Tokens should refill based on elapsed time."""
        limiter = TokenBucketRateLimiter(rate=100.0, capacity=5.0)
        # Exhaust all tokens
        for _ in range(5):
            await limiter.acquire()
        # Wait for some tokens to refill
        await asyncio.sleep(0.05)  # ~5 tokens at 100/s
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.02  # Should be available after refill

    @pytest.mark.asyncio
    async def test_custom_rate_and_capacity(self):
        """Custom rate and capacity are respected."""
        limiter = TokenBucketRateLimiter(rate=5.0, capacity=2.0)
        # Use both tokens
        await limiter.acquire()
        await limiter.acquire()
        # Next should wait ~0.2s (1 token / 5 per second)
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.1  # At least some delay


# -----------------------------------------------------------------------
# LambdaInspectClient
# -----------------------------------------------------------------------


@pytest.fixture
def mock_boto3_client():
    """Create a mock boto3 Lambda client."""
    with patch("rsf.inspect.client.boto3") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        yield mock_client


@pytest.fixture
def no_wait_limiter():
    """Create a rate limiter that never waits (for test speed)."""
    limiter = TokenBucketRateLimiter(rate=1000.0, capacity=1000.0)
    return limiter


class TestLambdaInspectClient:
    @pytest.mark.asyncio
    async def test_list_executions_basic(self, mock_boto3_client, no_wait_limiter):
        """list_executions returns parsed ExecutionListResponse."""
        mock_boto3_client.list_durable_executions_by_function.return_value = {
            "DurableExecutions": [
                {
                    "ExecutionId": "exec-001",
                    "ExecutionName": "my-exec",
                    "Status": "RUNNING",
                    "FunctionName": "my-func",
                    "StartTime": 1700000000,
                },
                {
                    "ExecutionId": "exec-002",
                    "ExecutionName": "my-exec-2",
                    "Status": "SUCCEEDED",
                    "FunctionName": "my-func",
                    "StartTime": 1700000100,
                    "EndTime": 1700000200,
                },
            ],
            "NextToken": None,
        }

        client = LambdaInspectClient(
            "my-func", rate_limiter=no_wait_limiter
        )
        client._client = mock_boto3_client

        result = await client.list_executions()

        assert len(result.executions) == 2
        assert result.executions[0].execution_id == "exec-001"
        assert result.executions[0].status == ExecutionStatus.RUNNING
        assert result.executions[1].status == ExecutionStatus.SUCCEEDED
        assert result.executions[1].end_time is not None

    @pytest.mark.asyncio
    async def test_list_executions_with_status_filter(
        self, mock_boto3_client, no_wait_limiter
    ):
        """list_executions passes status filter to API."""
        mock_boto3_client.list_durable_executions_by_function.return_value = {
            "DurableExecutions": [],
        }

        client = LambdaInspectClient(
            "my-func", rate_limiter=no_wait_limiter
        )
        client._client = mock_boto3_client

        await client.list_executions(status=ExecutionStatus.FAILED)

        call_kwargs = (
            mock_boto3_client.list_durable_executions_by_function.call_args[1]
        )
        assert call_kwargs["StatusFilter"] == "FAILED"

    @pytest.mark.asyncio
    async def test_list_executions_pagination(
        self, mock_boto3_client, no_wait_limiter
    ):
        """list_executions passes pagination tokens."""
        mock_boto3_client.list_durable_executions_by_function.return_value = {
            "DurableExecutions": [],
            "NextToken": "page2",
        }

        client = LambdaInspectClient(
            "my-func", rate_limiter=no_wait_limiter
        )
        client._client = mock_boto3_client

        result = await client.list_executions(next_token="page1", max_items=10)

        call_kwargs = (
            mock_boto3_client.list_durable_executions_by_function.call_args[1]
        )
        assert call_kwargs["NextToken"] == "page1"
        assert call_kwargs["MaxItems"] == 10
        assert result.next_token == "page2"

    @pytest.mark.asyncio
    async def test_get_execution_basic(self, mock_boto3_client, no_wait_limiter):
        """get_execution returns parsed ExecutionDetail."""
        mock_boto3_client.get_durable_execution.return_value = {
            "DurableExecution": {
                "ExecutionId": "exec-001",
                "ExecutionName": "my-exec",
                "Status": "SUCCEEDED",
                "FunctionName": "my-func",
                "StartTime": 1700000000,
                "EndTime": 1700000060,
                "Input": '{"key": "value"}',
                "Output": '{"result": 42}',
                "Events": [
                    {
                        "EventId": 1,
                        "Timestamp": 1700000001,
                        "EventType": "StepStarted",
                        "Details": {"state": "S1"},
                    },
                    {
                        "EventId": 2,
                        "Timestamp": 1700000002,
                        "EventType": "StepSucceeded",
                        "Details": {"state": "S1"},
                    },
                ],
            }
        }

        client = LambdaInspectClient(
            "my-func", rate_limiter=no_wait_limiter
        )
        client._client = mock_boto3_client

        detail = await client.get_execution("exec-001")

        assert detail.execution_id == "exec-001"
        assert detail.status == ExecutionStatus.SUCCEEDED
        assert detail.input_payload == {"key": "value"}
        assert detail.result == {"result": 42}
        assert len(detail.history) == 2
        assert detail.history[0].event_type == "StepStarted"
        assert detail.history[1].event_type == "StepSucceeded"

    @pytest.mark.asyncio
    async def test_get_execution_with_error(
        self, mock_boto3_client, no_wait_limiter
    ):
        """get_execution parses error fields."""
        mock_boto3_client.get_durable_execution.return_value = {
            "DurableExecution": {
                "ExecutionId": "exec-fail",
                "Status": "FAILED",
                "FunctionName": "my-func",
                "StartTime": 1700000000,
                "Error": "States.TaskFailed",
                "Cause": "Lambda function timed out",
                "Events": [],
            }
        }

        client = LambdaInspectClient(
            "my-func", rate_limiter=no_wait_limiter
        )
        client._client = mock_boto3_client

        detail = await client.get_execution("exec-fail")

        assert detail.error is not None
        assert detail.error.error == "States.TaskFailed"
        assert detail.error.cause == "Lambda function timed out"

    @pytest.mark.asyncio
    async def test_get_execution_no_events(
        self, mock_boto3_client, no_wait_limiter
    ):
        """get_execution works with empty events list."""
        mock_boto3_client.get_durable_execution.return_value = {
            "DurableExecution": {
                "ExecutionId": "exec-new",
                "Status": "RUNNING",
                "FunctionName": "my-func",
                "StartTime": 1700000000,
                "Events": [],
            }
        }

        client = LambdaInspectClient(
            "my-func", rate_limiter=no_wait_limiter
        )
        client._client = mock_boto3_client

        detail = await client.get_execution("exec-new")

        assert detail.history == []

    @pytest.mark.asyncio
    async def test_try_parse_json_dict_passthrough(self):
        """_try_parse_json passes dicts through unchanged."""
        result = LambdaInspectClient._try_parse_json({"a": 1})
        assert result == {"a": 1}

    @pytest.mark.asyncio
    async def test_try_parse_json_string(self):
        """_try_parse_json parses JSON strings."""
        result = LambdaInspectClient._try_parse_json('{"a": 1}')
        assert result == {"a": 1}

    @pytest.mark.asyncio
    async def test_try_parse_json_none(self):
        """_try_parse_json returns None for None."""
        result = LambdaInspectClient._try_parse_json(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_try_parse_json_invalid_string(self):
        """_try_parse_json wraps unparseable strings."""
        result = LambdaInspectClient._try_parse_json("not json")
        assert result == {"raw": "not json"}

    @pytest.mark.asyncio
    async def test_close(self, mock_boto3_client, no_wait_limiter):
        """close() calls underlying client close."""
        client = LambdaInspectClient(
            "my-func", rate_limiter=no_wait_limiter
        )
        client._client = mock_boto3_client

        await client.close()

        mock_boto3_client.close.assert_called_once()
