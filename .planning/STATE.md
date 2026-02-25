# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.
**Current focus:** Phase 10 — Testing

## Current Position

Phase: 10 of 11 (Testing)
Plan: 0 of 9 in current phase
Status: Ready to plan
Last activity: 2026-02-25 — Phase 9 complete

Progress: [███████░░░] 68%

## Performance Metrics

**Velocity:**
- Total plans completed: 26
- Average duration: ~3 min/plan
- Total execution time: ~65 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. DSL Core | 5 | ~25 min | ~5 min |
| 2. Code Generation | 3 | ~7 min | ~2 min |
| 3. Terraform Generation | 2 | ~3 min | ~1.5 min |
| 4. ASL Importer | 2 | ~3 min | ~1.5 min |
| 6. Graph Editor Backend | 2 | ~2 min | ~1 min |
| 7. Graph Editor UI | 5 | ~15 min | ~3 min |
| 8. Inspector Backend | 2 | ~3 min | ~1.5 min |
| 9. Inspector UI | 5 | ~7 min | ~1.5 min |

**Recent Trend:**
- Last 5 plans: 09-01 through 09-05 (Phase 9)
- Trend: steady execution

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
- React 19 + Vite + TypeScript for graph editor SPA
- @xyflow/react v12 with custom node/edge types for workflow visualization
- Zustand 5 + immer for state management
- syncSource pattern (set before mutation, cleared after queueMicrotask) prevents infinite YAML/graph update loops
- AST-merge strategy for Graph→YAML sync preserves complex data (Choice rules, Catch arrays)
- ELK.js Sugiyama layered algorithm for auto-layout (top-to-bottom, LAYER_SWEEP crossing minimization)
- Token bucket rate limiter (12 req/s) wrapping async boto3 calls to stay under 15 req/s Lambda control plane limit
- asyncio.to_thread wrapping synchronous boto3 calls (avoids aiobotocore dependency)
- SSE stream lifecycle: initial fetch → poll every 5s → close on terminal status
- Hash-based routing (#/editor, #/inspector) for SPA mode switching
- Separate Zustand inspectStore for inspector (parallel to flowStore for editor)
- Precomputed TransitionSnapshots array for O(1) time machine scrubbing
- InspectorNode/InspectorEdge components with overlay props (separate from editor node types)
- Flat path comparison for structural JSON diff (color-coded: green/red/yellow)
- Tab visibility API to pause SSE when browser tab hidden

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-25
Stopped at: Phase 9 complete (359 tests passing), ready for Phase 10
Resume file: None
