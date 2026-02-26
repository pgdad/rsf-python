# Roadmap: RSF — Replacement for Step Functions

## Milestones

- ✅ **v1.0 Core** - Phases 1-11 (shipped 2026-02-25)
- 🚧 **v1.1 CLI Toolchain** - Phase 12 (in progress)

## Phases

<details>
<summary>✅ v1.0 Core (Phases 1-11) - SHIPPED 2026-02-25</summary>

### Phase 1: DSL Core
**Goal**: Users can define any AWS Step Functions workflow in RSF YAML/JSON and have it parsed, validated, and schema-checked with clear error messages
**Depends on**: Nothing (first phase)
**Requirements**: DSL-01, DSL-02, DSL-03, DSL-04, DSL-05, DSL-06, DSL-07, DSL-08, DSL-09, DSL-10, IO-01, IO-02, IO-03, IO-04, IO-05, FUNC-01, FUNC-02, CTX-01, VAR-01, SCH-01, SCH-02
**Success Criteria** (what must be TRUE):
  1. User can write a YAML file with any of the 8 state types and have it parsed without error into typed Python objects
  2. User can write an intentionally invalid YAML (missing required field, wrong type, bad reference) and receive a clear, path-specific error message
  3. User can reference all 39 comparison operators in Choice states and all boolean combinators (And/Or/Not) and have them resolve correctly
  4. The 5-stage I/O pipeline (InputPath → Parameters → ResultSelector → ResultPath → OutputPath) correctly transforms data through a Task state
  5. All 18 intrinsic functions parse and evaluate correctly when called with valid arguments, including nested calls
**Plans**: 5 plans

Plans:
- [x] 01-01: DSL state models (all 8 state types, Pydantic v2, discriminated union)
- [x] 01-02: Semantic validator (BFS cross-state validation)
- [x] 01-03: I/O processing pipeline (5 stages, JSONPath evaluator, payload templates)
- [x] 01-04: Intrinsic function registry and recursive descent parser
- [x] 01-05: Context object model, variable store, and JSON Schema generation

### Phase 2: Code Generation
**Goal**: Users can generate a deployment-ready Lambda orchestrator Python file from any valid RSF workflow definition, with handler stubs created on first run and never overwritten on subsequent runs
**Depends on**: Phase 1
**Requirements**: REG-01, REG-02, REG-03, REG-04, REG-05, GEN-01, GEN-02, GEN-03, GEN-04, GEN-05, GEN-06
**Success Criteria** (what must be TRUE):
  1. User can run code generation against a workflow with all 8 state types and receive valid, executable Python that maps every state to the correct SDK primitive
  2. User can add custom logic to a handler file, run generation again, and confirm the custom code is not overwritten
  3. User can run generation twice with the same DSL and confirm the output is byte-for-byte identical (replay safety)
  4. Handler stubs are created for every Task state on first generation and skipped on subsequent runs
  5. Generated orchestrator file header contains DSL file SHA-256 hash and RSF version string
**Plans**: 3 plans

Plans:
- [x] 02-01: Handler registry (@state, @startup decorators, auto-discovery, test isolation)
- [x] 02-02: BFS traversal and SDK primitive mapping for all 8 state types
- [x] 02-03: Jinja2 orchestrator template, handler stub template, Generation Gap, topyrepr filter

### Phase 3: Terraform Generation
**Goal**: Users can generate a complete, deployable Terraform module for their Lambda Durable Function, with IAM permissions derived automatically and generated files never overwriting user customizations
**Depends on**: Phase 2
**Requirements**: TF-01, TF-02, TF-03, TF-04, TF-05, TF-06, TF-07, TF-08, TF-09, TF-10
**Success Criteria** (what must be TRUE):
  1. User can generate Terraform that plans cleanly against AWS (main.tf, variables.tf, iam.tf, outputs.tf, cloudwatch.tf, backend.tf all present)
  2. Generated IAM policy contains exactly 3 policy statements (CloudWatch Logs, Lambda self-invoke, durable execution)
  3. User can add a custom Terraform file alongside generated files and confirm it is not touched by regeneration
  4. HCL output contains no raw `${}` interpolations that would conflict with Terraform's syntax (all use `<< >>` delimiters)
  5. Terraform identifiers generated from PascalCase or kebab-case workflow names are valid Terraform identifier strings
**Plans**: 2 plans

Plans:
- [x] 03-01: HCL Jinja2 templates with custom delimiters (main.tf, variables.tf, backend.tf)
- [x] 03-02: IAM derivation, iam.tf, cloudwatch.tf, outputs.tf, name sanitizer, Generation Gap

### Phase 4: ASL Importer
**Goal**: Users can point RSF at any existing AWS Step Functions ASL JSON file and receive a valid RSF workflow YAML plus handler stubs for every Task state
**Depends on**: Phase 1
**Requirements**: IMP-01, IMP-02, IMP-03, IMP-04, IMP-05, IMP-06
**Success Criteria** (what must be TRUE):
  1. User can import a real ASL JSON file from their AWS account and receive a workflow.yaml that passes `rsf validate`
  2. User receives a clear error message (not a stack trace) when the ASL JSON file is malformed
  3. Workflows containing nested Parallel branches and Map ItemProcessors import correctly with recursive conversion
  4. User receives a warning (not an error) for distributed Map fields (ItemReader, ItemBatcher, ResultWriter) that RSF does not support
  5. Handler stubs are generated for every Task state found in the imported workflow
**Plans**: 2 plans

Plans:
- [x] 04-01: ASL parser, format converter (Resource rejection, field rename, version inject, Fail state strip)
- [x] 04-02: Recursive branch conversion, YAML emitter, handler stub generator

### Phase 6: Graph Editor Backend
**Goal**: Users can launch a local web server that serves the graph editor and exchanges workflow state in real time via WebSocket
**Depends on**: Phase 1
**Requirements**: GEB-01, GEB-02, GEB-03, GEB-04, GEB-05
**Success Criteria** (what must be TRUE):
  1. User can launch the graph editor server and a browser tab opens automatically with the editor loaded
  2. A WebSocket client can send a `parse` message with YAML content and receive a parsed AST response with validation errors highlighted
  3. A WebSocket client can send `load_file` and `save_file` messages and confirm files are read from and written to disk
  4. `GET /api/schema` returns valid JSON Schema that a Monaco editor can use for autocompletion and validation
**Plans**: 2 plans

Plans:
- [x] 06-01: FastAPI server setup, static file serving, GET /api/schema endpoint
- [x] 06-02: WebSocket handler (parse, validate, load_file, save_file, get_schema messages and responses)

### Phase 7: Graph Editor UI
**Goal**: Users can visually view, navigate, and edit RSF workflows in a browser with changes reflected in YAML and vice versa in real time
**Depends on**: Phase 6
**Requirements**: GEU-01, GEU-02, GEU-03, GEU-04, GEU-05, GEU-06, GEU-07, GEU-08, GEU-09, GEU-10, GEU-11, GEU-12
**Success Criteria** (what must be TRUE):
  1. User can open a workflow in the graph editor and see all states rendered as correctly typed nodes (Task, Choice, Parallel, Map, etc.) connected by edges
  2. User can edit the YAML in the Monaco editor pane and watch the graph update within 300ms without any infinite update loop
  3. User can drag nodes in the graph and see the YAML transitions update while complex state data (Choice rules, Catch arrays) is preserved
  4. User can drag a state type from the palette onto the canvas and have it appear in the graph and YAML
  5. Validation errors appear as badges on the affected canvas nodes and as a list in the validation overlay
**Plans**: 5 plans

Plans:
- [x] 07-01: React project setup, Zustand flow store, WebSocket connection management
- [x] 07-02: 8 state-type node components, TransitionEdge, ELK.js auto-layout
- [x] 07-03: YAML → Graph sync (debounce, astToFlowElements, syncSource pattern)
- [x] 07-04: Graph → YAML sync (mergeGraphIntoYaml, AST-merge strategy, fallback)
- [x] 07-05: MonacoEditor with monaco-yaml, GraphCanvas (minimap, controls), Palette, Inspector panel, ValidationOverlay

### Phase 8: Inspector Backend
**Goal**: Users can retrieve live and historical Lambda Durable Function execution data via REST and SSE from a locally running server
**Depends on**: Phase 1
**Requirements**: INB-01, INB-02, INB-03, INB-04, INB-05, INB-06, INB-07
**Success Criteria** (what must be TRUE):
  1. User can hit `GET /api/inspect/executions` and receive a list of durable executions with correct status and pagination
  2. User can subscribe to `GET /api/inspect/execution/{arn}/stream` and receive SSE events as an execution runs, with the stream closing automatically when the execution reaches a terminal state
  3. The server does not exceed 15 req/s to the Lambda control plane under any polling load (token bucket enforced at 12 req/s)
  4. Execution timestamps are normalized to UTC datetime strings regardless of what format AWS returns them in
**Plans**: 2 plans

Plans:
- [x] 08-01: FastAPI inspector server, async boto3 client, token bucket rate limiter
- [x] 08-02: REST endpoints (executions list, execution detail, history), SSE stream with lifecycle management

### Phase 9: Inspector UI
**Goal**: Users can inspect, scrub through, and compare state transitions in any Lambda Durable Function execution using a three-panel web interface
**Depends on**: Phase 8
**Requirements**: INU-01, INU-02, INU-03, INU-04, INU-05, INU-06, INU-07, INU-08, INU-09, INU-10, INU-11, INU-12
**Success Criteria** (what must be TRUE):
  1. User can select any execution from the list, see the workflow graph with node overlays showing status (pending/running/succeeded/failed/caught), timing, and I/O
  2. User can drag the time machine scrubber to any point in an execution and have the graph update instantly (O(1), no recomputation)
  3. User can click two consecutive state events in the timeline and see a color-coded structural diff of the data change
  4. User can watch a running execution with live SSE updates populating the graph and timeline, with the stream pausing when the browser tab is hidden
  5. User can filter the execution list by status and search by name
**Plans**: 5 plans

Plans:
- [x] 09-01: React inspector project setup, Zustand inspect store, SSE connection management
- [x] 09-02: ExecutionList (filter, search, status icons), ExecutionHeader
- [x] 09-03: Graph with node overlays (status, timing, I/O, retry) and edge overlays (traversed, timestamp)
- [x] 09-04: Time machine (precomputed TransitionSnapshots, TimelineScrubber slider)
- [x] 09-05: EventTimeline, StateDetailPanel, structural JSON diff component

### Phase 10: Testing
**Goal**: The complete RSF codebase is verified by a comprehensive automated test suite covering every DSL state type, every operator, every code generation path, every I/O stage, and every API endpoint
**Depends on**: Phase 9
**Requirements**: TST-01, TST-02, TST-03, TST-04, TST-05, TST-06, TST-07, TST-08, TST-09, TST-10, TST-11, TST-12, TST-13, TST-14
**Success Criteria** (what must be TRUE):
  1. `pytest` runs with zero failures and zero errors against the complete test suite
  2. Every DSL state type, field, and validator has at least one test proving correct parsing and one test proving correct rejection of invalid input
  3. All 39 Choice operators have tests; all 18 intrinsic functions have tests covering multiple argument types
  4. Generated code executed via the Mock SDK produces correct output for a multi-state workflow including Parallel and Map states
  5. The test suite includes at least 22 valid DSL fixture files and 8 invalid DSL fixture files used for conformance testing
**Plans**: 9 plans

Plans:
- [x] 10-01: MockDurableContext (mock SDK with step, wait, parallel, map)
- [x] 10-02: DSL model tests (all 8 state types, field validation, error cases)
- [x] 10-03: Choice operator tests (all 39), boolean combination tests
- [x] 10-04: I/O pipeline tests (all 5 stages) and intrinsic function tests (all 18)
- [x] 10-05: Code generation tests (all 8 state types, replay safety, Generation Gap)
- [x] 10-06: Terraform generation tests, ASL importer tests
- [x] 10-07: Inspector API tests (endpoints, SSE streaming, model serialization)
- [x] 10-08: SDK integration tests (generated code via mock SDK), DSL fixture files (22 valid, 8 invalid)
- [x] 10-09: React UI tests (vitest, component tests, sync logic tests)

### Phase 11: Documentation
**Goal**: Users can discover, install, use, and migrate to RSF through complete, accurate, and searchable documentation
**Depends on**: Phase 10
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05
**Success Criteria** (what must be TRUE):
  1. A developer who has never used RSF can follow the tutorial from `pip install rsf` through deploying a working Lambda workflow and inspecting its execution
  2. A developer with an existing Step Functions workflow can follow the migration guide to import and deploy it with RSF in under 30 minutes
  3. Every DSL field for every state type is documented with its type, allowed values, and a usage example
  4. The README gives a clear project overview and quickstart that lets a developer run their first `rsf generate` in under 5 minutes
  5. `mkdocs serve` produces a navigable documentation site with no broken links
**Plans**: 4 plans

Plans:
- [x] 11-01: README and MkDocs site setup (Material theme, admonitions, code tabs, superfences)
- [x] 11-02: Tutorial (install through deploy + inspect)
- [x] 11-03: DSL reference (all state types, all fields)
- [x] 11-04: Migration guide (ASL import walkthrough)

</details>

### 🚧 v1.1 CLI Toolchain (In Progress)

**Milestone Goal:** Complete the Typer-based CLI that ties all existing RSF modules together into a single `rsf` command with init, generate, validate, deploy, import, ui, and inspect subcommands.

#### Phase 12: CLI Toolchain
**Goal**: Users can perform the complete RSF workflow (init → generate → validate → deploy → import → ui → inspect) from the terminal with a single `rsf` entry point
**Depends on**: Phases 1-11 (all v1.0 work)
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, CLI-06, CLI-07, CLI-08
**Success Criteria** (what must be TRUE):
  1. User can run `rsf init my-project` and have a working project scaffold with workflow.yaml, handlers/, pyproject.toml, and .gitignore created in under 2 seconds
  2. User can run `rsf generate workflow.yaml` and receive a complete orchestrator Python file and handler stubs for every Task state with a single command
  3. User can run `rsf validate workflow.yaml` on a broken workflow and see field-path-specific error messages without any code being generated
  4. User can run `rsf deploy` in a project directory and have Terraform generated, initialized, and applied against AWS; `rsf deploy --code-only` re-packages and updates Lambda code only
  5. User can run `rsf import asl.json` and receive a workflow.yaml and handler stubs; `rsf ui` and `rsf inspect` launch their respective servers with auto-browser-open; `rsf --version` prints version info
**Plans**: 4 plans

Plans:
- [ ] 12-01: Typer CLI skeleton, --version flag, rsf init scaffold
- [ ] 12-02: rsf generate, rsf validate subcommands
- [ ] 12-03: rsf deploy (Terraform generation + terraform init/apply, --code-only flag)
- [ ] 12-04: rsf import, rsf ui, rsf inspect subcommands

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 6 → 7 → 8 → 9 → 10 → 11 → 12

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. DSL Core | v1.0 | 5/5 | Complete | 2026-02-25 |
| 2. Code Generation | v1.0 | 3/3 | Complete | 2026-02-25 |
| 3. Terraform Generation | v1.0 | 2/2 | Complete | 2026-02-25 |
| 4. ASL Importer | v1.0 | 2/2 | Complete | 2026-02-25 |
| 6. Graph Editor Backend | v1.0 | 2/2 | Complete | 2026-02-25 |
| 7. Graph Editor UI | v1.0 | 5/5 | Complete | 2026-02-25 |
| 8. Inspector Backend | v1.0 | 2/2 | Complete | 2026-02-25 |
| 9. Inspector UI | v1.0 | 5/5 | Complete | 2026-02-25 |
| 10. Testing | v1.0 | 9/9 | Complete | 2026-02-25 |
| 11. Documentation | v1.0 | 4/4 | Complete | 2026-02-25 |
| 12. CLI Toolchain | 2/4 | In Progress|  | - |
