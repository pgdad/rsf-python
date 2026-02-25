# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.
**Current focus:** Phase 3 — Terraform Generation

## Current Position

Phase: 3 of 11 (Terraform Generation)
Plan: 0 of 2 in current phase
Status: Ready to plan
Last activity: 2026-02-25 — Phase 2 complete

Progress: [██░░░░░░░░] 18%

## Performance Metrics

**Velocity:**
- Total plans completed: 8
- Average duration: ~4 min/plan
- Total execution time: ~32 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. DSL Core | 5 | ~25 min | ~5 min |
| 2. Code Generation | 3 | ~7 min | ~2 min |

**Recent Trend:**
- Last 3 plans: 02-01 through 02-03 (all Phase 2)
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

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-25
Stopped at: Phase 2 complete (213 tests passing), ready for Phase 3
Resume file: None
