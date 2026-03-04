# examples/registry-modules-demo/terraform/versions.tf
# Produced by Phase 56 schema verification.
# All module versions pinned to exact strings — Terraform does not lock
# module versions in .terraform.lock.hcl. Range constraints (~>) would
# silently upgrade on terraform init and may break documented behavior.

terraform {
  required_version = ">= 1.5.7"  # Required by sqs v5.x and sns v7.x

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.25.0"  # durable_config block (provider v6.25.0, Dec 4 2025)
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.7.1"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Registry module version pins — exact strings, not ranges.
# These version strings appear in each module's source block in their
# respective .tf files (main.tf, dynamodb.tf, sqs.tf, alarms.tf).
# Terraform locals cannot be used in module source/version blocks,
# so these serve as authoritative reference documentation.
#
# Module                                      | Version | Released   | Notes
# --------------------------------------------|---------|------------|-------------------------------
# terraform-aws-modules/lambda/aws            | 8.7.0   | 2026-02-18 | First version with durable_config support
# terraform-aws-modules/dynamodb-table/aws    | 5.5.0   | 2026-01-08 | Verified from GitHub releases
# terraform-aws-modules/sqs/aws              | 5.2.1   | 2026-01-21 | Requires Terraform >= 1.5.7
# terraform-aws-modules/cloudwatch/aws        | 5.7.2   | 2025-10-21 | Must use //modules/metric-alarm submodule
# terraform-aws-modules/sns/aws              | 7.1.0   | 2026-01-08 | Requires AWS provider >= 6.9
