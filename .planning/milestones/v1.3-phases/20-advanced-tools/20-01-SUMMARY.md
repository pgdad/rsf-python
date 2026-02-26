---
phase: 20-advanced-tools
plan: 01
subsystem: docs
tags: [tutorial, asl, import, migration, converter]

requires:
  - phase: 04-asl-importer
    provides: "ASL-to-RSF converter and import CLI command"
provides:
  - "Step-by-step rsf import tutorial with conversion rules reference"
affects: []

tech-stack:
  added: []
  patterns: [learn-by-doing tutorial with sample ASL input]

key-files:
  created:
    - tutorials/06-asl-import.md
  modified: []

key-decisions:
  - "Used order-processing ASL with 3 Task states to demonstrate Resource removal warnings"
  - "Documented all 5 conversion rules in a dedicated reference section"

patterns-established:
  - "Tutorial import pattern: sample input, run command, review output, validate, continue"

requirements-completed: [MIGR-01]

duration: 3min
completed: 2026-02-26
---

# Phase 20 Plan 01: rsf import Tutorial Summary

**Step-by-step ASL import tutorial covering sample ASL creation, Resource removal warnings, handler stub review, validation, and all 5 conversion rules**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-26T23:16:30Z
- **Completed:** 2026-02-26T23:17:30Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created tutorials/06-asl-import.md (277 lines) covering the full rsf import workflow
- Documented all 5 conversion rules: Resource removal, Fail I/O stripping, Iterator rename, distributed Map fields, recursive conversion
- Sample ASL JSON exercises the primary conversion rule (Resource field removal)
- Handler stub walkthrough with @state decorator explanation

## Task Commits

Each task was committed atomically:

1. **Task 1: Write the rsf import tutorial** - `3a28b30` (feat)

## Files Created/Modified
- `tutorials/06-asl-import.md` - Step-by-step rsf import tutorial with sample ASL, conversion output walkthrough, handler stub explanation, and conversion rules reference

## Decisions Made
- Used a realistic order-processing ASL with 3 Task states, 1 Choice, and 1 Succeed to exercise the main conversion rule (Resource removal)
- Documented all 5 conversion rules in a separate reference section rather than inline with the walkthrough
- Showed handler stub template output matching the actual Jinja2 template

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Tutorial 6 complete, pointer to Tutorial 7 (rsf ui) included
- Phase 20 tutorials can be read in sequence: import -> graph editor -> inspector

---
*Phase: 20-advanced-tools*
*Completed: 2026-02-26*
