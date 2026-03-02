---
phase: 42-developer-cli-commands
plan: 03
subsystem: cli
tags: [typer, rich, watch, file-watcher, watchfiles, auto-validate]

requires:
  - phase: 42-developer-cli-commands
    provides: Validate + generate pipeline from existing CLI commands
provides:
  - rsf watch CLI command with file monitoring and auto-validation
  - run_cycle function for validate+generate pipeline
  - watchfiles integration with polling fallback
affects: [43-operational-cli-commands]

tech-stack:
  added: [watchfiles]
  patterns: [run_cycle function, polling fallback, optional dependency]

key-files:
  created:
    - src/rsf/cli/watch_cmd.py
    - tests/test_cli/test_watch.py
  modified:
    - src/rsf/cli/main.py
    - pyproject.toml

key-decisions:
  - "watchfiles as optional dependency with polling fallback"
  - "run_cycle returns (bool, str) for testable cycle logic"
  - "Deploy failures reported but don't stop the watch loop"
  - "1-second polling interval for fallback mode"

patterns-established:
  - "run_cycle(workflow, deploy, tf_dir, stage) pure function"
  - "Optional dependency pattern with try/except ImportError"
  - "_format_timestamp for compact [HH:MM:SS] output"

requirements-completed: [CLI-03]

duration: 5min
completed: 2026-03-01
---

# Plan 42-03: rsf watch Summary

**File watcher with validate+generate cycle, --deploy for code-only Lambda updates, and watchfiles with polling fallback**

## Performance

- **Duration:** 5 min
- **Tasks:** 1
- **Files modified:** 4

## Accomplishments
- rsf watch monitors workflow.yaml and handlers/ directory for changes
- On each change: validate + regenerate orchestrator.py if valid
- Compact one-liner feedback: "[HH:MM:SS] Valid + regenerated"
- --deploy flag triggers code-only Lambda update after successful validation
- Deploy failures reported but don't crash the watch loop
- watchfiles library for efficient file watching
- Polling fallback when watchfiles not installed
- watchfiles added as optional dependency [watch] in pyproject.toml

## Task Commits

1. **Task 1: Implement watch cycle logic and CLI command** - `7c51cdf` (feat)

## Files Created/Modified
- `src/rsf/cli/watch_cmd.py` - Watch cycle, file watcher, polling fallback
- `src/rsf/cli/main.py` - Register watch command
- `tests/test_cli/test_watch.py` - 10 tests for watch cycle
- `pyproject.toml` - Add watchfiles optional dependency

## Decisions Made
None - followed plan as specified

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
None

## Next Phase Readiness
- Watch command ready for users
- Polling fallback ensures it works without watchfiles

---
*Phase: 42-developer-cli-commands*
*Completed: 2026-03-01*
