---
phase: 35-run-all-tests-that-do-not-require-aws-access-resources
plan: 01
subsystem: testing
tags: [pytest, importlib, conftest, test-discovery]

requires:
  - phase: 34-config-cleanup
    provides: clean ruff config with zero violations
provides:
  - unified pytest invocation running all 744 non-AWS tests
  - importlib-based test collection eliminating module naming collisions
  - handler module isolation between example test suites
affects: [ci, testing, examples]

tech-stack:
  added: []
  patterns: [importlib import mode for pytest, handler module cache purging in conftest]

key-files:
  created: []
  modified:
    - pyproject.toml
    - examples/order-processing/tests/conftest.py
    - examples/data-pipeline/tests/conftest.py
    - examples/intrinsic-showcase/tests/conftest.py
    - examples/approval-workflow/tests/conftest.py
    - examples/retry-and-recovery/tests/conftest.py

key-decisions:
  - "Used addopts = '--import-mode=importlib' instead of importmode config key (not supported in pytest 9.x ini_options)"
  - "Removed __init__.py from example test directories to eliminate conftest.py package-name collisions"
  - "Added handler module cache purging to conftest fixtures to prevent cross-example handler namespace pollution"

patterns-established:
  - "Handler isolation: each example conftest.py purges sys.modules entries for handlers.* before tests to prevent cross-example pollution"

requirements-completed: []

duration: 15min
completed: 2026-02-28
---

# Phase 35 Plan 01: Unified Non-AWS Test Suite Summary

**Unified pytest config discovers and runs all 744 non-AWS tests (592 unit + 152 example local) in one invocation with importlib mode and handler module isolation**

## Performance

- **Duration:** 15 min
- **Started:** 2026-02-28
- **Completed:** 2026-02-28
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- A single `pytest -m "not integration"` now runs all 744 non-AWS tests with zero failures
- Resolved ImportPathMismatchError by switching to importlib import mode and removing example test __init__.py files
- Resolved cross-example handler module collisions by purging cached handler modules in conftest fixtures
- CI runs the exact same comprehensive test suite without any workflow changes

## Task Commits

Each task was committed atomically:

1. **Task 1+2: Fix pytest config and verify CI** - `2be34b3` (fix)

## Files Created/Modified
- `pyproject.toml` - Added 5 example testpaths, addopts with --import-mode=importlib
- `examples/order-processing/tests/conftest.py` - Added handler module purging fixture
- `examples/data-pipeline/tests/conftest.py` - Added handler module purging fixture
- `examples/intrinsic-showcase/tests/conftest.py` - Added handler module purging fixture
- `examples/approval-workflow/tests/conftest.py` - Added handler module purging fixture
- `examples/retry-and-recovery/tests/conftest.py` - Added handler module purging fixture
- `examples/*/tests/__init__.py` (5 files deleted) - Removed to prevent package-name collisions

## Decisions Made
- Used `addopts = "--import-mode=importlib"` because `importmode` is not a valid pytest ini_options key (the plan suggested `importmode = "importlib"` which pytest 9.x does not recognize)
- Removed `__init__.py` from all 5 example test directories because with importlib mode they are not needed and their presence caused conftest.py files to be registered under the same `tests.conftest` module name
- Added handler module cache purging (`sys.modules` cleanup) to every example conftest.py fixture because all 5 examples have a `handlers/` package with `__init__.py` that collides when running tests across examples in the same process

## Deviations from Plan

### Auto-fixed Issues

**1. Config key name: importmode vs addopts**
- **Found during:** Task 1
- **Issue:** `importmode = "importlib"` in pyproject.toml is not recognized by pytest 9.x (produces `PytestConfigWarning: Unknown config option: importmode`)
- **Fix:** Used `addopts = "--import-mode=importlib"` instead
- **Files modified:** pyproject.toml
- **Verification:** `pytest --collect-only -q` collects 757 tests with no warnings
- **Committed in:** 2be34b3

**2. Example __init__.py removal required**
- **Found during:** Task 1
- **Issue:** Example test directories had `__init__.py` files that made them Python packages, causing conftest.py from different examples to collide as `tests.conftest`
- **Fix:** Removed all 5 `examples/*/tests/__init__.py` files
- **Files modified:** 5 files deleted
- **Verification:** All 757 tests collected without errors
- **Committed in:** 2be34b3

**3. Cross-example handler module collisions**
- **Found during:** Task 1
- **Issue:** All 5 examples have `handlers/` packages with `__init__.py`. When running all examples together, the first `handlers` package gets cached in `sys.modules` and subsequent examples fail with `ModuleNotFoundError` for their own handler modules
- **Fix:** Added handler module cache purging to each example conftest.py's `clean_registry` fixture
- **Files modified:** 5 conftest.py files
- **Verification:** `pytest -m "not integration" -q` runs 744 tests with 0 failures
- **Committed in:** 2be34b3

---

**Total deviations:** 3 auto-fixed (1 config, 1 packaging, 1 namespace collision)
**Impact on plan:** All fixes necessary for correctness. No scope creep. The plan's objective is fully achieved.

## Issues Encountered
- The plan did not anticipate the handler module collision issue since it only tested `pytest examples/` (which failed with ImportPathMismatchError). After fixing that, a second layer of collisions from the `handlers/` packages was discovered and resolved.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All non-AWS tests pass in a unified invocation
- CI workflow requires no changes
- Ready for any subsequent development phases

---
*Phase: 35-run-all-tests-that-do-not-require-aws-access-resources*
*Completed: 2026-02-28*
