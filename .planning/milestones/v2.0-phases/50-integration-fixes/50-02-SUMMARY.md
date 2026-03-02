---
phase: 50-integration-fixes
plan: 02
subsystem: cli
tags: [chaos-testing, cli, local-runner, failure-injection]

# Dependency graph
requires:
  - phase: 42-developer-cli-commands
    provides: "rsf test CLI command and LocalRunner"
  - phase: 45-advanced-testing-utilities
    provides: "ChaosFixture with inject_failure API"
provides:
  - "rsf test --chaos flag for CLI-based chaos injection"
  - "ChaosFixture integration in LocalRunner handler invocation path"
  - "Chaos failures participate in retry/catch logic"
affects: [cli-testing, chaos-testing, local-runner]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Handler wrapping for chaos injection inside retry loop"]

key-files:
  created: []
  modified:
    - src/rsf/cli/test_cmd.py
    - tests/test_cli/test_test_cmd.py

key-decisions:
  - "Chaos injection wraps handler_fn inside _call_handler_with_retry so failures participate in retry/catch logic, rather than bypassing them"
  - "Used lazy import of ChaosFixture (only when --chaos is provided) to avoid import overhead in normal usage"

patterns-established:
  - "Handler wrapping pattern: original_handler captured in closure, chaos check before delegation"
  - "CLI option parsing: colon-delimited STATE:TYPE format for chaos specs"

requirements-completed: [TEST-02]

# Metrics
duration: 4min
completed: 2026-03-02
---

# Phase 50 Plan 02: Bridge ChaosFixture to rsf test CLI Summary

**Added --chaos flag to rsf test that injects ChaosFixture failures (timeout, exception, throttle) into specific states during local workflow execution, with proper retry/catch interaction**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-02T20:03:00Z
- **Completed:** 2026-03-02T20:07:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `--chaos STATE:TYPE` repeatable CLI option to `rsf test` command
- Integrated ChaosFixture into LocalRunner's handler invocation path via handler wrapping
- Chaos-injected failures properly participate in retry/catch logic (not bypassing them)
- 7 new integration tests proving all failure types, catch routing, retry+count, selective injection, and backward compatibility

## Task Commits

Each task was committed atomically:

1. **Task 1: Add --chaos flag and ChaosFixture integration to LocalRunner** - `b4933aa` (feat)
2. **Task 2: Add chaos integration tests and verify E2E CLI flow** - `b398258` (test)

## Files Created/Modified
- `src/rsf/cli/test_cmd.py` - Added chaos_fixture param to LocalRunner, handler wrapping in _call_handler_with_retry, --chaos CLI option with parsing and validation
- `tests/test_cli/test_test_cmd.py` - 7 new TestChaosIntegration tests (22 total pass)

## Decisions Made
- Placed chaos check inside the retry loop by wrapping handler_fn, so chaos failures interact with Retry and Catch policies naturally
- Used lazy import of ChaosFixture to avoid import overhead when --chaos is not used

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 50 complete, ready for verification and milestone closure

---
*Phase: 50-integration-fixes*
*Completed: 2026-03-02*
