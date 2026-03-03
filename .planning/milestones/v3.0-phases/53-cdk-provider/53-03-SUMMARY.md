---
phase: 53-cdk-provider
plan: 03
status: complete
---

# Plan 03: CLI Integration (deploy_cmd + doctor_cmd + registry)

## What Was Built
- **CDKProvider registration** in src/rsf/providers/__init__.py as "cdk" provider
- **Provider-generic prerequisite checks** in deploy_cmd replacing hardcoded terraform binary check
- **Provider-aware doctor checks** including dynamic prerequisite detection
- **Terraform severity downgrade** (FAIL -> WARN) in doctor when non-terraform provider is active
- **Updated deploy tests** using provider prerequisite mocking instead of shutil.which patches

## Key Decisions
- Replaced `shutil.which("terraform")` check in `_deploy_full()` with `provider.check_prerequisites(ctx)`
- Deploy tests no longer patch `shutil.which` for the full deploy path (only code-only path retains it)
- Doctor `_check_terraform()` accepts `is_active` parameter to downgrade severity
- Dynamic `_DYNAMIC_ENV_NAMES` set populated at runtime from provider-specific checks
- `_detect_provider()` in doctor loads workflow and resolves infra config, defaults to "terraform"

## Test Results
- 25 deploy tests passing (all updated, zero regressions)
- 23 doctor tests passing (all existing tests pass)
- 52 CDK tests passing (engine + generator + provider)
- 365 total tests passing across CLI/providers/CDK

## Key Files
- `src/rsf/providers/__init__.py` — CDKProvider registered as "cdk"
- `src/rsf/cli/deploy_cmd.py` — provider-generic check_prerequisites() in _deploy_full()
- `src/rsf/cli/doctor_cmd.py` — provider-aware checks, _detect_provider(), is_active parameter
- `tests/test_cli/test_deploy.py` — updated _mock_provider() with check_prerequisites

## Self-Check: PASSED
- [x] CDKProvider is registered in the provider registry as "cdk"
- [x] rsf deploy with CDK provider uses provider.check_prerequisites() (not hardcoded terraform check)
- [x] rsf doctor shows CDK prerequisite checks when CDK provider is configured
- [x] Terraform check in doctor becomes WARN (not FAIL) when CDK provider is active
- [x] All 365 tests pass
