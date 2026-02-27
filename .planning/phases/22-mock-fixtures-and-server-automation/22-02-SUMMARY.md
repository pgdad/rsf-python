---
phase: 22-mock-fixtures-and-server-automation
plan: 02
subsystem: testing
tags: [server-lifecycle, child-process, health-check, typescript, spawn]

# Dependency graph
requires:
  - phase: 22-mock-fixtures-and-server-automation
    plan: 01
    provides: "mock-inspect-server.ts and fixture JSON files"
  - phase: 21-playwright-setup
    provides: "tsx for Node TypeScript execution, tsconfig.scripts.json"
provides:
  - "start-ui-server.ts — graph editor server lifecycle management"
  - "start-inspect-server.ts — mock inspect server lifecycle management"
affects: [23-screenshot-capture]

# Tech tracking
tech-stack:
  added: []
  patterns: ["child_process.spawn for server lifecycle with health-check polling", "SERVER_READY/SERVER_STOPPED signal protocol for downstream automation"]

key-files:
  created:
    - ui/scripts/start-ui-server.ts
    - ui/scripts/start-inspect-server.ts
  modified: []

key-decisions:
  - "Used venv rsf binary directly instead of python -m rsf (no __main__.py in rsf package)"
  - "Self-contained scripts with duplicated health-check pattern rather than shared module"
  - "SIGTERM with 2s SIGKILL fallback for graceful shutdown"

patterns-established:
  - "Server lifecycle CLI: --example <name> --port <number> with SERVER_READY/SERVER_STOPPED signals"
  - "Python venv detection: check .venv/bin/rsf first, fallback to PATH"

requirements-completed: [CAPT-02]

# Metrics
duration: 3min
completed: 2026-02-27
---

# Phase 22 Plan 02: Server Automation Summary

**Two server lifecycle scripts (start-ui-server.ts, start-inspect-server.ts) that spawn, health-check, and manage graph editor and mock inspect servers for downstream screenshot automation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-27T10:38:28Z
- **Completed:** 2026-02-27T10:42:07Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created start-ui-server.ts that spawns the rsf ui Python server for any example workflow with health-check polling
- Created start-inspect-server.ts that spawns mock-inspect-server.ts with fixture data and health-check polling
- Both scripts print SERVER_READY/SERVER_STOPPED signals consumable by Phase 23 screenshot capture scripts
- Both handle graceful shutdown (SIGTERM + SIGKILL fallback) and error cases (timeout, missing files, unexpected exits)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create start-ui-server.ts** - `20351a7` (feat)
2. **Task 2: Create start-inspect-server.ts** - `24e50f3` (feat)

## Files Created/Modified
- `ui/scripts/start-ui-server.ts` - Spawns rsf ui for a given example, health-checks root URL, manages lifecycle
- `ui/scripts/start-inspect-server.ts` - Spawns mock-inspect-server.ts for a given fixture, health-checks /api/inspect/executions, manages lifecycle

## Decisions Made
- Used the venv `rsf` binary directly instead of `python -m rsf` because the rsf package lacks `__main__.py` — the entry point is `rsf.cli.main:app` registered as a console_script
- Kept scripts self-contained (duplicated health-check pattern) rather than extracting a shared module, per plan guidance
- Added SIGTERM with 2-second SIGKILL fallback for reliable cleanup of child processes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed Python executable resolution for rsf ui**
- **Found during:** Task 1 (start-ui-server.ts)
- **Issue:** Plan specified `spawn('python', ['-m', 'rsf', ...])` but `python` binary not in PATH and `python -m rsf` fails (no `__main__.py`). The rsf CLI is installed as a venv entry point at `.venv/bin/rsf`.
- **Fix:** Added `findRsfCommand()` that discovers the venv rsf binary, falls back to PATH rsf, then to venv python with direct module import
- **Files modified:** ui/scripts/start-ui-server.ts
- **Verification:** Server starts successfully and returns HTTP 200 on both / and /api/schema
- **Committed in:** 20351a7 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential fix for the script to actually work. No scope creep.

## Issues Encountered
None beyond the Python executable resolution handled as a deviation.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both server lifecycle scripts ready for Phase 23 screenshot capture
- Scripts accept --example and --port for flexible usage across all 5 example workflows
- SERVER_READY signal can be detected by downstream scripts to know when servers are responsive

## Self-Check: PASSED

All 2 created files verified present (start-ui-server.ts: 216 lines, start-inspect-server.ts: 193 lines). Both task commits (20351a7, 24e50f3) confirmed in git log.

---
*Phase: 22-mock-fixtures-and-server-automation*
*Completed: 2026-02-27*
