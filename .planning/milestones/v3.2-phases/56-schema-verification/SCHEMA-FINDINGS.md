# Schema Verification Findings — Phase 56

**Verified:** 2026-03-04
**Confidence:** HIGH (all critical findings from live GitHub source and official AWS docs)
**Consumed by:** Phases 57-60 (do not modify without re-verification)

---

## Section 1: durable_config Variable Names (Confirmed)

**Source:** `https://raw.githubusercontent.com/terraform-aws-modules/terraform-aws-lambda/v8.7.0/variables.tf`

### Exact variable names (confirmed from live v8.7.0 tag)

- `durable_config_execution_timeout` — type: number, default: null
- `durable_config_retention_period` — type: number, default: null

### Activation gate

The module uses a dynamic block gated on `var.durable_config_execution_timeout != null`. Setting this variable to null (or omitting it) silently produces a non-durable Lambda function — no error is raised.

### Module usage (HCL)

```hcl
module "lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.7.0"

  durable_config_execution_timeout = 86400  # MUST be non-null
  durable_config_retention_period  = 14     # days, optional
}
```

### CRITICAL WARNING

Always use `coalesce(var.execution_timeout, 86400)` to prevent null propagation from WorkflowMetadata:

```hcl
durable_config_execution_timeout = coalesce(var.execution_timeout, 86400)
```

If `var.execution_timeout` is null (WorkflowMetadata default), the above safely falls back to 86400 seconds (24 hours). Without `coalesce`, the entire `durable_config` block is silently dropped.

### Dynamic block implementation (from v8.7.0 main.tf)

```hcl
dynamic "durable_config" {
  for_each = var.durable_config_execution_timeout != null ? [true] : []
  content {
    execution_timeout = var.durable_config_execution_timeout
    retention_period  = var.durable_config_retention_period
  }
}
```

---

## Section 2: Lambda Alias Convention

**Source:** `https://docs.aws.amazon.com/lambda/latest/dg/durable-getting-started-iac.html`
**Rationale:** Terraform provider issue #45800 (AllowInvokeLatest still open as of Jan 7, 2026)

### Convention

Always create a Lambda alias named `"live"` and invoke via alias ARN. Never use `$LATEST` or an unqualified ARN.

### Why

Terraform AWS provider issue #45800 (AllowInvokeLatest) is still open. The AWS SDK for Go v2 has not implemented `AllowInvokeLatest`. Without this field being settable, invoking a durable function via `$LATEST` or unqualified ARN may fail silently or raise a ResourceConflictException.

### Alias HCL pattern

```hcl
resource "aws_lambda_alias" "live" {
  name             = "live"
  function_name    = module.lambda.lambda_function_name
  function_version = module.lambda.lambda_function_version
}

output "alias_arn" {
  description = "Use this ARN for all durable function invocations (never $LATEST)"
  value       = aws_lambda_alias.live.arn
}
```

### Future update note

If issue #45800 is resolved before tutorial publication, `AllowInvokeLatest = true` can be added to the `durable_config` block to enable `$LATEST` invocations. Until then, the alias convention is mandatory.

---

## Section 3: IAM Approach Decision

**Decision: Managed policy + inline supplement (hybrid approach)**

### Managed policy

`AWSLambdaBasicDurableExecutionRolePolicy` (official AWS-recommended managed policy for Lambda Durable Functions)

**Source:** `https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AWSLambdaBasicDurableExecutionRolePolicy.html` (policy v3, Feb 12, 2026)

Covers:
- `lambda:CheckpointDurableExecution`
- `lambda:GetDurableExecutionState`
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

### Inline supplement

Covers operations NOT in the managed policy:
- `lambda:InvokeFunction` (self-invoke — RSF orchestration pattern)
- `lambda:ListDurableExecutionsByFunction` (RSF durable runtime)
- `lambda:GetDurableExecution` (user-facing describe API; different from `GetDurableExecutionState` which is the replay-state API)

### Action name mapping table

| Source | Action | Managed Policy | RSF Inline (existing) | Tutorial IAM |
|--------|--------|----------------|-----------------------|--------------|
| AWS managed policy | `lambda:CheckpointDurableExecution` | YES | YES | via managed policy |
| AWS managed policy | `lambda:GetDurableExecutionState` | YES | NO | via managed policy |
| RSF existing | `lambda:GetDurableExecution` | NO | YES | via inline supplement |
| RSF existing | `lambda:ListDurableExecutionsByFunction` | NO | YES | via inline supplement |
| RSF existing | `lambda:InvokeFunction` | NO | YES | via inline supplement |
| AWS managed policy | `logs:CreateLogGroup/Stream/PutLogEvents` | YES | YES | via managed policy (module handles via `attach_cloudwatch_logs_policy`) |

### Module attachment pattern

```hcl
module "lambda" {
  # ...
  attach_policies    = true
  number_of_policies = 1
  policies = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicDurableExecutionRolePolicy"
  ]
  attach_policy_json = true
  policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "DurableSelfInvokeAndList"
      Effect = "Allow"
      Action = [
        "lambda:InvokeFunction",
        "lambda:ListDurableExecutionsByFunction",
        "lambda:GetDurableExecution"
      ]
      Resource = "*"
    }]
  })
}
```

### WARNINGS

1. **Setting `policies = [...]` without `attach_policies = true` silently attaches nothing.** The module gates policy attachment on `attach_policies = true AND number_of_policies > 0`. Always set all three: `attach_policies`, `number_of_policies`, and `policies`.

2. **Regional availability of `AWSLambdaBasicDurableExecutionRolePolicy` must be verified in Phase 57** with:
   ```bash
   aws iam get-policy --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicDurableExecutionRolePolicy
   ```

3. **Fallback:** If the managed policy is unavailable in us-east-2, use an all-inline policy matching RSF's existing `iam.tf.j2` approach, adding `GetDurableExecutionState` to cover both API paths.

---

## Section 4: Registry Module Version Pins

All versions pinned to exact strings. Terraform does not include module versions in `.terraform.lock.hcl` — range constraints (`~>`) would silently upgrade on `terraform init` and may break documented behavior.

| Module | Exact Version | Released | Purpose | Notes |
|--------|---------------|----------|---------|-------|
| terraform-aws-modules/lambda/aws | 8.7.0 | 2026-02-18 | Lambda function + IAM role + CloudWatch log group | First version with native durable_config support |
| terraform-aws-modules/dynamodb-table/aws | 5.5.0 | 2026-01-08 | DynamoDB table per WorkflowMetadata.dynamodb_tables | Verified from GitHub releases |
| terraform-aws-modules/sqs/aws | 5.2.1 | 2026-01-21 | SQS DLQ for dlq_enabled workflows | Requires Terraform >= 1.5.7 |
| terraform-aws-modules/cloudwatch/aws | 5.7.2 | 2025-10-21 | CloudWatch metric alarms | Must use `//modules/metric-alarm` submodule path |
| terraform-aws-modules/sns/aws | 7.1.0 | 2026-01-08 | SNS topic for alarm notifications | Requires AWS provider >= 6.9 (satisfied by >= 6.25.0) |

### Rationale for exact pins

Terraform's `.terraform.lock.hcl` only locks provider versions, not module versions. Using `version = "~> 8.7"` on any module block allows silent upgrades when a new `8.8.0` is released, potentially changing output names, variable behavior, or breaking tutorial readers who run `terraform init` after a new release.

**Version strings in use (appear in each module's source block):**

```hcl
# versions.tf reference comments (Terraform locals cannot be used in module source blocks)
# terraform-aws-modules/lambda/aws            = "8.7.0"
# terraform-aws-modules/dynamodb-table/aws    = "5.5.0"
# terraform-aws-modules/sqs/aws              = "5.2.1"
# terraform-aws-modules/cloudwatch/aws        = "5.7.2"  (use //modules/metric-alarm submodule)
# terraform-aws-modules/sns/aws              = "7.1.0"
```

---

## Section 5: Lambda Zip Path Convention

### Path

`build/function.zip` in the example root directory, referenced from `terraform/` as:

```hcl
local_existing_package = "${path.module}/../build/function.zip"
```

### deploy.sh zip step

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "${SCRIPT_DIR}/build"
cd "${SCRIPT_DIR}"
zip -r "${SCRIPT_DIR}/build/function.zip" src/generated/ handlers/ -x "**/__pycache__/*" "**/*.pyc"
```

### What goes in the zip

- `src/generated/` — RSF orchestrator output (created by `rsf generate`)
- `handlers/` — user-written business logic handlers

**No pip dependencies.** Lambda Durable Functions runtime provides Python 3.13 stdlib. RSF generates standalone orchestrator code with no external runtime dependencies.

### Module settings for pre-built zip

```hcl
module "lambda" {
  # ...
  create_package          = false
  local_existing_package  = "${path.module}/../build/function.zip"
  ignore_source_code_hash = true
}
```

`ignore_source_code_hash = true` prevents Terraform from re-deploying on every `terraform apply` when the zip hash changes outside of Terraform's control (i.e., when `deploy.sh` rebuilds the zip).

### Gitignore

The `build/` directory is gitignored alongside `.terraform/`, `*.tfstate`, `*.tfstate.backup`.

---

## Section 6: Anti-Patterns (Quick Reference)

1. **`durable_config_execution_timeout = null` (or omitted):** The dynamic block gate means the entire durable_config is silently dropped. Always set a numeric value (use `coalesce()` to guard against null propagation from variables).

2. **`version = "~> 8.7"` on registry modules:** Silently upgrades on `terraform init`. Terraform does not lock module versions in `.terraform.lock.hcl`. Use exact version strings.

3. **`create_package = true` (module default):** Conflicts with RSF's zip creation workflow. Always set `create_package = false` and provide `local_existing_package`.

4. **Invoking via `$LATEST` or unqualified ARN:** Issue #45800 (AllowInvokeLatest) is unresolved. Always use a Lambda alias and invoke via alias ARN.

5. **Omitting `attach_policies = true` with a `policies` list:** The module only processes the `policies` variable when `attach_policies = true`. Setting `policies = [...]` alone silently attaches nothing.

6. **Using `terraform-aws-modules/cloudwatch/aws` root module:** The root module has no configuration. Must use `terraform-aws-modules/cloudwatch/aws//modules/metric-alarm` with the double-slash submodule path syntax.

---

## Section 7: Open Questions for Phase 57

1. **`GetDurableExecution` vs `GetDurableExecutionState` runtime usage**
   - The managed policy uses `GetDurableExecutionState` (replay path). RSF's existing generator grants `GetDurableExecution` (describe API). Both exist in AWS IAM.
   - Recommendation: Include both in the inline supplement. Validate with a live durable invocation to completion in Phase 57 before declaring IAM correct.

2. **AllowInvokeLatest resolution timing (issue #45800)**
   - Still open as of Jan 7, 2026. Depends on AWS SDK for Go v2 implementation.
   - Use alias convention throughout all tutorial phases. Add note: "If issue #45800 is resolved, `AllowInvokeLatest = true` can be added to the `durable_config` block."

3. **`AWSLambdaBasicDurableExecutionRolePolicy` regional availability in us-east-2**
   - Managed policy confirmed to exist (v3, Feb 12, 2026). Regional rollout in us-east-2 unverified.
   - Phase 57 MUST run before writing Terraform that attaches it:
     ```bash
     aws iam get-policy --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicDurableExecutionRolePolicy --region us-east-2
     ```
   - Fallback if unavailable: all-inline IAM policy matching RSF's existing `iam.tf.j2` approach, adding `lambda:GetDurableExecutionState` to cover both API paths.

---

*Phase: 56-schema-verification*
*Verified: 2026-03-04*
*Valid until: 2026-04-04 (30 days — modules are stable; issue #45800 may resolve sooner)*
