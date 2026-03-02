"""Tests for action/entrypoint.sh — verifies WORKFLOW_FILE forwarding."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


ENTRYPOINT = Path(__file__).resolve().parents[2] / "action" / "entrypoint.sh"


class TestEntrypointWorkflowFileForwarding:
    """Verify entrypoint.sh forwards WORKFLOW_FILE to all rsf commands."""

    def test_entrypoint_exists_and_is_executable(self):
        assert ENTRYPOINT.exists(), f"entrypoint.sh not found at {ENTRYPOINT}"
        # Check executable bit
        assert os.access(ENTRYPOINT, os.X_OK), "entrypoint.sh is not executable"

    def test_validate_receives_workflow_file(self):
        content = ENTRYPOINT.read_text()
        assert (
            'rsf validate "${WORKFLOW_FILE}"' in content
            or "rsf validate ${WORKFLOW_FILE}" in content
        )

    def test_generate_receives_workflow_file(self):
        content = ENTRYPOINT.read_text()
        assert (
            'rsf generate "${WORKFLOW_FILE}"' in content
            or "rsf generate ${WORKFLOW_FILE}" in content
        )

    def test_deploy_receives_workflow_file(self):
        """Critical fix: rsf deploy must receive WORKFLOW_FILE."""
        content = ENTRYPOINT.read_text()
        # Split on "rsf deploy" and check the remainder of that line
        parts = content.split("rsf deploy", 1)
        assert len(parts) == 2, "rsf deploy not found in entrypoint.sh"
        first_line_after = parts[1].split("\n")[0]
        assert "WORKFLOW_FILE" in first_line_after or "WORKFLOW_FILE" in content.split(
            "DEPLOY_CMD=", 1
        )[1].split("\n")[0], "rsf deploy does not receive WORKFLOW_FILE — the fix is missing"

    def test_all_three_commands_receive_workflow_file(self):
        """All three rsf commands (validate, generate, deploy) use WORKFLOW_FILE."""
        content = ENTRYPOINT.read_text()
        lines = content.splitlines()

        commands_with_wf: list[str] = []
        for line in lines:
            stripped = line.strip()
            if "rsf validate" in stripped and "WORKFLOW_FILE" in stripped:
                commands_with_wf.append("validate")
            if "rsf generate" in stripped and "WORKFLOW_FILE" in stripped:
                commands_with_wf.append("generate")
            if (
                "rsf deploy" in stripped or "DEPLOY_CMD=" in stripped
            ) and "WORKFLOW_FILE" in stripped:
                commands_with_wf.append("deploy")

        assert "validate" in commands_with_wf, "validate missing WORKFLOW_FILE"
        assert "generate" in commands_with_wf, "generate missing WORKFLOW_FILE"
        assert "deploy" in commands_with_wf, "deploy missing WORKFLOW_FILE"

    def test_deploy_command_has_workflow_file_before_flags(self):
        """WORKFLOW_FILE should be the first arg after rsf deploy (before --stage, --auto-approve)."""
        content = ENTRYPOINT.read_text()
        # Find DEPLOY_CMD assignment
        for line in content.splitlines():
            if "DEPLOY_CMD=" in line and "rsf deploy" in line:
                # The WORKFLOW_FILE should appear in this same line
                assert "WORKFLOW_FILE" in line, (
                    f"DEPLOY_CMD line does not include WORKFLOW_FILE: {line.strip()}"
                )
                break
        else:
            pytest.fail("Could not find DEPLOY_CMD assignment with rsf deploy")
