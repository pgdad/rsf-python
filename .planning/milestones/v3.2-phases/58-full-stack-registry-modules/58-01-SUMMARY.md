---
phase: 58-full-stack-registry-modules
plan: 01
subsystem: infra
tags: [terraform, dynamodb, sqs, sns, cloudwatch, registry-modules, iam]

# Dependency graph
requires:
  - phase: 57-core-lambda-example
    provides: Lambda module block with hybrid IAM, versions.tf with all module version pins
  - phase: 56-schema-verification
    provides: durable_config variable names, module version pins, alias workaround pattern
provides:
  - DynamoDB table module with for_each over dynamodb_tables variable
  - SQS DLQ module conditionally created via count on dlq_enabled
  - SNS topic module for alarm notifications (unconditional)
  - Three CloudWatch metric-alarm module blocks (error_rate, duration, throttle) each with count conditional
  - Lambda IAM policy_json extended with concat() — DynamoDB + SQS conditional statements
  - dead_letter_target_arn wired to SQS DLQ ARN when dlq_enabled
  - 5 new Terraform variables (dynamodb_tables, dlq_enabled, dlq_queue_name, dlq_max_receive_count, alarms)
  - 3 new Terraform outputs (dynamodb_table_arns, sqs_dlq_url, sns_alarm_topic_arn)
affects: [58-02-deploy-sh-workflow-yaml, future tutorial documentation]

# Tech tracking
tech-stack:
  added:
    - terraform-aws-modules/dynamodb-table/aws v5.5.0
    - terraform-aws-modules/sqs/aws v5.2.1
    - terraform-aws-modules/sns/aws v7.1.0
    - terraform-aws-modules/cloudwatch/aws//modules/metric-alarm v5.7.2
  patterns:
    - for_each with list-to-map conversion for multi-resource modules
    - count conditional for optional modules (dlq_enabled)
    - concat() with conditional list arrays for dynamic IAM policy statements
    - locals alarm_by_type map for O(1) alarm type lookup in count conditionals
    - Empty list [] for false branches in concat() (not null — type safety)

key-files:
  created:
    - examples/registry-modules-demo/terraform/dynamodb.tf
    - examples/registry-modules-demo/terraform/sqs.tf
    - examples/registry-modules-demo/terraform/sns.tf
    - examples/registry-modules-demo/terraform/alarms.tf
  modified:
    - examples/registry-modules-demo/terraform/variables.tf
    - examples/registry-modules-demo/terraform/outputs.tf
    - examples/registry-modules-demo/terraform/main.tf

key-decisions:
  - "concat() with conditional list arrays used for IAM policy_json — enables dynamic statement inclusion without multiple policy attachments"
  - "locals alarm_by_type map (for a in var.alarms : a.type => a) used in count conditionals — O(1) lookup, readable state resource names"
  - "Empty list [] for false branches in concat(), not null — concat() requires lists not null values (Terraform type safety)"
  - "SNS topic created unconditionally — alarms always need a notification target per locked phase decision"
  - "terraform init run as auto-fix (Rule 3) when new modules not installed caused terraform validate to fail"

patterns-established:
  - "List-to-map for_each: { for t in var.list : t.key_field => t } — stable state keys, self-documenting"
  - "Count conditional module: count = var.flag ? 1 : 0 — clean optional resource pattern"
  - "IAM concat() pattern: concat([always], condition ? [optional] : [], flag ? [optional] : []) — no null, no separate policies"
  - "locals alarm_by_type map for alarm count gating: contains(keys(local.alarm_by_type), 'TYPE') ? 1 : 0"

requirements-completed: [REG-02, REG-03, REG-04, REG-05]

# Metrics
duration: 2min
completed: 2026-03-04
---

# Phase 58 Plan 01: Full-Stack Registry Modules Terraform Summary

**Four new Terraform files and extended IAM policy wiring DynamoDB, SQS DLQ, SNS, and CloudWatch alarms to the registry-modules-demo Lambda via terraform-aws-modules registry modules with for_each, count, and concat() conditional patterns.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-04T14:42:07Z
- **Completed:** 2026-03-04T14:43:59Z
- **Tasks:** 2
- **Files modified:** 7 (4 created, 3 extended)

## Accomplishments

- Created `dynamodb.tf` using terraform-aws-modules/dynamodb-table/aws v5.5.0 with `for_each = { for t in var.dynamodb_tables : t.table_name => t }` — maps RSF WorkflowMetadata dynamodb_tables list to one DynamoDB table per entry
- Created `sqs.tf` using terraform-aws-modules/sqs/aws v5.2.1 with `count = var.dlq_enabled ? 1 : 0` — conditional DLQ with 14-day retention matching RSF's dlq.tf.j2 template
- Created `sns.tf` using terraform-aws-modules/sns/aws v7.1.0 — unconditional alarm notification topic
- Created `alarms.tf` using terraform-aws-modules/cloudwatch//modules/metric-alarm v5.7.2 — three conditional alarm module blocks (error_rate/Errors/Sum, duration/Duration/Average, throttle/Throttles/Sum) gated via `locals.alarm_by_type` map
- Extended `variables.tf` from 3 to 8 variables (added dynamodb_tables, dlq_enabled, dlq_queue_name, dlq_max_receive_count, alarms)
- Extended `outputs.tf` from 3 to 6 outputs (added dynamodb_table_arns, sqs_dlq_url, sns_alarm_topic_arn)
- Extended `main.tf` IAM policy_json from single Statement to concat() with three conditional arrays; added dead_letter_target_arn wiring
- `terraform validate` passes on complete configuration

## Task Commits

Each task was committed atomically:

1. **Task 1: Create four new Terraform module files and extend variables.tf + outputs.tf** - `058c59c` (feat)
2. **Task 2: Extend main.tf IAM policy_json and add dead_letter_target_arn wiring** - `3a8946b` (feat)

## Files Created/Modified

- `examples/registry-modules-demo/terraform/dynamodb.tf` - DynamoDB table module with for_each over dynamodb_tables, maps partition_key.name/type, billing_mode
- `examples/registry-modules-demo/terraform/sqs.tf` - SQS DLQ module, conditional count on dlq_enabled, 14-day retention, queue name fallback to workflow_name-dlq
- `examples/registry-modules-demo/terraform/sns.tf` - SNS alarm topic module, unconditional, topic_arn passed to alarm_actions
- `examples/registry-modules-demo/terraform/alarms.tf` - Three conditional CloudWatch metric-alarm modules with alarm_by_type locals map
- `examples/registry-modules-demo/terraform/variables.tf` - Extended with 5 new variables (8 total)
- `examples/registry-modules-demo/terraform/outputs.tf` - Extended with 3 new outputs (6 total)
- `examples/registry-modules-demo/terraform/main.tf` - concat() IAM policy_json + dead_letter_target_arn

## Decisions Made

- Used `concat()` with conditional list arrays for IAM policy_json — allows single `policy_json` to include DynamoDB/SQS statements only when those resources exist, avoiding separate `attach_policy_jsons` blocks which require numbering.
- Used `locals { alarm_by_type = { for a in var.alarms : a.type => a } }` for alarm count gating — makes count conditionals readable (`contains(keys(local.alarm_by_type), "error_rate") ? 1 : 0`) and produces stable state keys.
- Used `[]` (empty list) not `null` for false branches in `concat()` — Terraform's concat() requires list types, null would fail at plan time.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ran terraform init to install new registry modules**
- **Found during:** Task 2 verification (terraform validate)
- **Issue:** terraform validate failed with "Module not installed" errors for all 6 new module blocks — .terraform/modules did not have the new modules from dynamodb.tf, sqs.tf, sns.tf, alarms.tf
- **Fix:** Ran `terraform init` in the terraform directory, which downloaded all 6 new modules
- **Files modified:** .terraform/modules/ (not committed — gitignored)
- **Verification:** terraform validate passed after init
- **Committed in:** No separate commit — init output is gitignored

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** terraform init is a prerequisite for validate whenever new module sources are added; running it is part of the normal Terraform workflow. No scope creep.

## Issues Encountered

None beyond the terraform init requirement documented above.

## User Setup Required

None - no external service configuration required for this plan. This plan creates only Terraform configuration files; actual AWS deployment happens in a separate step.

## Next Phase Readiness

- All Terraform infrastructure files are complete and validated
- Phase 58 Plan 02 can proceed: update deploy.sh to generate terraform.tfvars.json, add alarms to workflow.yaml
- Blockers: None

---
*Phase: 58-full-stack-registry-modules*
*Completed: 2026-03-04*
