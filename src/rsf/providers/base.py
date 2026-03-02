"""Provider base classes: ABC, context, and prerequisite check types."""

from __future__ import annotations

import logging
import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)


@dataclass
class PrerequisiteCheck:
    """Result of a single provider prerequisite check.

    Returned by InfrastructureProvider.check_prerequisites().
    Compatible with doctor_cmd.CheckResult display pattern.
    """

    name: str
    status: Literal["pass", "warn", "fail"]
    message: str


@dataclass
class ProviderContext:
    """Context passed to all provider lifecycle methods.

    Single-argument pattern: all methods receive one ProviderContext
    instead of multiple parameters, making the interface extensible.
    """

    metadata: Any  # WorkflowMetadata (Any to avoid circular import)
    output_dir: Path
    stage: str | None
    workflow_path: Path
    definition: Any = None  # StateMachineDefinition, optional


class InfrastructureProvider(ABC):
    """Abstract base class for infrastructure providers.

    All downstream providers (Terraform, CDK, Custom) implement this
    interface. The ABC enforces all abstract methods at instantiation
    time via TypeError.

    Lifecycle: validate_config -> check_prerequisites -> generate -> deploy
    Teardown: teardown (separate lifecycle)
    """

    @abstractmethod
    def generate(self, ctx: ProviderContext) -> None:
        """Generate infrastructure code/templates.

        For Terraform: generate .tf files via Jinja2 templates.
        For CDK: generate Python CDK app (app.py, stack.py, cdk.json).
        For Custom: may be a no-op if provider doesn't generate code.
        """
        ...

    @abstractmethod
    def deploy(self, ctx: ProviderContext) -> None:
        """Deploy infrastructure using the generated code.

        For Terraform: terraform init + terraform apply.
        For CDK: cdk deploy.
        For Custom: invoke configured program with metadata transport.
        """
        ...

    @abstractmethod
    def teardown(self, ctx: ProviderContext) -> None:
        """Tear down deployed infrastructure.

        For Terraform: terraform destroy.
        For CDK: cdk destroy.
        For Custom: invoke configured teardown program.
        """
        ...

    @abstractmethod
    def check_prerequisites(self, ctx: ProviderContext) -> list[PrerequisiteCheck]:
        """Check that all prerequisites are met for this provider.

        Returns a list of checks with pass/warn/fail status.
        Feeds into `rsf doctor` multi-check display.
        """
        ...

    @abstractmethod
    def validate_config(self, ctx: ProviderContext) -> None:
        """Validate provider configuration.

        Raises ValueError if configuration is invalid.
        Called at `rsf validate` time, not deploy time.
        """
        ...

    def run_provider_command(
        self,
        cmd: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Shared subprocess runner for provider commands.

        Always uses shell=False for security. Merges provided env with
        os.environ. Raises subprocess.CalledProcessError on non-zero exit.

        Args:
            cmd: Command and arguments as a list (no shell expansion).
            cwd: Working directory for the command.
            env: Extra environment variables (merged with os.environ).

        Returns:
            CompletedProcess with stdout/stderr captured as text.
        """
        logger.info("Running: %s", " ".join(cmd))
        merged_env = {**os.environ, **(env or {})}
        return subprocess.run(
            cmd,
            cwd=cwd,
            env=merged_env,
            check=True,
            capture_output=True,
            text=True,
            shell=False,
        )
