---
phase: 39-infrastructure-decoupling-and-workflow-timeout
plan: 01
subsystem: cli
tags: [typer, cli, terraform, no-infra]

requires:
  - phase: 38-lambda-function-url-support
    provides: "deploy command with Terraform generation pipeline"
provides:
  - "--no-infra flag on rsf generate and rsf deploy commands"
  - "Mutual exclusion check for --no-infra and --code-only"
affects: [cli, deploy, terraform]

tech-stack:
  added: []
  patterns: ["mutual exclusion flag validation pattern"]

key-files:
  created: []
  modified:
    - src/rsf/cli/generate_cmd.py
    - src/rsf/cli/deploy_cmd.py
    - tests/test_cli/test_generate.py
    - tests/test_cli/test_deploy.py

key-decisions:
  - "--no-infra on generate is a no-op today (generate already only produces code) but accepted for forward compatibility"
  - "--no-infra on deploy skips all Terraform steps after code generation"
  - "--no-infra and --code-only are mutually exclusive (code-only targets existing Terraform state)"

patterns-established:
  - "Flag mutual exclusion: check at top of command, exit 1 with clear message"

requirements-completed: [INFRA-01]

duration: 2min
completed: 2026-03-01
---

# Phase 39 Plan 01: Add --no-infra Flag to Generate and Deploy Summary

**Added `--no-infra` flag to `rsf generate` and `rsf deploy` enabling infrastructure-free code generation and deployment**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-01T21:12:16Z
- **Completed:** 2026-03-01T21:13:53Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 4

## Accomplishments
- `rsf generate --no-infra` accepted and prints informational skip message
- `rsf deploy --no-infra` generates code but skips all Terraform generation, init, and apply steps
- `rsf deploy --no-infra --code-only` rejected with clear mutual exclusion error (exit 1)
- All 24 existing + new CLI tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing tests for --no-infra** - `6bb029a` (test)
2. **Task 1 (GREEN): Implement --no-infra flag** - `8e419b8` (feat)

## Files Created/Modified
- `src/rsf/cli/generate_cmd.py` - Added `--no-infra` flag parameter and skip message
- `src/rsf/cli/deploy_cmd.py` - Added `--no-infra` flag with mutual exclusion check and Terraform skip logic
- `tests/test_cli/test_generate.py` - Added TestGenerateNoInfra class with 3 tests
- `tests/test_cli/test_deploy.py` - Added 4 tests for --no-infra behavior on deploy

## Decisions Made
- --no-infra on generate is a no-op since generate currently only produces code, but the flag is accepted for forward compatibility
- Mutual exclusion with --code-only enforced because --code-only targets existing Terraform state which conflicts with --no-infra's intent

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Ready for plan 39-02 (workflow timeout enforcement)
- --no-infra flag is independent of timeout functionality

---
*Phase: 39-infrastructure-decoupling-and-workflow-timeout*
*Completed: 2026-03-01*
