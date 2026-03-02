---
phase: 40-event-triggers-sub-workflows-and-dynamodb
plan: 03
subsystem: dsl, terraform
tags: [pydantic, dynamodb, terraform, iam, jinja2, hcl]

requires:
  - phase: 40-01
    provides: Trigger models, IAM template with SQS conditional, trigger Terraform generation
provides:
  - DynamoDBTableConfig, DynamoDBAttribute Pydantic models with billing mode and attribute types
  - Semantic validation for DynamoDB configurations (PROVISIONED without capacities, duplicates)
  - dynamodb.tf.j2 Terraform template for aws_dynamodb_table resources
  - Conditional DynamoDB IAM permissions in iam.tf.j2 scoped to specific table ARNs
  - deploy_cmd.py wiring for DynamoDB config to TerraformConfig
affects: [dsl-models, terraform-generation, iam-permissions, deploy-pipeline]

tech-stack:
  added: []
  patterns: [dynamodb-table-definition, conditional-iam-permissions, hcl-jinja2-delimiters]

key-files:
  created:
    - src/rsf/terraform/templates/dynamodb.tf.j2
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
  - "DynamoDB enums (DynamoDBBillingMode, DynamoDBAttributeType) in types.py following existing pattern"
  - "DynamoDB models use extra=forbid and snake_case field names (RSF extension convention)"
  - "IAM permissions scoped to specific table ARNs via Terraform resource references (least-privilege)"
  - "DynamoDB IAM conditional placed between SQS and Lambda URL conditionals in iam.tf.j2"

patterns-established:
  - "DynamoDB table definition: partition_key + optional sort_key + billing_mode"
  - "Conditional DynamoDB IAM permissions with 8 CRUD actions including batch operations"

requirements-completed: [DSL-03]

duration: 8min
completed: 2026-03-01
---

# Plan 40-03: DynamoDB Table Definitions Summary

**DynamoDB table definition DSL support with Pydantic models, semantic validation, Terraform generation, and least-privilege IAM permissions**

## Performance

- **Duration:** 8 min
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- DynamoDBTableConfig and DynamoDBAttribute Pydantic models with extra=forbid
- DynamoDBBillingMode and DynamoDBAttributeType enums in types.py
- StateMachineDefinition accepts optional dynamodb_tables list (snake_case RSF extension)
- Semantic validator catches PROVISIONED billing without capacities, duplicate table names, empty lists
- dynamodb.tf.j2 generates aws_dynamodb_table resources with hash/range keys and billing modes
- IAM template conditionally includes DynamoDB CRUD permissions scoped to specific table ARNs
- deploy_cmd.py wires DSL DynamoDB config to TerraformConfig
- Full backward compatibility maintained (667 tests pass)

## Task Commits

1. **Task 1: DynamoDB Pydantic models and semantic validation** - `8bb1e9d` (feat)
2. **Task 2: Terraform DynamoDB generation and IAM permissions** - `c35fc9e` (feat)

## Files Created/Modified
- `src/rsf/dsl/types.py` - DynamoDBBillingMode, DynamoDBAttributeType enums
- `src/rsf/dsl/models.py` - DynamoDBAttribute, DynamoDBTableConfig models, dynamodb_tables field
- `src/rsf/dsl/__init__.py` - New model and enum exports
- `src/rsf/dsl/validator.py` - _validate_dynamodb_tables semantic validation
- `src/rsf/terraform/generator.py` - dynamodb_tables/has_dynamodb_tables fields, skip logic, context
- `src/rsf/terraform/templates/dynamodb.tf.j2` - HCL template for DynamoDB table resources
- `src/rsf/terraform/templates/iam.tf.j2` - Conditional DynamoDB IAM permissions block
- `src/rsf/cli/deploy_cmd.py` - DynamoDB config wiring to TerraformConfig

## Decisions Made
- Enums follow existing types.py pattern (DynamoDBBillingMode, DynamoDBAttributeType)
- IAM permissions use 8 DynamoDB CRUD actions including batch operations (least-privilege)
- DynamoDB IAM conditional placed between SQS and Lambda URL conditionals in iam.tf.j2

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
None

## Next Phase Readiness
- DynamoDB table definition pattern established
- Phase 40 complete: triggers, sub-workflows, and DynamoDB all implemented

---
*Phase: 40-event-triggers-sub-workflows-and-dynamodb*
*Completed: 2026-03-01*
