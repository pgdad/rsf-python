"""Tests for metadata transport mechanisms: FileTransport, EnvTransport, ArgsTransport."""

from __future__ import annotations

import json
import os
import stat
from dataclasses import asdict
from pathlib import Path

import pytest

from rsf.providers.metadata import WorkflowMetadata
from rsf.providers.transports import (
    ArgsTransport,
    EnvTransport,
    FileTransport,
    MetadataTransport,
)


@pytest.fixture
def sample_metadata() -> WorkflowMetadata:
    """Create a sample WorkflowMetadata for testing."""
    return WorkflowMetadata(
        workflow_name="test-workflow",
        stage="dev",
        handler_count=2,
        timeout_seconds=300,
        triggers=[{"type": "eventbridge", "schedule_expression": "rate(1 hour)"}],
        dynamodb_tables=[
            {
                "table_name": "items",
                "partition_key": {"name": "id", "type": "S"},
                "billing_mode": "PAY_PER_REQUEST",
            }
        ],
        dlq_enabled=True,
        dlq_max_receive_count=5,
        dlq_queue_name="test-dlq",
        lambda_url_enabled=True,
        lambda_url_auth_type="AWS_IAM",
    )


@pytest.fixture
def minimal_metadata() -> WorkflowMetadata:
    """Create a minimal WorkflowMetadata for testing."""
    return WorkflowMetadata(workflow_name="minimal-wf")


# --- MetadataTransport ABC tests ---


class TestMetadataTransportABC:
    """Verify MetadataTransport cannot be instantiated directly."""

    def test_cannot_instantiate(self) -> None:
        """MetadataTransport is abstract — direct instantiation raises TypeError."""
        with pytest.raises(TypeError):
            MetadataTransport()  # type: ignore[abstract]


# --- FileTransport tests ---


class TestFileTransport:
    """Verify FileTransport behavior."""

    def test_prepare_writes_json_file(self, sample_metadata: WorkflowMetadata) -> None:
        """FileTransport.prepare() writes a JSON file."""
        transport = FileTransport()
        env: dict[str, str] = {}
        try:
            transport.prepare(sample_metadata, env)
            path = env["RSF_METADATA_FILE"]
            assert os.path.exists(path)
            with open(path) as f:
                data = json.load(f)
            assert data["workflow_name"] == "test-workflow"
        finally:
            transport.cleanup()

    def test_prepare_sets_rsf_metadata_file_env(
        self, sample_metadata: WorkflowMetadata
    ) -> None:
        """FileTransport sets RSF_METADATA_FILE in env dict."""
        transport = FileTransport()
        env: dict[str, str] = {}
        try:
            transport.prepare(sample_metadata, env)
            assert "RSF_METADATA_FILE" in env
            assert env["RSF_METADATA_FILE"].endswith(".json")
        finally:
            transport.cleanup()

    def test_file_contents_match_asdict(
        self, sample_metadata: WorkflowMetadata
    ) -> None:
        """Written file contains valid JSON matching dataclasses.asdict()."""
        transport = FileTransport()
        env: dict[str, str] = {}
        try:
            transport.prepare(sample_metadata, env)
            with open(env["RSF_METADATA_FILE"]) as f:
                data = json.load(f)
            expected = asdict(sample_metadata)
            assert data == expected
        finally:
            transport.cleanup()

    def test_file_mode_0600(self, sample_metadata: WorkflowMetadata) -> None:
        """Written file has mode 0600 (owner read/write only)."""
        transport = FileTransport()
        env: dict[str, str] = {}
        try:
            transport.prepare(sample_metadata, env)
            path = env["RSF_METADATA_FILE"]
            file_stat = os.stat(path)
            mode = stat.S_IMODE(file_stat.st_mode)
            assert mode == 0o600, f"Expected 0600, got {oct(mode)}"
        finally:
            transport.cleanup()

    def test_file_is_pretty_printed(
        self, sample_metadata: WorkflowMetadata
    ) -> None:
        """Written JSON is pretty-printed (indent=2)."""
        transport = FileTransport()
        env: dict[str, str] = {}
        try:
            transport.prepare(sample_metadata, env)
            with open(env["RSF_METADATA_FILE"]) as f:
                content = f.read()
            # Pretty-printed JSON has newlines and indentation
            assert "\n" in content
            assert "  " in content
            # Verify it's indent=2 by comparing with expected format
            expected = json.dumps(asdict(sample_metadata), indent=2, default=str)
            assert content == expected
        finally:
            transport.cleanup()

    def test_prepare_returns_empty_list(
        self, sample_metadata: WorkflowMetadata
    ) -> None:
        """FileTransport.prepare() returns empty list (no extra CLI args)."""
        transport = FileTransport()
        env: dict[str, str] = {}
        try:
            result = transport.prepare(sample_metadata, env)
            assert result == []
        finally:
            transport.cleanup()

    def test_cleanup_removes_file(
        self, sample_metadata: WorkflowMetadata
    ) -> None:
        """FileTransport.cleanup() removes the temp file."""
        transport = FileTransport()
        env: dict[str, str] = {}
        transport.prepare(sample_metadata, env)
        path = env["RSF_METADATA_FILE"]
        assert os.path.exists(path)
        transport.cleanup()
        assert not os.path.exists(path)

    def test_cleanup_safe_to_call_twice(
        self, sample_metadata: WorkflowMetadata
    ) -> None:
        """FileTransport.cleanup() is safe to call multiple times."""
        transport = FileTransport()
        env: dict[str, str] = {}
        transport.prepare(sample_metadata, env)
        transport.cleanup()
        transport.cleanup()  # Should not raise

    def test_cleanup_safe_before_prepare(self) -> None:
        """FileTransport.cleanup() is safe to call before prepare()."""
        transport = FileTransport()
        transport.cleanup()  # Should not raise


# --- EnvTransport tests ---


class TestEnvTransport:
    """Verify EnvTransport behavior."""

    def test_sets_rsf_workflow_name(
        self, sample_metadata: WorkflowMetadata
    ) -> None:
        """EnvTransport sets RSF_WORKFLOW_NAME in env dict."""
        transport = EnvTransport()
        env: dict[str, str] = {}
        transport.prepare(sample_metadata, env)
        assert env["RSF_WORKFLOW_NAME"] == "test-workflow"

    def test_sets_rsf_stage(self, sample_metadata: WorkflowMetadata) -> None:
        """EnvTransport sets RSF_STAGE in env dict."""
        transport = EnvTransport()
        env: dict[str, str] = {}
        transport.prepare(sample_metadata, env)
        assert env["RSF_STAGE"] == "dev"

    def test_stage_none_becomes_empty_string(
        self, minimal_metadata: WorkflowMetadata
    ) -> None:
        """EnvTransport sets RSF_STAGE to empty string when stage is None."""
        transport = EnvTransport()
        env: dict[str, str] = {}
        transport.prepare(minimal_metadata, env)
        assert env["RSF_STAGE"] == ""

    def test_sets_rsf_metadata_json(
        self, sample_metadata: WorkflowMetadata
    ) -> None:
        """EnvTransport sets RSF_METADATA_JSON with full JSON blob."""
        transport = EnvTransport()
        env: dict[str, str] = {}
        transport.prepare(sample_metadata, env)
        assert "RSF_METADATA_JSON" in env
        data = json.loads(env["RSF_METADATA_JSON"])
        assert data["workflow_name"] == "test-workflow"
        assert data["dlq_enabled"] is True

    def test_prepare_returns_empty_list(
        self, sample_metadata: WorkflowMetadata
    ) -> None:
        """EnvTransport.prepare() returns empty list (no extra CLI args)."""
        transport = EnvTransport()
        env: dict[str, str] = {}
        result = transport.prepare(sample_metadata, env)
        assert result == []

    def test_cleanup_is_noop(self) -> None:
        """EnvTransport.cleanup() is a no-op."""
        transport = EnvTransport()
        transport.cleanup()  # Should not raise


# --- ArgsTransport tests ---


class TestArgsTransport:
    """Verify ArgsTransport behavior."""

    def test_workflow_name_substitution(
        self, sample_metadata: WorkflowMetadata
    ) -> None:
        """ArgsTransport substitutes {workflow_name} placeholder."""
        transport = ArgsTransport(["--workflow {workflow_name}"])
        env: dict[str, str] = {}
        args = transport.prepare(sample_metadata, env)
        assert args == ["--workflow", "test-workflow"]

    def test_stage_substitution(
        self, sample_metadata: WorkflowMetadata
    ) -> None:
        """ArgsTransport substitutes {stage} placeholder."""
        transport = ArgsTransport(["--stage {stage}"])
        env: dict[str, str] = {}
        args = transport.prepare(sample_metadata, env)
        assert args == ["--stage", "dev"]

    def test_metadata_file_substitution(
        self, sample_metadata: WorkflowMetadata
    ) -> None:
        """ArgsTransport substitutes {metadata_file} from env."""
        transport = ArgsTransport(["--meta {metadata_file}"])
        env: dict[str, str] = {"RSF_METADATA_FILE": "/tmp/test.json"}
        args = transport.prepare(sample_metadata, env)
        assert args == ["--meta", "/tmp/test.json"]

    def test_multiple_templates(
        self, sample_metadata: WorkflowMetadata
    ) -> None:
        """ArgsTransport handles multiple templates."""
        transport = ArgsTransport([
            "--workflow {workflow_name}",
            "--stage {stage}",
        ])
        env: dict[str, str] = {}
        args = transport.prepare(sample_metadata, env)
        assert args == ["--workflow", "test-workflow", "--stage", "dev"]

    def test_invalid_placeholder_raises_at_construction(self) -> None:
        """ArgsTransport raises ValueError for invalid placeholder at construction."""
        with pytest.raises(ValueError, match="Invalid placeholder"):
            ArgsTransport(["--bad {nonexistent}"])

    def test_attribute_access_rejected(self) -> None:
        """ArgsTransport rejects attribute access in placeholders."""
        with pytest.raises(ValueError, match="Attribute access"):
            ArgsTransport(["--bad {workflow_name.__class__}"])

    def test_indexing_rejected(self) -> None:
        """ArgsTransport rejects indexing in placeholders."""
        with pytest.raises(ValueError, match="Attribute access"):
            ArgsTransport(["--bad {triggers[0]}"])

    def test_valid_metadata_fields_accepted(self) -> None:
        """All WorkflowMetadata field names are valid placeholders."""
        # Should not raise
        ArgsTransport([
            "{workflow_name}",
            "{stage}",
            "{handler_count}",
            "{timeout_seconds}",
            "{dlq_enabled}",
            "{dlq_max_receive_count}",
            "{dlq_queue_name}",
            "{lambda_url_enabled}",
            "{lambda_url_auth_type}",
            "{metadata_file}",
        ])

    def test_prepare_returns_args_list(
        self, sample_metadata: WorkflowMetadata
    ) -> None:
        """ArgsTransport.prepare() returns the substituted args as a list."""
        transport = ArgsTransport(["--name {workflow_name}"])
        env: dict[str, str] = {}
        result = transport.prepare(sample_metadata, env)
        assert isinstance(result, list)
        assert all(isinstance(a, str) for a in result)

    def test_cleanup_is_noop(self) -> None:
        """ArgsTransport.cleanup() is a no-op."""
        transport = ArgsTransport(["--test {workflow_name}"])
        transport.cleanup()  # Should not raise

    def test_empty_templates(
        self, sample_metadata: WorkflowMetadata
    ) -> None:
        """ArgsTransport with empty templates returns empty args."""
        transport = ArgsTransport([])
        env: dict[str, str] = {}
        args = transport.prepare(sample_metadata, env)
        assert args == []

    def test_literal_text_without_placeholders(
        self, sample_metadata: WorkflowMetadata
    ) -> None:
        """ArgsTransport handles templates with no placeholders."""
        transport = ArgsTransport(["--verbose"])
        env: dict[str, str] = {}
        args = transport.prepare(sample_metadata, env)
        assert args == ["--verbose"]
