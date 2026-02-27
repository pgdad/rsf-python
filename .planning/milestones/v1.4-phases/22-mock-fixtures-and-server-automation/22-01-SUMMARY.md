---
phase: 22-mock-fixtures-and-server-automation
plan: 01
subsystem: testing
tags: [mock-server, fixtures, sse, inspector, rest-api, typescript]

# Dependency graph
requires:
  - phase: 21-playwright-setup
    provides: "tsx for Node TypeScript execution, tsconfig.scripts.json"
provides:
  - "5 mock execution fixture JSON files covering all example workflows"
  - "Mock inspect server (mock-inspect-server.ts) serving fixture data via REST and SSE"
  - "Inspector UI can display realistic execution data without AWS connectivity"
affects: [22-02-screenshot-automation, 23-screenshot-capture]

# Tech tracking
tech-stack:
  added: []
  patterns: ["fixture-driven mock server using Node built-in http module", "SSE event framing for execution_info and history events"]

key-files:
  created:
    - ui/scripts/fixtures/order-processing.json
    - ui/scripts/fixtures/approval-workflow.json
    - ui/scripts/fixtures/data-pipeline.json
    - ui/scripts/fixtures/retry-and-recovery.json
    - ui/scripts/fixtures/intrinsic-showcase.json
    - ui/scripts/mock-inspect-server.ts
  modified: []

key-decisions:
  - "Used Node built-in http module (no Express/Fastify deps) for zero-dependency mock server"
  - "Each fixture contains both executions array and execution_detail for list and detail views"
  - "SSE stream sends execution_info then history then closes (fixture is terminal/SUCCEEDED)"

patterns-established:
  - "Fixture JSON schema: { executions: [...], execution_detail: { ...with history } }"
  - "Mock server CLI pattern: node --import tsx/esm scripts/mock-inspect-server.ts --fixture <name> --port <port>"

requirements-completed: [CAPT-03]

# Metrics
duration: 3min
completed: 2026-02-27
---

# Phase 22 Plan 01: Mock Fixtures and Server Summary

**5 mock execution fixtures with REST/SSE server matching inspector API contract for offline UI screenshot capture**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-27T10:32:35Z
- **Completed:** 2026-02-27T10:35:27Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Created 5 fixture JSON files with realistic execution data tracing through every state in each example workflow
- Built mock inspect server serving all 4 inspector API endpoints (list, detail, history, SSE stream)
- All history events use stateName/StateEntered/StateSucceeded patterns compatible with timeMachine.ts graph overlays
- Server requires zero external dependencies (uses Node built-in http module)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create mock execution fixture JSON files for all 5 examples** - `6f9b172` (feat)
2. **Task 2: Create mock inspect server that serves fixture data** - `ebbe21f` (feat)

## Files Created/Modified
- `ui/scripts/fixtures/order-processing.json` - 14 events: ValidateOrder through OrderComplete (happy path, total=99.98)
- `ui/scripts/fixtures/approval-workflow.json` - 14 events: SubmitRequest through RequestApproved (approved on first check)
- `ui/scripts/fixtures/data-pipeline.json` - 14 events: InitPipeline through PipelineComplete (3 records ETL)
- `ui/scripts/fixtures/retry-and-recovery.json` - 6 events: CallPrimaryService through ServiceComplete (no retries needed)
- `ui/scripts/fixtures/intrinsic-showcase.json` - 12 events: PrepareData through ShowcaseComplete (intrinsic function outputs)
- `ui/scripts/mock-inspect-server.ts` - HTTP server with REST + SSE endpoints, CORS, CLI args, graceful shutdown

## Decisions Made
- Used Node built-in `http` module instead of Express/Fastify to avoid adding dependencies for a dev-only tool
- Each fixture contains both `executions` array (for list view) and `execution_detail` (for detail/timeline view) in one file
- SSE stream immediately sends execution_info + history then closes since fixtures represent terminal SUCCEEDED executions
- History events use `StateEntered` and `StateSucceeded` event_types with `stateName` in details to match timeMachine.ts parsing

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Mock server ready for Phase 22 Plan 02 (screenshot automation scripts)
- All 5 example workflows have fixture data for realistic inspector screenshots
- Server can be started per-fixture for targeted screenshot capture

## Self-Check: PASSED

All 7 files verified present. Both task commits (6f9b172, ebbe21f) confirmed in git log.

---
*Phase: 22-mock-fixtures-and-server-automation*
*Completed: 2026-02-27*
