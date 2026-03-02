---
phase: 52-terraform-provider-deploy-cmd-refactor-and-configuration
plan: 03
status: complete
---

# Plan 03: deploy_cmd Refactor to Provider Interface

## What Was Built
- **deploy_cmd.py** fully refactored: removed ~80-LOC inline infrastructure extraction block
- All infrastructure operations now route through `get_provider()` / `provider.generate()` / `provider.deploy()`
- Replaced direct `TerraformConfig` construction and `generate_terraform()` calls with provider interface
- `--output-dir` replaces `--tf-dir` as canonical option name (`--tf-dir` kept as hidden alias)
- Added `--code-only` guard that errors for non-terraform providers with clear message
- Added unknown provider error handling via `ProviderNotFoundError`
- `--auto-approve`, `--stage`, and `stage_var_file` flow through `ProviderContext`

## Key Decisions
- Kept `_deploy_code_only()` as Terraform-specific (direct subprocess call for targeted apply) since `--code-only` is explicitly gated to terraform provider only
- Used `resolve_infra_config()` for config cascade (YAML > rsf.toml > default) before provider dispatch
- Used `create_metadata()` to build `WorkflowMetadata` from definition, replacing the inline extraction
- `_deploy_full()` now takes `(provider, ctx)` instead of building TerraformConfig inline

## Test Results
- 25 tests passing (all existing scenarios preserved + 4 new tests)
- New tests: `test_deploy_output_dir_option`, `test_deploy_tf_dir_alias_still_works`, `test_deploy_code_only_non_terraform_errors`, `test_deploy_unknown_provider_errors`
- No regressions

## Key Files
- `src/rsf/cli/deploy_cmd.py` -- refactored deploy command using provider interface
- `tests/test_cli/test_deploy.py` -- updated tests for provider-based flow

## Self-Check: PASSED
- [x] deploy_cmd.py no longer contains direct TerraformConfig or generate_terraform imports
- [x] deploy_cmd.py calls get_provider(), provider.generate(), provider.deploy()
- [x] ~80-LOC extraction block removed, replaced by create_metadata()
- [x] --output-dir replaces --tf-dir (hidden alias kept)
- [x] --code-only errors for non-terraform providers
- [x] --auto-approve and --stage work through provider interface
- [x] All 25 tests pass
