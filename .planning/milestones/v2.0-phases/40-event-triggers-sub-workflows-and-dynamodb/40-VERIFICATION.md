---
phase: 40
status: passed
verified: 2026-03-02
requirements: [DSL-01, DSL-02, DSL-03]
---

# Phase 40: Event Triggers, Sub-Workflows, and DynamoDB — Verification

## Phase Goal

> Users can configure EventBridge, SQS, and SNS as workflow triggers, invoke child workflows from a parent, and define DynamoDB tables directly in the DSL

## Success Criteria Verification

### SC1: Event source triggers produce corresponding Terraform
**Status: PASSED**

- User can declare EventBridge rules, SQS queues, or SNS subscriptions as trigger sources in workflow.yaml
- `rsf generate` produces the corresponding Terraform via triggers.tf.j2
- Three trigger types (EventBridge, SQS, SNS) parse via discriminated union on `type` field
- Semantic validator catches EventBridge missing both schedule and event pattern, warns on large SQS batch sizes
- IAM template conditionally includes SQS permissions when SQS triggers are configured

**Evidence:**
- `src/rsf/dsl/models.py` — EventBridgeTrigger, SQSTrigger, SNSTrigger Pydantic models with discriminated union
- `src/rsf/dsl/validator.py` — `_validate_triggers` semantic validation
- `src/rsf/terraform/templates/triggers.tf.j2` — HCL template for trigger resources
- `src/rsf/terraform/templates/iam.tf.j2` — Conditional SQS IAM permissions
- `src/rsf/terraform/generator.py` — triggers/has_sqs_triggers fields on TerraformConfig
- `src/rsf/cli/deploy_cmd.py` — Wiring DSL trigger config to TerraformConfig
- Tests: `tests/test_dsl/test_models.py`, `tests/test_dsl/test_validator.py`, `tests/test_terraform/test_terraform.py`

### SC2: Sub-workflow invocation by name
**Status: PASSED**

- User can reference a child workflow by name inside a parent workflow state
- Generated orchestrator code invokes child workflows via boto3 Lambda invoke with RequestResponse
- TaskState accepts optional SubWorkflow field referencing child workflows by name
- StateMachineDefinition accepts sub_workflows list for declaring available child workflows
- Conditional boto3/json imports only when sub-workflows are used
- Sub-workflow tasks skip handler stub generation (invoke Lambda, not local handler)

**Evidence:**
- `src/rsf/dsl/models.py` — SubWorkflowRef model, SubWorkflow field on TaskState, sub_workflows on SMD
- `src/rsf/dsl/validator.py` — `_validate_sub_workflows` with recursive state walking
- `src/rsf/codegen/state_mappers.py` — sub_workflow field on StateMapping
- `src/rsf/codegen/emitter.py` — Lambda invoke code emission for sub-workflow tasks
- `src/rsf/codegen/generator.py` — has_sub_workflows context, skip handler stubs
- `src/rsf/codegen/templates/orchestrator.py.j2` — Conditional boto3/json/os imports
- Tests: `tests/test_dsl/test_models.py`, `tests/test_dsl/test_validator.py`, `tests/test_codegen/test_generator.py`

### SC3: DynamoDB table definitions in DSL
**Status: PASSED**

- User can define DynamoDB table schemas in workflow.yaml with partition key, optional sort key, and billing mode
- `rsf generate` produces Terraform table definitions via dynamodb.tf.j2
- Correct IAM permissions scoped to specific table ARNs (least-privilege)
- DynamoDBBillingMode and DynamoDBAttributeType enums in types.py
- Semantic validator catches PROVISIONED billing without capacities, duplicate table names, empty lists

**Evidence:**
- `src/rsf/dsl/types.py` — DynamoDBBillingMode, DynamoDBAttributeType enums
- `src/rsf/dsl/models.py` — DynamoDBAttribute, DynamoDBTableConfig models, dynamodb_tables field
- `src/rsf/dsl/validator.py` — `_validate_dynamodb_tables` semantic validation
- `src/rsf/terraform/generator.py` — dynamodb_tables/has_dynamodb_tables fields, skip logic, context
- `src/rsf/terraform/templates/dynamodb.tf.j2` — HCL template for DynamoDB table resources
- `src/rsf/terraform/templates/iam.tf.j2` — Conditional DynamoDB IAM permissions (8 CRUD actions)
- `src/rsf/cli/deploy_cmd.py` — DynamoDB config wiring to TerraformConfig
- Tests: `tests/test_dsl/test_models.py`, `tests/test_dsl/test_validator.py`, `tests/test_terraform/test_terraform.py`

### SC4: rsf validate catches invalid trigger configs and unknown sub-workflow references
**Status: PASSED**

- EventBridge triggers require either schedule_expression or event_pattern (semantic validation)
- Large SQS batch sizes produce warnings
- Undeclared sub-workflow references are caught as errors
- Unused sub-workflow declarations produce warnings
- PROVISIONED billing mode without read/write capacity is rejected
- Duplicate table names are caught

**Evidence:**
- `src/rsf/dsl/validator.py` — `_validate_triggers`, `_validate_sub_workflows`, `_validate_dynamodb_tables`
- Tests in `tests/test_dsl/test_validator.py` covering all error scenarios

## Requirements Cross-Reference

| Requirement | Status | Verified By |
|-------------|--------|-------------|
| DSL-01 | Complete | SC1: EventBridge, SQS, SNS trigger models + Terraform generation |
| DSL-02 | Complete | SC2: Sub-workflow invocation by name with boto3 Lambda invoke |
| DSL-03 | Complete | SC3: DynamoDB table definitions with Terraform and IAM |

## Test Coverage

- **Phase 40 test suite:** 211 tests pass (verified 2026-03-02)
- **Plan 40-01 (Triggers):** 10 files modified, discriminated union + Terraform generation
- **Plan 40-02 (Sub-workflows):** 10 files modified, boto3 invoke + semantic validation
- **Plan 40-03 (DynamoDB):** 11 files modified, table models + IAM permissions
- **Regressions:** None

## Commits

1. `9ed67bd` feat(40-01): trigger Pydantic models and semantic validation
2. `b66492c` feat(40-01): Terraform trigger generation and IAM permissions
3. `b80b94c` feat(40-02): sub-workflow models and semantic validation
4. `b326b14` feat(40-02): orchestrator code generation for sub-workflows
5. `8bb1e9d` feat(40-03): DynamoDB Pydantic models and semantic validation
6. `c35fc9e` feat(40-03): Terraform DynamoDB generation and IAM permissions

## Verdict

**PASSED** -- All 4 success criteria verified. All requirements (DSL-01, DSL-02, DSL-03) are complete. 211 tests pass with zero regressions. Phase 40 delivers event triggers, sub-workflow invocation, and DynamoDB table definitions as fully integrated DSL extensions.
