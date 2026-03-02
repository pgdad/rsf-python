# Phase 42: Developer CLI Commands - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Three new CLI commands that improve the inner development loop: `rsf diff` (compare local vs deployed), `rsf test` (local workflow execution with trace), and `rsf watch` (auto-validate/generate on file changes with optional deploy). These are developer-facing commands registered in the existing Typer CLI app.

</domain>

<decisions>
## Implementation Decisions

### Diff output format
- Semantic diff at the workflow definition level — compare state names, transitions, handler signatures (not raw YAML lines)
- Also support `--raw` flag for full YAML diff when needed
- Display as a Rich structured table with columns: Component | Change | Local | Deployed
- Color-coded rows: green=added, red=removed, yellow=changed
- Exit code 1 when differences exist (like `git diff --exit-code`) for CI pipeline drift detection
- "No differences found." simple message + exit 0 when clean

### Deployed state source
- Read from Terraform state files (matches existing `rsf inspect` pattern) — works offline after initial deploy
- Support `--stage` flag (same pattern as Phase 41's `rsf deploy --stage`) to diff against specific stages — looks in `terraform/<stage>/`
- When no Terraform state exists (never deployed), show everything as 'new' (all additions) — useful pre-deploy
- Compare at the workflow definition level, not Terraform resource level — extract workflow.yaml equivalent from state

### Local test execution
- Actually call Python handler functions locally (real execution with real results)
- Also support `--mock-handlers` flag for pass-through mode that tests workflow structure without handler logic
- Streaming line-by-line trace output: `State1 -> State2 (handler: 42ms)` with input/output on verbose
- Plus summary table at the end — both streaming and summary
- Follow Retry/Catch states on handler exceptions (mirrors real Step Functions behavior); stop with traceback if no error handling exists
- Support `--json` flag for machine-readable JSON lines output (one per transition) for piping to jq or CI

### Watch behavior
- Monitor workflow.yaml + handlers/ directory by default
- On each change: validate + regenerate orchestrator.py if valid (mirrors `rsf generate` pipeline)
- Compact one-liner feedback per cycle: `[12:34:05] Valid + regenerated` or `[12:34:05] 2 errors — see above`
- `--deploy` failures: show error, keep watching (don't stop the loop — user can fix and save again)

### Claude's Discretion
- Debounce timing for rapid consecutive saves in watch mode
- Exact column widths and formatting in diff table
- How to extract workflow definition from Terraform state internals
- File watcher library choice (watchdog, watchfiles, etc.)

</decisions>

<specifics>
## Specific Ideas

- `rsf diff` should feel like `git diff --exit-code` — clean output, useful exit codes, CI-friendly
- `rsf test` trace should feel like watching a workflow execute step-by-step in real time
- `rsf watch` should feel like `tsc --watch` or `nodemon` — lightweight, stays out of the way

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `rich.console.Console` and `rich.status.Status`: Used by all existing CLI commands for output
- `rsf.dsl.parser.load_definition`: Loads and validates workflow YAML — reusable for diff and test
- `rsf.dsl.validator.validate_definition`: Semantic validation — reusable for watch cycle
- `rsf.codegen.generator.generate`: Code generation — reusable for watch cycle
- `rsf.cli.inspect_cmd`: Terraform state ARN discovery pattern — reusable for diff

### Established Patterns
- Typer CLI with `app.command(name=...)` registration in main.py
- Each command in its own `*_cmd.py` file
- `console = Console()` at module level
- Rich Status spinners for long operations
- Common flag patterns: `--tf-dir`, `--stage`, positional `workflow` argument

### Integration Points
- `main.py` — register `diff`, `test`, `watch` commands
- `deploy_cmd.py` — `--stage` and `--tf-dir` patterns to reuse
- `validate_cmd.py` + `generate_cmd.py` — validation+generation pipeline for watch
- Terraform state files in `terraform/` or `terraform/<stage>/`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 42-developer-cli-commands*
*Context gathered: 2026-03-01*
