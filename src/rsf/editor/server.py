"""FastAPI server for the RSF graph editor.

Serves:
1. Static files — Built React SPA (index.html, JS/CSS assets)
2. REST endpoint — GET /api/schema returns JSON Schema for the DSL
3. WebSocket endpoint — /ws for bidirectional DSL operations
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from rsf.editor.websocket import websocket_endpoint
from rsf.schema.generate import generate_json_schema

# Default static files directory (React SPA build output)
_STATIC_DIR = Path(__file__).parent / "static"


def create_app(workflow_path: str | None = None) -> FastAPI:
    """Create the FastAPI application for the graph editor.

    Args:
        workflow_path: Optional path to a workflow YAML file to auto-load
                      on WebSocket connect.

    Returns:
        Configured FastAPI application.
    """
    app = FastAPI(
        title="RSF Graph Editor",
        description="Visual graph editor backend for RSF workflows",
    )

    # Store workflow_path in app state for WebSocket access
    app.state.workflow_path = workflow_path

    # Cache the JSON Schema (generated once, immutable during server lifetime)
    app.state.json_schema = generate_json_schema()

    # REST endpoint: GET /api/schema
    @app.get("/api/schema")
    async def get_schema() -> JSONResponse:
        """Return JSON Schema for the RSF DSL."""
        return JSONResponse(content=app.state.json_schema)

    # WebSocket endpoint: /ws
    app.websocket("/ws")(websocket_endpoint)

    # Static file serving for React SPA (only if build directory exists)
    static_dir = _STATIC_DIR
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


def launch(
    workflow_path: str | None = None,
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    """Start the graph editor server.

    Args:
        workflow_path: Optional path to a workflow YAML file to auto-load.
        port: Port to listen on (default: 8765).
        open_browser: Whether to open the browser automatically.
    """
    app = create_app(workflow_path)

    if open_browser:
        import webbrowser
        import threading

        def _open():
            import time
            time.sleep(0.5)
            webbrowser.open(f"http://127.0.0.1:{port}")

        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(app, host="127.0.0.1", port=port)
