"""CDKProvider -- AWS CDK infrastructure provider for RSF.

Implements the InfrastructureProvider interface for AWS CDK.
Generates a Python CDK app from Jinja2 templates and invokes
CDK CLI via ``npx aws-cdk@latest`` (no global install needed).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from rsf.cdk.generator import CDKConfig, generate_cdk
from rsf.providers.base import InfrastructureProvider, PrerequisiteCheck, ProviderContext

logger = logging.getLogger(__name__)


class CDKProvider(InfrastructureProvider):
    """Infrastructure provider for AWS CDK.

    Generates a Python CDK app from Jinja2 templates and deploys
    via ``npx aws-cdk@latest``. Streams deploy output in real-time.

    Lifecycle:
        validate_config -> check_prerequisites -> generate -> deploy
    Teardown:
        teardown (separate lifecycle)
    """

    CDK_CMD: list[str] = ["npx", "aws-cdk@latest"]

    def generate(self, ctx: ProviderContext) -> None:
        """Generate CDK Python app from Jinja2 templates.

        Converts WorkflowMetadata into CDKConfig and delegates
        to the CDK generator.
        """
        config = self._build_config(ctx)
        generate_cdk(config=config, output_dir=ctx.output_dir)

    def deploy(self, ctx: ProviderContext) -> None:
        """Run ``cdk deploy`` with streaming output.

        Checks CDK bootstrap status first, then invokes
        ``npx aws-cdk@latest deploy`` with real-time stdout/stderr.
        """
        self._check_bootstrap_or_warn(ctx)

        cmd = list(self.CDK_CMD) + [
            "deploy",
            "--app",
            "python3 app.py",
            "--output",
            "cdk.out",
        ]
        if ctx.auto_approve:
            cmd.extend(["--require-approval", "never"])
        if ctx.stage:
            cmd.extend(["-c", f"stage={ctx.stage}"])

        self.run_provider_command_streaming(cmd, cwd=ctx.output_dir)

    def teardown(self, ctx: ProviderContext) -> None:
        """Run ``cdk destroy --force``."""
        cmd = list(self.CDK_CMD) + [
            "destroy",
            "--app",
            "python3 app.py",
            "--force",
        ]
        if ctx.stage:
            cmd.extend(["-c", f"stage={ctx.stage}"])

        self.run_provider_command_streaming(cmd, cwd=ctx.output_dir)

    def check_prerequisites(self, ctx: ProviderContext) -> list[PrerequisiteCheck]:
        """Check for Node.js/npx (required) and CDK CLI (optional).

        npx is REQUIRED (FAIL if missing) because CDK cannot run without it.
        cdk global binary is optional (WARN if missing) per success criteria #4.
        """
        checks: list[PrerequisiteCheck] = []

        if shutil.which("npx"):
            checks.append(
                PrerequisiteCheck("node/npx", "pass", "npx found")
            )
        else:
            checks.append(
                PrerequisiteCheck(
                    "node/npx",
                    "fail",
                    "npx not found. Install Node.js from https://nodejs.org/",
                )
            )

        if shutil.which("cdk"):
            checks.append(
                PrerequisiteCheck("cdk", "pass", "cdk binary found")
            )
        else:
            checks.append(
                PrerequisiteCheck(
                    "cdk",
                    "warn",
                    "cdk binary not found. Install with: npm install -g aws-cdk",
                )
            )

        return checks

    def validate_config(self, ctx: ProviderContext) -> None:
        """Validate CDK provider configuration.

        Currently a no-op: Pydantic models handle config validation
        at parse time.
        """
        pass

    def run_provider_command_streaming(
        self,
        cmd: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run a command with real-time stdout/stderr output.

        Unlike ``run_provider_command`` (which captures output), this
        method lets stdout/stderr stream directly to the terminal so
        users see CDK stack events as they happen.

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

    def _build_config(self, ctx: ProviderContext) -> CDKConfig:
        """Convert ProviderContext metadata to CDKConfig.

        Maps all WorkflowMetadata fields to their CDKConfig equivalents.
        """
        md = ctx.metadata
        return CDKConfig(
            workflow_name=md.workflow_name,
            triggers=md.triggers,
            has_sqs_triggers=any(t.get("type") == "sqs" for t in md.triggers),
            dynamodb_tables=md.dynamodb_tables,
            has_dynamodb_tables=bool(md.dynamodb_tables),
            alarms=md.alarms,
            has_alarms=bool(md.alarms),
            dlq_enabled=md.dlq_enabled,
            dlq_max_receive_count=md.dlq_max_receive_count,
            dlq_queue_name=md.dlq_queue_name,
            lambda_url_enabled=md.lambda_url_enabled,
            lambda_url_auth_type=md.lambda_url_auth_type,
            timeout_seconds=md.timeout_seconds,
            stage=ctx.stage,
        )

    def _check_bootstrap_or_warn(self, ctx: ProviderContext) -> None:
        """Check for CDKToolkit CloudFormation stack.

        If the bootstrap stack is missing, raises SystemExit with a
        clear message showing the exact ``cdk bootstrap`` command.
        """
        try:
            cf = boto3.client("cloudformation")
            cf.describe_stacks(StackName="CDKToolkit")
        except ClientError as e:
            if "does not exist" in str(e):
                account, region = self._get_account_and_region()
                raise SystemExit(
                    f"CDK bootstrap stack (CDKToolkit) not found.\n"
                    f"Run: cdk bootstrap aws://{account}/{region}\n"
                    f"This creates the staging resources CDK needs to deploy."
                ) from e
            raise

    def _get_account_and_region(self) -> tuple[str, str]:
        """Get AWS account ID and region for bootstrap command message.

        Returns:
            Tuple of (account_id, region). Uses "UNKNOWN" placeholders
            if AWS API calls fail.
        """
        try:
            session = boto3.Session()
            sts = session.client("sts")
            account = sts.get_caller_identity()["Account"]
            region = session.region_name or "us-east-1"
            return account, region
        except Exception:
            return "UNKNOWN", "UNKNOWN"
