"""Tests for the inspector FastAPI server (REST endpoints and SSE stream)."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from rsf.inspect.client import LambdaInspectClient
from rsf.inspect.models import (
    ExecutionDetail,
    ExecutionError,
    ExecutionListResponse,
    ExecutionStatus,
    ExecutionSummary,
    HistoryEvent,
)
from rsf.inspect.server import create_app


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------


def _ts(epoch: int) -> datetime:
    """Helper: epoch seconds → UTC datetime."""
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


def _make_summary(
    execution_id: str = "exec-001",
    status: ExecutionStatus = ExecutionStatus.RUNNING,
) -> ExecutionSummary:
    return ExecutionSummary(
        execution_id=execution_id,
        name=f"name-{execution_id}",
        status=status,
        function_name="test-func",
        start_time=_ts(1700000000),
    )


def _make_detail(
    execution_id: str = "exec-001",
    status: ExecutionStatus = ExecutionStatus.RUNNING,
    history: list[HistoryEvent] | None = None,
) -> ExecutionDetail:
    return ExecutionDetail(
        execution_id=execution_id,
        name=f"name-{execution_id}",
        status=status,
        function_name="test-func",
        start_time=_ts(1700000000),
        history=history or [],
    )


@pytest.fixture
def mock_client():
    """Create a mock LambdaInspectClient."""
    client = MagicMock(spec=LambdaInspectClient)
    client.list_executions = AsyncMock()
    client.get_execution = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def app(mock_client):
    """Create a test app with a mocked client."""
    application = create_app()
    application.state.inspect_client = mock_client
    return application


# -----------------------------------------------------------------------
# Server creation
# -----------------------------------------------------------------------


class TestCreateApp:
    def test_creates_app_without_function_name(self):
        app = create_app()
        assert app.state.function_name is None
        assert app.state.inspect_client is None

    def test_stores_function_name(self):
        with patch("rsf.inspect.server.LambdaInspectClient"):
            app = create_app(function_name="my-func", region_name="us-east-2")
        assert app.state.function_name == "my-func"


# -----------------------------------------------------------------------
# GET /api/inspect/executions
# -----------------------------------------------------------------------


class TestListExecutions:
    @pytest.mark.asyncio
    async def test_list_executions_returns_json(self, app, mock_client):
        mock_client.list_executions.return_value = ExecutionListResponse(
            executions=[_make_summary(), _make_summary("exec-002")],
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/api/inspect/executions")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["executions"]) == 2
        assert data["executions"][0]["execution_id"] == "exec-001"

    @pytest.mark.asyncio
    async def test_list_executions_with_status_filter(self, app, mock_client):
        mock_client.list_executions.return_value = ExecutionListResponse(
            executions=[],
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/api/inspect/executions?status=FAILED")

        assert resp.status_code == 200
        mock_client.list_executions.assert_called_once()
        call_kwargs = mock_client.list_executions.call_args[1]
        assert call_kwargs["status"] == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_list_executions_with_pagination(self, app, mock_client):
        mock_client.list_executions.return_value = ExecutionListResponse(
            executions=[_make_summary()],
            next_token="token-abc",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/api/inspect/executions?max_items=10&next_token=prev-token")

        assert resp.status_code == 200
        data = resp.json()
        assert data["next_token"] == "token-abc"
        call_kwargs = mock_client.list_executions.call_args[1]
        assert call_kwargs["max_items"] == 10
        assert call_kwargs["next_token"] == "prev-token"

    @pytest.mark.asyncio
    async def test_list_executions_no_client_returns_503(self):
        app = create_app()  # No client configured
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/api/inspect/executions")

        assert resp.status_code == 503


# -----------------------------------------------------------------------
# GET /api/inspect/execution/{id}
# -----------------------------------------------------------------------


class TestGetExecution:
    @pytest.mark.asyncio
    async def test_get_execution_returns_detail(self, app, mock_client):
        mock_client.get_execution.return_value = _make_detail(
            status=ExecutionStatus.SUCCEEDED,
            history=[
                HistoryEvent(
                    event_id=1,
                    timestamp=_ts(1700000001),
                    event_type="StepStarted",
                ),
            ],
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/api/inspect/execution/exec-001")

        assert resp.status_code == 200
        data = resp.json()
        assert data["execution_id"] == "exec-001"
        assert data["status"] == "SUCCEEDED"
        assert len(data["history"]) == 1

    @pytest.mark.asyncio
    async def test_get_execution_passes_id(self, app, mock_client):
        mock_client.get_execution.return_value = _make_detail("my-id")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            await c.get("/api/inspect/execution/my-id")

        mock_client.get_execution.assert_called_once_with("my-id")


# -----------------------------------------------------------------------
# GET /api/inspect/execution/{id}/history
# -----------------------------------------------------------------------


class TestGetExecutionHistory:
    @pytest.mark.asyncio
    async def test_returns_events_only(self, app, mock_client):
        mock_client.get_execution.return_value = _make_detail(
            history=[
                HistoryEvent(
                    event_id=1,
                    timestamp=_ts(1700000001),
                    event_type="StepStarted",
                    details={"state": "S1"},
                ),
                HistoryEvent(
                    event_id=2,
                    timestamp=_ts(1700000002),
                    event_type="StepSucceeded",
                    details={"state": "S1"},
                ),
            ],
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/api/inspect/execution/exec-001/history")

        assert resp.status_code == 200
        data = resp.json()
        assert data["execution_id"] == "exec-001"
        assert len(data["events"]) == 2
        assert data["events"][0]["event_type"] == "StepStarted"

    @pytest.mark.asyncio
    async def test_empty_history(self, app, mock_client):
        mock_client.get_execution.return_value = _make_detail(history=[])

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/api/inspect/execution/exec-001/history")

        assert resp.status_code == 200
        data = resp.json()
        assert data["events"] == []


# -----------------------------------------------------------------------
# GET /api/inspect/execution/{id}/stream (SSE)
# -----------------------------------------------------------------------


class TestSSEStream:
    @pytest.mark.asyncio
    async def test_terminal_execution_closes_immediately(self, app, mock_client):
        """SSE stream for a terminal execution sends info + history then closes."""
        mock_client.get_execution.return_value = _make_detail(
            status=ExecutionStatus.SUCCEEDED,
            history=[
                HistoryEvent(
                    event_id=1,
                    timestamp=_ts(1700000001),
                    event_type="StepStarted",
                ),
            ],
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            async with c.stream("GET", "/api/inspect/execution/exec-001/stream") as resp:
                assert resp.status_code == 200

                lines = []
                async for line in resp.aiter_lines():
                    lines.append(line)

        # Should have execution_info event and history event.
        raw = "\n".join(lines)
        assert "event: execution_info" in raw
        assert "event: history" in raw

    @pytest.mark.asyncio
    async def test_running_execution_sends_updates(self, app, mock_client):
        """SSE stream for a running execution polls and sends updates."""
        call_count = 0

        async def mock_get_execution(execution_id):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: running with 1 event.
                return _make_detail(
                    status=ExecutionStatus.RUNNING,
                    history=[
                        HistoryEvent(
                            event_id=1,
                            timestamp=_ts(1700000001),
                            event_type="StepStarted",
                        ),
                    ],
                )
            else:
                # Second call: succeeded with 2 events.
                return _make_detail(
                    status=ExecutionStatus.SUCCEEDED,
                    history=[
                        HistoryEvent(
                            event_id=1,
                            timestamp=_ts(1700000001),
                            event_type="StepStarted",
                        ),
                        HistoryEvent(
                            event_id=2,
                            timestamp=_ts(1700000002),
                            event_type="StepSucceeded",
                        ),
                    ],
                )

        mock_client.get_execution = mock_get_execution

        # Patch asyncio.sleep to avoid real waiting.
        with patch("rsf.inspect.router.asyncio.sleep", new_callable=AsyncMock):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                async with c.stream("GET", "/api/inspect/execution/exec-001/stream") as resp:
                    assert resp.status_code == 200

                    lines = []
                    async for line in resp.aiter_lines():
                        lines.append(line)

        raw = "\n".join(lines)
        # Should have initial execution_info, history, poll execution_info, and history_update.
        assert raw.count("event: execution_info") == 2
        assert "event: history" in raw
        assert "event: history_update" in raw

    @pytest.mark.asyncio
    async def test_no_history_skips_history_event(self, app, mock_client):
        """SSE stream skips history event if no events exist."""
        mock_client.get_execution.return_value = _make_detail(
            status=ExecutionStatus.SUCCEEDED,
            history=[],
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            async with c.stream("GET", "/api/inspect/execution/exec-001/stream") as resp:
                lines = []
                async for line in resp.aiter_lines():
                    lines.append(line)

        raw = "\n".join(lines)
        assert "event: execution_info" in raw
        # No history event because there are no events.
        assert "event: history" not in raw
