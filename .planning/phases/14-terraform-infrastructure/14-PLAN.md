# Phase 14: Terraform Infrastructure — Plan

## Objective
Generate per-example Terraform directories with isolated local state, durable_config with retention_period=1, pinned AWS provider, and DynamoDB resources for data-pipeline and order-processing.

## Success Criteria
1. `terraform plan` succeeds inside each example's `terraform/` directory
2. Each example has its own `terraform.tfstate` — no shared state
3. Every Lambda has `durable_config { retention_period = 1 }` and `runtime = "python3.13"`
4. data-pipeline and order-processing include DynamoDB table resources + IAM policies

## Plan

### Step 1: Generate base Terraform files (all 5 examples)
Use RSF `generate_terraform()` API to create 6 HCL files per example:
- main.tf, variables.tf, iam.tf, outputs.tf, cloudwatch.tf, backend.tf

### Step 2: Create src/ packaging structure
Each example needs `src/` dir so `archive_file` data source can find source code:
- `src/generated/orchestrator.py` — generated via RSF codegen
- `src/handlers/` — copy of example handlers

### Step 3: Add versions.tf with provider pinning
Each example gets:
```hcl
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws     = { source = "hashicorp/aws", version = ">= 6.25.0" }
    archive = { source = "hashicorp/archive", version = ">= 2.0" }
  }
}
provider "aws" { region = var.aws_region }
```

### Step 4: Add terraform.tfvars
Each example gets:
```hcl
retention_period = 1
aws_region       = "us-east-2"
```

### Step 5: Add DynamoDB resources (data-pipeline & order-processing)
- `dynamodb.tf` — DynamoDB table definition (PAY_PER_REQUEST)
- Extended IAM policy with DynamoDB actions

### Step 6: Verify
- `terraform init && terraform plan` for all 5 examples
- Run existing test suite

## Examples
1. order-processing — DynamoDB: `order-history` table
2. data-pipeline — DynamoDB: `pipeline-results` table
3. approval-workflow — no DynamoDB
4. retry-and-recovery — no DynamoDB
5. intrinsic-showcase — no DynamoDB
