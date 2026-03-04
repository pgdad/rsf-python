# Phase 58: Full-Stack Registry Modules - Research

**Researched:** 2026-03-04
**Domain:** Terraform registry modules — DynamoDB, SQS, CloudWatch, SNS
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Metadata passing strategy**
- Migrate deploy.sh from scalar `-var` flags to a generated `terraform.tfvars.json` file
- deploy.sh uses jq to transform RSF_METADATA_FILE into terraform.tfvars.json with all variables (workflow_name, execution_timeout, dynamodb_tables, dlq_enabled, dlq_queue_name, dlq_max_receive_count, alarms)
- `terraform apply -var-file=terraform.tfvars.json` replaces individual `-var` flags
- terraform.tfvars.json is gitignored (generated at deploy time, contains runtime values)
- Same approach for `terraform destroy -var-file=terraform.tfvars.json`
- This handles list/object variables cleanly and is tutorial-friendly (readers can inspect the generated file)

**Alarm definitions**
- Add alarms section to workflow.yaml with all three alarm types: error_rate, duration, throttle
- Use reasonable tutorial-friendly thresholds (not production-tuned — this is a learning example)
- All alarms auto-create an SNS topic via the sns registry module (no pre-existing sns_topic_arn)

**Terraform file layout**
- One .tf file per registry module: `dynamodb.tf`, `sqs.tf`, `alarms.tf`, `sns.tf`
- Each file is self-contained with its registry module block
- Matches tutorial structure: one section per resource type, easy to follow

**DynamoDB Terraform**
- Use terraform-aws-modules/dynamodb-table/aws v5.5.0
- `for_each` over dynamodb_tables variable (list of objects → map keyed by table_name)
- Map RSF table schema (table_name, partition_key, billing_mode) to module inputs
- Add DynamoDB IAM permissions to Lambda role (read/write on created table ARNs)

**SQS DLQ Terraform**
- Use terraform-aws-modules/sqs/aws v5.2.1
- Conditional creation: `count = var.dlq_enabled ? 1 : 0`
- Wire to lambda module via `dead_letter_target_arn` — requires updating main.tf lambda module block
- Pass max_receive_count from metadata
- 14-day message retention (matches RSF's existing DLQ template)

**CloudWatch alarms Terraform**
- Use terraform-aws-modules/cloudwatch/aws v5.7.2 `//modules/metric-alarm` submodule
- One module block per alarm type (error_rate, duration, throttle)
- Dynamic creation from alarms variable (list of alarm configs)
- All alarms reference the Lambda function name from module.lambda output
- All alarms send to SNS topic created by sns module

**SNS topic Terraform**
- Use terraform-aws-modules/sns/aws v7.1.0
- Single topic for all alarm notifications
- Created unconditionally when alarms exist (alarms require a notification target)
- Topic ARN passed to alarm modules via `alarm_actions`

**IAM expansion**
- Extend the inline supplement policy in main.tf to include DynamoDB and SQS permissions
- DynamoDB: dynamodb:PutItem, dynamodb:GetItem, dynamodb:UpdateItem, dynamodb:DeleteItem, dynamodb:Query, dynamodb:Scan — scoped to created table ARNs
- SQS: sqs:SendMessage — scoped to DLQ ARN (conditional on dlq_enabled)
- Use conditional jsonencode to build policy statement list dynamically

### Claude's Discretion

- Exact alarm thresholds and evaluation periods for the tutorial example
- Whether to use `for_each` with `tomap()` or `for` expression for DynamoDB module iteration
- How to structure the conditional IAM policy (single policy_json with conditional statements vs. separate attach_policy_jsons)
- Exact terraform.tfvars.json generation jq command structure
- Whether alarms variable uses a single list or separate per-type variables
- Output additions (DynamoDB table names, SQS queue URL, SNS topic ARN, alarm names)
- Whether to add alarm config to workflow.yaml in this phase or defer to a separate small update

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REG-02 | DynamoDB table deployed via terraform-aws-modules/dynamodb-table/aws | Module inputs verified: name, hash_key, billing_mode, attributes (list of maps). for_each pattern over dynamodb_tables variable confirmed viable. |
| REG-03 | SQS DLQ deployed via terraform-aws-modules/sqs/aws conditionally based on dlq_enabled | `create` variable confirmed (bool, default true). `count` pattern via `create` or direct `count = var.dlq_enabled ? 1 : 0` on module. `queue_arn` output feeds dead_letter_target_arn on lambda module. |
| REG-04 | CloudWatch alarms deployed via terraform-aws-modules/cloudwatch metric-alarm submodule | Source path confirmed: `terraform-aws-modules/cloudwatch/aws//modules/metric-alarm`. All three alarm types (Errors, Duration, Throttles) use identical variable interface with different metric_name/statistic. |
| REG-05 | SNS topic deployed via terraform-aws-modules/sns/aws for alarm notifications | `topic_arn` output confirmed. `name` input for topic name. Feeds `alarm_actions` on all alarm module blocks. |
</phase_requirements>

## Summary

Phase 58 extends `examples/registry-modules-demo/terraform/` with four new .tf files (one per registry module) and refactors `deploy.sh` to generate a `terraform.tfvars.json` file instead of passing individual `-var` flags. The existing Phase 57 infrastructure (Lambda + IAM in `main.tf`) remains intact — this phase adds DynamoDB, SQS DLQ, CloudWatch alarms, and SNS notification topic alongside it.

All four registry modules have been verified from their GitHub source at the exact pinned versions (`versions.tf` already has the correct pins). The module APIs are stable and well-understood. The primary implementation challenge is correctly expressing Terraform's type system for the new variables (list-of-objects for DynamoDB tables and alarms), the `for_each` conversion from list to map for DynamoDB, and the conditional IAM policy statement construction.

The `deploy.sh` refactor from individual `-var` flags to `terraform.tfvars.json` generation is the key enabler for list/object variable passing. The existing jq pattern in deploy.sh (`jq -r '.field'`) extends naturally to `jq -n` with object construction.

**Primary recommendation:** Implement in dependency order: sns.tf → dynamodb.tf → sqs.tf → alarms.tf → variables.tf → outputs.tf → main.tf (IAM expansion) → deploy.sh (tfvars.json refactor) → workflow.yaml (add alarms).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| terraform-aws-modules/dynamodb-table/aws | 5.5.0 | DynamoDB table creation | Already pinned in versions.tf; canonical community module |
| terraform-aws-modules/sqs/aws | 5.2.1 | SQS queue creation | Already pinned in versions.tf; canonical community module |
| terraform-aws-modules/cloudwatch/aws | 5.7.2 | CloudWatch metric alarms via submodule | Already pinned in versions.tf; //modules/metric-alarm submodule |
| terraform-aws-modules/sns/aws | 7.1.0 | SNS topic creation | Already pinned in versions.tf; canonical community module |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jq | system-provided | JSON transformation in deploy.sh | Transform RSF_METADATA_FILE to terraform.tfvars.json |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| terraform.tfvars.json | Individual -var flags | -var flags cannot pass list/object values cleanly; tfvars.json is the correct mechanism for structured data |
| for_each on DynamoDB module | Multiple static module blocks | for_each scales; static blocks require code changes for each additional table |

**No additional installation needed** — all modules already pinned in `versions.tf`. `terraform init` will download them.

## Architecture Patterns

### Recommended Project Structure
```
examples/registry-modules-demo/
├── deploy.sh              # REFACTOR: generate terraform.tfvars.json
├── workflow.yaml          # ADD: alarms section (3 alarm types)
└── terraform/
    ├── main.tf            # EXTEND: dead_letter_target_arn + IAM expansion
    ├── variables.tf       # EXTEND: new vars for dynamodb_tables, dlq_*, alarms
    ├── outputs.tf         # EXTEND: DynamoDB ARNs, SQS URL, SNS ARN, alarm names
    ├── dynamodb.tf        # NEW: for_each over dynamodb_tables variable
    ├── sqs.tf             # NEW: conditional SQS DLQ module
    ├── alarms.tf          # NEW: three metric-alarm module blocks
    ├── sns.tf             # NEW: single SNS topic module
    ├── versions.tf        # NO CHANGE: all versions already pinned
    ├── backend.tf         # NO CHANGE: local backend
    └── iam_durable.tf     # NO CHANGE: documentation file only
```

### Pattern 1: DynamoDB for_each via list-to-map conversion

**What:** Convert `var.dynamodb_tables` (list of objects) to a map keyed by `table_name` for use with `for_each` on the module block.

**When to use:** Any time a Terraform module must be instantiated once per element in a list variable.

**Example:**
```hcl
# dynamodb.tf
# DynamoDB table(s) deployed via terraform-aws-modules/dynamodb-table/aws v5.5.0
# for_each creates one table per entry in var.dynamodb_tables.

module "dynamodb_table" {
  source   = "terraform-aws-modules/dynamodb-table/aws"
  version  = "5.5.0"

  for_each = { for t in var.dynamodb_tables : t.table_name => t }

  name         = each.value.table_name
  hash_key     = each.value.partition_key.name
  billing_mode = each.value.billing_mode

  attributes = [
    {
      name = each.value.partition_key.name
      type = each.value.partition_key.type
    }
  ]

  tags = {
    ManagedBy = "rsf"
    Workflow  = var.workflow_name
  }
}
```

### Pattern 2: Conditional SQS DLQ with count

**What:** Use `count = var.dlq_enabled ? 1 : 0` on the module block to conditionally create the DLQ. Reference with `module.sqs_dlq[0].queue_arn`.

**When to use:** Resource that may or may not exist based on a boolean flag from workflow metadata.

**Example:**
```hcl
# sqs.tf
# SQS DLQ deployed via terraform-aws-modules/sqs/aws v5.2.1
# count gates creation on dlq_enabled from workflow metadata.

module "sqs_dlq" {
  source  = "terraform-aws-modules/sqs/aws"
  version = "5.2.1"

  count = var.dlq_enabled ? 1 : 0

  name                      = var.dlq_queue_name != null ? var.dlq_queue_name : "${var.workflow_name}-dlq"
  message_retention_seconds = 1209600  # 14 days — matches RSF's dlq.tf.j2 default

  tags = {
    ManagedBy = "rsf"
    Workflow  = var.workflow_name
  }
}
```

**Wire to Lambda in main.tf:**
```hcl
# Add to module "lambda" block in main.tf:
dead_letter_target_arn = var.dlq_enabled ? module.sqs_dlq[0].queue_arn : null
```

### Pattern 3: CloudWatch metric-alarm submodule — one block per alarm type

**What:** Three separate module blocks for error_rate, duration, and throttle alarms. Each block uses a `count` conditional to exist only if an alarm of that type appears in `var.alarms`.

**When to use:** Fixed set of alarm types where each type has different metric_name and statistic.

**Example:**
```hcl
# alarms.tf
# CloudWatch alarms via terraform-aws-modules/cloudwatch/aws v5.7.2
# Source: //modules/metric-alarm submodule.

locals {
  # Index alarms by type for easy lookup
  alarm_by_type = { for a in var.alarms : a.type => a }
}

module "alarm_error_rate" {
  source  = "terraform-aws-modules/cloudwatch/aws//modules/metric-alarm"
  version = "5.7.2"

  count = contains(keys(local.alarm_by_type), "error_rate") ? 1 : 0

  alarm_name          = "${var.workflow_name}-error-rate"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = local.alarm_by_type["error_rate"].evaluation_periods
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = local.alarm_by_type["error_rate"].period
  statistic           = "Sum"
  threshold           = local.alarm_by_type["error_rate"].threshold
  alarm_description   = "Error rate alarm for ${var.workflow_name}"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = module.lambda.lambda_function_name
  }

  alarm_actions = [module.sns_alarms.topic_arn]

  tags = {
    ManagedBy = "rsf"
    Workflow  = var.workflow_name
  }
}

module "alarm_duration" {
  source  = "terraform-aws-modules/cloudwatch/aws//modules/metric-alarm"
  version = "5.7.2"

  count = contains(keys(local.alarm_by_type), "duration") ? 1 : 0

  alarm_name          = "${var.workflow_name}-duration"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = local.alarm_by_type["duration"].evaluation_periods
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = local.alarm_by_type["duration"].period
  statistic           = "Average"
  threshold           = local.alarm_by_type["duration"].threshold
  alarm_description   = "Duration alarm for ${var.workflow_name}"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = module.lambda.lambda_function_name
  }

  alarm_actions = [module.sns_alarms.topic_arn]

  tags = {
    ManagedBy = "rsf"
    Workflow  = var.workflow_name
  }
}

module "alarm_throttle" {
  source  = "terraform-aws-modules/cloudwatch/aws//modules/metric-alarm"
  version = "5.7.2"

  count = contains(keys(local.alarm_by_type), "throttle") ? 1 : 0

  alarm_name          = "${var.workflow_name}-throttle"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = local.alarm_by_type["throttle"].evaluation_periods
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = local.alarm_by_type["throttle"].period
  statistic           = "Sum"
  threshold           = local.alarm_by_type["throttle"].threshold
  alarm_description   = "Throttle alarm for ${var.workflow_name}"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = module.lambda.lambda_function_name
  }

  alarm_actions = [module.sns_alarms.topic_arn]

  tags = {
    ManagedBy = "rsf"
    Workflow  = var.workflow_name
  }
}
```

### Pattern 4: SNS topic module

**What:** Single SNS topic, created unconditionally (alarms always require a notification target in this example).

**Example:**
```hcl
# sns.tf
# SNS topic for alarm notifications via terraform-aws-modules/sns/aws v7.1.0

module "sns_alarms" {
  source  = "terraform-aws-modules/sns/aws"
  version = "7.1.0"

  name = "${var.workflow_name}-alarm-notifications"

  tags = {
    ManagedBy = "rsf"
    Workflow  = var.workflow_name
  }
}
```

### Pattern 5: terraform.tfvars.json generation with jq

**What:** deploy.sh generates a JSON file containing all Terraform variables (including list/object types) from RSF_METADATA_FILE, then passes it via `-var-file`.

**Why:** Individual `-var` flags cannot cleanly pass JSON arrays or objects. `terraform.tfvars.json` is the Terraform-idiomatic solution for structured variable values.

**Example:**
```bash
# In deploy.sh deploy branch, after METADATA_FILE is set:
TFVARS_FILE="${TF_DIR}/terraform.tfvars.json"

jq -n \
  --argjson metadata "$(cat "${METADATA_FILE}")" \
  '{
    workflow_name:         $metadata.workflow_name,
    execution_timeout:     ($metadata.timeout_seconds // 86400),
    dynamodb_tables:       ($metadata.dynamodb_tables // []),
    dlq_enabled:           ($metadata.dlq_enabled // false),
    dlq_queue_name:        $metadata.dlq_queue_name,
    dlq_max_receive_count: ($metadata.dlq_max_receive_count // 3),
    alarms:                ($metadata.alarms // [])
  }' > "${TFVARS_FILE}"

terraform apply -auto-approve -var-file=terraform.tfvars.json
```

For destroy, regenerate tfvars.json with the same jq command before `terraform destroy -var-file=terraform.tfvars.json`.

**Gitignore:** `terraform.tfvars.json` must be added to `.gitignore` at the example root — it contains runtime-generated values.

### Pattern 6: Conditional IAM policy_json with DynamoDB + SQS permissions

**What:** Extend the existing `policy_json` in main.tf's lambda module block to dynamically include DynamoDB and SQS statements based on what resources exist.

**Example:**
```hcl
# In module "lambda" block in main.tf, replace policy_json with:
attach_policy_json = true
policy_json = jsonencode({
  Version = "2012-10-17"
  Statement = concat(
    # Always present: durable function extra permissions
    [{
      Sid    = "DurableExtraPermissions"
      Effect = "Allow"
      Action = [
        "lambda:InvokeFunction",
        "lambda:ListDurableExecutionsByFunction",
        "lambda:GetDurableExecution"
      ]
      Resource = "*"
    }],
    # DynamoDB permissions — only when tables are defined
    length(var.dynamodb_tables) > 0 ? [{
      Sid    = "DynamoDBTableAccess"
      Effect = "Allow"
      Action = [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ]
      Resource = [for t in module.dynamodb_table : t.dynamodb_table_arn]
    }] : [],
    # SQS permissions — only when DLQ is enabled
    var.dlq_enabled ? [{
      Sid      = "SQSDLQAccess"
      Effect   = "Allow"
      Action   = ["sqs:SendMessage"]
      Resource = [module.sqs_dlq[0].queue_arn]
    }] : []
  )
})
```

### Anti-Patterns to Avoid

- **count on module with for_each dependency:** Never use `count` on a module that is referenced by another resource using `for_each`. The count-to-single-instance accessor (`[0]`) creates type conflicts. Plan carefully which resources use count vs for_each.
- **Referencing count-gated module without index:** `module.sqs_dlq.queue_arn` fails when count is used — must be `module.sqs_dlq[0].queue_arn`. Always include `[0]` for count-gated modules.
- **Passing list variable via -var flag:** `-var="dynamodb_tables=[{...}]"` is fragile with shell quoting. This is exactly why the tfvars.json approach was chosen.
- **Using //modules/metric-alarm without double-slash:** The double-slash (`//`) is mandatory in the source string to indicate a submodule path within a registry module. `terraform-aws-modules/cloudwatch/aws/modules/metric-alarm` (single slash) will not resolve correctly.
- **Omitting attributes in DynamoDB module:** The dynamodb-table module requires `attributes` to be a list of maps with `name` and `type` keys even if the table only has a hash key. Omitting attributes will cause plan-time errors.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DynamoDB table | `aws_dynamodb_table` resource directly | `terraform-aws-modules/dynamodb-table/aws` | Module handles capacity mode defaults, TTL, streams, backup options consistently |
| SQS queue | `aws_sqs_queue` resource directly | `terraform-aws-modules/sqs/aws` | Module handles visibility timeout, FIFO options, managed SSE defaults |
| CloudWatch alarms | `aws_cloudwatch_metric_alarm` resource directly | `//modules/metric-alarm` submodule | Consistent variable names and defaults; matches tutorial style |
| SNS topic | `aws_sns_topic` resource directly | `terraform-aws-modules/sns/aws` | Module handles topic policy, subscription management, FIFO options |
| JSON variable transformation | Custom bash string manipulation | `jq -n` with `--argjson` | jq handles JSON types, null fallbacks, and nested objects correctly |

**Key insight:** All four modules are already pinned in `versions.tf` from Phase 56 pre-work. The task is to write the module blocks — not to choose or evaluate modules.

## Common Pitfalls

### Pitfall 1: for_each requires map, not list

**What goes wrong:** `for_each = var.dynamodb_tables` fails if `dynamodb_tables` is typed as `list(object(...))` — Terraform requires a map or set for `for_each`.

**Why it happens:** Terraform's `for_each` meta-argument only accepts maps or sets of strings, not lists.

**How to avoid:** Convert with `{ for t in var.dynamodb_tables : t.table_name => t }` inline in the for_each expression, or use `tomap()` if the input is already a map.

**Warning signs:** `for_each value must be a map or set` error during `terraform plan`.

### Pitfall 2: count-gated module reference requires [0] index

**What goes wrong:** `module.sqs_dlq.queue_arn` fails with "Module instance key required" when `count` is used on the module.

**Why it happens:** When a module uses `count`, Terraform treats it as a list of instances. Instance 0 is accessed as `module.sqs_dlq[0]`.

**How to avoid:** Always reference count-gated modules with `[0]`: `module.sqs_dlq[0].queue_arn`. Use a conditional in the lambda module block: `dead_letter_target_arn = var.dlq_enabled ? module.sqs_dlq[0].queue_arn : null`.

**Warning signs:** Plan-time error: "Because module.sqs_dlq has count set, its attributes must be accessed on specific instances."

### Pitfall 3: policy_json concat with empty lists

**What goes wrong:** `concat([...], null)` fails — Terraform's `concat()` does not accept null. Conditional IAM statements must return `[]` (empty list), not `null`, for the false branch.

**Why it happens:** HCL ternary `condition ? value : null` propagates null into concat().

**How to avoid:** Always use `condition ? [{...}] : []` — empty list, not null. The concat() of an empty list is a no-op.

**Warning signs:** `Invalid value for function argument: argument must not be null` during terraform plan.

### Pitfall 4: DynamoDB attributes must list ALL key attributes

**What goes wrong:** DynamoDB plan fails with "attributes must include all key attributes" if the `attributes` list is missing any attribute referenced by `hash_key` or `range_key`.

**Why it happens:** DynamoDB requires attribute definitions for every key attribute, even for PAY_PER_REQUEST tables.

**How to avoid:** The `attributes` list in the module must include at minimum the partition key attribute. For tables with sort keys, include both.

**Warning signs:** AWS API error during apply: "One or more parameter values were invalid: Missing the key hash_key in the item"

### Pitfall 5: terraform.tfvars.json left uncommitted breaks destroy

**What goes wrong:** `terraform destroy` fails if `terraform.tfvars.json` is not regenerated before destroy — the `-var-file` reference will fail if the file is absent.

**Why it happens:** The file is gitignored and only created at deploy time. After a fresh checkout, it does not exist.

**How to avoid:** The destroy branch in deploy.sh must regenerate `terraform.tfvars.json` using the same jq command before calling `terraform destroy -var-file=terraform.tfvars.json`. This ensures destroy always has the required variable values.

**Warning signs:** `Error: Failed to read variables file: The file "terraform.tfvars.json" does not exist`

### Pitfall 6: SNS topic ARN circular reference

**What goes wrong:** If alarms reference SNS and SNS references alarms (e.g., for subscription confirmation), circular dependency errors occur during plan.

**Why it happens:** Terraform resolves dependencies at plan time. Cycles prevent ordering.

**How to avoid:** SNS topic is created with no subscriptions (no `subscriptions` map in the module block). Alarms simply push to the topic ARN. No subscription from SNS back to alarms is needed — this is one-directional.

**Warning signs:** `Error: Cycle: module.sns_alarms, module.alarm_error_rate`

## Code Examples

### variables.tf additions
```hcl
variable "dynamodb_tables" {
  description = "DynamoDB tables to create — from workflow.yaml dynamodb_tables section"
  type = list(object({
    table_name = string
    partition_key = object({
      name = string
      type = string
    })
    billing_mode = string
  }))
  default = []
}

variable "dlq_enabled" {
  description = "Whether to create an SQS dead letter queue"
  type        = bool
  default     = false
}

variable "dlq_queue_name" {
  description = "SQS DLQ name (null = auto-generate from workflow_name)"
  type        = string
  default     = null
}

variable "dlq_max_receive_count" {
  description = "Max receive count before message moves to DLQ"
  type        = number
  default     = 3
}

variable "alarms" {
  description = "CloudWatch alarm configurations — from workflow.yaml alarms section"
  type = list(object({
    type               = string
    threshold          = number
    period             = number
    evaluation_periods = number
  }))
  default = []
}
```

### outputs.tf additions
```hcl
output "dynamodb_table_arns" {
  description = "ARNs of created DynamoDB tables keyed by table name"
  value       = { for k, v in module.dynamodb_table : k => v.dynamodb_table_arn }
}

output "sqs_dlq_url" {
  description = "SQS DLQ URL (null if dlq_enabled = false)"
  value       = var.dlq_enabled ? module.sqs_dlq[0].queue_url : null
}

output "sns_alarm_topic_arn" {
  description = "SNS topic ARN for alarm notifications"
  value       = module.sns_alarms.topic_arn
}
```

### workflow.yaml alarms section (recommended thresholds for tutorial)
```yaml
alarms:
  - type: error_rate
    # Alert when Lambda errors exceed 1 in a 5-minute window.
    # Tutorial threshold: 1 error is enough to alarm on in a demo workflow.
    threshold: 1
    period: 300
    evaluation_periods: 1

  - type: duration
    # Alert when average Lambda duration exceeds 10 seconds in a 5-minute window.
    # Tutorial threshold: image-processing workflow has a 30s handler timeout.
    threshold: 10000  # milliseconds
    period: 300
    evaluation_periods: 1

  - type: throttle
    # Alert when Lambda throttles occur at all in a 5-minute window.
    # Tutorial threshold: 1 throttle is worth investigating.
    threshold: 1
    period: 300
    evaluation_periods: 1
```

### deploy.sh tfvars.json generation
```bash
# Generate terraform.tfvars.json from RSF_METADATA_FILE
# All Terraform variables in one file — readers can inspect it after deploy
TFVARS_FILE="${TF_DIR}/terraform.tfvars.json"

jq -n \
  --argjson metadata "$(cat "${METADATA_FILE}")" \
  '{
    workflow_name:         $metadata.workflow_name,
    execution_timeout:     ($metadata.timeout_seconds // 86400),
    dynamodb_tables:       ($metadata.dynamodb_tables // []),
    dlq_enabled:           ($metadata.dlq_enabled // false),
    dlq_queue_name:        $metadata.dlq_queue_name,
    dlq_max_receive_count: ($metadata.dlq_max_receive_count // 3),
    alarms:                ($metadata.alarms // [])
  }' > "${TFVARS_FILE}"

echo "Generated: ${TFVARS_FILE}"
```

Note: `dlq_queue_name` intentionally passes through as `null` when absent — Terraform handles null string variables correctly and the sqs module falls back to the name expression.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `-var` flag for each Terraform variable | `-var-file=terraform.tfvars.json` with jq generation | Phase 58 (this phase) | Enables list/object variable passing from RSF metadata |
| Raw `aws_dynamodb_table` resource | `terraform-aws-modules/dynamodb-table/aws` module | Phase 56 pinned, Phase 58 implements | Consistent with rest of tutorial's registry module pattern |
| No alarms in workflow.yaml | alarms section with error_rate/duration/throttle | Phase 58 (this phase) | Demonstrates full RSF alarm DSL capability in tutorial example |

**No deprecated approaches in scope:** All four modules are at their Phase 56-verified versions. No deprecation concerns for this implementation scope.

## Open Questions

1. **jq null handling for dlq_queue_name in tfvars.json**
   - What we know: `jq` emits `null` for absent JSON keys; Terraform string variables accept null as valid (treated as no value, uses default)
   - What's unclear: Whether Terraform allows `null` in a `.tfvars.json` for a `string` type variable or requires the key to be absent entirely
   - Recommendation: Test with `terraform plan` after generation. If null string causes error, use `($metadata.dlq_queue_name // "")` with an empty string sentinel and handle in HCL with `var.dlq_queue_name != "" ? var.dlq_queue_name : null`

2. **DynamoDB for_each key collision**
   - What we know: The for expression keys by `table_name`. If two tables share a name (invalid anyway), the second silently overwrites.
   - What's unclear: Whether a Terraform validation rule should enforce unique table names
   - Recommendation: The RSF DSL layer (Pydantic) already validates uniqueness. No additional Terraform validation needed.

3. **alarm_actions type for metric-alarm submodule**
   - What we know: `alarm_actions = list(string)` (default null), accepts SNS topic ARNs
   - What's unclear: Whether passing an empty list `[]` vs null for alarm_actions when SNS topic does not exist causes any warnings
   - Recommendation: SNS topic is always created when alarms list is non-empty (per locked decision). No empty list scenario in this phase.

## Validation Architecture

> nyquist_validation not found in .planning/config.json — treating as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (project-wide) |
| Config file | pytest.ini / pyproject.toml (project root) |
| Quick run command | `cd /path/to/example && rsf generate workflow.yaml && bash deploy.sh deploy` |
| Full suite command | Manual AWS Console verification post-deploy |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REG-02 | DynamoDB table created with for_each | smoke (terraform plan) | `cd terraform && terraform plan -var-file=terraform.tfvars.json` | ❌ Wave 0 |
| REG-03 | SQS DLQ conditionally created | smoke (terraform plan) | `cd terraform && terraform plan -var-file=terraform.tfvars.json` | ❌ Wave 0 |
| REG-04 | CloudWatch alarms created | smoke (terraform plan) | `cd terraform && terraform plan -var-file=terraform.tfvars.json` | ❌ Wave 0 |
| REG-05 | SNS topic created | smoke (terraform plan) | `cd terraform && terraform plan -var-file=terraform.tfvars.json` | ❌ Wave 0 |

### Sampling Rate
- **Per task:** `terraform validate && terraform plan -var-file=terraform.tfvars.json` (after generating tfvars.json)
- **Per wave merge:** Full `rsf deploy` sequence (generate + deploy.sh)
- **Phase gate:** AWS Console verification of all five resource types before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `examples/registry-modules-demo/terraform.tfvars.json` — not a test file, but must be generated by deploy.sh before any terraform command
- [ ] `examples/registry-modules-demo/.gitignore` — must include `terraform.tfvars.json` and `build/`

*(The example has no automated Terraform tests — Phase 59 handles TEST-01/02/03. Phase 58 validation is manual deploy + AWS Console check.)*

## Sources

### Primary (HIGH confidence)
- GitHub: terraform-aws-modules/terraform-aws-dynamodb-table v5.5.0 — variables.tf, outputs.tf (verified: name, hash_key, billing_mode, attributes, dynamodb_table_arn output)
- GitHub: terraform-aws-modules/terraform-aws-sqs v5.2.1 — variables.tf, outputs.tf (verified: create, name, message_retention_seconds, queue_arn output)
- GitHub: terraform-aws-modules/terraform-aws-cloudwatch v5.7.2 — modules/metric-alarm/variables.tf (verified: alarm_name, comparison_operator, evaluation_periods, metric_name, namespace, period, statistic, threshold, dimensions, alarm_actions, treat_missing_data)
- GitHub: terraform-aws-modules/terraform-aws-sns v7.1.0 — variables.tf, outputs.tf (verified: name, topic_arn output)
- GitHub: terraform-aws-modules/terraform-aws-lambda v8.7.0 — variables.tf (verified: dead_letter_target_arn accepts SQS ARN or SNS ARN)
- Existing codebase: examples/registry-modules-demo/terraform/ — versions.tf, main.tf, variables.tf, outputs.tf, deploy.sh, iam_durable.tf
- Existing codebase: src/rsf/providers/metadata.py — WorkflowMetadata schema (dynamodb_tables, alarms, dlq_enabled, dlq_max_receive_count, dlq_queue_name)
- Existing codebase: src/rsf/dsl/models.py — ErrorRateAlarm, DurationAlarm, ThrottleAlarm field names and types
- Existing codebase: src/rsf/terraform/templates/ — dynamodb.tf.j2, dlq.tf.j2, alarms.tf.j2 (RSF raw HCL reference for metric names, statistic types, treat_missing_data)

### Secondary (MEDIUM confidence)
- HashiCorp Terraform docs — JSON Configuration Syntax for .tfvars.json format (list/object support)
- jq documentation — `--argjson` flag for passing pre-parsed JSON; `//` operator for null fallback

### Tertiary (LOW confidence)
- None required — all critical claims verified from official GitHub sources at pinned versions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all four modules verified from GitHub at exact pinned versions; variables and outputs confirmed
- Architecture: HIGH — patterns derived directly from module APIs and existing Phase 57 code; no speculation
- Pitfalls: HIGH — for_each/count patterns are well-known Terraform constraints; confirmed from module API inspection
- jq tfvars generation: MEDIUM — pattern is correct (jq -n --argjson); null handling for optional string variable is an open question flagged above

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (stable modules, 30-day window)
