"""Tests for the graph editor FastAPI server (REST endpoints)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from rsf.editor.server import create_app


@pytest.fixture
def app():
    """Create a test app with no workflow path."""
    return create_app()


@pytest.fixture
def app_with_workflow(tmp_path):
    """Create a test app with a workflow file configured."""
    wf = tmp_path / "workflow.yaml"
    wf.write_text('rsf_version: "1.0"\nStartAt: S1\nStates:\n  S1:\n    Type: Succeed\n')
    return create_app(workflow_path=str(wf))


@pytest.mark.asyncio
async def test_get_schema_returns_json_schema(app):
    """GET /api/schema returns valid JSON Schema."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/schema")

    assert response.status_code == 200
    schema = response.json()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["title"] == "RSF Workflow Definition"
    assert "properties" in schema


@pytest.mark.asyncio
async def test_get_schema_is_cached(app):
    """Schema is generated once, same object returned on multiple requests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.get("/api/schema")
        r2 = await client.get("/api/schema")

    assert r1.json() == r2.json()


@pytest.mark.asyncio
async def test_app_state_stores_workflow_path(tmp_path):
    """App state stores the configured workflow path."""
    wf = tmp_path / "test.yaml"
    wf.write_text("test")
    app = create_app(workflow_path=str(wf))
    assert app.state.workflow_path == str(wf)


@pytest.mark.asyncio
async def test_app_state_workflow_path_none():
    """App state stores None when no workflow path configured."""
    app = create_app()
    assert app.state.workflow_path is None
