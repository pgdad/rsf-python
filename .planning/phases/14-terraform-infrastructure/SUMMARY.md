# Phase 14: Terraform Infrastructure — Summary

## What was delivered
Per-example Terraform directories for all 5 RSF examples with:
- 6 generated HCL files each (main.tf, variables.tf, iam.tf, outputs.tf, cloudwatch.tf, backend.tf)
- versions.tf with AWS provider >= 6.25.0 and archive provider >= 2.0 pinning
- terraform.tfvars with retention_period=1 and aws_region=us-east-2
- src/ packaging structure with generated orchestrator and handler copies
- DynamoDB table resources + IAM policies for data-pipeline and order-processing

## Files created/modified

### Per example (×5):
- `examples/<name>/terraform/` — 8-9 HCL files (6 generated + versions.tf + terraform.tfvars + dynamodb.tf where applicable)
- `examples/<name>/src/generated/orchestrator.py` — Generated orchestrator code
- `examples/<name>/src/handlers/` — Copy of handler code for Lambda packaging

### DynamoDB examples:
- `examples/data-pipeline/terraform/dynamodb.tf` — pipeline-results table + IAM
- `examples/order-processing/terraform/dynamodb.tf` — order-history table + IAM

### Template fix:
- `src/rsf/terraform/templates/main.tf.j2` — Fixed lifecycle ignore_changes from `[last_modified]` to `[filename, source_code_hash]` (last_modified was a provider-computed attribute, causing Terraform warnings)

### Other:
- `.gitignore` — Added Terraform runtime patterns (.terraform/, *.tfstate, *.zip)

## Verification
- `terraform validate` passes for all 5 examples
- `terraform plan` requires active AWS credentials (ADFS session expired) — configuration validated structurally
- 572 core tests pass, 152 example tests pass (no regressions)

## Success criteria status
1. ✓ terraform init + validate succeeds for all 5 examples (plan needs active AWS creds)
2. ✓ Each example has isolated local state (separate terraform/ directories)
3. ✓ Every Lambda has durable_config { retention_period = 1 } and runtime = "python3.13"
4. ✓ data-pipeline and order-processing include DynamoDB resources + IAM policies
