---
phase: 41-alerts-dead-letter-queues-and-multi-stage-deploy
plan: 01
subsystem: dsl, infra
tags: [cloudwatch, alarms, sns, terraform, pydantic]

requires:
  - phase: 40-event-triggers-sub-workflows-and-dynamodb
    provides: DSL extension pattern (Pydantic models, validator, Terraform generation)
provides:
  - AlarmConfig discriminated union (ErrorRateAlarm, DurationAlarm, ThrottleAlarm)
  - Semantic validation for alarm configurations
  - alarms.tf.j2 Terraform template with CloudWatch metric alarms
  - SNS notification topic auto-creation
  - IAM SNS publish permissions
affects: [phase-41-02, phase-41-03, phase-42, phase-44]

tech-stack:
  added: []
  patterns: [alarm-config-discriminated-union, conditional-sns-topic-creation]

key-files:
  created:
    - src/rsf/terraform/templates/alarms.tf.j2
  modified:
    - src/rsf/dsl/types.py
    - src/rsf/dsl/models.py
    - src/rsf/dsl/__init__.py
    - src/rsf/dsl/validator.py
    - src/rsf/terraform/generator.py
    - src/rsf/terraform/templates/iam.tf.j2
    - src/rsf/cli/deploy_cmd.py
    - tests/test_dsl/test_models.py
    - tests/test_dsl/test_validator.py
    - tests/test_terraform/test_terraform.py

key-decisions:
  - "AlarmConfig uses discriminated union on 'type' field, same pattern as TriggerConfig"
  - "SNS topic auto-created when no sns_topic_arn provided; existing topic ARN used otherwise"
  - "IAM SNS publish uses Resource = '*' to cover both auto-generated and user-provided topics"

patterns-established:
  - "Alarm config pattern: Pydantic model with extra=forbid, discriminated union, semantic validation, Terraform template"

requirements-completed: [DSL-04]

duration: 8min
completed: 2026-03-01
---

# Plan 41-01: CloudWatch Alarm DSL and Terraform Summary

**CloudWatch alarm models (error_rate, duration, throttle) with Pydantic validation, semantic checks, and Terraform generation including auto-created SNS notification topics**

## Performance

- **Duration:** 8 min
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- ErrorRateAlarm, DurationAlarm, ThrottleAlarm Pydantic models with extra=forbid
- AlarmConfig discriminated union dispatches on 'type' field
- Semantic validation catches error rate >100%, empty list, duplicate types
- alarms.tf.j2 generates CloudWatch metric alarms with correct metrics per type
- SNS topic auto-created when no sns_topic_arn; existing ARN used when provided
- IAM permissions conditionally include SNS publish
- 25 new tests, 305 total passing with zero regressions

## Task Commits

1. **Task 1: Add CloudWatch alarm Pydantic models and semantic validation** - `ac25953` (feat)
2. **Task 2: Add Terraform alarm generation with SNS notification targets** - `b45cac4` (feat)

## Files Created/Modified
- `src/rsf/dsl/types.py` - Added AlarmType enum
- `src/rsf/dsl/models.py` - Added ErrorRateAlarm, DurationAlarm, ThrottleAlarm, AlarmConfig; added alarms field to StateMachineDefinition
- `src/rsf/dsl/__init__.py` - Exported new alarm types
- `src/rsf/dsl/validator.py` - Added _validate_alarms semantic validation
- `src/rsf/terraform/generator.py` - Added alarms/has_alarms to TerraformConfig and context
- `src/rsf/terraform/templates/alarms.tf.j2` - New template for CloudWatch alarms with SNS topics
- `src/rsf/terraform/templates/iam.tf.j2` - Added SNSAlarmPublish conditional IAM statement
- `src/rsf/cli/deploy_cmd.py` - Wire alarm config from DSL to TerraformConfig

## Decisions Made
- Used discriminated union pattern (same as TriggerConfig) for alarm type dispatch
- Auto-create shared SNS topic only when at least one alarm has no sns_topic_arn
- IAM SNS publish uses Resource = "*" to handle both auto-generated and user-provided topics

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Alarm models and Terraform generation complete
- Ready for Plan 41-02 (Dead Letter Queue support)

---
*Plan: 41-01*
*Completed: 2026-03-01*
