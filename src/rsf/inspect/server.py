"""FastAPI server for the RSF execution inspector.

Serves:
1. REST endpoints under /api/inspect for execution list, detail, and history
2. SSE stream for live execution updates
3. Static files for the inspector React SPA (when built)
"""

from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI

from rsf.inspect.client import LambdaInspectClient
from rsf.inspect.router import router

# Both editor and inspector share the same React SPA build (hash routing).
# The Vite build outputs to editor/static/, so we reference it from there.
_STATIC_DIR = Path(__file__).resolve().parent.parent / "editor" / "static"


def create_app(
    function_name: str | None = None,
    region_name: str | None = None,
) -> FastAPI:
    """Create the FastAPI application for the execution inspector.

    Args:
        function_name: Lambda function name or ARN to inspect.
        region_name: AWS region name (defaults to session default).

    Returns:
        Configured FastAPI application.
    """
    app = FastAPI(
        title="RSF Execution Inspector",
        description="Live execution inspector for Lambda Durable Functions",
    )

    # Store function_name in app state for diagnostics.
    app.state.function_name = function_name

    # Create the Lambda inspect client if a function name is provided.
    if function_name is not None:
        app.state.inspect_client = LambdaInspectClient(
            function_name=function_name,
            region_name=region_name,
        )
    else:
        app.state.inspect_client = None

    # Include the inspector router.
    app.include_router(router)

    # Static file serving for inspector React SPA (only if build exists).
    if _STATIC_DIR.is_dir():
        from fastapi.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")

    return app


def launch(
    function_name: str,
    region_name: str | None = None,
    port: int = 8766,
    open_browser: bool = True,
) -> None:
    """Start the execution inspector server.

    Args:
        function_name: Lambda function name or ARN to inspect.
        region_name: AWS region name.
        port: Port to listen on (default: 8766).
        open_browser: Whether to open the browser automatically.
    """
    app = create_app(function_name=function_name, region_name=region_name)

    if open_browser:
        import threading
        import webbrowser

        def _open() -> None:
            import time

            time.sleep(0.5)
            webbrowser.open(f"http://127.0.0.1:{port}")

        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(app, host="127.0.0.1", port=port)
