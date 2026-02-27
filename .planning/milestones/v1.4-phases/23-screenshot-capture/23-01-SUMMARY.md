---
phase: 23-screenshot-capture
plan: 01
subsystem: ui
tags: [playwright, screenshots, automation, typescript, graph-editor, inspector]

# Dependency graph
requires:
  - phase: 22-mock-fixtures-and-server-automation
    plan: 01
    provides: "mock-inspect-server.ts and fixture JSON files for inspector screenshots"
  - phase: 22-mock-fixtures-and-server-automation
    plan: 02
    provides: "start-ui-server.ts and start-inspect-server.ts server lifecycle patterns"
  - phase: 21-playwright-setup
    provides: "Playwright + tsx for Node TypeScript execution"
provides:
  - "15 PNG screenshots in docs/images/ covering all 5 examples x 3 views"
  - "capture-screenshots.ts Playwright orchestration script (481 lines)"
  - "npm run screenshots one-command capture pipeline"
affects: [24-documentation]

# Tech tracking
tech-stack:
  added: [websockets]
  patterns: ["detached process group spawn for reliable child tree cleanup", "port-release polling between sequential server lifecycles"]

key-files:
  created:
    - ui/scripts/capture-screenshots.ts
    - docs/images/order-processing-graph.png
    - docs/images/order-processing-dsl.png
    - docs/images/order-processing-inspector.png
    - docs/images/approval-workflow-graph.png
    - docs/images/approval-workflow-dsl.png
    - docs/images/approval-workflow-inspector.png
    - docs/images/data-pipeline-graph.png
    - docs/images/data-pipeline-dsl.png
    - docs/images/data-pipeline-inspector.png
    - docs/images/retry-and-recovery-graph.png
    - docs/images/retry-and-recovery-dsl.png
    - docs/images/retry-and-recovery-inspector.png
    - docs/images/intrinsic-showcase-graph.png
    - docs/images/intrinsic-showcase-dsl.png
    - docs/images/intrinsic-showcase-inspector.png
  modified:
    - ui/package.json

key-decisions:
  - "Installed websockets pip package in venv so uvicorn can serve WebSocket connections (graph editor requires /ws for YAML loading)"
  - "Used detached process groups (detached: true) with negative-PID kill for reliable npx/Vite child tree cleanup"
  - "Added port-release polling (waitForPortFree) between sequential server lifecycles to prevent port conflicts"
  - "Graph screenshot hides editor pane and palette via page.evaluate CSS manipulation for graph-focused view"

patterns-established:
  - "Screenshot capture pattern: rsf ui server for graph editor, Vite + mock inspect for inspector"
  - "Process tree cleanup: spawn with detached:true, kill with process.kill(-pid, signal)"

requirements-completed: [CAPT-04, CAPT-05, CAPT-06, CAPT-07]

# Metrics
duration: 12min
completed: 2026-02-27
---

# Phase 23 Plan 01: Screenshot Capture Summary

**Playwright-based capture of 15 PNG screenshots (graph-only, DSL editor, and execution inspector views) for all 5 example workflows via a single npm run screenshots command**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-27T10:56:13Z
- **Completed:** 2026-02-27T11:08:48Z
- **Tasks:** 2
- **Files modified:** 17

## Accomplishments
- Built capture-screenshots.ts (481 lines) that orchestrates rsf ui server, Vite dev server, and mock inspect server to capture all 15 screenshots automatically
- Graph editor screenshots show complete workflow graphs with all nodes, edges, retry/catch annotations, and state type labels for each example
- DSL screenshots show the full editor layout with Palette + YAML Editor + Graph Canvas side by side
- Inspector screenshots show populated execution data with timeline events, execution status, and state detail panels
- Wired up `npm run screenshots` for single-command regeneration

## Task Commits

Each task was committed atomically:

1. **Task 1: Create capture-screenshots.ts and capture 15 PNGs** - `57cb85c` (feat)
2. **Task 2: Add npm run screenshots and verify pipeline** - `b6cbc49` (feat)

## Files Created/Modified
- `ui/scripts/capture-screenshots.ts` - Playwright screenshot orchestration: manages server lifecycles, navigates browser, captures 3 views per example
- `ui/package.json` - Added `screenshots` script entry
- `docs/images/{example}-graph.png` (x5) - Graph-focused screenshots showing workflow graphs without editor panes
- `docs/images/{example}-dsl.png` (x5) - Full editor layout with YAML editor + graph canvas + palette
- `docs/images/{example}-inspector.png` (x5) - Execution inspector with timeline events, execution headers, state detail

## Decisions Made
- Installed `websockets` pip package in the Python venv to enable uvicorn's WebSocket protocol support. The graph editor SPA requires a WebSocket connection to `/ws` to receive the workflow YAML via `file_loaded` message, which triggers graph rendering. Without websockets, uvicorn returned 404 on WebSocket upgrade requests.
- Used `detached: true` in spawn options and `process.kill(-pid, signal)` for process group cleanup. The `npx vite` command creates wrapper child processes that don't die with simple `child.kill()`. Killing the process group ensures all descendants are cleaned up.
- Added `waitForPortFree()` helper that polls `lsof` to confirm ports are released before starting the next example's servers. This prevents "Port in use" errors on sequential captures.
- For the graph-only screenshot, used `page.evaluate()` to set `display: none` on `.editor-pane` and `.palette` elements, giving the graph canvas the full viewport width.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed websockets pip package for WebSocket support**
- **Found during:** Task 1 (initial capture attempt)
- **Issue:** rsf ui server's uvicorn instance had no WebSocket library installed, causing all `/ws` connections to fail with 404. The graph editor SPA requires WebSocket to load workflow YAML.
- **Fix:** Ran `pip install websockets` in the project venv, enabling uvicorn's websockets protocol handler
- **Files modified:** .venv/ (pip install, not committed)
- **Verification:** WebSocket connection succeeds, graph editor receives `file_loaded` message, nodes render
- **Committed in:** Part of 57cb85c (Task 1 commit)

**2. [Rule 3 - Blocking] Added process group management for reliable Vite cleanup**
- **Found during:** Task 1 (initial capture attempt)
- **Issue:** Vite spawned via `npx` creates child processes that survive SIGTERM on the npx wrapper. Ports remained occupied between examples causing "Port in use" errors.
- **Fix:** Used `detached: true` spawn option and `process.kill(-pid, signal)` to kill entire process trees. Added `waitForPortFree()` port-release polling between server cycles.
- **Files modified:** ui/scripts/capture-screenshots.ts
- **Verification:** All 5 examples capture sequentially with clean port handoff. No "Port in use" errors. `lsof` shows no leftover listeners after completion.
- **Committed in:** 57cb85c (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both auto-fixes essential for the script to function at all. No scope creep.

## Issues Encountered
- Inspector graph nodes do not render in the inspector screenshots because the mock inspect server provides execution event data but not the workflow graph definition. The inspector shows execution list, timeline events, execution header, and state detail panel correctly. The center graph area is empty but the ReactFlow container is present. This is a limitation of the mock data approach, not a bug.

## User Setup Required
None - no external service configuration required. The `websockets` pip package must be installed in the project venv for the rsf ui server WebSocket support (installed automatically during execution, can be reinstalled with `pip install websockets`).

## Next Phase Readiness
- All 15 screenshots ready for Phase 24 documentation integration
- Screenshots are idempotent: re-running `npm run screenshots` overwrites existing files
- Graph editor screenshots show rich workflow visualizations suitable for documentation
- Inspector screenshots show realistic execution data timeline

## Self-Check: PASSED

All 17 files verified present. Both task commits (57cb85c, b6cbc49) confirmed in git log.

---
*Phase: 23-screenshot-capture*
*Completed: 2026-02-27*
