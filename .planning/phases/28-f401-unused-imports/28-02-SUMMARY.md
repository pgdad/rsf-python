---
phase: 28-f401-unused-imports
plan: 02
subsystem: linting
tags: [ruff, F401, unused-imports, code-quality, pyproject]

# Dependency graph
requires:
  - phase: 28-01
    provides: "Zero F401 violations in src/, tests/, examples/ (at time of 28-01)"
provides:
  - "pyproject.toml ruff config without examples/ exclusion (already done in b249df0)"
  - "F401 removed from global ruff ignore list (already done in b249df0)"
  - "Zero F401 violations across entire codebase after v3.0 additions"
affects: [29-f841-unused-variables, 30-f541-fstrings, 31-e402-module-level-imports, 32-e741-ambiguous-names]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ruff --fix for auto-correcting lint violations in bulk"

key-files:
  created: []
  modified:
    - pyproject.toml
    - src/rsf/cli/diff_cmd.py
    - src/rsf/cli/deploy_cmd.py
    - src/rsf/cli/export_cmd.py
    - src/rsf/cli/watch_cmd.py
    - src/rsf/providers/metadata.py
    - src/rsf/providers/transports.py
    - tests/test_cdk/test_generator.py
    - tests/test_cli/test_cost.py
    - tests/test_cli/test_diff.py
    - tests/test_cli/test_doctor.py
    - tests/test_cli/test_export.py
    - tests/test_cli/test_logs.py
    - tests/test_cli/test_test_cmd.py
    - tests/test_cli/test_watch.py
    - tests/test_dsl/test_models.py
    - tests/test_inspect/test_replay.py
    - tests/test_providers/test_base.py
    - tests/test_providers/test_cdk_provider.py
    - tests/test_providers/test_custom_integration.py
    - tests/test_providers/test_custom_provider.py
    - tests/test_providers/test_metadata.py
    - tests/test_providers/test_terraform_provider.py
    - tests/test_providers/test_transports.py

key-decisions:
  - "pyproject.toml changes (exclude removal, F401 from ignore) were already committed in b249df0 from a prior partial execution"
  - "34 F401 violations from v3.0 development auto-fixed using ruff --fix; all are auto-fixable trivial unused imports"

patterns-established:
  - "ruff --fix for bulk auto-correction of lint violations when all are marked as fixable"

requirements-completed: [CONF-01, F401-06]

# Metrics
duration: 10min
completed: 2026-03-03
---

# Phase 28 Plan 02: Ruff Config Strictification Summary

**Removed examples/ exclusion and F401 from ruff ignore list; fixed 34 F401 violations introduced during v3.0 development so entire codebase is now clean**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-03T00:00:00Z
- **Completed:** 2026-03-03T00:10:00Z
- **Tasks:** 1
- **Files modified:** 24

## Accomplishments
- Confirmed pyproject.toml ruff config was already updated in prior partial execution (commit b249df0): `exclude = ["examples"]` removed and `"F401"` removed from ignore list
- Fixed 34 F401 violations introduced during v3.0 Pluggable Infrastructure Providers development (phases 51-55 added new files with unused imports)
- All 34 violations were auto-fixable (ruff --fix); removed unused typing.Any, pathlib.Path, pytest, os, json, time, datetime.timedelta, unittest.mock.patch/call, and various rsf module imports
- 1224 tests pass after fixes (integration tests require AWS credentials, pre-existing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Update pyproject.toml ruff config and verify full codebase** - `b249df0` (fix) — pyproject.toml changes (prior execution)
2. **Task 1 continuation: Fix 34 F401 violations from v3.0 development** - `0e0c590` (fix)

## Files Created/Modified
- `pyproject.toml` - Removed `exclude = ["examples"]` from [tool.ruff], removed "F401" from ignore list (committed in b249df0)
- `src/rsf/cli/diff_cmd.py` - Removed unused `typing.Any`
- `src/rsf/cli/deploy_cmd.py` - Removed unused imports (noted in status)
- `src/rsf/cli/export_cmd.py` - Removed unused imports
- `src/rsf/cli/watch_cmd.py` - Removed unused imports
- `src/rsf/providers/metadata.py` - Removed unused imports
- `src/rsf/providers/transports.py` - Removed unused `typing.Any`
- `tests/test_cdk/test_generator.py` - Removed unused `pathlib.Path` and `CDKResult`
- `tests/test_cli/test_cost.py` - Removed unused `unittest.mock.patch`
- `tests/test_cli/test_diff.py` - Removed unused `pytest` and `DiffEntry`
- `tests/test_cli/test_doctor.py` - Removed unused `pytest`
- `tests/test_cli/test_export.py` - Removed unused `json`, `typing.Any`, `pytest`, `_sanitize_logical_id`
- `tests/test_cli/test_logs.py` - Removed unused `time`, `datetime.timedelta`, `pytest`
- `tests/test_cli/test_test_cmd.py` - Removed unused `json`, `os`, `pathlib.Path`, `unittest.mock.patch`
- `tests/test_cli/test_watch.py` - Removed unused `pytest`
- `tests/test_dsl/test_models.py` - Removed unused `AlarmConfig`, `DeadLetterQueueConfig`
- `tests/test_inspect/test_replay.py` - Removed unused `asyncio`
- `tests/test_providers/test_base.py` - Removed unused `typing.Any`
- `tests/test_providers/test_cdk_provider.py` - Removed unused `call`, `PrerequisiteCheck`
- `tests/test_providers/test_custom_integration.py` - Removed unused `os`
- `tests/test_providers/test_custom_provider.py` - Removed unused `os`, `StateMachineDefinition`, `PrerequisiteCheck`
- `tests/test_providers/test_metadata.py` - Removed unused `pytest`
- `tests/test_providers/test_terraform_provider.py` - Removed unused `PrerequisiteCheck`
- `tests/test_providers/test_transports.py` - Removed unused `pathlib.Path`

## Decisions Made
- pyproject.toml had already been updated in a prior partial execution of this plan (b249df0), so only the F401 violation cleanup remained
- Used `ruff check --select F401 --fix .` for bulk auto-correction since all 34 violations were auto-fixable
- Pre-existing test failure in test_infra_config.py::test_custom_provider_with_dict_config is out of scope (existed before changes, unrelated to F401 cleanup)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed 34 F401 violations introduced by v3.0 development after original Plan 28-01 execution**
- **Found during:** Task 1 (verifying zero F401 violations)
- **Issue:** Plan assumed zero F401 violations after Plan 28-01, but v3.0 development (phases 51-55) introduced 34 new unused imports across 23 files
- **Fix:** Applied `ruff check --select F401 --fix .` to auto-correct all violations
- **Files modified:** 23 files across src/rsf/ and tests/
- **Verification:** `ruff check --select F401 .` reports "All checks passed!" — zero violations
- **Committed in:** 0e0c590 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug - new F401 violations from subsequent development)
**Impact on plan:** Auto-fix necessary to achieve zero F401 goal. All violations were trivial unused imports auto-correctable by ruff. No scope creep.

## Issues Encountered
- pyproject.toml changes were already committed in b249df0 from a prior partial execution of this plan — the SUMMARY.md had not been created, so re-execution was triggered
- 34 F401 violations existed from v3.0 code additions after Plan 28-01 execution; fixed automatically with ruff

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Zero F401 violations across entire codebase (src/, tests/, examples/)
- pyproject.toml ruff config enforces F401 — future unused imports will be caught immediately
- Ready for phases 29+ to address remaining lint rules (F841, F541, E402, E741)

---
*Phase: 28-f401-unused-imports*
*Completed: 2026-03-03*
