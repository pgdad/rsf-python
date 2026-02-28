# RSF — Replacement for Step Functions

## What This Is

RSF is a complete replacement for AWS Step Functions built on AWS Lambda Durable Functions (launched at re:Invent 2025). It provides a YAML/JSON-based DSL for defining state machines, a Python code generator that produces Lambda Durable Functions SDK code, a React-based visual graph editor, Terraform infrastructure generation, an ASL JSON importer, a CLI toolchain, and an execution inspector with time machine debugging. Users define workflows in the DSL, generate deployment-ready Lambda code, connect business logic via `@state` decorators, deploy via Terraform, and inspect execution state with a web-based debugger. Five real-world example workflows with automated integration testing prove end-to-end correctness on real AWS.

## Core Value

Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.

## Current State

v1.5 shipped (2026-02-28). RSF is installable via `pip install rsf` with bundled React UIs, git-tag versioning (hatch-vcs), and CI/CD publishing to PyPI. GitHub Actions CI runs lint + tests on PRs; release workflow builds wheel with React UIs and publishes to PyPI on v* tag push using OIDC trusted publisher (no API tokens). README serves as polished landing page on both GitHub and PyPI with badges, quick-start guide, and hero screenshots. 18,696 LOC Python. 152 local tests + 13 integration tests + 20 harness tests passing.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ YAML/JSON DSL with full ASL feature parity (8 state types, 39 comparison operators, error handling, I/O processing, intrinsic functions, variables, context object) — v1.0
- ✓ Pydantic v2 models for all DSL elements with semantic cross-state validation (BFS) — v1.0
- ✓ Python code generator (Jinja2) producing Lambda Durable Functions SDK orchestrator code — v1.0
- ✓ Handler registry with `@state` and `@startup` decorators and auto-discovery — v1.0
- ✓ 5-stage I/O processing pipeline (InputPath → Parameters → ResultSelector → ResultPath → OutputPath) — v1.0
- ✓ 18 intrinsic functions with recursive descent parser — v1.0
- ✓ ASL Context Object model (`$$`) — v1.0
- ✓ Terraform HCL generation with custom Jinja2 delimiters, IAM derivation, and Generation Gap pattern — v1.0
- ✓ ASL JSON importer (parse → convert → emit YAML + handler stubs) — v1.0
- ✓ FastAPI backend for graph editor (REST + WebSocket + static file serving) — v1.0
- ✓ React graph editor with bidirectional YAML ↔ graph sync, per-state-type nodes, ELK.js auto-layout — v1.0
- ✓ FastAPI backend for execution inspector (REST + SSE) — v1.0
- ✓ React execution inspector with time machine scrubbing, live updates, structural data diffs — v1.0
- ✓ JSON Schema generation from Pydantic models for Monaco editor validation — v1.0
- ✓ Mock SDK for local testing of generated code — v1.0
- ✓ Comprehensive test suite (unit tests, integration tests, golden fixtures) — v1.0
- ✓ CLI toolchain: `rsf init`, `rsf generate`, `rsf validate`, `rsf deploy`, `rsf import`, `rsf ui`, `rsf inspect` — v1.1
- ✓ Five example workflows covering all 8 state types with DSL YAML, Python handlers, and local tests — v1.2
- ✓ Per-example Terraform infrastructure with isolated state, durable_config, and DynamoDB integration — v1.2
- ✓ Integration test harness: poll_execution, query_logs, terraform_teardown, UUID execution IDs — v1.2
- ✓ Dual-channel AWS verification: Lambda return values + CloudWatch log assertions on real AWS — v1.2
- ✓ Example documentation: per-example READMEs + top-level quick-start guide — v1.2
- ✓ 8 step-by-step tutorials covering all 7 CLI commands (init, generate, validate, deploy, import, ui, inspect) — v1.3
- ✓ Hands-on walkthroughs with working code users can follow step-by-step — v1.3
- ✓ Real AWS deployment tutorials with complete Terraform and provisioning scripts — v1.3
- ✓ Self-contained tutorial artifacts (handler code, YAML workflows, test scripts) — v1.3
- ✓ Automated Playwright screenshot capture for graph editor and execution inspector — v1.4
- ✓ Screenshot assets for all 5 example workflows (15 PNGs via `npm run screenshots`) — v1.4
- ✓ Example READMEs updated with embedded screenshots — v1.4
- ✓ Tutorial docs (07-graph-editor, 08-execution-inspector) updated with screenshots — v1.4
- ✓ PyPI package with bundled React UI static assets and hatch-vcs git-tag versioning — v1.5
- ✓ GitHub Actions CI/CD pipeline (lint + test on PR, build + publish on tag push) — v1.5
- ✓ OIDC trusted publisher for zero-secret PyPI publishing — v1.5
- ✓ README as polished landing page with badges, quick-start, and hero screenshots — v1.5

### Active

<!-- Current scope. Building toward these. -->

(None — start next milestone with `/gsd:new-milestone`)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Go or other language runtime support — Python-only implementation
- Team collaboration features — local-first tool, no multi-user editing
- Hosted web service with authentication — runs on developer's machine
- VS Code extension — CLI + web UI is the interface
- Direct AWS Console integration — operates independently
- Mobile app — desktop developer tool
- LocalStack / moto mocking of durable functions — Lambda Durable Functions (re:Invent 2025) not supported by either framework
- Parallel CI test execution — need cost and timing data from sequential runs first
- Java port — moved to separate rsf-java repo

## Context

- **Lambda Durable Functions SDK:** `aws_lambda_durable_execution_sdk_python` provides `context.step()`, `context.wait()`, `context.parallel()`, `context.map()` primitives with checkpoint/replay semantics
- **Runtime requirement:** Python 3.13+ (SDK requirement)
- **AWS provider >= 6.25.0** required for `durable_config` block in Terraform
- **Lambda control plane rate limit:** 15 req/s — inspector uses token bucket rate limiter at 12 req/s ceiling
- **Durable Lambda invocation:** Uses Event type (async), poll `list_durable_executions_by_function` for completion
- **Key SDK note:** `parallel()` and `map()` return `BatchResult` — call `.get_results()` for plain list
- The DSL achieves full AWS Step Functions ASL feature parity
- Shipped v1.2 with ~8,261 LOC in examples + test harness (Python, YAML, Terraform, Markdown)
- Shipped v1.3 with 2,753 lines of tutorial documentation across 8 tutorials
- Shipped v1.4 with 15 automated Playwright screenshots embedded in example READMEs and tutorials
- Shipped v1.5 with PyPI packaging, CI/CD, and README landing page

## Constraints

- **Runtime:** Python 3.13+ — Lambda Durable Functions SDK requirement
- **Infrastructure:** Terraform for IaC (not CDK/SAM/CloudFormation)
- **UI Framework:** React 19.x with @xyflow/react 12.x for graph visualization
- **Graph Layout:** elkjs 0.11.x Sugiyama layered algorithm
- **Import Format:** AWS Step Functions ASL JSON as input format
- **Feature Parity:** All AWS Step Functions features in the DSL
- **Local-first:** No hosted service, no authentication
- **License:** Apache-2.0

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Pydantic v2 discriminated unions for state types | Type-safe parsing with clear error messages; circular import broken via late binding in `__init__.py` | ✓ Good |
| BFS traversal for code generation | Ensures all reachable states (including Choice branches and loop targets) are included | ✓ Good |
| AST-merge strategy for Graph→YAML sync | Preserves complex state data (Choice rules, Catch arrays, Parallel branches) that the graph view can't represent | ✓ Good |
| Custom Jinja2 delimiters (`<< >>`, `<% %>`) for HCL | Avoids `${}` conflict with Terraform interpolation | ✓ Good |
| syncSource flag for bidirectional sync | Prevents infinite YAML↔Graph update loops; set before mutation, cleared after microtask | ✓ Good |
| Precomputed snapshots for time machine | O(1) scrubbing instead of O(n) recomputation per position | ✓ Good |
| Generation Gap pattern (first-line marker) | Generated code always overwritten; user code never touched | ✓ Good |
| Token bucket rate limiter (12 req/s) | Stays under 15 req/s Lambda control plane limit | ✓ Good |
| Separate Zustand stores (Flow + Inspect) | No cross-contamination between editor and inspector concerns | ✓ Good |
| Mock SDK for testing | Enables local execution of generated code without AWS | ✓ Good |
| Custom polling helper over DurableFunctionCloudTestRunner | Simpler, fewer dependencies, polling `list_durable_executions_by_function` by DurableExecutionName | ✓ Good |
| CloudWatch Logs Insights with 15s propagation buffer | Handles log delivery delays; retry loop ensures eventual consistency | ✓ Good |
| UUID-suffixed execution IDs (test-{name}-{ts}-{uuid8}) | Prevents collision across parallel/sequential re-runs | ✓ Good |
| Explicit delete_log_group after terraform destroy | Catches orphaned log groups that Terraform may miss | ✓ Good |
| hatchling + hatch-vcs for packaging | Git-tag-derived versioning, simple config, standard PEP 517 build | ✓ Good |
| Separate ci.yml and release.yml workflows | Different triggers, different permission scopes (id-token: write only on publish) | ✓ Good |
| OIDC trusted publisher for PyPI | Zero secrets stored in repo; PyPI and GitHub exchange OIDC token at publish time | ✓ Good |
| Absolute URLs in README for PyPI | PyPI does not resolve relative paths; raw.githubusercontent.com for images | ✓ Good |

---
*Last updated: 2026-02-28 after v1.5 milestone*
