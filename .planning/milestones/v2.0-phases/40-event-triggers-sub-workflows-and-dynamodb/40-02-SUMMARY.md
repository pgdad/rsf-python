---
phase: 40-event-triggers-sub-workflows-and-dynamodb
plan: 02
subsystem: dsl
tags: [pydantic, sub-workflow, codegen, boto3, lambda-invoke, orchestrator]

requires:
  - phase: 30-codegen
    provides: Orchestrator template, emitter, state_mappers BFS infrastructure
provides:
  - SubWorkflowRef model for declaring child workflows
  - SubWorkflow field on TaskState for referencing child workflows
  - Semantic validation for sub-workflow references (undeclared, unused)
  - Generated orchestrator code with boto3 Lambda invoke for sub-workflows
  - RSF_NAME_PREFIX env var for child workflow function name resolution
affects: [codegen, orchestrator-template, workflow-composition]

tech-stack:
  added: []
  patterns: [sub-workflow-invocation, conditional-boto3-import, rsf-name-prefix-convention]

key-files:
  created: []
  modified:
    - src/rsf/dsl/models.py
    - src/rsf/dsl/__init__.py
    - src/rsf/dsl/validator.py
    - src/rsf/codegen/generator.py
    - src/rsf/codegen/state_mappers.py
    - src/rsf/codegen/emitter.py
    - src/rsf/codegen/templates/orchestrator.py.j2
    - tests/test_dsl/test_models.py
    - tests/test_dsl/test_validator.py
    - tests/test_codegen/test_generator.py

key-decisions:
  - "SubWorkflow uses PascalCase alias (ASL convention for state fields)"
  - "sub_workflows uses snake_case alias (RSF extension convention for top-level fields)"
  - "Child workflow function name resolved via RSF_NAME_PREFIX env var at runtime"
  - "Sub-workflow tasks skip handler stub generation (invoke Lambda, not local handler)"

patterns-established:
  - "Sub-workflow invocation: boto3 lambda_client.invoke with RequestResponse"
  - "Sub-workflow task states do not generate handler imports or stubs"

requirements-completed: [DSL-02]

duration: 10min
completed: 2026-03-01
---

# Plan 40-02: Sub-Workflow Invocation Summary

**Sub-workflow DSL support with TaskState SubWorkflow field, semantic validation, and generated boto3 Lambda invoke code**

## Performance

- **Duration:** 10 min
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- TaskState accepts optional SubWorkflow field referencing child workflows by name
- StateMachineDefinition accepts sub_workflows list for declaring available child workflows
- Semantic validator catches undeclared sub-workflow references and warns about unused declarations
- Generated orchestrator code invokes child workflows via boto3 Lambda invoke
- Conditional boto3/json imports only when sub-workflows are used

## Task Commits

1. **Task 1: Sub-workflow models and semantic validation** - `b80b94c` (feat)
2. **Task 2: Orchestrator code generation for sub-workflows** - `b326b14` (feat)

## Files Created/Modified
- `src/rsf/dsl/models.py` - SubWorkflowRef model, SubWorkflow field on TaskState, sub_workflows on SMD
- `src/rsf/dsl/validator.py` - _validate_sub_workflows with recursive state walking
- `src/rsf/codegen/state_mappers.py` - sub_workflow field on StateMapping
- `src/rsf/codegen/emitter.py` - Lambda invoke code emission for sub-workflow tasks
- `src/rsf/codegen/generator.py` - has_sub_workflows context, skip handler stubs for sub-workflow tasks
- `src/rsf/codegen/templates/orchestrator.py.j2` - Conditional boto3/json/os imports

## Decisions Made
- SubWorkflow uses PascalCase (ASL state field convention); sub_workflows uses snake_case (RSF extension)
- RSF_NAME_PREFIX env var defaults to "rsf" for child workflow function name construction

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
None

## Next Phase Readiness
- Sub-workflow composition pattern established
- Ready for DynamoDB table definitions (Plan 40-03)

---
*Phase: 40-event-triggers-sub-workflows-and-dynamodb*
*Completed: 2026-03-01*
