# RSF — Replacement for Step Functions

## What This Is

RSF is a complete replacement for AWS Step Functions built on AWS Lambda Durable Functions (launched at re:Invent 2025). It provides a YAML/JSON-based DSL for defining state machines, a Python code generator that produces Lambda Durable Functions SDK code, a React-based visual graph editor, Terraform infrastructure generation, an ASL JSON importer, a CLI toolchain, and an execution inspector with time machine debugging. Users define workflows in the DSL, generate deployment-ready Lambda code, connect business logic via `@state` decorators, deploy via Terraform, and inspect execution state with a web-based debugger.

## Core Value

Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.

## Current State

v1.1 shipped (2026-02-26). Full CLI toolchain delivered. The complete RSF workflow (init → generate → validate → deploy → import → ui → inspect) is available from a single `rsf` entry point.

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

### Active

<!-- Current scope. Building toward these. -->

- [ ] Use-case based example workflows covering all 8 state types, 39 comparison operators, 18 intrinsic functions, error handling, I/O processing, variables, and context objects
- [ ] Complete implementation for each example: DSL YAML, Python handlers, Terraform files
- [ ] Automated test harness: deploy → invoke → verify (CloudWatch logs + Lambda return values) → teardown
- [ ] 1-2 examples with real AWS service integration (e.g., DynamoDB)

## Current Milestone: v1.2 Comprehensive Examples & Integration Testing

**Goal:** Create use-case based examples that demonstrate all DSL features with automated AWS deployment testing and programmatic verification.

**Target features:**
- Real-world scenario examples (order processing, data pipeline, etc.) that naturally exercise the full feature surface
- Each example: complete DSL YAML + Python handler code + Terraform infrastructure files
- Automated test runner: single command to deploy, invoke, verify, and tear down each example
- Dual verification: Lambda return values for workflow output + CloudWatch logs for intermediate state checks
- Mostly self-contained compute handlers; 1-2 examples showcase real AWS service integration

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Go or other language runtime support — Python-only implementation
- Team collaboration features — local-first tool, no multi-user editing
- Hosted web service with authentication — runs on developer's machine
- VS Code extension — CLI + web UI is the interface
- Direct AWS Console integration — operates independently
- Mobile app — desktop developer tool

## Context

- **Lambda Durable Functions SDK:** `aws_lambda_durable_execution_sdk_python` provides `context.step()`, `context.wait()`, `context.parallel()`, `context.map()` primitives with checkpoint/replay semantics
- **Runtime requirement:** Python 3.13+ (SDK requirement)
- **AWS provider >= 6.25.0** required for `durable_config` block in Terraform
- **Lambda control plane rate limit:** 15 req/s — inspector uses token bucket rate limiter at 12 req/s ceiling
- **Durable Lambda invocation:** Uses Event type (async), poll `list_durable_executions_by_function` for completion
- **Key SDK note:** `parallel()` and `map()` return `BatchResult` — call `.get_results()` for plain list
- The DSL achieves full AWS Step Functions ASL feature parity
- This is a greenfield rebuild from a complete blueprint specification

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

---
*Last updated: 2026-02-26 after v1.2 milestone started*
