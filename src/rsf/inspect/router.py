"""FastAPI router for the RSF execution inspector.

Provides REST endpoints for listing and inspecting durable executions,
plus an SSE stream for live execution updates.

Endpoints:
- GET /api/inspect/executions         — list executions (INB-01)
- GET /api/inspect/execution/{id}     — execution detail + history (INB-02)
- GET /api/inspect/execution/{id}/history — history events only (INB-03)
- GET /api/inspect/execution/{id}/stream  — SSE live stream (INB-04, INB-05)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse

from rsf.inspect.client import LambdaInspectClient
from rsf.inspect.models import (
    TERMINAL_STATUSES,
    ExecutionDetail,
    ExecutionListResponse,
    ExecutionStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/inspect")


def _get_client(request: Request) -> LambdaInspectClient:
    """Retrieve the Lambda inspect client from app state."""
    client: LambdaInspectClient | None = getattr(
        request.app.state, "inspect_client", None
    )
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="Inspector client not configured",
        )
    return client


# -----------------------------------------------------------------------
# REST endpoints
# -----------------------------------------------------------------------


@router.get("/executions", response_model=ExecutionListResponse)
async def list_executions(
    request: Request,
    status: ExecutionStatus | None = Query(default=None),
    max_items: int = Query(default=50, ge=1, le=200),
    next_token: str | None = Query(default=None),
) -> ExecutionListResponse:
    """List durable executions with optional status filter and pagination."""
    client = _get_client(request)
    return await client.list_executions(
        status=status,
        max_items=max_items,
        next_token=next_token,
    )


@router.get("/execution/{execution_id}", response_model=ExecutionDetail)
async def get_execution(
    request: Request,
    execution_id: str,
) -> ExecutionDetail:
    """Get execution detail including history events."""
    client = _get_client(request)
    return await client.get_execution(execution_id)


@router.get("/execution/{execution_id}/history")
async def get_execution_history(
    request: Request,
    execution_id: str,
) -> dict[str, Any]:
    """Get history events only for a specific execution."""
    client = _get_client(request)
    detail = await client.get_execution(execution_id)
    return {
        "execution_id": execution_id,
        "events": [evt.model_dump(mode="json") for evt in detail.history],
    }


@router.get("/execution/{execution_id}/stream")
async def stream_execution(
    request: Request,
    execution_id: str,
) -> EventSourceResponse:
    """SSE stream for live execution updates.

    Stream lifecycle:
    1. Connect → send execution_info + full history
    2. Poll every 5s → send execution_info; if new events, send history_update
    3. Close when execution reaches a terminal status
    """
    client = _get_client(request)

    async def event_generator() -> AsyncGenerator[dict[str, str], None]:
        seen_event_ids: set[int] = set()

        # Initial fetch: send execution info + full history.
        detail = await client.get_execution(execution_id)

        yield {
            "event": "execution_info",
            "data": detail.model_dump_json(exclude={"history"}),
        }

        if detail.history:
            for evt in detail.history:
                seen_event_ids.add(evt.event_id)
            yield {
                "event": "history",
                "data": json.dumps(
                    [e.model_dump(mode="json") for e in detail.history]
                ),
            }

        # If already terminal, close immediately.
        if detail.status in TERMINAL_STATUSES:
            return

        # Poll loop.
        while True:
            await asyncio.sleep(5)

            # Check if the client has disconnected.
            if await request.is_disconnected():
                logger.debug("SSE client disconnected for %s", execution_id)
                return

            detail = await client.get_execution(execution_id)

            yield {
                "event": "execution_info",
                "data": detail.model_dump_json(exclude={"history"}),
            }

            # Send only new history events.
            new_events = [
                e for e in detail.history if e.event_id not in seen_event_ids
            ]
            if new_events:
                for evt in new_events:
                    seen_event_ids.add(evt.event_id)
                yield {
                    "event": "history_update",
                    "data": json.dumps(
                        [e.model_dump(mode="json") for e in new_events]
                    ),
                }

            if detail.status in TERMINAL_STATUSES:
                return

    return EventSourceResponse(event_generator())
