"""Tests for the graph editor WebSocket handler."""

from __future__ import annotations

import json

import pytest
from starlette.testclient import TestClient

from rsf.editor.server import create_app

VALID_YAML = """\
rsf_version: "1.0"
StartAt: S1
States:
  S1:
    Type: Task
    Next: Done
  Done:
    Type: Succeed
"""

INVALID_YAML = """\
rsf_version: "1.0"
StartAt: S1
States:
  S1:
    Type: Task
"""

BAD_YAML_SYNTAX = ":\n  invalid: [unclosed"


@pytest.fixture
def client():
    """Create a synchronous test client (for WebSocket testing)."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def client_with_workflow(tmp_path):
    """Create a test client with a workflow file configured for auto-load."""
    wf = tmp_path / "workflow.yaml"
    wf.write_text(VALID_YAML)
    app = create_app(workflow_path=str(wf))
    return TestClient(app), str(wf)


class TestParse:
    """Tests for the 'parse' WebSocket message."""

    def test_parse_valid_yaml(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "parse", "yaml": VALID_YAML})
            response = ws.receive_json()

        assert response["type"] == "parsed"
        assert response["yaml"] == VALID_YAML
        assert response["ast"] is not None
        assert response["ast"]["StartAt"] == "S1"
        assert "S1" in response["ast"]["States"]
        assert response["errors"] == []

    def test_parse_invalid_schema(self, client):
        """Pydantic validation errors are returned."""
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "parse", "yaml": INVALID_YAML})
            response = ws.receive_json()

        assert response["type"] == "parsed"
        assert response["ast"] is None
        assert len(response["errors"]) > 0
        assert any("error" == e["severity"] for e in response["errors"])

    def test_parse_bad_yaml_syntax(self, client):
        """YAML syntax errors are returned."""
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "parse", "yaml": BAD_YAML_SYNTAX})
            response = ws.receive_json()

        assert response["type"] == "parsed"
        assert response["ast"] is None
        assert len(response["errors"]) > 0
        assert "YAML syntax error" in response["errors"][0]["message"]

    def test_parse_missing_yaml_field(self, client):
        """Missing 'yaml' field returns error."""
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "parse"})
            response = ws.receive_json()

        assert response["type"] == "error"
        assert "yaml" in response["message"]

    def test_parse_semantic_errors(self, client):
        """Semantic validation errors (bad references) are returned."""
        yaml_with_bad_ref = """\
rsf_version: "1.0"
StartAt: S1
States:
  S1:
    Type: Task
    Next: NonExistent
  Done:
    Type: Succeed
"""
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "parse", "yaml": yaml_with_bad_ref})
            response = ws.receive_json()

        assert response["type"] == "parsed"
        assert response["ast"] is not None  # Pydantic parsing succeeds
        assert len(response["errors"]) > 0
        assert any("NonExistent" in e["message"] for e in response["errors"])


class TestValidate:
    """Tests for the 'validate' WebSocket message."""

    def test_validate_valid_yaml(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "validate", "yaml": VALID_YAML})
            response = ws.receive_json()

        assert response["type"] == "validated"
        assert response["errors"] == []

    def test_validate_invalid_yaml(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "validate", "yaml": INVALID_YAML})
            response = ws.receive_json()

        assert response["type"] == "validated"
        assert len(response["errors"]) > 0

    def test_validate_missing_yaml_field(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "validate"})
            response = ws.receive_json()

        assert response["type"] == "error"
        assert "yaml" in response["message"]


class TestLoadFile:
    """Tests for the 'load_file' WebSocket message."""

    def test_load_existing_file(self, client, tmp_path):
        wf = tmp_path / "test.yaml"
        wf.write_text(VALID_YAML)

        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "load_file", "path": str(wf)})
            response = ws.receive_json()

        assert response["type"] == "file_loaded"
        assert response["yaml"] == VALID_YAML
        assert response["path"] == str(wf)

    def test_load_nonexistent_file(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "load_file", "path": "/tmp/nonexistent_rsf_test.yaml"})
            response = ws.receive_json()

        assert response["type"] == "error"
        assert "not found" in response["message"].lower()

    def test_load_missing_path_field(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "load_file"})
            response = ws.receive_json()

        assert response["type"] == "error"
        assert "path" in response["message"]


class TestSaveFile:
    """Tests for the 'save_file' WebSocket message."""

    def test_save_file(self, client, tmp_path):
        target = tmp_path / "output.yaml"

        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "save_file", "path": str(target), "yaml": VALID_YAML})
            response = ws.receive_json()

        assert response["type"] == "file_saved"
        assert response["path"] == str(target)
        assert target.read_text() == VALID_YAML

    def test_save_creates_parent_dirs(self, client, tmp_path):
        target = tmp_path / "sub" / "dir" / "output.yaml"

        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "save_file", "path": str(target), "yaml": VALID_YAML})
            response = ws.receive_json()

        assert response["type"] == "file_saved"
        assert target.read_text() == VALID_YAML

    def test_save_missing_path(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "save_file", "yaml": "content"})
            response = ws.receive_json()

        assert response["type"] == "error"
        assert "path" in response["message"]

    def test_save_missing_yaml(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "save_file", "path": "/tmp/test.yaml"})
            response = ws.receive_json()

        assert response["type"] == "error"
        assert "yaml" in response["message"]


class TestGetSchema:
    """Tests for the 'get_schema' WebSocket message."""

    def test_get_schema(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "get_schema"})
            response = ws.receive_json()

        assert response["type"] == "schema"
        assert "$schema" in response["json_schema"]
        assert response["json_schema"]["title"] == "RSF Workflow Definition"


class TestAutoLoad:
    """Tests for auto-loading workflow file on WebSocket connect."""

    def test_auto_load_on_connect(self, client_with_workflow):
        client, wf_path = client_with_workflow

        with client.websocket_connect("/ws") as ws:
            response = ws.receive_json()

        assert response["type"] == "file_loaded"
        assert response["path"] == wf_path
        assert "StartAt" in response["yaml"]

    def test_no_auto_load_when_not_configured(self, client):
        """No auto-load message when no workflow path configured."""
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "get_schema"})
            response = ws.receive_json()

        # First message should be the schema response, not file_loaded
        assert response["type"] == "schema"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_invalid_json_message(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_text("not valid json {{{")
            response = ws.receive_json()

        assert response["type"] == "error"
        assert "Invalid JSON" in response["message"]

    def test_missing_type_field(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"yaml": "content"})
            response = ws.receive_json()

        assert response["type"] == "error"
        assert "type" in response["message"]

    def test_unknown_message_type(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "unknown_action"})
            response = ws.receive_json()

        assert response["type"] == "error"
        assert "Unknown" in response["message"]

    def test_multiple_messages_in_sequence(self, client):
        """Multiple messages can be sent in a single connection."""
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "get_schema"})
            r1 = ws.receive_json()

            ws.send_json({"type": "validate", "yaml": VALID_YAML})
            r2 = ws.receive_json()

        assert r1["type"] == "schema"
        assert r2["type"] == "validated"
        assert r2["errors"] == []
