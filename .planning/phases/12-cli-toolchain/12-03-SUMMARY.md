---
phase: 12-cli-toolchain
plan: 03
subsystem: cli
tags: [typer, rich, terraform, subprocess, deploy, cli]

requires:
  - phase: 12-01
    provides: CLI skeleton (main.py, Typer app, test patterns)
  - phase: 01-dsl-core
    provides: StateMachineDefinition, load_definition parser
  - phase: 02-code-generation
    provides: codegen.generator.generate() for orchestrator + handlers
  - phase: 03-terraform-generation
    provides: terraform.generator.generate_terraform(), TerraformConfig

provides:
  - rsf deploy subcommand with --code-only, --auto-approve/-y, --tf-dir flags
  - Full deploy pipeline: validate -> codegen -> terraform gen -> init -> apply
  - Code-only pipeline: validate -> codegen -> targeted Lambda apply
  - 9 passing tests with all subprocess calls mocked

affects: []

tech-stack:
  added: []
  patterns:
    - "subprocess.run with check=True + CalledProcessError handler for terraform invocation"
    - "shutil.which for binary availability detection"
    - "Rich Status spinner for long-running generation steps"
    - "Targeted terraform apply with -target=aws_lambda_function.* for code-only updates"

key-files:
  created:
    - src/rsf/cli/deploy_cmd.py
    - tests/test_cli/test_deploy.py
  modified:
    - src/rsf/cli/main.py (deploy subcommand already registered by prior plans)

key-decisions:
  - "load_definition() from rsf.dsl.parser already performs both loading and Pydantic validation — no separate validate_definition() needed"
  - "Workflow name derived from definition.comment when set, falling back to workflow filename stem"
  - "Code-only mode checks for tf_dir existence before proceeding — clear error if infrastructure not deployed yet"
  - "terraform init is only run during full deploy, not during code-only updates"

duration: 1min
completed: 2026-02-26
---

# Phase 12 Plan 03: rsf deploy Subcommand Summary

**rsf deploy subcommand orchestrating validate -> codegen -> terraform gen -> init -> apply with --code-only for targeted Lambda-only updates**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-26T14:38:52Z
- **Completed:** 2026-02-26T14:40:00Z
- **Tasks:** 1
- **Files created:** 2

## Accomplishments

- `rsf deploy` orchestrates the full pipeline: load/validate workflow -> codegen -> terraform gen -> terraform init -> terraform apply
- `rsf deploy --code-only` skips Terraform generation and init, runs targeted `terraform apply -target=aws_lambda_function.* -auto-approve`
- `rsf deploy --auto-approve` / `-y` appends `-auto-approve` to terraform apply command
- `rsf deploy --tf-dir <path>` allows custom Terraform output directory (default: `terraform`)
- Terraform binary detection via `shutil.which("terraform")` with clear error and install URL
- `subprocess.CalledProcessError` caught at both init and apply stages with exit code 1
- 9 tests, all passing, all subprocess calls mocked (no actual terraform execution)

## Task Commits

1. **Task 1: deploy_cmd.py + tests** - `9d9d271` (feat)

## Files Created/Modified

- `src/rsf/cli/deploy_cmd.py` - Deploy subcommand with full and code-only flows using Rich console + subprocess
- `tests/test_cli/test_deploy.py` - 9 tests covering happy path, --code-only, --auto-approve, no workflow, no terraform binary, CalledProcessError, no tf_dir

## Decisions Made

- `load_definition()` already validates via Pydantic v2 — the plan's reference to `validate_definition` is handled by the same call
- Workflow name falls back to `workflow.stem` (e.g., `workflow.yaml` → `workflow`) when `definition.comment` is None
- Code-only path checks `tf_dir.exists()` before running targeted apply — gives a clear error if infrastructure hasn't been deployed yet
- No `terraform init` in code-only path (infrastructure already initialized on prior full deploy)

## Deviations from Plan

None — plan executed exactly as written.

The `validate_definition` function mentioned in the plan does not exist as a separate function; `load_definition()` in `rsf.dsl.parser` performs both parsing and Pydantic validation atomically. This was handled by using `load_definition()` and wrapping it in a `try/except (ValueError, ValidationError)` block.

## Issues Encountered

None. All tests pass on first run.

## Self-Check

- `src/rsf/cli/deploy_cmd.py` — created
- `tests/test_cli/test_deploy.py` — created
- Commit `9d9d271` — exists

## Self-Check: PASSED

## Next Phase Readiness

- Phase 12 is now 3/4 plans complete (plans 01, 03 confirmed; prior work included 02 and 04)
- All CLI subcommands (init, deploy, validate, import) are registered in main.py
- Pattern for future subcommands established: `{cmd}_cmd.py` + register in `main.py` + tests

---
*Phase: 12-cli-toolchain*
*Completed: 2026-02-26*
