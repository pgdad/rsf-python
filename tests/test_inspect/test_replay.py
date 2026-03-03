"""Tests for the RSF inspector replay functionality.

Tests cover:
- ReplayRequest / ReplayResponse Pydantic models
- LambdaInspectClient.invoke_execution() method
- POST /api/inspect/execution/{id}/replay endpoint
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from rsf.inspect.client import LambdaInspectClient, TokenBucketRateLimiter
from rsf.inspect.models import (
    ExecutionDetail,
    ExecutionStatus,
    ReplayRequest,
    ReplayResponse,
)
from rsf.inspect.router import router


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


def test_replay_request_accepts_optional_input_payload() -> None:
    """ReplayRequest model accepts optional input_payload dict."""
    r = ReplayRequest(input_payload={"key": "value"})
    assert r.input_payload == {"key": "value"}


def test_replay_request_defaults_input_payload_to_none() -> None:
    """ReplayRequest model defaults input_payload to None when not provided."""
    r = ReplayRequest()
    assert r.input_payload is None


def test_replay_response_has_required_fields() -> None:
    """ReplayResponse model includes execution_id, replay_from, function_name, status_code."""
    r = ReplayResponse(
        execution_id="new-exec-123",
        replay_from="orig-exec-456",
        function_name="my-function",
        status_code=202,
    )
    assert r.execution_id == "new-exec-123"
    assert r.replay_from == "orig-exec-456"
    assert r.function_name == "my-function"
    assert r.status_code == 202


# ---------------------------------------------------------------------------
# Client invoke_execution tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invoke_execution_calls_lambda_invoke() -> None:
    """invoke_execution calls boto3 lambda_client.invoke with InvocationType='Event'."""
    mock_boto_client = MagicMock()
    mock_boto_client.invoke.return_value = {
        "StatusCode": 202,
        "ResponseMetadata": {"RequestId": "req-123"},
    }

    with patch("rsf.inspect.client.boto3") as mock_boto:
        mock_boto.client.return_value = mock_boto_client
        client = LambdaInspectClient(
            function_name="my-function",
            rate_limiter=TokenBucketRateLimiter(rate=1000.0, capacity=1000.0),
        )
        result = await client.invoke_execution({"key": "value"})

    mock_boto_client.invoke.assert_called_once_with(
        FunctionName="my-function",
        InvocationType="Event",
        Payload=json.dumps({"key": "value"}).encode("utf-8"),
    )
    assert result["StatusCode"] == 202


@pytest.mark.asyncio
async def test_invoke_execution_passes_json_payload() -> None:
    """invoke_execution passes JSON-serialized payload as Payload parameter."""
    mock_boto_client = MagicMock()
    mock_boto_client.invoke.return_value = {"StatusCode": 202, "ResponseMetadata": {}}

    with patch("rsf.inspect.client.boto3") as mock_boto:
        mock_boto.client.return_value = mock_boto_client
        client = LambdaInspectClient(
            function_name="fn",
            rate_limiter=TokenBucketRateLimiter(rate=1000.0, capacity=1000.0),
        )
        await client.invoke_execution({"nested": {"data": [1, 2, 3]}})

    call_kwargs = mock_boto_client.invoke.call_args[1]
    payload_bytes = call_kwargs["Payload"]
    parsed = json.loads(payload_bytes)
    assert parsed == {"nested": {"data": [1, 2, 3]}}


@pytest.mark.asyncio
async def test_invoke_execution_respects_rate_limiter() -> None:
    """invoke_execution acquires a rate limiter token before invoking."""
    mock_limiter = AsyncMock(spec=TokenBucketRateLimiter)
    mock_boto_client = MagicMock()
    mock_boto_client.invoke.return_value = {"StatusCode": 202, "ResponseMetadata": {}}

    with patch("rsf.inspect.client.boto3") as mock_boto:
        mock_boto.client.return_value = mock_boto_client
        client = LambdaInspectClient(function_name="fn", rate_limiter=mock_limiter)
        await client.invoke_execution({"key": "val"})

    mock_limiter.acquire.assert_awaited_once()


@pytest.mark.asyncio
async def test_invoke_execution_returns_response_metadata() -> None:
    """invoke_execution returns the raw response dict including StatusCode."""
    mock_boto_client = MagicMock()
    expected = {
        "StatusCode": 202,
        "ResponseMetadata": {"RequestId": "abc-123"},
        "FunctionError": None,
    }
    mock_boto_client.invoke.return_value = expected

    with patch("rsf.inspect.client.boto3") as mock_boto:
        mock_boto.client.return_value = mock_boto_client
        client = LambdaInspectClient(
            function_name="fn",
            rate_limiter=TokenBucketRateLimiter(rate=1000.0, capacity=1000.0),
        )
        result = await client.invoke_execution({})

    assert result["StatusCode"] == 202
    assert result["ResponseMetadata"]["RequestId"] == "abc-123"


# ---------------------------------------------------------------------------
# Router endpoint tests
# ---------------------------------------------------------------------------


def _make_test_app() -> FastAPI:
    """Create a test FastAPI app with the inspect router."""
    app = FastAPI()
    app.include_router(router)
    return app


def _make_mock_client(
    execution_status: ExecutionStatus = ExecutionStatus.SUCCEEDED,
    input_payload: dict[str, Any] | None = None,
    invoke_response: dict[str, Any] | None = None,
    get_raises: Exception | None = None,
) -> MagicMock:
    """Create a mock LambdaInspectClient."""
    mock_client = MagicMock()
    mock_client.function_name = "test-function"

    if get_raises:
        mock_client.get_execution = AsyncMock(side_effect=get_raises)
    else:
        detail = ExecutionDetail(
            execution_id="exec-001",
            name="test-execution",
            status=execution_status,
            function_name="test-function",
            start_time=datetime(2026, 3, 1, tzinfo=timezone.utc),
            end_time=datetime(2026, 3, 1, 0, 5, tzinfo=timezone.utc),
            input_payload=input_payload or {"original": "payload"},
        )
        mock_client.get_execution = AsyncMock(return_value=detail)

    mock_client.invoke_execution = AsyncMock(
        return_value=invoke_response
        or {
            "StatusCode": 202,
            "ResponseMetadata": {"RequestId": "new-exec-789"},
        }
    )

    return mock_client


@pytest.mark.asyncio
async def test_replay_terminal_execution_returns_200() -> None:
    """POST replay with valid terminal execution returns 200 with ReplayResponse."""
    app = _make_test_app()
    mock_client = _make_mock_client(ExecutionStatus.SUCCEEDED)
    app.state.inspect_client = mock_client

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/inspect/execution/exec-001/replay",
            json={"input_payload": {"modified": "data"}},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["replay_from"] == "exec-001"
    assert data["function_name"] == "test-function"
    assert data["status_code"] == 202


@pytest.mark.asyncio
async def test_replay_running_execution_returns_400() -> None:
    """POST replay with RUNNING execution returns 400 error."""
    app = _make_test_app()
    mock_client = _make_mock_client(ExecutionStatus.RUNNING)
    app.state.inspect_client = mock_client

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/inspect/execution/exec-001/replay")

    assert resp.status_code == 400
    assert "RUNNING" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_replay_without_body_uses_original_payload() -> None:
    """POST replay without body uses the original execution's input_payload."""
    app = _make_test_app()
    mock_client = _make_mock_client(
        ExecutionStatus.FAILED,
        input_payload={"original": "data"},
    )
    app.state.inspect_client = mock_client

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/inspect/execution/exec-001/replay")

    assert resp.status_code == 200
    mock_client.invoke_execution.assert_awaited_once_with({"original": "data"})


@pytest.mark.asyncio
async def test_replay_with_custom_payload_uses_provided() -> None:
    """POST replay with custom input_payload uses the provided payload."""
    app = _make_test_app()
    mock_client = _make_mock_client(ExecutionStatus.SUCCEEDED)
    app.state.inspect_client = mock_client

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/inspect/execution/exec-001/replay",
            json={"input_payload": {"custom": "payload"}},
        )

    assert resp.status_code == 200
    mock_client.invoke_execution.assert_awaited_once_with({"custom": "payload"})


@pytest.mark.asyncio
async def test_replay_nonexistent_execution_returns_404() -> None:
    """POST replay for non-existent execution returns 404."""
    app = _make_test_app()
    mock_client = _make_mock_client(get_raises=Exception("Not found"))
    app.state.inspect_client = mock_client

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/inspect/execution/nonexistent/replay")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_replay_response_replay_from_matches_source() -> None:
    """ReplayResponse replay_from field matches the source execution_id."""
    app = _make_test_app()
    mock_client = _make_mock_client(ExecutionStatus.TIMED_OUT)
    app.state.inspect_client = mock_client

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/inspect/execution/exec-001/replay")

    data = resp.json()
    assert data["replay_from"] == "exec-001"
