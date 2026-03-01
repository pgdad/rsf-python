---
phase: 41-alerts-dead-letter-queues-and-multi-stage-deploy
plan: 02
subsystem: dsl, infra
tags: [sqs, dlq, dead-letter-queue, terraform, pydantic, lambda]

requires:
  - phase: 41-alerts-dead-letter-queues-and-multi-stage-deploy
    provides: Alarm DSL extension pattern (plan 01)
provides:
  - DeadLetterQueueConfig Pydantic model
  - dlq.tf.j2 Terraform template for SQS DLQ
  - Lambda dead_letter_config wiring in main.tf.j2
  - DLQ IAM permissions (sqs:SendMessage)
affects: [phase-41-03, phase-42, phase-44]

tech-stack:
  added: []
  patterns: [dlq-lambda-wiring, conditional-dead-letter-config]

key-files:
  created:
    - src/rsf/terraform/templates/dlq.tf.j2
  modified:
    - src/rsf/dsl/models.py
    - src/rsf/dsl/__init__.py
    - src/rsf/dsl/validator.py
    - src/rsf/terraform/generator.py
    - src/rsf/terraform/templates/main.tf.j2
    - src/rsf/terraform/templates/iam.tf.j2
    - src/rsf/cli/deploy_cmd.py
    - tests/test_dsl/test_models.py
    - tests/test_dsl/test_validator.py
    - tests/test_terraform/test_terraform.py

key-decisions:
  - "DLQ uses Lambda dead_letter_config (not SQS redrive policy) since this is for async invocation failures"
  - "max_receive_count stored as informational; Lambda retry is handled by Lambda service (2 retries for async)"
  - "14-day message retention on DLQ queue for debugging window"

patterns-established:
  - "DLQ pattern: single optional config model on StateMachineDefinition, conditional Terraform generation"

requirements-completed: [DSL-05]

duration: 6min
completed: 2026-03-01
---

# Plan 41-02: Dead Letter Queue DSL and Terraform Summary

**SQS dead letter queue with Lambda dead_letter_config wiring, configurable max_receive_count, and scoped IAM permissions**

## Performance

- **Duration:** 6 min
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- DeadLetterQueueConfig Pydantic model with enabled, max_receive_count (1-1000), queue_name
- dlq.tf.j2 generates SQS DLQ with 14-day retention and optional custom queue name
- main.tf.j2 conditionally adds dead_letter_config block to Lambda resource
- iam.tf.j2 conditionally adds DLQSendMessage permission scoped to DLQ ARN
- Semantic validation warns on unusually high max_receive_count (>100)
- 20 new tests, 325 total passing with zero regressions

## Task Commits

1. **Task 1: Add DLQ Pydantic model and semantic validation** - `6f6cf3b` (feat)
2. **Task 2: Add Terraform DLQ generation, Lambda wiring, and IAM permissions** - `8611e35` (feat)

## Files Created/Modified
- `src/rsf/dsl/models.py` - Added DeadLetterQueueConfig; added dead_letter_queue field to StateMachineDefinition
- `src/rsf/dsl/__init__.py` - Exported DeadLetterQueueConfig
- `src/rsf/dsl/validator.py` - Added _validate_dlq semantic validation
- `src/rsf/terraform/generator.py` - Added dlq fields to TerraformConfig
- `src/rsf/terraform/templates/dlq.tf.j2` - New SQS DLQ template
- `src/rsf/terraform/templates/main.tf.j2` - Added conditional dead_letter_config block
- `src/rsf/terraform/templates/iam.tf.j2` - Added DLQSendMessage IAM permission
- `src/rsf/cli/deploy_cmd.py` - Wire DLQ config from DSL to TerraformConfig

## Decisions Made
- Used Lambda dead_letter_config (not SQS redrive policy) for async invocation failure capture
- 14-day message retention on DLQ for debugging window
- IAM permission scoped to specific DLQ ARN (not wildcard)

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DLQ support complete
- Ready for Plan 41-03 (Multi-stage deployment)

---
*Plan: 41-02*
*Completed: 2026-03-01*
