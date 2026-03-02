---
phase: 40-event-triggers-sub-workflows-and-dynamodb
plan: 01
subsystem: dsl
tags: [pydantic, eventbridge, sqs, sns, terraform, jinja2, triggers]

requires:
  - phase: 37-lambda-function-url
    provides: LambdaUrlConfig pattern for DSL extension fields and conditional Terraform generation
provides:
  - EventBridgeTrigger, SQSTrigger, SNSTrigger Pydantic models with discriminated union
  - Semantic validation for trigger configurations
  - triggers.tf.j2 Terraform template for trigger resources
  - Conditional SQS IAM permissions in iam.tf.j2
  - deploy_cmd.py wiring for trigger config to TerraformConfig
affects: [40-03-dynamodb, terraform-generation, iam-permissions]

tech-stack:
  added: []
  patterns: [discriminated-union-triggers, conditional-terraform-templates, hcl-jinja2-delimiters]

key-files:
  created:
    - src/rsf/terraform/templates/triggers.tf.j2
  modified:
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
  - "Used discriminated union with type field for trigger dispatch (eventbridge/sqs/sns)"
  - "SQS uses IAM role policy; EventBridge and SNS use resource-based lambda permissions"
  - "Triggers field uses snake_case alias following RSF extension convention"

patterns-established:
  - "Discriminated union pattern: Annotated[Union[...], Field(discriminator='type')]"
  - "Conditional Terraform template skip: if filename == 'X' and not config.X: continue"

requirements-completed: [DSL-01]

duration: 12min
completed: 2026-03-01
---

# Plan 40-01: Event Trigger Support Summary

**EventBridge, SQS, and SNS trigger models with Pydantic discriminated union, semantic validation, Terraform generation, and conditional IAM permissions**

## Performance

- **Duration:** 12 min
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Three trigger types (EventBridge, SQS, SNS) parse from workflow.yaml via discriminated union
- Semantic validator catches EventBridge missing both schedule/pattern, warns on large SQS batch sizes
- triggers.tf.j2 generates correct Terraform resources for all three trigger types
- IAM template conditionally includes SQS permissions when SQS triggers are configured
- Full backward compatibility maintained

## Task Commits

1. **Task 1: Trigger Pydantic models and semantic validation** - `9ed67bd` (feat)
2. **Task 2: Terraform trigger generation and IAM permissions** - `b66492c` (feat)

## Files Created/Modified
- `src/rsf/dsl/models.py` - EventBridgeTrigger, SQSTrigger, SNSTrigger models + TriggerConfig union
- `src/rsf/dsl/validator.py` - _validate_triggers semantic validation
- `src/rsf/terraform/templates/triggers.tf.j2` - HCL template for trigger resources
- `src/rsf/terraform/templates/iam.tf.j2` - Conditional SQS IAM permissions
- `src/rsf/terraform/generator.py` - triggers/has_sqs_triggers fields on TerraformConfig
- `src/rsf/cli/deploy_cmd.py` - Wiring DSL trigger config to TerraformConfig

## Decisions Made
- Used discriminated union on "type" field for trigger dispatch
- SQS uses IAM role policy (pull model); EventBridge/SNS use resource-based permissions (push model)

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
None

## Next Phase Readiness
- Trigger infrastructure patterns established for future trigger types
- IAM template extension pattern ready for DynamoDB permissions (Plan 40-03)

---
*Phase: 40-event-triggers-sub-workflows-and-dynamodb*
*Completed: 2026-03-01*
