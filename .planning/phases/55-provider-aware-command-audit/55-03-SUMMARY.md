---
phase: 55
plan: 3
status: complete
---

# Plan 55-03 Summary: Watch command provider-based deploy routing

## What was built
Replaced hard-coded `terraform apply` in `rsf watch --deploy` with provider-based deploy routing through the provider interface.

## Key changes
- Removed hard-coded `terraform apply -target=aws_lambda_function.*` subprocess call
- Deploy now routes through `resolve_infra_config()` -> `get_provider()` -> `provider.generate()` + `provider.deploy()`
- ProviderContext created with `auto_approve=True` for watch mode
- Removed unused `shutil` import
- Deploy message now includes provider name

## Key files
- `src/rsf/cli/watch_cmd.py` -- provider-based deploy routing
- `tests/test_cli/test_watch.py` -- 2 updated + 4 new tests (13 total)

## Test results
13/13 tests pass

## Commits
- `feat(55-03): replace hard-coded terraform deploy with provider routing in watch`
