---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Pluggable Infrastructure Providers
status: ready_to_plan
last_updated: "2026-03-02"
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-02)

**Core value:** Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.
**Current focus:** v3.0 Pluggable Infrastructure Providers — Phase 51

## Current Position

Phase: 51 of 55 (Provider Interface and Metadata Foundation)
Plan: — (not yet planned)
Status: Ready to plan
Last activity: 2026-03-02 — v3.0 roadmap created; 5 phases, 29 requirements mapped

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 118 (across v1.0–v2.0)

**By Milestone:**

| Milestone | Phases | Plans | Timeline |
|-----------|--------|-------|----------|
| v1.0 Core | 10 | 39 | 2026-02-25 |
| v1.1 CLI Toolchain | 1 | 4 | 2026-02-26 |
| v1.2 Examples & Integration | 5 | 10 | 2026-02-24 → 2026-02-26 |
| v1.3 Comprehensive Tutorial | 3 | 8 | 2026-02-26 |
| v1.4 UI Screenshots | 4 | 5 | 2026-02-26 → 2026-02-27 |
| v1.5 PyPI Packaging | 3 | 3 | 2026-02-28 |
| v1.6 Ruff Linting Cleanup | 8 | 3 | 2026-02-28 → 2026-03-01 |
| v1.7 Lambda Function URL | 3 | 8 | 2026-03-01 |
| v2.0 Enhancement Suite | 12 | 34 | 2026-03-01 → 2026-03-02 |

## Accumulated Context

### Decisions

All decisions logged in PROJECT.md Key Decisions table.

Key decisions for v3.0 (from research):
- [Phase 51]: Use `abc.ABC` over `typing.Protocol` — RSF owns all providers, ABC gives runtime TypeError on missing methods
- [Phase 51]: Interface defined in DSL/workflow semantics (WorkflowMetadata), not IaC tool semantics — prevents leaky abstraction
- [Phase 52]: Default provider is `"terraform"` with zero config required — v2.0 workflows must work unchanged
- [Phase 52]: Provider selection cascade: workflow YAML → rsf.toml → hardcoded default `"terraform"`
- [Phase 53]: `aws-cdk-lib` goes in generated CDK app's requirements.txt only — not in RSF's pyproject.toml
- [Phase 54]: Always `shell=False`; program path must be absolute and executable before invocation
- [Phase 55]: Terraform check in `rsf doctor` becomes WARN (not FAIL) when non-Terraform provider is configured

### Pending Todos

None.

### Blockers/Concerns

- [Phase 53]: CDK app template structure (`app.py`, `stack.py`, `cdk.json`) needs CDK CLI experiment (`cdk init app --language python`) before template authoring — flag for plan-phase
- [Phase 53]: CDK bootstrap detection (exact AWS API call to detect `CDKToolkit` stack) not yet specified — flag for plan-phase
- [Phase 55]: `watch --deploy` behavior with slow providers (CDK deploy takes minutes) needs design decision: debounce, disable, or provider timeout

## Session Continuity

Last session: 2026-03-02
Stopped at: Roadmap created for v3.0, ready to plan Phase 51
Resume file: None
