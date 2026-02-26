# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.
**Current focus:** v1.3 Comprehensive Tutorial — Phase 18: Getting Started

## Current Position

Phase: 18 — Getting Started
Plan: 2/2 complete
Status: Phase 18 complete — Plan 01 (rsf init tutorial) and Plan 02 (rsf validate tutorial) done
Last activity: 2026-02-26 — Plan 18-02 complete: rsf validate tutorial (tutorials/02-workflow-validation.md)

Progress: [####░░░░░░░░░░░░░░░░] 10%

## Performance Metrics

**Velocity:**
- Total plans completed: 55 (v1.0: 39, v1.1: 4, v1.2: 10, v1.3: 2)

**By Milestone:**

| Milestone | Phases | Plans | Timeline |
|-----------|--------|-------|----------|
| v1.0 Core | 10 | 39 | 2026-02-25 |
| v1.1 CLI Toolchain | 1 | 4 | 2026-02-26 |
| v1.2 Examples & Integration | 5 | 10 | 2026-02-24 → 2026-02-26 |
| v1.3 Comprehensive Tutorial | 3 | TBD | 2026-02-26 → ? |

## Accumulated Context

### Decisions

All decisions logged in PROJECT.md Key Decisions table.

**18-01:** Tutorial structure established — prerequisites, numbered steps, verbatim template content in fenced code blocks, blockquotes for tips, explicit forward pointer to next tutorial.

**18-02:** rsf validate tutorial uses actual CLI output (not idealized); Stage 2 structural error (invalid Type) produces empty field-path — documented reality, not expectation. Learn-by-breaking pattern: full broken file + exact output + interpretation + fix.

### v1.3 Phase Structure

- Phase 18: Getting Started (SETUP-01, SETUP-02) — rsf init + rsf validate tutorials
- Phase 19: Build and Deploy (DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04) — rsf generate + rsf deploy + code-only + invoke/teardown
- Phase 20: Advanced Tools (MIGR-01, VIS-01, VIS-02, VIS-03) — rsf import + rsf ui + inspection Terraform + rsf inspect

### Tutorial Conventions (established at roadmap time)

- Every tutorial is a Markdown document with working code users follow step-by-step
- Self-contained: each tutorial includes all code, YAML, Terraform, and scripts needed
- Real AWS tutorials (Phase 19, Phase 20) use us-east-2 and require AWS credentials
- Teardown scripts must leave zero orphaned AWS resources

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-02-26
Stopped at: Completed 18-02-PLAN.md (rsf validate tutorial) — Phase 18 complete
Resume file: None
