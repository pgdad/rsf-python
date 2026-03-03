---
phase: 52-terraform-provider-deploy-cmd-refactor-and-configuration
plan: 01
status: complete
---

# Plan 01: InfrastructureConfig Models + rsf.toml Loader

## What Was Built
- **TerraformProviderConfig** Pydantic model with tf_dir, backend_bucket, backend_key, backend_dynamodb_table fields
- **InfrastructureConfig** Pydantic model with provider (default "terraform"), terraform, cdk, custom fields
- Both models use `extra="forbid"` consistent with all DSL models
- Added `infrastructure` optional field to **StateMachineDefinition**
- Created **src/rsf/config.py** with `load_project_config()` and `resolve_infra_config()`
- Config cascade: workflow YAML > rsf.toml > hardcoded default "terraform"

## Key Decisions
- Used `dict[str, Any] | None` for cdk and custom config fields (forward compat for Phase 53/54)
- rsf.toml parsed with stdlib `tomllib` (Python 3.12+ requirement satisfied)
- Empty `[infrastructure]` table in rsf.toml returns InfrastructureConfig with defaults (not None)

## Test Results
- 23 tests passing (13 model tests, 10 config tests)
- No regressions in existing test suite (602 tests pass)

## Key Files
- `src/rsf/dsl/models.py` — added TerraformProviderConfig, InfrastructureConfig, and infrastructure field
- `src/rsf/config.py` — new module for rsf.toml loading and config resolution
- `tests/test_dsl/test_infra_config.py` — model validation tests
- `tests/test_config.py` — TOML loading and cascade resolution tests

## Self-Check: PASSED
- [x] InfrastructureConfig validates with extra="forbid"
- [x] StateMachineDefinition.infrastructure field parses from YAML
- [x] rsf.toml loader works with [infrastructure] table
- [x] Cascade resolution: YAML > rsf.toml > default
- [x] All tests pass
