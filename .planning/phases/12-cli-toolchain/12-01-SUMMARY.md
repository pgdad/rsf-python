---
phase: 12-cli-toolchain
plan: 01
subsystem: cli
tags: [typer, rich, jinja2, pyyaml, cli, scaffold, init]

requires:
  - phase: 01-dsl-core
    provides: StateMachineDefinition, load_yaml parser used in test validation
  - phase: 02-code-generation
    provides: handler decorator pattern shown in scaffold template

provides:
  - Typer CLI app at src/rsf/cli/main.py with --version flag
  - rsf init subcommand that scaffolds complete RSF project structure
  - Template files for workflow.yaml, handler, tests, pyproject.toml, .gitignore
  - CLI test suite with 7 passing tests

affects: [12-02-run-cmd, 12-03-validate-cmd, 12-04-generate-cmd]

tech-stack:
  added: []
  patterns:
    - "Typer app with app.command() decorator pattern for subcommand registration"
    - "Templates via Path(__file__).parent / 'templates' — no importlib.resources complexity"
    - "Jinja2 used only for pyproject.toml.j2; all other templates are static copies"
    - "Rich console for all CLI output (success summaries, error messages)"

key-files:
  created:
    - src/rsf/cli/main.py
    - src/rsf/cli/init_cmd.py
    - src/rsf/cli/templates/workflow.yaml
    - src/rsf/cli/templates/handler_example.py
    - src/rsf/cli/templates/test_example.py
    - src/rsf/cli/templates/gitignore
    - src/rsf/cli/templates/pyproject.toml.j2
    - tests/test_cli/__init__.py
    - tests/test_cli/test_main.py
    - tests/test_cli/test_init.py
  modified:
    - src/rsf/cli/__init__.py

key-decisions:
  - "Simplified __init__.py to empty package marker to avoid circular import warnings when running via -m"
  - "no_args_is_help=True uses Typer exit code 2 (not 0); test updated to accept both"
  - "Templates accessed via Path(__file__).parent / 'templates' for simplicity over importlib.resources"
  - "Only pyproject.toml uses Jinja2 template; other templates are shutil.copy2 for simplicity"

patterns-established:
  - "CLI subcommands live in src/rsf/cli/{cmd}_cmd.py, registered in main.py via app.command(name=...)(mod.func)"
  - "Tests use typer.testing.CliRunner with tmp_path + monkeypatch.chdir for isolation"

requirements-completed: [CLI-01, CLI-08]

duration: 3min
completed: 2026-02-26
---

# Phase 12 Plan 01: CLI Skeleton and rsf init Summary

**Typer CLI app with --version flag and rsf init scaffold that creates workflow.yaml, handlers/, pyproject.toml, .gitignore, and tests/ in under 100ms**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-26T14:32:58Z
- **Completed:** 2026-02-26T14:36:08Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- Typer CLI app at `src/rsf/cli/main.py` with `--version` callback and `init` subcommand registration
- Full `rsf init <project>` scaffold command creating 7 files in ~78ms
- 7 passing tests covering version flag, help display, scaffold creation, duplicate prevention, YAML validity, and pyproject.toml content
- Entry point `rsf = "rsf.cli.main:app"` in pyproject.toml confirmed working

## Task Commits

Each task was committed atomically:

1. **Task 1: Typer CLI skeleton with --version flag and subcommand stubs** - `b18a511` (feat)
2. **Task 2: rsf init scaffold command with templates and tests** - `45fd615` (feat)

**Plan metadata:** (pending final commit)

## Files Created/Modified
- `src/rsf/cli/main.py` - Typer app with --version callback and init subcommand registration
- `src/rsf/cli/__init__.py` - Package marker (simplified to avoid circular import warnings)
- `src/rsf/cli/init_cmd.py` - Full init subcommand using Rich for output, Jinja2 for pyproject.toml
- `src/rsf/cli/templates/workflow.yaml` - Minimal valid RSF workflow (Pass + Succeed states)
- `src/rsf/cli/templates/handler_example.py` - Sample handler using @state decorator pattern
- `src/rsf/cli/templates/test_example.py` - Pytest skeleton for scaffold project
- `src/rsf/cli/templates/gitignore` - Python/Terraform/IDE gitignore
- `src/rsf/cli/templates/pyproject.toml.j2` - Jinja2 template with {{ project_name }} placeholder
- `tests/test_cli/__init__.py` - Empty test package marker
- `tests/test_cli/test_main.py` - 3 tests for --version, --help, no-args behavior
- `tests/test_cli/test_init.py` - 4 tests for scaffold creation, duplicate guard, YAML validity, pyproject name

## Decisions Made
- Simplified `__init__.py` to empty package marker: importing `app` from `__init__.py` caused a `RuntimeWarning` about finding `rsf.cli.main` in sys.modules before execution when invoked via `python -m rsf.cli.main`. Keeping `__init__.py` as a plain marker avoids this.
- `no_args_is_help=True` with Typer exits with code 2 (not 0). Test updated to accept `exit_code in (0, 2)` to be version-tolerant.
- Only `pyproject.toml` uses Jinja2 templating; all other templates are static files copied with `shutil.copy2`. This avoids complexity when templates don't need variable substitution.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test assertion for no_args_is_help exit code**
- **Found during:** Task 1 test run
- **Issue:** Test asserted `exit_code == 0` but Typer's `no_args_is_help=True` exits with code 2
- **Fix:** Updated assertion to `exit_code in (0, 2)` with explanatory comment
- **Files modified:** tests/test_cli/test_main.py
- **Verification:** All 3 test_main.py tests pass
- **Committed in:** b18a511 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — incorrect test expectation for Typer version behavior)
**Impact on plan:** Minimal. Test expectation was incorrect for the installed Typer version. No scope creep.

## Issues Encountered
- Python 3.12 virtual environment required using `.venv/bin/python` for all test runs (no `python` alias in PATH)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CLI entry point established; all future subcommands (run, validate, generate) register via `app.command(name=...)(mod.func)` in `main.py`
- Template infrastructure in place under `src/rsf/cli/templates/`
- Test infrastructure established with `typer.testing.CliRunner` pattern
- Plans 12-02, 12-03, 12-04 can add subcommands by adding new `{cmd}_cmd.py` files and one line in `main.py`

---
*Phase: 12-cli-toolchain*
*Completed: 2026-02-26*
