# Milestone Context: v1.3 Comprehensive Tutorial

**Captured:** 2026-02-26
**Status:** Ready for new-milestone workflow (step 2 — gather goals)

## User's Description

Create comprehensive tutorial that teaches users how to use the RSF CLI tool covering all of its use cases, include examples with the tutorial, walk user through how to use each feature end-to-end. Include inspecting running state machines, which means the specific tutorial for the inspection feature has to create real workflows in AWS and then provision and use them. Provide complete Terraform for all tutorials that require real deployment to AWS. Provide all scripts needed to provision and test.

## Scope Summary

- **Tutorial coverage:** All RSF CLI commands (init, generate, validate, deploy, import, ui, inspect)
- **End-to-end walkthroughs:** Each feature demonstrated with working code
- **Real AWS deployment:** Inspector tutorial requires live workflows — Terraform + scripts included
- **Self-contained:** Complete Terraform, handler code, and test scripts for every tutorial requiring AWS
- **Hands-on:** User follows along step-by-step, not just reads documentation

## Key Decisions Needed

- Suggested version: v1.3
- Suggested name: "Comprehensive Tutorial"
- Research: Skip (existing codebase is well-understood, no new tech needed)
- Phase numbering: Continue from 18

## Existing CLI Commands to Cover

From v1.1 (validated):
1. `rsf init` — Project scaffolding
2. `rsf generate` — Code generation (orchestrator + handler stubs)
3. `rsf validate` — 3-stage validation pipeline
4. `rsf deploy` — Terraform deploy + `--code-only` fast path
5. `rsf import` — ASL JSON import
6. `rsf ui` — Graph editor
7. `rsf inspect` — Execution inspector with time machine

## Previous Milestones

- v1.0: Core (DSL, codegen, Terraform, ASL importer, graph editor, inspector, testing, docs) — 10 phases
- v1.1: CLI Toolchain (7 commands) — 1 phase
- v1.2: Examples & Integration Testing (5 examples, 13 integration tests) — 5 phases
- Last phase number: 17
