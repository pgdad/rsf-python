"""Terraform generation package."""

from rsf.terraform.generator import (
    GENERATED_MARKER,
    TerraformConfig,
    TerraformResult,
    derive_iam_statements,
    generate_terraform,
    sanitize_name,
)

__all__ = [
    "GENERATED_MARKER",
    "TerraformConfig",
    "TerraformResult",
    "derive_iam_statements",
    "generate_terraform",
    "sanitize_name",
]
