"""CustomProvider -- user-configurable external program infrastructure provider.

Implements the InfrastructureProvider interface for arbitrary external
programs. The program receives workflow metadata via the user's chosen
transport mechanism (JSON file, env vars, or CLI arg templates).

Security: Always uses ``shell=False``. Program path must be absolute
and executable. No string interpolation into shell commands.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from rsf.dsl.models import CustomProviderConfig
from rsf.providers.base import InfrastructureProvider, PrerequisiteCheck, ProviderContext
from rsf.providers.transports import (
    ArgsTransport,
    EnvTransport,
    FileTransport,
    MetadataTransport,
)

logger = logging.getLogger(__name__)


class CustomProvider(InfrastructureProvider):
    """Infrastructure provider for user-configured external programs.

    Invokes the configured program with the selected metadata transport.
    Supports three transport mechanisms: JSON file, environment variables,
    and CLI arg templates with placeholder substitution.

    Security hardening:
        - Always uses ``shell=False`` (via ``run_provider_command_streaming``)
        - Program path validated as absolute and executable before invocation
        - No string interpolation into shell commands
        - Placeholder substitution only via ``ArgsTransport`` with validated names

    Lifecycle:
        validate_config -> check_prerequisites -> generate (no-op) -> deploy
    Teardown:
        teardown (requires ``teardown_args`` in config)
    """

    def generate(self, ctx: ProviderContext) -> None:
        """No-op. Custom providers don't generate infrastructure code."""
        logger.debug("Custom provider: generate is a no-op")

    def deploy(self, ctx: ProviderContext) -> None:
        """Invoke the configured program with metadata transport.

        1. Reads ``CustomProviderConfig`` from the workflow definition
        2. Validates program path (absolute, exists, executable)
        3. Creates the selected ``MetadataTransport``
        4. Prepares transport (writes temp files, sets env vars)
        5. Builds command: ``[program] + args + transport_extra_args``
        6. Invokes via streaming subprocess (``shell=False``)
        7. Cleans up transport resources in ``finally`` block

        Raises:
            ValueError: If program path is not absolute.
            FileNotFoundError: If program does not exist.
            PermissionError: If program is not executable.
            subprocess.CalledProcessError: If program exits non-zero.
        """
        config = self._get_config(ctx)
        program = self._validate_program(config.program)
        transport = self._create_transport(config)

        env: dict[str, str] = {}
        if config.env:
            env.update(config.env)

        try:
            extra_args = transport.prepare(ctx.metadata, env)
            cmd = [str(program)] + list(config.args) + extra_args
            self.run_provider_command_streaming(cmd, cwd=ctx.workflow_path.parent, env=env)
        finally:
            transport.cleanup()

    def teardown(self, ctx: ProviderContext) -> None:
        """Invoke the configured program with teardown args.

        Uses ``teardown_args`` from config instead of ``args``.
        If ``teardown_args`` is not configured, raises ``NotImplementedError``.

        Raises:
            NotImplementedError: If ``teardown_args`` is not configured.
            ValueError: If program path is not absolute.
            FileNotFoundError: If program does not exist.
            PermissionError: If program is not executable.
            subprocess.CalledProcessError: If program exits non-zero.
        """
        config = self._get_config(ctx)

        if config.teardown_args is None:
            raise NotImplementedError(
                "Custom provider teardown not configured. "
                "Set 'teardown_args' in the custom provider config to enable teardown."
            )

        program = self._validate_program(config.program)
        transport = self._create_transport(config)

        env: dict[str, str] = {}
        if config.env:
            env.update(config.env)

        try:
            extra_args = transport.prepare(ctx.metadata, env)
            cmd = [str(program)] + list(config.teardown_args) + extra_args
            self.run_provider_command_streaming(cmd, cwd=ctx.workflow_path.parent, env=env)
        finally:
            transport.cleanup()

    def check_prerequisites(self, ctx: ProviderContext) -> list[PrerequisiteCheck]:
        """Check that the custom program exists and is executable.

        Returns:
            List of PrerequisiteCheck results for program existence
            and executable permission.
        """
        config = self._get_config(ctx)
        checks: list[PrerequisiteCheck] = []

        program_path = Path(config.program)
        if program_path.exists():
            checks.append(
                PrerequisiteCheck(
                    "custom-program",
                    "pass",
                    f"custom program found: {config.program}",
                )
            )
            if os.access(config.program, os.X_OK):
                checks.append(
                    PrerequisiteCheck(
                        "custom-program-executable",
                        "pass",
                        "custom program is executable",
                    )
                )
            else:
                checks.append(
                    PrerequisiteCheck(
                        "custom-program-executable",
                        "fail",
                        f"custom program is not executable: {config.program}. Fix: chmod +x {config.program}",
                    )
                )
        else:
            checks.append(
                PrerequisiteCheck(
                    "custom-program",
                    "fail",
                    f"custom program not found: {config.program}",
                )
            )

        return checks

    def validate_config(self, ctx: ProviderContext) -> None:
        """Validate custom provider configuration.

        Checks:
            1. Program path is absolute
            2. Arg templates have valid placeholders (if args transport)
            3. Teardown arg templates have valid placeholders (if args transport)

        Raises:
            ValueError: If program path is not absolute or templates are invalid.
        """
        config = self._get_config(ctx)

        if not Path(config.program).is_absolute():
            raise ValueError(f"Custom provider program must be an absolute path, got: {config.program}")

        # Validate arg templates if using args transport
        if config.metadata_transport == "args":
            ArgsTransport(config.args)  # Raises ValueError on invalid placeholders

            if config.teardown_args is not None:
                ArgsTransport(config.teardown_args)  # Validate teardown templates too

    def run_provider_command_streaming(
        self,
        cmd: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run a command with real-time stdout/stderr output.

        Unlike ``run_provider_command`` (which captures output), this
        method lets stdout/stderr stream directly to the terminal so
        users see custom program output as it happens.

        Args:
            cmd: Command and arguments as a list.
            cwd: Working directory for the command.
            env: Extra environment variables (merged with os.environ).

        Returns:
            CompletedProcess (no captured output).

        Raises:
            subprocess.CalledProcessError: On non-zero exit code.
        """
        logger.info("Running (streaming): %s", " ".join(cmd))
        merged_env = {**os.environ, **(env or {})}
        return subprocess.run(
            cmd,
            cwd=cwd,
            env=merged_env,
            check=True,
            text=True,
            shell=False,
        )

    def _get_config(self, ctx: ProviderContext) -> CustomProviderConfig:
        """Extract CustomProviderConfig from ProviderContext.

        Reads from ``ctx.definition.infrastructure.custom``.

        Args:
            ctx: Provider context with workflow definition.

        Returns:
            The custom provider configuration.

        Raises:
            ValueError: If definition or custom config is missing.
        """
        if ctx.definition is None or not hasattr(ctx.definition, "infrastructure"):
            raise ValueError(
                "CustomProvider requires workflow definition in ProviderContext. "
                "Ensure 'definition' is passed to ProviderContext."
            )

        if ctx.definition.infrastructure is None or ctx.definition.infrastructure.custom is None:
            raise ValueError(
                "CustomProvider requires 'custom' block in infrastructure config. "
                "Add 'custom:' with 'program:' to your workflow YAML."
            )

        return ctx.definition.infrastructure.custom

    def _validate_program(self, program: str) -> Path:
        """Validate program path: absolute, exists, executable.

        Args:
            program: Path string to the external program.

        Returns:
            Validated Path object.

        Raises:
            ValueError: If path is not absolute.
            FileNotFoundError: If program does not exist.
            PermissionError: If program is not executable.
        """
        path = Path(program)

        if not path.is_absolute():
            raise ValueError(f"Custom provider program must be an absolute path, got: {program}")

        if not path.exists():
            raise FileNotFoundError(f"Custom provider program not found: {program}")

        if not os.access(path, os.X_OK):
            raise PermissionError(f"Custom provider program is not executable: {program}\nFix: chmod +x {program}")

        return path

    def _create_transport(self, config: CustomProviderConfig) -> MetadataTransport:
        """Create the appropriate MetadataTransport from config.

        Args:
            config: Custom provider configuration with transport selection.

        Returns:
            MetadataTransport instance (FileTransport, EnvTransport, or ArgsTransport).

        Raises:
            ValueError: If transport type is unknown.
        """
        if config.metadata_transport == "file":
            return FileTransport()
        if config.metadata_transport == "env":
            return EnvTransport()
        if config.metadata_transport == "args":
            return ArgsTransport(config.args)
        raise ValueError(f"Unknown metadata_transport: {config.metadata_transport}")
