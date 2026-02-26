---
phase: 18-getting-started
plan: 02
subsystem: docs
tags: [rsf, validate, tutorial, yaml, pydantic, semantic-validation, bfs]

# Dependency graph
requires:
  - phase: 18-01
    provides: rsf init tutorial establishing project setup baseline
provides:
  - Step-by-step rsf validate tutorial with 3-stage pipeline explanation and error examples
  - Learn-by-breaking approach: Stage 1 YAML, Stage 2 Pydantic, Stage 3 semantic errors
  - Error reference table covering all 5 common validation error patterns
affects:
  - 19-build-and-deploy (rsf generate tutorials reference validate as prerequisite)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tutorial structure: prerequisites, pipeline overview, staged exercises, error reference table, what's next"
    - "Learn-by-breaking: each error type demonstrated with full broken file, exact output, interpretation, fix"

key-files:
  created:
    - tutorials/02-workflow-validation.md
  modified: []

key-decisions:
  - "Used actual rsf validate CLI output (not idealized) for all error examples — verified against running rsf validate on test fixtures"
  - "Chose custom Task+Choice+Fail workflow for Step 5 to demonstrate real-world patterns beyond the starter template"
  - "Showed full workflow.yaml in each 'break it' section rather than diff to prevent copy-paste confusion"

patterns-established:
  - "Tutorial error examples: show full file, command, exact output, interpretation, fix — not just the changed line"
  - "Cross-check: validate all workflow YAML examples actually pass rsf validate before including in tutorial"

requirements-completed: [SETUP-02]

# Metrics
duration: 4min
completed: 2026-02-26
---

# Phase 18 Plan 02: Workflow Validation Tutorial Summary

**403-line step-by-step rsf validate tutorial with verified error output for all three validation stages (YAML syntax, Pydantic structural, BFS semantic)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-26T06:27:23Z
- **Completed:** 2026-02-26T06:31:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created `tutorials/02-workflow-validation.md` (403 lines) covering the complete rsf validate workflow
- All three error types demonstrated with real CLI output verified against running rsf validate on test fixtures
- Custom multi-state workflow (Task + Choice + Fail) in Step 5 validated passes before inclusion
- Error reference table covers all 5 patterns from validator.py: YAML error, invalid type, invalid field value, dangling reference, unreachable state, missing terminal state

## Task Commits

Each task was committed atomically:

1. **Task 1: Write the rsf validate tutorial** - `057b72e` (feat)

**Plan metadata:** (docs commit — in progress)

## Files Created/Modified

- `tutorials/02-workflow-validation.md` - Complete rsf validate tutorial: prerequisites, 3-stage pipeline diagram, 5 steps (validate starter, break YAML, break structural, break semantic, validate custom workflow), error reference table, what's next pointer

## Decisions Made

- Used actual rsf validate CLI output for all error examples rather than idealized output — the Stage 2 structural error (invalid Type) produces an empty field-path (`  : Input tag 'Invalid' found...`) which differs from what you might expect. The tutorial documents reality and explains it.
- Used a Task+Choice+Fail workflow for Step 5 (not another Pass/Succeed) to demonstrate real-world patterns and show that Choice states require `Choices` arrays, not `Next` fields.
- Showed full workflow.yaml in each error section as the plan specified — prevents confusion about what changed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Tutorial 2 complete — users can validate workflow YAML and interpret all three error types
- Ready for Tutorial 3 (rsf generate) in Phase 19: Build and Deploy
- Note: Tutorial 1 (rsf init) and Tutorial 2 (rsf validate) together form the getting-started prerequisite for all Phase 19 tutorials

## Self-Check: PASSED

- `tutorials/02-workflow-validation.md`: FOUND
- `.planning/phases/18-getting-started/18-02-SUMMARY.md`: FOUND
- Commit `057b72e`: FOUND

---
*Phase: 18-getting-started*
*Completed: 2026-02-26*
