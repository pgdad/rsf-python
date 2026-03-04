# Stack Research

**Domain:** Terraform Registry Modules Tutorial (RSF v3.2)
**Researched:** 2026-03-03
**Confidence:** HIGH (all versions verified from GitHub releases pages, source files fetched directly)

## Context

RSF v3.2 adds a tutorial and example showing how to implement an RSF custom provider backed by
HashiCorp's official terraform-aws-modules. The tutorial teaches users to replace RSF's raw HCL
resource generation with curated registry modules. No new Python dependencies. No RSF core changes.
The stack additions live entirely inside the tutorial's bash deploy script and Terraform configuration.

**Existing RSF custom provider interface (already shipped in v3.0):**
- `CustomProvider` invokes an external program (`shell=False`, absolute path, executable)
- Metadata delivered via one of three transports: JSON file, env vars, or CLI arg templates
- `WorkflowMetadata` fields: `workflow_name`, `stage`, `handler_count`, `timeout_seconds`,
  `triggers`, `dynamodb_tables`, `alarms`, `dlq_enabled`, `dlq_max_receive_count`,
  `dlq_queue_name`, `lambda_url_enabled`, `lambda_url_auth_type`

**What the tutorial demonstrates:** A `deploy.sh` that RSF's `CustomProvider` invokes, which in
turn runs `terraform apply` on a configuration that uses terraform-aws-modules instead of raw HCL.

---

## Recommended Stack — Registry Modules

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| terraform-aws-modules/lambda/aws | 8.7.0 | Lambda function + built-in IAM role + package management | Only official module with native `durable_config` support (v8.7.0, Feb 18, 2026). Handles archive creation, IAM role, CloudWatch log group, and DLQ wiring as an integrated unit. Eliminates the need for separate raw HCL iam.tf, cloudwatch.tf, main.tf files. `durable_config_execution_timeout` and `durable_config_retention_period` variables map directly from `WorkflowMetadata.timeout_seconds`. |
| terraform-aws-modules/dynamodb-table/aws | 5.5.0 | DynamoDB table with billing mode, keys, attributes | Direct 1:1 mapping to RSF `dynamodb_tables` WorkflowMetadata fields (name, billing_mode, hash_key, range_key, attributes). `PAY_PER_REQUEST` default matches RSF's generated raw HCL default. Use with `for_each` to provision one module per table entry. |
| terraform-aws-modules/sqs/aws | 5.2.1 | SQS queue for Lambda DLQ | `dead_letter_queue_arn` output connects cleanly to lambda module's `dead_letter_target_arn`. AWS provider >= 6.0 requirement already satisfied by RSF's `>= 6.25.0` constraint. `message_retention_seconds = 1209600` matches RSF's dlq.tf.j2 default (14 days). |
| terraform-aws-modules/cloudwatch/aws (metric-alarm submodule) | 5.7.2 | CloudWatch metric alarms for error rate, duration, throttles | The `//modules/metric-alarm` submodule maps directly to RSF's three alarm types (error_rate, duration, throttle) in `WorkflowMetadata.alarms`. `dimensions = { FunctionName = ... }` pattern is identical to RSF's raw alarms.tf.j2 template. |
| terraform-aws-modules/sns/aws | 7.1.0 | SNS topic for alarm notifications | Simple wrapper around `aws_sns_topic`. Requires AWS provider >= 6.9; RSF's existing `>= 6.25.0` satisfies this (6.25 > 6.9). `topic_arn` output feeds directly into `alarm_actions` for all CloudWatch metric alarms. |

### Supporting — Tutorial Infrastructure

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hashicorp/archive provider | >= 2.7.1 | Zip the generated Lambda source directory | When RSF generates code to `src/` and the tutorial needs a `source.zip` as input to the lambda module's `local_existing_package`. Already used in all RSF examples' `versions.tf`. |
| hashicorp/aws provider | >= 6.25.0 | AWS resource provisioning | Already required by RSF for `durable_config` block. Satisfies all module requirements: lambda >= 6.0, sqs >= 6.0, sns >= 6.9. No version bump required. |
| jq | system tool | Parse `WorkflowMetadata` JSON inside `deploy.sh` | Used in the custom provider bash script to extract `workflow_name`, `stage`, `dlq_enabled`, `dynamodb_tables` etc. from the metadata file transport payload. Standard on Linux/macOS. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Bash (deploy.sh) | Custom provider program invoked by RSF `CustomProvider` | Must be absolute path, `chmod +x`. Receives `WorkflowMetadata` via file transport. Calls `terraform apply`. This is the tutorial's primary teaching artifact. |
| terraform CLI >= 1.5.7 | Apply the registry module configuration | Required by sqs v5.0+ and sns v7.0+. RSF already requires terraform >= 1.0 generally; this tutorial's `versions.tf` must specify >= 1.5.7. |

---

## Module Interface Details

### terraform-aws-modules/lambda/aws v8.7.0

**Key inputs for RSF use case:**

```hcl
module "lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 8.7"

  function_name = var.workflow_name
  handler       = "generated.orchestrator.lambda_handler"
  runtime       = "python3.13"

  # Use RSF-generated zip — do not let module build it
  create_package          = false
  local_existing_package  = "${path.module}/source.zip"
  ignore_source_code_hash = true  # zip is managed by RSF CLI externally

  # Durable Lambda — maps from WorkflowMetadata
  durable_config_execution_timeout = var.execution_timeout   # from timeout_seconds
  durable_config_retention_period  = var.retention_period    # 1-90 days, default 14

  # Built-in IAM role — replaces RSF's raw iam.tf entirely
  create_role               = true
  attach_dead_letter_policy = var.dlq_enabled
  dead_letter_target_arn    = var.dlq_enabled ? module.dlq[0].queue_arn : null

  # CloudWatch Logs policy is attached by default (attach_cloudwatch_logs_policy = true)
  # Durable execution API requires a separate custom policy (see critical note below)
  policies = [aws_iam_policy.durable_execution.arn]
}
```

**Key outputs:**
- `module.lambda.lambda_function_arn` — for IAM policy resources, alarm dimensions
- `module.lambda.lambda_function_name` — for CloudWatch alarm dimensions
- `module.lambda.lambda_role_arn` — to reference the auto-created execution role
- `module.lambda.lambda_role_name` — to attach additional inline policies if needed

**CRITICAL — Durable execution IAM permissions not built-in:** The lambda module does NOT
include `lambda:CheckpointDurableExecution`, `lambda:GetDurableExecution`,
`lambda:ListDurableExecutionsByFunction`, or `lambda:InvokeFunction` (self-invoke). These must
be added as a separate `aws_iam_policy` resource and attached via the `policies` variable. This
is a primary teaching point in the tutorial: registry modules handle most of the IAM boilerplate
but durable-specific permissions remain manual.

```hcl
resource "aws_iam_policy" "durable_execution" {
  name = "${var.workflow_name}-durable-execution"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = [
          "lambda:InvokeFunction",
          "lambda:CheckpointDurableExecution",
          "lambda:GetDurableExecution",
          "lambda:ListDurableExecutionsByFunction"
        ]
        Resource = module.lambda.lambda_function_arn
      }
    ]
  })
}
```

### terraform-aws-modules/dynamodb-table/aws v5.5.0

**Key inputs for RSF use case:**

```hcl
module "dynamodb_table" {
  for_each = { for t in var.dynamodb_tables : t.table_name => t }

  source  = "terraform-aws-modules/dynamodb-table/aws"
  version = "~> 5.5"

  name         = each.value.table_name
  billing_mode = each.value.billing_mode  # "PAY_PER_REQUEST" or "PROVISIONED"
  hash_key     = each.value.partition_key.name
  range_key    = try(each.value.sort_key.name, null)  # optional

  attributes = concat(
    [{ name = each.value.partition_key.name, type = each.value.partition_key.type }],
    each.value.sort_key != null ? [{ name = each.value.sort_key.name, type = each.value.sort_key.type }] : []
  )
}
```

**Key outputs:**
- `module.dynamodb_table[*].dynamodb_table_arn` — for IAM policy `Resource` (DynamoDB access)
- `module.dynamodb_table[*].dynamodb_table_id` — table name for application config

**WorkflowMetadata mapping:** `dynamodb_tables[*]` → one module instance per table entry via
`for_each`. `billing_mode` from metadata maps directly. `partition_key.name` → `hash_key`.
`sort_key` (optional) → `range_key`. Both keys must appear in `attributes` list.

### terraform-aws-modules/sqs/aws v5.2.1

**Key inputs for RSF DLQ use case:**

```hcl
module "dlq" {
  count = var.dlq_enabled ? 1 : 0

  source  = "terraform-aws-modules/sqs/aws"
  version = "~> 5.2"

  name                       = coalesce(var.dlq_queue_name, "${var.workflow_name}-dlq")
  message_retention_seconds  = 1209600  # 14 days — matches RSF dlq.tf.j2 default
  visibility_timeout_seconds = 30
}
```

**Key outputs:**
- `module.dlq[0].queue_arn` — used as `dead_letter_target_arn` in lambda module
- `module.dlq[0].queue_url` — for application config output

**WorkflowMetadata mapping:** `dlq_enabled` → `count` gate. `dlq_queue_name` → `name` with
`coalesce` fallback. Note: `dlq_max_receive_count` is the Lambda retry count, NOT a SQS queue
property — it is not configurable via this module and does not need to be set here.

### terraform-aws-modules/cloudwatch/aws metric-alarm submodule v5.7.2

**Key inputs for RSF alarm use case:**

```hcl
module "alarm_error_rate" {
  source  = "terraform-aws-modules/cloudwatch/aws//modules/metric-alarm"
  version = "~> 5.7"

  alarm_name          = "${var.workflow_name}-error-rate"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"        # error_rate alarm type
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = var.error_threshold
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = module.lambda.lambda_function_name
  }

  alarm_actions = [module.sns_alarms.topic_arn]
}
```

**WorkflowMetadata alarm type → metric mapping:**

| RSF `alarm.type` | `metric_name` | `statistic` |
|-----------------|---------------|-------------|
| `error_rate`    | `"Errors"`    | `"Sum"`     |
| `duration`      | `"Duration"`  | `"Average"` |
| `throttle`      | `"Throttles"` | `"Sum"`     |

**Note:** Module source path uses `//modules/metric-alarm` double-slash syntax for submodule
selection. This is a Terraform convention. Calling the root module directly fails with "no root
configuration" error.

### terraform-aws-modules/sns/aws v7.1.0

**Key inputs for alarm topic use case:**

```hcl
module "sns_alarms" {
  source  = "terraform-aws-modules/sns/aws"
  version = "~> 7.1"

  name = "${var.workflow_name}-alarm-notifications"
}
```

**Key outputs:**
- `module.sns_alarms.topic_arn` — used in `alarm_actions` for all CloudWatch metric alarms

---

## Installation

```bash
# No new Python packages required — all changes are Terraform-only.
# Registry modules are downloaded by Terraform init automatically.
# Run inside the tutorial example's terraform/ directory:

terraform init    # Downloads all modules from registry.terraform.io
terraform plan    # Preview
terraform apply   # Deploy
```

The tutorial's `deploy.sh` (the RSF custom provider program) must:

```bash
#!/usr/bin/env bash
# deploy.sh — RSF custom provider program for registry-modules tutorial
set -euo pipefail

# RSF CustomProvider writes WorkflowMetadata JSON to a temp file
# and passes the path via the RSF_METADATA_FILE env var (file transport)
METADATA_FILE="${RSF_METADATA_FILE}"
WORKFLOW_NAME=$(jq -r '.workflow_name' "${METADATA_FILE}")
STAGE=$(jq -r '.stage // "dev"' "${METADATA_FILE}")
DLQ_ENABLED=$(jq -r '.dlq_enabled' "${METADATA_FILE}")

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/terraform"

terraform init -input=false
terraform apply -auto-approve \
  -var="workflow_name=${WORKFLOW_NAME}" \
  -var="stage=${STAGE}" \
  -var="dlq_enabled=${DLQ_ENABLED}"
```

The RSF workflow YAML configures this via:

```yaml
infrastructure:
  provider: custom
  custom:
    program: /absolute/path/to/deploy.sh
    metadata_transport: file
    args: []
    teardown_args: ["--destroy"]
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| lambda module built-in `create_role = true` | Separate `terraform-aws-modules/iam/aws//modules/iam-role` | Never for this use case. The iam-role module v6.x was redesigned for OIDC/SAML use cases and removed `trusted_role_services`. Configuring a Lambda execution role via the iam-role module requires complex `trust_policy_permissions` maps, which are harder to understand than letting the lambda module create the role automatically. |
| `local_existing_package` + `create_package = false` | `source_path` (module builds the zip via pip) | Only if the tutorial explicitly demonstrates module-driven Python packaging. For RSF, code is already generated and the zip built separately, making `local_existing_package` correct. `source_path` would create a competing packaging step that conflicts with RSF's code generation pipeline. |
| `//modules/metric-alarm` submodule | Raw `aws_cloudwatch_metric_alarm` resource | Either works. The submodule adds minimal value for simple alarms. Use the module to demonstrate the registry pattern consistently. If the tutorial already has three alarm module blocks (error, duration, throttle), use a `for_each` loop over a list to reduce repetition. |
| terraform-aws-modules/sqs/aws for DLQ | Raw `aws_sqs_queue` | Raw resource is simpler for a single DLQ queue. Use the module to demonstrate the registry pattern. Overhead is negligible. |
| File transport for metadata | Env transport or args transport | File transport is recommended for tutorial because: (1) the JSON file persists after the run for easy inspection and debugging; (2) nested structures like `dynamodb_tables` and `alarms` are straightforward to read with `jq`; (3) the `RSF_METADATA_FILE` env var name makes the mechanism self-documenting. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| terraform-aws-modules/lambda/aws version < 8.7.0 | No native `durable_config` support before v8.7.0 (Feb 18, 2026). Earlier versions require patching the module or using a raw `aws_lambda_function` resource alongside the module, defeating the purpose. | Pin to `~> 8.7` |
| terraform-aws-modules/iam/aws for Lambda execution role | v6.x redesigned for OIDC/SAML; removed `trusted_role_services`. Configuring `lambda.amazonaws.com` as a trusted service requires undocumented `trust_policy_permissions` map syntax. More complex than letting the lambda module handle IAM. | lambda module's built-in `create_role = true` (the default) |
| `source_path` variable in lambda module | Triggers module-internal python packaging logic (pip install, zip creation) which conflicts with RSF's own code generation pipeline. RSF already generates the orchestrator; the zip must be built separately. | `create_package = false` + `local_existing_package` |
| cloudwatch module root (no submodule path) | v5.7.2 has no root configuration — calling it without `//modules/metric-alarm` fails with an error. Must use submodule path. | `terraform-aws-modules/cloudwatch/aws//modules/metric-alarm` |
| terraform-aws-modules/iam/aws for DynamoDB access policy | Adds abstraction overhead for what is a single targeted IAM policy statement. Cleaner as a raw `aws_iam_policy` + reference via the lambda module's `policies` variable. | Raw `aws_iam_policy` resource attached to lambda module via `policies` |
| `lambda_url_enabled` via lambda module | The lambda module does not expose `aws_lambda_function_url`. Lambda URLs must be created as a raw `aws_lambda_function_url` resource referencing the module's function ARN output. | Raw `aws_lambda_function_url` resource (use `module.lambda.lambda_function_name` as qualifier) |

---

## Stack Patterns by Variant

**If the workflow has no DynamoDB tables:**
- Omit all `module "dynamodb_table"` blocks
- Lambda module's `policies` list has no DynamoDB ARN entries

**If the workflow has no CloudWatch alarms:**
- Omit `module "alarm_*"` and `module "sns_alarms"` blocks
- Reduces the tutorial scope significantly — consider a workflow with at least one alarm to demonstrate the pattern

**If the workflow has no DLQ:**
- Omit `module "dlq"` block
- Set `attach_dead_letter_policy = false` on lambda module (already the default)

**If multiple alarm types are needed:**
- Use a `for_each` loop over `var.alarms` rather than one module block per alarm
- Map `alarm.type` → `{ metric_name, statistic }` via a `local` lookup map

**If the custom provider needs teardown support:**
- Add `teardown_args: ["--destroy"]` to the workflow YAML custom provider config
- Add a `--destroy` flag to `deploy.sh` that runs `terraform destroy -auto-approve`

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| terraform-aws-modules/lambda/aws ~> 8.7 | hashicorp/aws >= 6.0, terraform >= 1.0 | RSF already requires >= 6.25.0 and >= 1.0. No constraint conflict. |
| terraform-aws-modules/sqs/aws ~> 5.2 | hashicorp/aws >= 6.0, terraform >= 1.5.7 | v5.0.0 (Jun 2025) introduced the 1.5.7 requirement. Tutorial's `versions.tf` must specify `required_version = ">= 1.5.7"`. |
| terraform-aws-modules/sns/aws ~> 7.1 | hashicorp/aws >= 6.9, terraform >= 1.5.7 | v7.0.0 (Oct 2025) bumped requirements. RSF's >= 6.25.0 satisfies >= 6.9. |
| terraform-aws-modules/cloudwatch/aws ~> 5.7 | hashicorp/aws >= 4.0 | No conflict with RSF's constraints. |
| terraform-aws-modules/dynamodb-table/aws ~> 5.5 | hashicorp/aws >= 5.0 | No conflict with RSF's constraints. |
| hashicorp/archive ~> 2.7 | terraform >= 1.0 | Already in all RSF example versions.tf files. |

**Tutorial's versions.tf:**

```hcl
terraform {
  required_version = ">= 1.5.7"  # Required by sqs v5.x and sns v7.x

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.25.0"  # RSF durable_config requirement; also satisfies sns >= 6.9
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.7"
    }
  }
}
```

---

## WorkflowMetadata → Registry Module Mapping

| WorkflowMetadata Field | Registry Module Variable | Notes |
|------------------------|--------------------------|-------|
| `workflow_name` | `module.lambda.function_name` | Direct mapping via Terraform variable |
| `stage` | Terraform variable suffix or workspace | Used as naming convention for multi-stage |
| `timeout_seconds` | `module.lambda.durable_config_execution_timeout` | In seconds |
| `dlq_enabled` | `count = var.dlq_enabled ? 1 : 0` on dlq module | Gates the SQS module creation |
| `dlq_queue_name` | `module.dlq[0].name` with `coalesce` fallback | Falls back to `"${workflow_name}-dlq"` |
| `dlq_max_receive_count` | Not applicable to SQS queue module | This is a Lambda retry count, not a queue attribute |
| `dynamodb_tables[*]` | `module.dynamodb_table` with `for_each` | One module instance per table in the list |
| `dynamodb_tables[*].billing_mode` | `module.dynamodb_table.billing_mode` | "PAY_PER_REQUEST" or "PROVISIONED" |
| `dynamodb_tables[*].partition_key.name` | `module.dynamodb_table.hash_key` + `attributes[0].name` | Must appear in both `hash_key` and `attributes` |
| `dynamodb_tables[*].sort_key` (optional) | `module.dynamodb_table.range_key` + `attributes[1]` | Only when sort key is defined |
| `alarms[*].type` | Determines `metric_name` + `statistic` | error_rate→Errors/Sum, duration→Duration/Average, throttle→Throttles/Sum |
| `alarms[*].threshold` | `module.alarm_*.threshold` | Direct mapping |
| `alarms[*].period` | `module.alarm_*.period` | In seconds |
| `alarms[*].evaluation_periods` | `module.alarm_*.evaluation_periods` | Direct mapping |
| `alarms[*].sns_topic_arn` | `module.alarm_*.alarm_actions[0]` | When set, skip creating the SNS module |
| `lambda_url_enabled` | Raw `aws_lambda_function_url` resource | Lambda module does not expose function URL |
| `lambda_url_auth_type` | Raw `aws_lambda_function_url.authorization_type` | "NONE" or "AWS_IAM" |
| `triggers[*].type == "sqs"` | Not addressed by tutorial scope | Tutorial focuses on deployment pattern, not all trigger types |

---

## Sources

- GitHub releases — terraform-aws-modules/terraform-aws-lambda v8.7.0 (Feb 18, 2026):
  https://github.com/terraform-aws-modules/terraform-aws-lambda/releases
- GitHub releases — terraform-aws-modules/terraform-aws-iam v6.4.0 (Jan 23, 2026):
  https://github.com/terraform-aws-modules/terraform-aws-iam/releases
- GitHub releases — terraform-aws-modules/terraform-aws-dynamodb-table v5.5.0 (Jan 8, 2026):
  https://github.com/terraform-aws-modules/terraform-aws-dynamodb-table/releases
- GitHub releases — terraform-aws-modules/terraform-aws-sqs v5.2.1 (Jan 21, 2026):
  https://github.com/terraform-aws-modules/terraform-aws-sqs/releases
- GitHub releases — terraform-aws-modules/terraform-aws-sns v7.1.0 (Jan 8, 2026):
  https://github.com/terraform-aws-modules/terraform-aws-sns/releases
- GitHub releases — terraform-aws-modules/terraform-aws-cloudwatch v5.7.2 (Oct 21, 2025):
  https://github.com/terraform-aws-modules/terraform-aws-cloudwatch/releases
- GitHub source — lambda variables.tf (durable_config_execution_timeout, local_existing_package verified):
  https://raw.githubusercontent.com/terraform-aws-modules/terraform-aws-lambda/master/variables.tf
- GitHub source — lambda main.tf (dynamic durable_config block implementation verified):
  https://github.com/terraform-aws-modules/terraform-aws-lambda/blob/master/main.tf
- GitHub source — lambda iam.tf (trust policy lambda.amazonaws.com, attach_dead_letter_policy verified):
  https://github.com/terraform-aws-modules/terraform-aws-lambda/blob/master/iam.tf
- GitHub source — dynamodb-table variables.tf (name, billing_mode, hash_key, range_key, attributes verified):
  https://github.com/terraform-aws-modules/terraform-aws-dynamodb-table/blob/master/variables.tf
- GitHub source — sqs variables.tf (name, create_dlq, message_retention_seconds verified):
  https://github.com/terraform-aws-modules/terraform-aws-sqs/blob/master/variables.tf
- GitHub source — cloudwatch metric-alarm variables.tf (alarm_name, metric_name, namespace, dimensions verified):
  https://github.com/terraform-aws-modules/terraform-aws-cloudwatch/blob/master/modules/metric-alarm/variables.tf
- RSF source — WorkflowMetadata fields verified:
  /home/esa/git/rsf-python/src/rsf/providers/metadata.py
- RSF source — CustomProvider interface verified:
  /home/esa/git/rsf-python/src/rsf/providers/custom.py
- RSF source — existing raw HCL templates (iam.tf.j2, alarms.tf.j2, dlq.tf.j2, dynamodb.tf.j2):
  /home/esa/git/rsf-python/src/rsf/terraform/templates/

---

*Stack research for: Terraform Registry Modules Tutorial (RSF v3.2)*
*Researched: 2026-03-03*
