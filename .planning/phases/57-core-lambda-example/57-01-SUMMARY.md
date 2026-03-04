---
phase: 57-core-lambda-example
plan: 01
subsystem: cli
tags: [typer, pytest, tdd, lambda, step-functions, dynamodb, handlers, registry]

# Dependency graph
requires:
  - phase: 56-schema-verification
    provides: confirmed durable_config variable names and Lambda alias convention
provides:
  - "--teardown flag on rsf deploy CLI with provider.teardown(ctx) routing"
  - "image-processing example with 4 Task state handlers registered via @state decorator"
  - "workflow.yaml with dynamodb_tables and dead_letter_queue declarations"
  - "16 handler unit tests in examples/registry-modules-demo/tests/"
affects: [57-core-lambda-example, deploy.sh, Terraform phase plans]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD workflow: write failing tests first, implement to pass, verify GREEN"
    - "@state decorator handler pattern: one file per Task state"
    - "conftest.py clean_registry pattern for example test isolation"

key-files:
  created:
    - examples/registry-modules-demo/workflow.yaml
    - examples/registry-modules-demo/handlers/__init__.py
    - examples/registry-modules-demo/handlers/validate_image.py
    - examples/registry-modules-demo/handlers/resize_image.py
    - examples/registry-modules-demo/handlers/analyze_content.py
    - examples/registry-modules-demo/handlers/catalogue_image.py
    - examples/registry-modules-demo/tests/conftest.py
    - examples/registry-modules-demo/tests/test_handlers.py
  modified:
    - src/rsf/cli/deploy_cmd.py
    - tests/test_cli/test_deploy.py

key-decisions:
  - "--teardown dispatch placed after Step 8 (ctx creation) so provider receives full ProviderContext"
  - "workflow.yaml uses table_name/partition_key object schema matching DynamoDBTableConfig Pydantic model (not name/partition_key_type flat keys)"
  - "_teardown_infra catches CalledProcessError and NotImplementedError separately for distinct error messages"

patterns-established:
  - "teardown_pattern: _teardown_infra(provider, ctx) function mirrors _deploy_full(provider, ctx) structure"
  - "handler_file_pattern: one handler per Task state, @state decorator, _log helper, custom Exception class in validate handlers"

requirements-completed: [TOOL-01, EXAM-01, EXAM-02, EXAM-03]

# Metrics
duration: 20min
completed: 2026-03-04
---

# Phase 57 Plan 01: Core Lambda Example Summary

**rsf deploy --teardown flag routing to provider.teardown(ctx), plus image-processing example with 4 @state handlers, DynamoDB/DLQ workflow YAML, and 16 passing unit tests**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-04T13:22:00Z
- **Completed:** 2026-03-04T13:42:46Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Added `--teardown` flag to `rsf deploy` with provider.teardown(ctx) dispatch, mutual exclusion checks against --code-only and --no-infra, and graceful error handling for CalledProcessError and NotImplementedError
- Created image-processing workflow.yaml with 4 Task states (ValidateImage, ResizeImage, AnalyzeContent, CatalogueImage), dynamodb_tables declaration, and dead_letter_queue configuration — all parsing correctly via RSF Pydantic DSL
- Built 4 handler files following the @state decorator pattern established by the order-processing example
- Added 16 handler unit tests covering valid inputs, invalid formats, size limits, error raises, dimension computation, confidence scores, and ISO timestamp generation

## Task Commits

Each task was committed atomically:

1. **Task 1: Add --teardown flag to rsf deploy CLI** - `aa73cf4` (feat, TDD)
2. **Task 2: Create workflow YAML, handlers, and handler tests** - `d5aed42` (feat)

## Files Created/Modified
- `src/rsf/cli/deploy_cmd.py` - Added teardown parameter, mutual exclusion check, _teardown_infra() function
- `tests/test_cli/test_deploy.py` - Added 6 TDD test cases for teardown behavior
- `examples/registry-modules-demo/workflow.yaml` - Image processing pipeline with 6 states, DynamoDB table, DLQ
- `examples/registry-modules-demo/handlers/__init__.py` - Empty package init
- `examples/registry-modules-demo/handlers/validate_image.py` - ValidateImage handler, InvalidImageError, format/size validation
- `examples/registry-modules-demo/handlers/resize_image.py` - ResizeImage handler, aspect ratio computation
- `examples/registry-modules-demo/handlers/analyze_content.py` - AnalyzeContent handler, format-to-tags simulation
- `examples/registry-modules-demo/handlers/catalogue_image.py` - CatalogueImage handler, ISO timestamp
- `examples/registry-modules-demo/tests/conftest.py` - clean_registry fixture with module cache purge
- `examples/registry-modules-demo/tests/test_handlers.py` - 16 unit tests across all 4 handlers

## Decisions Made
- Placed --teardown dispatch after Step 8 (ctx creation) so provider.teardown receives a full ProviderContext — tear-down needs the same metadata (workflow name, output_dir, stage) as a full deploy
- workflow.yaml DynamoDB schema uses `table_name` and `partition_key: {name: ..., type: ...}` object structure matching the Pydantic `DynamoDBTableConfig` model (initial attempt using `name`/`partition_key_type` flat keys was rejected by validation)
- _teardown_infra catches CalledProcessError and NotImplementedError in separate except clauses for distinct, actionable error messages

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed workflow.yaml DynamoDB table schema to match Pydantic model**
- **Found during:** Task 2 (workflow YAML creation)
- **Issue:** Initial workflow.yaml used `name`/`partition_key_type` flat fields; actual DynamoDBTableConfig model requires `table_name` and `partition_key` as an object `{name: ..., type: ...}`
- **Fix:** Updated workflow.yaml to use correct field names per the Pydantic schema
- **Files modified:** examples/registry-modules-demo/workflow.yaml
- **Verification:** `load_definition(workflow.yaml)` returns correct DynamoDBTableConfig objects
- **Committed in:** d5aed42 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Schema correction was necessary for correctness. No scope creep.

## Issues Encountered
- Pre-existing test failures in tests/test_editor/test_server.py and tests/test_inspect/test_replay.py due to missing `httpx` module — unrelated to this plan's changes. All deploy and DSL tests pass.

## Next Phase Readiness
- --teardown CLI flag ready for use in deploy.sh teardown script
- Example application (workflow.yaml + 4 handlers) ready for Terraform deploy scaffold in Phase 57 plan 02+
- handler tests provide regression coverage as the example evolves

---
*Phase: 57-core-lambda-example*
*Completed: 2026-03-04*
