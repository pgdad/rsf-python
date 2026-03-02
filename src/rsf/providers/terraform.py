"""TerraformProvider -- wraps existing generator.py and terraform CLI.

Implements the InfrastructureProvider interface for HashiCorp Terraform.
Zero behavior change from the pre-refactor deploy_cmd: same TerraformConfig
construction, same generate_terraform() call, same terraform init/apply flow.
"""

from __future__ import annotations

import shutil

from rsf.providers.base import InfrastructureProvider, PrerequisiteCheck, ProviderContext
from rsf.terraform.generator import TerraformConfig, generate_terraform


class TerraformProvider(InfrastructureProvider):
    """Infrastructure provider for HashiCorp Terraform.

    Wraps the existing ``generate_terraform()`` flow and ``terraform`` CLI
    invocations. Zero behavior change from the pre-refactor ``deploy_cmd``.

    Lifecycle:
        validate_config -> check_prerequisites -> generate -> deploy
    Teardown:
        teardown (separate lifecycle)
    """

    def generate(self, ctx: ProviderContext) -> None:
        """Generate Terraform HCL files via Jinja2 templates.

        Converts WorkflowMetadata into TerraformConfig and delegates
        to the existing ``generate_terraform()`` function.
        """
        config = self._build_config(ctx)
        generate_terraform(config=config, output_dir=ctx.output_dir)

    def deploy(self, ctx: ProviderContext) -> None:
        """Run ``terraform init`` then ``terraform apply``.

        Respects auto_approve and stage_var_file from ProviderContext.
        """
        self.run_provider_command(["terraform", "init"], cwd=ctx.output_dir)

        apply_cmd = ["terraform", "apply"]
        if ctx.stage_var_file is not None:
            apply_cmd.extend(["-var-file", str(ctx.stage_var_file)])
        if ctx.auto_approve:
            apply_cmd.append("-auto-approve")
        self.run_provider_command(apply_cmd, cwd=ctx.output_dir)

    def teardown(self, ctx: ProviderContext) -> None:
        """Run ``terraform destroy -auto-approve``."""
        self.run_provider_command(
            ["terraform", "destroy", "-auto-approve"],
            cwd=ctx.output_dir,
        )

    def check_prerequisites(self, ctx: ProviderContext) -> list[PrerequisiteCheck]:
        """Check that the ``terraform`` binary is available on PATH."""
        if shutil.which("terraform"):
            return [PrerequisiteCheck("terraform", "pass", "terraform binary found")]
        return [
            PrerequisiteCheck(
                "terraform",
                "warn",
                "terraform binary not found. Install from https://terraform.io",
            )
        ]

    def validate_config(self, ctx: ProviderContext) -> None:
        """Validate Terraform provider configuration.

        Currently a no-op: Pydantic models (TerraformProviderConfig)
        handle config validation at parse time.
        """
        pass

    def _build_config(self, ctx: ProviderContext) -> TerraformConfig:
        """Convert ProviderContext metadata to TerraformConfig.

        Maps all WorkflowMetadata fields to their TerraformConfig equivalents.
        Derives boolean flags (has_sqs_triggers, has_dynamodb_tables, etc.)
        from the list contents.
        """
        md = ctx.metadata
        return TerraformConfig(
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
            stage=ctx.stage,
        )
