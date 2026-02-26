# Requirements: RSF — Replacement for Step Functions

**Defined:** 2026-02-24
**Core Value:** Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.

## v1.1 Requirements

Requirements for CLI toolchain milestone. Each maps to roadmap phases.

### CLI

- [x] **CLI-01**: User can run `rsf init <project-name>` to scaffold a project with directory structure, workflow.yaml, pyproject.toml, handler example, test example, .gitignore
- [x] **CLI-02**: User can run `rsf generate <workflow.yaml>` to parse DSL, validate, map states, render orchestrator, create handler stubs (if missing), maintain handlers/__init__.py
- [x] **CLI-03**: User can run `rsf validate <workflow.yaml>` to validate DSL (Pydantic + semantic) without generating code, with field-path error reporting
- [x] **CLI-04**: User can run `rsf deploy [--code-only]` to generate Terraform + run terraform init/apply; --code-only re-packages and updates Lambda code only
- [x] **CLI-05**: User can run `rsf import <asl.json> [--output workflow.yaml]` to import Step Functions ASL JSON through full pipeline
- [x] **CLI-06**: User can run `rsf ui [workflow.yaml] [--port 8765]` to launch graph editor FastAPI server, serve React SPA, auto-open browser
- [x] **CLI-07**: User can run `rsf inspect [--arn <lambda-arn>] [--port 8766]` to launch inspector with ARN discovery (terraform output or --arn override)
- [x] **CLI-08**: Typer-based CLI with `--version` flag and subcommands

## v1.0 Requirements (Shipped)

All v1.0 requirements delivered in Phases 1-4, 6-11.

### DSL Models (Phase 1) — Complete

- [x] **DSL-01**: User can define workflows in YAML/JSON with `rsf_version`, `StartAt`, `States`, and optional `Comment`, `Version`, `TimeoutSeconds`, `QueryLanguage` fields
- [x] **DSL-02**: User can define Task states with I/O processing, timeout, heartbeat, Retry policies (exponential backoff, jitter), and Catch handlers
- [x] **DSL-03**: User can define Pass states with optional `Result` injection and `ResultPath`
- [x] **DSL-04**: User can define Choice states with 39 comparison operators (equality, ordering, pattern, type checking), boolean logic (And/Or/Not), and Default fallback
- [x] **DSL-05**: User can define Wait states with exactly one of Seconds/Timestamp/SecondsPath/TimestampPath
- [x] **DSL-06**: User can define Succeed and Fail terminal states (Fail with Error/Cause and Path variants, no I/O fields)
- [x] **DSL-07**: User can define Parallel states with concurrent branches (sub-state machines), Retry, and Catch
- [x] **DSL-08**: User can define Map states with ItemProcessor (INLINE/DISTRIBUTED), ItemsPath, MaxConcurrency, ItemSelector, Retry, and Catch
- [x] **DSL-09**: All models use Pydantic v2 with `extra=forbid`, PascalCase aliases, `populate_by_name=True`, and discriminated union for State types
- [x] **DSL-10**: Semantic validator performs BFS cross-state validation: reference resolution, reachability, terminal state existence, States.ALL ordering, recursive branch validation

### I/O Processing (Phase 1) — Complete

- [x] **IO-01**: User's workflows process data through 5-stage JSONPath pipeline: InputPath → Parameters → ResultSelector → ResultPath → OutputPath
- [x] **IO-02**: ResultPath merges into raw input (not effective input) with deep-copy to prevent mutation
- [x] **IO-03**: JSONPath evaluator supports ASL subset: root ($), dot/bracket notation, array indexing, variable references ($varName)
- [x] **IO-04**: Payload templates resolve keys ending with `.$` (JSONPath refs, context refs, intrinsic function calls)
- [x] **IO-05**: ResultPath handles `$` (replace all), `$.field` (deep merge), and `null` (discard result)

### Intrinsic Functions (Phase 1) — Complete

- [x] **FUNC-01**: 18 intrinsic functions registered via `@intrinsic` decorator
- [x] **FUNC-02**: Recursive descent parser supporting nested calls, string escaping, path/context references, JSON literals, max nesting depth 10

### Context Object (Phase 1) — Complete

- [x] **CTX-01**: ASL Context Object model with Execution, State, StateMachine, Task, Map sections

### Variables (Phase 1) — Complete

- [x] **VAR-01**: Variable store and resolver supporting `$varName` detection and runtime variable storage with Assign/Output support

### Handler Registry (Phase 2) — Complete

- [x] **REG-01** through **REG-05**: Handler registry with @state/@startup decorators, auto-discovery, test isolation

### Code Generation (Phase 2) — Complete

- [x] **GEN-01** through **GEN-06**: BFS traversal, Jinja2 templates, Generation Gap, handler stubs

### Terraform Generation (Phase 3) — Complete

- [x] **TF-01** through **TF-10**: HCL templates, IAM derivation, custom delimiters, Generation Gap

### ASL Importer (Phase 4) — Complete

- [x] **IMP-01** through **IMP-06**: Parse, convert, recursive branch, YAML emit, handler stubs

### Graph Editor Backend (Phase 6) — Complete

- [x] **GEB-01** through **GEB-05**: FastAPI server, REST, WebSocket, static files

### Graph Editor UI (Phase 7) — Complete

- [x] **GEU-01** through **GEU-12**: Zustand store, bidirectional sync, 8 node types, ELK layout, Monaco, palette, validation

### Inspector Backend (Phase 8) — Complete

- [x] **INB-01** through **INB-07**: REST + SSE, rate limiter, timestamp normalization

### Inspector UI (Phase 9) — Complete

- [x] **INU-01** through **INU-12**: Three-panel layout, time machine, structural diffs, live SSE

### Schema (Phase 1) — Complete

- [x] **SCH-01** through **SCH-02**: JSON Schema generation and serving

### Testing (Phase 10) — Complete

- [x] **TST-01** through **TST-14**: Mock SDK, unit tests, integration tests, golden fixtures, React UI tests

### Documentation (Phase 11) — Complete

- [x] **DOC-01** through **DOC-05**: Tutorial, migration guide, DSL reference, README, MkDocs

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### Extended Features

- **V2-01**: Go or other language runtime support
- **V2-02**: VS Code extension for DSL editing
- **V2-03**: Direct AWS Console integration
- **V2-04**: Real `BatchResult` handling in mock SDK (currently returns plain lists)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Multi-language support (Go, etc.) | Python-only implementation per blueprint |
| Team collaboration features | Local-first tool, no multi-user editing needed |
| Hosted web service with auth | Runs on developer's machine only |
| Mobile app | Desktop developer tool |
| Real-time chat/collaboration | Not applicable to dev tooling |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLI-01 | Phase 12 | Complete |
| CLI-02 | Phase 12 | Complete |
| CLI-03 | Phase 12 | Complete |
| CLI-04 | Phase 12 | Complete |
| CLI-05 | Phase 12 | Complete |
| CLI-06 | Phase 12 | Complete |
| CLI-07 | Phase 12 | Complete |
| CLI-08 | Phase 12 | Complete |

**Coverage:**
- v1.1 requirements: 8 total (8 CLI)
- Mapped to phases: 8
- Unmapped: 0

---
*Requirements defined: 2026-02-24*
*Last updated: 2026-02-26 after v1.1 roadmap creation*
