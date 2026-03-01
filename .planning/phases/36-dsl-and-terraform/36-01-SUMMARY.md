---
phase: 36-dsl-and-terraform
plan: 01
subsystem: dsl
tags: [pydantic, enum, lambda-url, validation]

requires:
  - phase: 35-run-all-tests
    provides: clean test baseline (744 tests passing)
provides:
  - LambdaUrlAuthType enum with NONE and AWS_IAM values
  - LambdaUrlConfig Pydantic model with enabled and auth_type fields
  - Optional lambda_url field on StateMachineDefinition
  - Exports from rsf.dsl package
affects: [36-02-terraform-generation, 37-example-workflow]

tech-stack:
  added: []
  patterns: [snake_case alias for RSF extension fields on StateMachineDefinition]

key-files:
  created: []
  modified:
    - src/rsf/dsl/types.py
    - src/rsf/dsl/models.py
    - src/rsf/dsl/__init__.py
    - tests/test_dsl/test_models.py

key-decisions:
  - "Used snake_case alias (lambda_url) for RSF extension field, matching existing rsf_version convention"
  - "Made both enabled and auth_type required fields on LambdaUrlConfig (no defaults)"
  - "Used extra=forbid on LambdaUrlConfig to reject unknown fields"

patterns-established:
  - "RSF extension fields use snake_case aliases; ASL fields use PascalCase aliases"

requirements-completed: [DSL-01, DSL-02]

duration: 5min
completed: 2026-03-01
---

# Plan 36-01: DSL Lambda URL Configuration Summary

**LambdaUrlAuthType enum and LambdaUrlConfig Pydantic model added to RSF DSL with full validation and backward compatibility**

## Performance

- **Duration:** 5 min
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added LambdaUrlAuthType enum (NONE, AWS_IAM) to types.py
- Added LambdaUrlConfig model with enabled (bool) and auth_type (LambdaUrlAuthType) fields
- Attached optional lambda_url field on StateMachineDefinition (default None for backward compatibility)
- Exported both new types from rsf.dsl package
- Added 8 comprehensive tests covering valid parsing, backward compatibility, and validation rejection
- Full test suite passes: 752 tests, 0 failures

## Task Commits

1. **Task 1 + Task 2: LambdaUrlConfig model and full regression check** - `6ec58fa` (feat)

## Files Created/Modified
- `src/rsf/dsl/types.py` - Added LambdaUrlAuthType enum
- `src/rsf/dsl/models.py` - Added LambdaUrlConfig model and lambda_url field on StateMachineDefinition
- `src/rsf/dsl/__init__.py` - Added imports and exports for LambdaUrlConfig and LambdaUrlAuthType
- `tests/test_dsl/test_models.py` - Added TestLambdaUrlConfig class with 8 behavior tests

## Decisions Made
- Used snake_case alias (lambda_url) for RSF extension field, matching existing rsf_version convention
- Made both enabled and auth_type required fields (no defaults) for explicit configuration
- Used extra=forbid on LambdaUrlConfig to reject unknown fields like cors

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
- Ruff flagged unused LambdaUrlConfig import in test file (not directly referenced, only used via StateMachineDefinition). Removed the import.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- LambdaUrlConfig model ready for consumption by Plan 36-02 (Terraform generation)
- definition.lambda_url accessible on parsed StateMachineDefinition objects
- rsf validate CLI automatically handles lambda_url validation via Pydantic

---
*Phase: 36-dsl-and-terraform*
*Completed: 2026-03-01*
