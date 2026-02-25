"""WebSocket handler for the RSF graph editor.

Handles bidirectional messages for:
- parse: YAML string → parsed definition dict + validation errors
- validate: YAML string → validation errors only
- load_file: file path → YAML contents
- save_file: file path + YAML → write to disk
- get_schema: → JSON Schema for DSL

On connect, auto-loads workflow file if configured via app state.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from rsf.dsl.parser import parse_definition, parse_yaml
from rsf.dsl.validator import validate_definition
from rsf.schema.generate import generate_json_schema

logger = logging.getLogger(__name__)


async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle WebSocket connections for the graph editor."""
    await websocket.accept()

    # Auto-load workflow file on connect if configured
    workflow_path = websocket.app.state.workflow_path
    if workflow_path is not None:
        await _handle_load_file(websocket, {"path": workflow_path})

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await _send_error(websocket, "Invalid JSON message")
                continue

            msg_type = message.get("type")
            if msg_type is None:
                await _send_error(websocket, "Missing 'type' field in message")
                continue

            if msg_type == "parse":
                await _handle_parse(websocket, message)
            elif msg_type == "validate":
                await _handle_validate(websocket, message)
            elif msg_type == "load_file":
                await _handle_load_file(websocket, message)
            elif msg_type == "save_file":
                await _handle_save_file(websocket, message)
            elif msg_type == "get_schema":
                await _handle_get_schema(websocket)
            else:
                await _send_error(websocket, f"Unknown message type: {msg_type}")

    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected")


async def _handle_parse(websocket: WebSocket, message: dict[str, Any]) -> None:
    """Parse YAML and return AST + validation errors."""
    yaml_content = message.get("yaml")
    if yaml_content is None:
        await _send_error(websocket, "Missing 'yaml' field in parse message")
        return

    errors: list[dict[str, str]] = []
    ast: dict[str, Any] | None = None

    try:
        raw = parse_yaml(yaml_content)
        definition = parse_definition(raw)
        ast = definition.model_dump(by_alias=True, exclude_none=True)

        # Run semantic validation
        semantic_errors = validate_definition(definition)
        for err in semantic_errors:
            errors.append({
                "message": err.message,
                "path": err.path,
                "severity": err.severity,
            })

    except yaml.YAMLError as exc:
        errors.append({
            "message": f"YAML syntax error: {exc}",
            "path": "",
            "severity": "error",
        })
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(part) for part in err["loc"])
            errors.append({
                "message": err["msg"],
                "path": loc,
                "severity": "error",
            })

    await websocket.send_json({
        "type": "parsed",
        "ast": ast,
        "yaml": yaml_content,
        "errors": errors,
    })


async def _handle_validate(websocket: WebSocket, message: dict[str, Any]) -> None:
    """Validate YAML and return errors only (no AST)."""
    yaml_content = message.get("yaml")
    if yaml_content is None:
        await _send_error(websocket, "Missing 'yaml' field in validate message")
        return

    errors: list[dict[str, str]] = []

    try:
        raw = parse_yaml(yaml_content)
        definition = parse_definition(raw)

        # Run semantic validation
        semantic_errors = validate_definition(definition)
        for err in semantic_errors:
            errors.append({
                "message": err.message,
                "path": err.path,
                "severity": err.severity,
            })

    except yaml.YAMLError as exc:
        errors.append({
            "message": f"YAML syntax error: {exc}",
            "path": "",
            "severity": "error",
        })
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(part) for part in err["loc"])
            errors.append({
                "message": err["msg"],
                "path": loc,
                "severity": "error",
            })

    await websocket.send_json({
        "type": "validated",
        "errors": errors,
    })


async def _handle_load_file(websocket: WebSocket, message: dict[str, Any]) -> None:
    """Load a workflow file from disk and send its contents."""
    file_path = message.get("path")
    if file_path is None:
        await _send_error(websocket, "Missing 'path' field in load_file message")
        return

    path = Path(file_path)
    if not path.is_file():
        await _send_error(websocket, f"File not found: {file_path}")
        return

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        await _send_error(websocket, f"Failed to read file: {exc}")
        return

    await websocket.send_json({
        "type": "file_loaded",
        "yaml": content,
        "path": str(path),
    })


async def _handle_save_file(websocket: WebSocket, message: dict[str, Any]) -> None:
    """Save YAML content to a file on disk."""
    file_path = message.get("path")
    yaml_content = message.get("yaml")

    if file_path is None:
        await _send_error(websocket, "Missing 'path' field in save_file message")
        return
    if yaml_content is None:
        await _send_error(websocket, "Missing 'yaml' field in save_file message")
        return

    path = Path(file_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml_content, encoding="utf-8")
    except OSError as exc:
        await _send_error(websocket, f"Failed to write file: {exc}")
        return

    await websocket.send_json({
        "type": "file_saved",
        "path": str(path),
    })


async def _handle_get_schema(websocket: WebSocket) -> None:
    """Send the JSON Schema for the RSF DSL."""
    schema = websocket.app.state.json_schema
    await websocket.send_json({
        "type": "schema",
        "json_schema": schema,
    })


async def _send_error(websocket: WebSocket, error_message: str) -> None:
    """Send an error response."""
    await websocket.send_json({
        "type": "error",
        "message": error_message,
    })
