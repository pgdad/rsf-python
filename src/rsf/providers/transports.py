"""Metadata transport mechanisms for infrastructure providers.

Three transport strategies for delivering WorkflowMetadata to external
provider commands: JSON file, environment variables, and CLI arg templates.
"""

from __future__ import annotations

import json
import os
import string
import tempfile
from abc import ABC, abstractmethod
from dataclasses import asdict

from rsf.providers.metadata import WorkflowMetadata


class MetadataTransport(ABC):
    """Abstract base for metadata delivery mechanisms.

    Each transport prepares metadata for delivery to a provider command.
    ``prepare()`` mutates the env dict and returns extra CLI args.
    ``cleanup()`` releases any resources (temp files, etc.).
    """

    @abstractmethod
    def prepare(self, metadata: WorkflowMetadata, env: dict[str, str]) -> list[str]:
        """Prepare transport. Mutates env dict, returns extra CLI args."""
        ...

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up transport resources (e.g., temp files)."""
        ...


class FileTransport(MetadataTransport):
    """Deliver metadata via JSON file written to temp directory.

    File written with mode 0600 (owner read/write only).
    Path passed as ``RSF_METADATA_FILE`` env var.
    Auto-cleanup after provider command completes.
    """

    def __init__(self) -> None:
        self._temp_path: str | None = None

    def prepare(self, metadata: WorkflowMetadata, env: dict[str, str]) -> list[str]:
        """Write metadata JSON to temp file, set RSF_METADATA_FILE env var."""
        fd, path = tempfile.mkstemp(suffix=".json", prefix="rsf_metadata_")
        self._temp_path = path
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(asdict(metadata), f, indent=2, default=str)
            os.chmod(path, 0o600)
        except Exception:
            # If writing fails, clean up the file descriptor and re-raise
            try:
                os.unlink(path)
            except OSError:
                pass
            self._temp_path = None
            raise
        env["RSF_METADATA_FILE"] = path
        return []

    def cleanup(self) -> None:
        """Remove the temp file. Safe to call multiple times."""
        if self._temp_path is not None:
            try:
                os.unlink(self._temp_path)
            except OSError:
                pass
            self._temp_path = None


class EnvTransport(MetadataTransport):
    """Deliver metadata via environment variables.

    Sets RSF_WORKFLOW_NAME, RSF_STAGE, and RSF_METADATA_JSON.
    """

    def prepare(self, metadata: WorkflowMetadata, env: dict[str, str]) -> list[str]:
        """Set RSF_* environment variables in the env dict."""
        env["RSF_WORKFLOW_NAME"] = metadata.workflow_name
        env["RSF_STAGE"] = metadata.stage or ""
        env["RSF_METADATA_JSON"] = json.dumps(asdict(metadata), default=str)
        return []

    def cleanup(self) -> None:
        """No-op: env vars are scoped to subprocess, no cleanup needed."""
        pass


# Valid placeholders for CLI arg templates: WorkflowMetadata field names + metadata_file
_VALID_PLACEHOLDERS: set[str] = set(WorkflowMetadata.__dataclass_fields__.keys()) | {"metadata_file"}


class ArgsTransport(MetadataTransport):
    """Deliver metadata via CLI arg templates with {placeholder} substitution.

    Templates use Python ``str.format()`` style: ``{workflow_name}``,
    ``{stage}``, ``{metadata_file}``, etc.

    Only WorkflowMetadata field names and ``metadata_file`` are valid
    placeholders. Invalid placeholders raise ValueError at construction time.
    """

    def __init__(self, arg_templates: list[str]) -> None:
        self._templates = arg_templates
        self._validate_templates()

    def _validate_templates(self) -> None:
        """Validate all templates use only valid placeholder names."""
        formatter = string.Formatter()
        for template in self._templates:
            for _, field_name, _, _ in formatter.parse(template):
                if field_name is None:
                    continue
                # Reject attribute access and indexing (security)
                if "." in field_name or "[" in field_name:
                    raise ValueError(
                        f"Invalid placeholder '{{{field_name}}}' in CLI arg template. "
                        f"Attribute access and indexing are not allowed."
                    )
                if field_name not in _VALID_PLACEHOLDERS:
                    raise ValueError(
                        f"Invalid placeholder '{{{field_name}}}' in CLI arg template. "
                        f"Valid placeholders: {sorted(_VALID_PLACEHOLDERS)}"
                    )

    def prepare(self, metadata: WorkflowMetadata, env: dict[str, str]) -> list[str]:
        """Substitute placeholders in templates and return as CLI args."""
        values = {
            **asdict(metadata),
            "metadata_file": env.get("RSF_METADATA_FILE", ""),
        }
        args: list[str] = []
        for template in self._templates:
            formatted = template.format(**values)
            args.extend(formatted.split())
        return args

    def cleanup(self) -> None:
        """No-op: no resources to clean up."""
        pass
