---
phase: 28-f401-unused-imports
plan: 01
subsystem: linting
tags: [ruff, F401, unused-imports, code-quality]

# Dependency graph
requires: []
provides:
  - "Zero F401 violations across src/, tests/, and examples/"
  - "Side-effect imports in functions/__init__.py annotated with noqa: F401"
  - "Generated code noqa pattern in codegen/generator.py preserved"
affects: [28-02]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "noqa: F401 for intentional side-effect imports"

key-files:
  created: []
  modified:
    - src/rsf/functions/__init__.py
    - src/rsf/codegen/generator.py
    - src/rsf/dsl/choice.py
    - src/rsf/dsl/errors.py
    - src/rsf/dsl/models.py
    - src/rsf/dsl/parser.py
    - src/rsf/dsl/validator.py
    - src/rsf/editor/server.py
    - src/rsf/editor/websocket.py
    - src/rsf/registry/registry.py
    - src/rsf/cli/templates/test_example.py
    - tests/test_cli/test_deploy.py
    - tests/test_cli/test_ui.py
    - tests/test_codegen/test_generator.py
    - tests/test_codegen/test_state_mappers.py
    - tests/test_context/test_context.py
    - tests/test_dsl/test_models.py
    - tests/test_dsl/test_parser.py
    - tests/test_dsl/test_validator.py
    - tests/test_editor/test_websocket.py
    - tests/test_examples/test_harness.py
    - tests/test_importer/test_importer.py
    - tests/test_inspect/test_server.py
    - tests/test_integration/test_sdk_integration.py
    - tests/test_mock_sdk/test_mock_context.py
    - tests/test_registry/test_registry.py
    - tests/test_terraform/test_terraform.py
    - examples/data-pipeline/tests/test_local.py
    - examples/intrinsic-showcase/tests/test_local.py
    - examples/retry-and-recovery/tests/test_local.py

key-decisions:
  - "Side-effect imports in functions/__init__.py get noqa: F401 rather than removal, preserving @intrinsic decorator registration"
  - "Generated code noqa: F401 string in codegen/generator.py preserved as it appears in output code, not source"

patterns-established:
  - "noqa: F401 for side-effect imports that trigger decorator registration"

requirements-completed: [F401-01, F401-02, F401-03, F401-04, F401-05]

# Metrics
duration: 4min
completed: 2026-02-28
---

# Phase 28 Plan 01: F401 Unused Imports Summary

**Removed all 61 F401 unused imports across 30 files in src/, tests/, and examples/; annotated side-effect imports with noqa: F401**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-28T23:31:10Z
- **Completed:** 2026-02-28T23:35:10Z
- **Tasks:** 2
- **Files modified:** 30

## Accomplishments
- Removed 27 unused imports across 11 src/ files (typing.Any, Literal, Optional, Union, Annotated; pydantic.ValidationError, model_validator; model imports from validator.py; generate_json_schema from websocket.py)
- Removed 34 unused imports across 19 test and example files (stdlib, unittest.mock, rsf model/type, and test SDK imports)
- Added noqa: F401 to side-effect imports in functions/__init__.py to preserve @intrinsic decorator registration
- Fixed 3 cascading F401 violations in test_parser.py (tempfile, Path, pytest became unused after removing StateMachineDefinition)
- Preserved generated code noqa: F401 pattern in codegen/generator.py
- All 572 unit tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix F401 violations in src/ (27 violations across 11 files)** - `d4cef53` (fix)
2. **Task 2: Fix F401 violations in tests/ and examples/ (34 violations across 19 files)** - `8a04dd9` (fix)

## Files Created/Modified
- `src/rsf/functions/__init__.py` - Added noqa: F401 to side-effect import line
- `src/rsf/codegen/generator.py` - Removed unused typing.Any import
- `src/rsf/dsl/choice.py` - Removed typing.Literal and COMPARISON_OPERATORS imports
- `src/rsf/dsl/errors.py` - Removed typing.Any and pydantic.model_validator imports
- `src/rsf/dsl/models.py` - Removed typing.Annotated, Optional, Union imports
- `src/rsf/dsl/parser.py` - Removed pydantic.ValidationError import
- `src/rsf/dsl/validator.py` - Removed dataclasses.field, 4 model imports, DataTestRule, Catcher, RetryPolicy
- `src/rsf/editor/server.py` - Removed typing.Any import
- `src/rsf/editor/websocket.py` - Removed generate_json_schema import
- `src/rsf/registry/registry.py` - Removed typing.Any import
- `src/rsf/cli/templates/test_example.py` - Removed unused pytest import
- 19 test and example files - Removed various unused imports

## Decisions Made
- Side-effect imports in functions/__init__.py annotated with noqa: F401 rather than removed, because they trigger @intrinsic decorator registration as a side effect of import
- Generated code noqa string in codegen/generator.py preserved (it's output code, not a source-level lint suppression)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed 3 cascading F401 violations in test_parser.py**
- **Found during:** Task 2 (tests/ cleanup)
- **Issue:** After removing the unused `StateMachineDefinition` import, three more imports became unused: `tempfile`, `pathlib.Path`, and `pytest` (none were used anywhere else in the file)
- **Fix:** Removed the three newly-unused imports
- **Files modified:** tests/test_dsl/test_parser.py
- **Verification:** ruff check --select F401 reports zero violations
- **Committed in:** 8a04dd9 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug - cascading unused imports)
**Impact on plan:** Minimal -- natural consequence of removing an import that was the only consumer of other imports. No scope creep.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Zero F401 violations across the entire codebase
- Ready for Plan 02 to remove F401 from the global ruff ignore list
- All 572 unit tests pass

---
*Phase: 28-f401-unused-imports*
*Completed: 2026-02-28*
