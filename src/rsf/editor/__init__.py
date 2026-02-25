"""Graph editor backend — FastAPI server with REST, WebSocket, and static file serving."""

from rsf.editor.server import create_app, launch

__all__ = ["create_app", "launch"]
