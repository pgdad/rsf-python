# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.
**Current focus:** v1.1 CLI Toolchain — Phase 12

## Current Position

Phase: 12 of 12 (CLI Toolchain)
Plan: 4 of 4 in current phase
Status: Complete
Last activity: 2026-02-26 — Plan 12-04 complete (rsf import, rsf ui, rsf inspect subcommands)

Progress: [##########] v1.1 complete — Phase 12 plan 4/4 complete (all plans done)

## Performance Metrics

**Velocity:**
- Total plans completed: 39 (v1.0)
- Average duration: ~2 min/plan
- Total execution time: ~80 min

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
| 10. Testing | 9 | ~10 min | ~1 min |
| 11. Documentation | 4 | ~5 min | ~1.25 min |
| 12. CLI Toolchain | 4/4 | ~6 min | ~1.5 min |

**Recent Trend:**
- v1.0 complete: 39 plans across 10 phases
- Trend: Stable
| Phase 12 P04 | 2 | 2 tasks | 7 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v1.1]: Phase 12 is a single phase (4 plans) covering all 8 CLI requirements — CLI work is one coherent delivery with no internal dependency split
- [12-01]: Simplified CLI __init__.py to empty package marker to avoid circular import warnings
- [12-01]: no_args_is_help=True uses Typer exit code 2; tests updated to accept both 0 and 2
- [12-01]: Templates accessed via Path(__file__).parent / 'templates'; only pyproject.toml.j2 uses Jinja2
- [12-02]: validate_cmd and generate_cmd each implement the validation pipeline inline (no shared helper) for self-contained readability
- [12-02]: generate_cmd passes handlers_dir=output_dir/'handlers' explicitly to generator.generate() for predictable output structure
- [12-02]: Field-path formatting: Pydantic errors via '.'.join(str(loc) for loc in err['loc']); semantic errors via ValidationError.path attribute
- [12-03]: load_definition() handles both loading and Pydantic validation — no separate validate_definition() needed
- [12-03]: Workflow name derived from definition.comment, falling back to workflow filename stem
- [12-03]: Code-only mode checks tf_dir existence before proceeding; terraform init skipped in code-only path
- [Phase 12]: import_asl() function name (not 'import') avoids Python reserved keyword; Typer name='import' in app.command() still works
- [Phase 12]: Terraform ARN discovery checks terraform.tfstate existence before invoking binary for clean error handling
- [Phase 12]: KeyboardInterrupt caught in server commands (ui/inspect) to print graceful shutdown message

### Pending Todos

None.

### Blockers/Concerns

None. All v1.0 modules (DSL, codegen, Terraform, importer, graph editor backend, inspector backend) exist and are tested. Phase 12 wires them together via Typer.

## Session Continuity

Last session: 2026-02-26
Stopped at: Completed 12-04-PLAN.md (rsf import, rsf ui, rsf inspect subcommands — Phase 12 complete)
Resume file: None
