---
phase: 52-terraform-provider-deploy-cmd-refactor-and-configuration
plan: 04
status: complete
---

# Plan 04: validate_cmd Infrastructure Validation

## What Was Built
- **validate_cmd.py** extended with two new validation steps after semantic validation:
  - Step 5: Validate provider name in workflow YAML `infrastructure:` block against registry
  - Step 6: Validate rsf.toml `[infrastructure]` config (both schema and provider name)
- Error messages use `infrastructure.field_path` format for consistency
- Unknown provider errors include available providers list
- Backward compatible: workflows with no `infrastructure:` block and no rsf.toml still pass

## Key Decisions
- Pydantic `extra="forbid"` on InfrastructureConfig catches unknown fields at parse time (step 3)
- Provider name validation happens separately (step 5/6) since Pydantic can't check registry
- rsf.toml validation catches both ValidationError (bad schema) and ProviderNotFoundError (unknown provider)
- ValidationError from rsf.toml prefixes field paths with `infrastructure.` for clarity

## Test Results
- 16 total validate tests passing (8 existing + 8 new)
- 226 total CLI tests passing, no regressions
- New tests cover: valid infra block, unknown provider, unknown field, no infra block (compat), rsf.toml valid, rsf.toml unknown provider, rsf.toml invalid field, error format field path

## Key Files
- `src/rsf/cli/validate_cmd.py` -- infrastructure validation steps added
- `tests/test_cli/test_validate.py` -- 8 new infrastructure validation tests

## Self-Check: PASSED
- [x] Valid infrastructure block passes validation
- [x] Invalid infrastructure block (unknown field) reports error at exit 1
- [x] Unknown provider name reports error with available providers list
- [x] No infrastructure block still passes (backward compat)
- [x] rsf.toml with invalid config caught at validate time
- [x] Error messages use infrastructure.field_path format
- [x] All 16 validate tests pass
- [x] All 226 CLI tests pass (no regressions)
