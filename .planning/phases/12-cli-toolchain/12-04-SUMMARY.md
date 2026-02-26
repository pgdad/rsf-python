---
phase: 12-cli-toolchain
plan: 04
subsystem: cli
tags: [typer, rich, fastapi, uvicorn, subprocess, asl, importer, editor, inspector, cli]

requires:
  - phase: 04-asl-importer
    provides: import_asl() pipeline, ImportResult with warnings and task_state_names
  - phase: 06-graph-editor-backend
    provides: rsf.editor.server.launch() FastAPI server launcher
  - phase: 08-inspector-backend
    provides: rsf.inspect.server.launch() FastAPI server launcher
  - phase: 12-01
    provides: Typer CLI app, subcommand registration pattern, CliRunner test pattern

provides:
  - rsf import subcommand: converts ASL JSON to RSF YAML with handler stubs
  - rsf ui subcommand: launches graph editor on configurable port with browser open
  - rsf inspect subcommand: launches inspector with ARN from --arn or terraform output discovery
  - 17 tests covering all three subcommands

affects: []

tech-stack:
  added: []
  patterns:
    - "Subcommand function name != command name: import_asl() registered as app.command(name='import') to avoid Python keyword conflict"
    - "Terraform ARN discovery: check tfstate exists first, then subprocess.run(['terraform', 'output', '-raw', 'function_arn'])"
    - "Server commands are blocking (uvicorn.run) — catch KeyboardInterrupt for clean shutdown message"
    - "Rich console used for all output: [blue] for status, [green] for success, [red] for errors, [yellow] for warnings, [dim] for server-stop"

key-files:
  created:
    - src/rsf/cli/import_cmd.py
    - src/rsf/cli/ui_cmd.py
    - src/rsf/cli/inspect_cmd.py
    - tests/test_cli/test_import.py
    - tests/test_cli/test_ui.py
    - tests/test_cli/test_inspect_cmd.py
  modified:
    - src/rsf/cli/main.py

key-decisions:
  - "import_asl() function name (not 'import') avoids Python reserved keyword; Typer name='import' in app.command() still works"
  - "Warn-and-overwrite pattern for existing output files: import is intentional conversion, not generation gap protection"
  - "Terraform ARN discovery: check terraform.tfstate existence before running terraform binary to give clean error when no state exists"
  - "KeyboardInterrupt caught in server commands (ui/inspect) to print graceful shutdown message instead of crash traceback"

patterns-established:
  - "Server launch commands use try/except KeyboardInterrupt with [dim]Server stopped[/dim] message"
  - "Terraform discovery: check {tf_dir}/terraform.tfstate exists, then subprocess.run terraform output"

requirements-completed: [CLI-05, CLI-06, CLI-07]

duration: 2min
completed: 2026-02-26
---

# Phase 12 Plan 04: rsf import, rsf ui, rsf inspect Subcommands Summary

**Three CLI subcommands wiring existing modules to the terminal: ASL-to-YAML conversion via rsf.importer.converter, graph editor launch via rsf.editor.server, and execution inspector launch via rsf.inspect.server with Terraform ARN discovery**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-26T14:38:46Z
- **Completed:** 2026-02-26T14:41:18Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- `rsf import asl.json` converts ASL JSON to workflow.yaml with handler stubs, showing per-warning messages for stripped Resource fields, malformed JSON, or missing files
- `rsf ui` launches graph editor on port 8765 with auto-browser open; `--no-browser` and `--port` flags work correctly
- `rsf inspect --arn <arn>` launches inspector; without `--arn`, attempts Terraform output discovery from `terraform/terraform.tfstate`
- 17 tests across all three subcommands — 7 for import (happy path, custom output, errors, warnings, stubs), 4 for ui, 6 for inspect

## Task Commits

Each task was committed atomically:

1. **Task 1: rsf import subcommand** - `fb5bf96` (feat)
2. **Task 2: rsf ui and rsf inspect subcommands** - `ad24759` (feat)

**Plan metadata:** (docs: complete plan)

## Files Created/Modified
- `src/rsf/cli/import_cmd.py` - import_asl() registered as 'import' command; file existence check, ValueError catch, overwrite warning, Rich output
- `src/rsf/cli/ui_cmd.py` - ui() registered as 'ui' command; blocking uvicorn launch with KeyboardInterrupt handler
- `src/rsf/cli/inspect_cmd.py` - inspect() registered as 'inspect' command; ARN from --arn or terraform output discovery, blocking launch
- `src/rsf/cli/main.py` - Added import_cmd, ui_cmd, inspect_cmd to subcommand registrations
- `tests/test_cli/test_import.py` - 7 tests: workflow.yaml creation, custom output, file-not-found, malformed JSON, Resource warnings, handler stubs, overwrite warning
- `tests/test_cli/test_ui.py` - 4 tests: defaults, custom port/no-browser, open_browser flag behavior
- `tests/test_cli/test_inspect_cmd.py` - 6 tests: arn flag, no-arn error, terraform discovery, terraform failure, port/browser flags, default port

## Decisions Made
- Function named `import_asl` (not `import`) to avoid Python reserved keyword conflict; `app.command(name="import")` maps it correctly to `rsf import`
- Warn-and-overwrite for existing output files: ASL import is explicit conversion, not incremental generation
- Terraform discovery checks `terraform.tfstate` existence before invoking the terraform binary to give a clean "no state" error vs a subprocess error
- `KeyboardInterrupt` caught inside both ui and inspect server commands to print `[dim]Server stopped[/dim]` cleanly

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 4 plans in Phase 12 are now complete
- Full CLI toolchain: rsf init, rsf deploy, rsf validate, rsf generate, rsf import, rsf ui, rsf inspect
- v1.1 milestone (CLI Toolchain) is delivered

---
*Phase: 12-cli-toolchain*
*Completed: 2026-02-26*
