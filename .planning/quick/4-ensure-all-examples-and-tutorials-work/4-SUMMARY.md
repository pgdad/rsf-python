---
phase: quick-4
plan: 1
subsystem: cli
tags: [rsf-test, rsf-validate, rsf-generate, templates, tutorials, handler-resolution]

requires:
  - phase: none
    provides: existing examples and tutorials
provides:
  - All 7 examples pass rsf validate, rsf generate, and pytest
  - Both init templates (api-gateway-crud, s3-event-pipeline) produce valid projects
  - rsf test works with both handlers/ and src/handlers/ layouts
  - Tutorial docs reference correct paths matching rsf init output
affects: [examples, tutorials, cli-test]

tech-stack:
  added: []
  patterns: [handler-cache-in-rsf-test, handlers-first-path-resolution]

key-files:
  created:
    - src/rsf/cli/templates/s3-event-pipeline/handlers/notify_failure.py
  modified:
    - src/rsf/cli/templates/api-gateway-crud/workflow.yaml
    - src/rsf/cli/templates/s3-event-pipeline/workflow.yaml
    - src/rsf/cli/test_cmd.py
    - tutorials/01-project-setup.md
    - tutorials/03-code-generation.md
    - tutorials/04-deploy-to-aws.md
    - tutorials/05-iterate-invoke-teardown.md
    - tutorials/08-execution-inspector.md

key-decisions:
  - "Handler path priority: handlers/ checked first, src/handlers/ as fallback -- prevents rsf generate stubs from shadowing real handlers in examples"
  - "Handler module caching in rsf test: prevents duplicate @state registration when workflows loop through the same state multiple times"
  - "Tutorial 06 (rsf import) left unchanged: rsf import correctly creates handlers/ at root, matching existing docs"
  - "Tutorial 09 left unchanged: describes registry-modules-demo which uses legacy handlers/ layout"

patterns-established:
  - "Handler resolution: handlers/ takes priority over src/handlers/ in rsf test to support both layouts"
  - "Handler caching: _handler_cache dict prevents re-importing modules in looping workflows"

requirements-completed: []

duration: 13min
completed: 2026-03-06
---

# Quick Task 4: Ensure All Examples and Tutorials Work

**Fixed template validation failures, duplicate handler registration, rsf test path resolution, and outdated tutorial paths across all 7 examples and 5 tutorials**

## Performance

- **Duration:** 13 min
- **Started:** 2026-03-06T10:34:17Z
- **Completed:** 2026-03-06T10:47:44Z
- **Tasks:** 3
- **Files modified:** 38 (33 deleted, 1 created, 4 modified)

## Accomplishments

- All 7 examples pass rsf validate, rsf generate, and pytest (195 tests)
- Both init templates (api-gateway-crud, s3-event-pipeline) produce valid, validateable projects -- Handler field removed, NotifyFailure handler stub added
- rsf test works with both handlers/ (examples) and src/handlers/ (new projects) layouts with module caching to prevent duplicate registration in looping workflows
- Tutorials 01, 03, 04, 05, 08 updated to reference src/handlers/ matching current rsf init output
- 244 CLI tests, 52 project example tests all pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix template workflows and rsf test handler resolution** - `b8a4167` (fix)
2. **Task 2: Remove duplicate handler directories from examples and update tutorials** - `0291513` (fix)
3. **Task 3: End-to-end verification and handler caching fix** - `fee61a4` (fix)

## Files Created/Modified

- `src/rsf/cli/templates/api-gateway-crud/workflow.yaml` - Removed invalid Handler: fields from Task states
- `src/rsf/cli/templates/s3-event-pipeline/workflow.yaml` - Removed invalid Handler: fields from Task states
- `src/rsf/cli/templates/s3-event-pipeline/handlers/notify_failure.py` - NEW: handler stub for NotifyFailure state (was reusing NotifyComplete handler via Handler field)
- `src/rsf/cli/test_cmd.py` - Dual-path handler resolution (handlers/ first, then src/handlers/) with module caching
- `examples/*/src/handlers/` - DELETED from 6 examples (approval-workflow, data-pipeline, intrinsic-showcase, lambda-url-trigger, order-processing, retry-and-recovery)
- `tutorials/01-project-setup.md` - Updated rsf init output, directory tree, handler paths to src/handlers/
- `tutorials/03-code-generation.md` - Updated rsf generate output, directory tree, handler references to src/handlers/
- `tutorials/04-deploy-to-aws.md` - Updated directory tree to show src/ layout
- `tutorials/05-iterate-invoke-teardown.md` - Updated handler file reference to src/handlers/
- `tutorials/08-execution-inspector.md` - Updated handler file references to src/handlers/

## Decisions Made

- **Handler path priority reversed:** Changed from src/handlers/-first to handlers/-first. This ensures examples with real handlers in handlers/ are not shadowed by rsf generate stubs in src/handlers/. New projects with only src/handlers/ still work via fallback.
- **Handler module caching added:** The _load_handler function now caches loaded modules keyed by workflow_dir:module_name. This prevents the @state decorator from being re-triggered when a workflow revisits a state (e.g., approval-workflow's polling loop), which was causing "Duplicate handler" errors.
- **Tutorials 06 and 09 left unchanged:** Tutorial 06 correctly documents rsf import creating handlers/ at root. Tutorial 09 correctly documents the registry-modules-demo example which uses the legacy handlers/ layout.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed handler caching for looping workflows**
- **Found during:** Task 3 (end-to-end verification)
- **Issue:** rsf test crashed with "Duplicate handler for state X: already registered" when a workflow revisited a Task state (e.g., approval-workflow polling loop). The _load_handler function re-imported the module on every call, triggering the @state decorator each time.
- **Fix:** Added _handler_cache dict that stores loaded handler functions keyed by workflow_dir:module_name. On subsequent calls for the same handler, the cached function is returned without re-importing.
- **Files modified:** src/rsf/cli/test_cmd.py
- **Verification:** rsf test runs approval-workflow without duplicate handler errors; all 244 CLI tests pass
- **Committed in:** fee61a4

**2. [Rule 1 - Bug] Reversed handler path priority (src/handlers/ -> handlers/ first)**
- **Found during:** Task 3 (end-to-end verification)
- **Issue:** Original fix checked src/handlers/ first, but this caused rsf test to load NotImplementedError stubs from src/handlers/ instead of real handlers from handlers/ when rsf generate had been run on an example.
- **Fix:** Reversed priority to check handlers/ first, then src/handlers/ as fallback.
- **Files modified:** src/rsf/cli/test_cmd.py
- **Verification:** rsf test correctly loads real handlers from handlers/ in all examples
- **Committed in:** fee61a4

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes are necessary for rsf test correctness. The plan's original approach (src/handlers/ first) was incorrect for the examples use case. No scope creep.

## Issues Encountered

- rsf generate always outputs handler stubs to src/handlers/ (sibling of src/generated/), so running it on examples re-creates the duplicate directory. This is by design -- the generate command assumes the new project layout. The fix is ensuring rsf test prefers handlers/ when both exist, and the generated stubs are harmless (gitignored or not committed).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All examples and tutorials work end-to-end with the current RSF CLI
- No blockers or concerns

---
## Self-Check: PASSED

- All created files exist on disk
- All 6 duplicate src/handlers/ directories confirmed deleted
- All 3 task commits found in git log (b8a4167, 0291513, fee61a4)

---
*Quick Task: 4-ensure-all-examples-and-tutorials-work*
*Completed: 2026-03-06*
