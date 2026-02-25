# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.
**Current focus:** Phase 5 — CLI Toolchain

## Current Position

Phase: 5 of 11 (CLI Toolchain)
Plan: 0 of 4 in current phase
Status: Ready to plan
Last activity: 2026-02-25 — Phase 4 complete

Progress: [████░░░░░░] 36%

## Performance Metrics

**Velocity:**
- Total plans completed: 12
- Average duration: ~3 min/plan
- Total execution time: ~38 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. DSL Core | 5 | ~25 min | ~5 min |
| 2. Code Generation | 3 | ~7 min | ~2 min |
| 3. Terraform Generation | 2 | ~3 min | ~1.5 min |
| 4. ASL Importer | 2 | ~3 min | ~1.5 min |

**Recent Trend:**
- Last 2 plans: 04-01 through 04-02 (all Phase 4)
- Trend: fast execution

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Pydantic v2 discriminated unions for state types (circular import broken via model_validator hook in __init__.py)
- BFS traversal for code generation (ensures all reachable states included)
- Custom Jinja2 delimiters (`<< >>`, `<% %>`) for HCL (avoids `${}` Terraform conflict)
- Generation Gap pattern (first-line marker determines overwritability)
- State validation hook pattern: _state_validator callable injected from dsl/__init__.py into models module, triggered by model_validator on BranchDefinition and StateMachineDefinition
- Pre-rendered state code blocks passed to Jinja2 template (hybrid approach: Python emitter + Jinja2 template for orchestrator)
- topyrepr filter uses Python repr() (single quotes for strings, True/False/None)
- ASL JSON string detection: check for `{` or `[` prefix to distinguish from file paths
- Reuse codegen render_handler_stub and _to_snake_case for importer handler stubs

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-25
Stopped at: Phase 4 complete (280 tests passing), ready for Phase 5
Resume file: None
