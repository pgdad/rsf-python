# Roadmap: RSF — Replacement for Step Functions

## Milestones

- ✅ **v1.0 Core** — Phases 1-11 (shipped 2026-02-25)
- ✅ **v1.1 CLI Toolchain** — Phase 12 (shipped 2026-02-26)
- ✅ **v1.2 Comprehensive Examples & Integration Testing** — Phases 13-17 (shipped 2026-02-26)
- ✅ **v1.3 Comprehensive Tutorial** — Phases 18-20 (shipped 2026-02-26)
- ✅ **v1.4 UI Screenshots** — Phases 21-24 (shipped 2026-02-27)
- 🚧 **v1.5 PyPI Packaging & Distribution** — Phases 25-27 (paused — resume after v1.6)
- 🚧 **v1.6 Java Port Blueprint** — Phases 28-33 (in progress)

## Phases

<details>
<summary>✅ v1.0 Core (Phases 1-11) — SHIPPED 2026-02-25</summary>

- [x] Phase 1: DSL Core (5/5 plans) — completed 2026-02-25
- [x] Phase 2: Code Generation (3/3 plans) — completed 2026-02-25
- [x] Phase 3: Terraform Generation (2/2 plans) — completed 2026-02-25
- [x] Phase 4: ASL Importer (2/2 plans) — completed 2026-02-25
- [x] Phase 6: Graph Editor Backend (2/2 plans) — completed 2026-02-25
- [x] Phase 7: Graph Editor UI (5/5 plans) — completed 2026-02-25
- [x] Phase 8: Inspector Backend (2/2 plans) — completed 2026-02-25
- [x] Phase 9: Inspector UI (5/5 plans) — completed 2026-02-25
- [x] Phase 10: Testing (9/9 plans) — completed 2026-02-25
- [x] Phase 11: Documentation (4/4 plans) — completed 2026-02-25

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 CLI Toolchain (Phase 12) — SHIPPED 2026-02-26</summary>

- [x] Phase 12: CLI Toolchain (4/4 plans) — completed 2026-02-26

Full details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

<details>
<summary>✅ v1.2 Comprehensive Examples & Integration Testing (Phases 13-17) — SHIPPED 2026-02-26</summary>

- [x] Phase 13: Example Foundation (5/5 plans) — completed 2026-02-26
- [x] Phase 14: Terraform Infrastructure (1/1 plan) — completed 2026-02-26
- [x] Phase 15: Integration Test Harness (1/1 plan) — completed 2026-02-26
- [x] Phase 16: AWS Deployment and Verification (1/1 plan) — completed 2026-02-26
- [x] Phase 17: Cleanup and Documentation (1/1 plan) — completed 2026-02-26

Full details: `.planning/milestones/v1.2-ROADMAP.md`

</details>

<details>
<summary>✅ v1.3 Comprehensive Tutorial (Phases 18-20) — SHIPPED 2026-02-26</summary>

- [x] Phase 18: Getting Started (2/2 plans) — completed 2026-02-26
- [x] Phase 19: Build and Deploy (3/3 plans) — completed 2026-02-26
- [x] Phase 20: Advanced Tools (3/3 plans) — completed 2026-02-26

Full details: `.planning/milestones/v1.3-ROADMAP.md`

</details>

<details>
<summary>✅ v1.4 UI Screenshots (Phases 21-24) — SHIPPED 2026-02-27</summary>

- [x] Phase 21: Playwright Setup (1/1 plan) — completed 2026-02-26
- [x] Phase 22: Mock Fixtures and Server Automation (2/2 plans) — completed 2026-02-27
- [x] Phase 23: Screenshot Capture (1/1 plan) — completed 2026-02-27
- [x] Phase 24: Documentation Integration (1/1 plan) — completed 2026-02-27

Full details: `.planning/milestones/v1.4-ROADMAP.md`

</details>

### 🚧 v1.5 PyPI Packaging & Distribution (Paused)

**Milestone Goal:** Make RSF installable via `pip install rsf` with bundled UIs, git-tag versioning, and CI/CD publishing to PyPI.

- [ ] **Phase 25: Package & Version** - Installable Python package with bundled React UIs and git-tag-derived versioning
- [ ] **Phase 26: CI/CD Pipeline** - GitHub Actions automated testing on PRs and publishing to PyPI on tag push
- [ ] **Phase 27: README as Landing Page** - README updated as polished PyPI and GitHub landing page with badges and quick start

### 🚧 v1.6 Java Port Blueprint (In Progress)

**Milestone Goal:** Produce RSF-BUILDPRINT-JAVA.md — a comprehensive blueprint for porting all RSF functionality to Java using the AWS Lambda Durable Execution SDK for Java (preview), with idiomatic Java patterns, annotations, and Maven-based builds.

**Output:** Single document — `RSF-BUILDPRINT-JAVA.md`

- [ ] **Phase 28: Foundation and DSL Models** - Maven multi-module structure, SDK assessment, and all 8 state type DTOs as Java sealed interfaces
- [ ] **Phase 29: Runtime Core** - I/O pipeline, 18 intrinsic functions, handler registry annotations, JSONPath evaluator, and Mock SDK sections
- [ ] **Phase 30: Code Generation** - FreeMarker template strategy, BFS traversal, orchestrator template, and Generation Gap pattern sections
- [ ] **Phase 31: Terraform and ASL Importer** - Container-image Terraform generator and ASL-to-RSF conversion rule sections
- [ ] **Phase 32: CLI and Web Backends** - Picocli command hierarchy, Spring Boot editor and inspector backends, and React UI sharing sections
- [ ] **Phase 33: Testing Strategy and Document Assembly** - JUnit 5 test patterns per module and final RSF-BUILDPRINT-JAVA.md assembly

## Phase Details

### Phase 25: Package & Version
**Goal**: RSF is installable via `pip install rsf` from source with bundled React UI static assets and git-tag-derived version numbers
**Depends on**: Phase 24 (v1.4 complete)
**Requirements**: PKG-01, PKG-02, PKG-03, PKG-04, PKG-05, VER-01, VER-02, VER-03
**Success Criteria** (what must be TRUE):
  1. Running `pip install .` in the repo installs the `rsf` CLI command with all subcommands functional
  2. `rsf ui` and `rsf inspect` serve their React UIs from bundled static assets without npm or node installed
  3. Running `rsf --version` displays the version string derived from the current git tag (e.g., `1.5.0`)
  4. On a repo with no release tag, `rsf --version` displays a dev version (e.g., `1.5.0.dev3+gabcdef`)
  5. The built wheel contains correct package metadata: authors, description, classifiers, project URLs, and Apache-2.0 license
**Plans**: TBD

### Phase 26: CI/CD Pipeline
**Goal**: GitHub Actions automatically runs tests on every pull request and publishes a new wheel to PyPI on every git tag push, with React UIs compiled as part of the build
**Depends on**: Phase 25
**Requirements**: CICD-01, CICD-02, CICD-03, CICD-04
**Success Criteria** (what must be TRUE):
  1. Opening a pull request triggers a GitHub Actions workflow that runs lint and the full test suite; the PR shows a pass/fail status check
  2. Pushing a `v*` git tag triggers a separate GitHub Actions workflow that builds the wheel (including React UI compilation) and publishes it to PyPI
  3. The published package on PyPI is installable immediately after the tag workflow completes (`pip install rsf==<version>` works)
  4. PyPI publishing uses OIDC trusted publisher authentication — no API tokens stored in repository secrets
**Plans**: TBD

### Phase 27: README as Landing Page
**Goal**: The README serves as a polished landing page on both GitHub and PyPI, with accurate install instructions, a working quick-start example, and status badges
**Depends on**: Phase 26
**Requirements**: README-01, README-02, README-03, README-04
**Success Criteria** (what must be TRUE):
  1. The README contains a `pip install rsf` install command that users can copy and run to get a working CLI
  2. The README contains a quick-start sequence (init → generate → deploy) showing the end-to-end workflow with commands and expected output
  3. The README displays a PyPI version badge, a CI status badge, and a license badge that all link to their respective targets
  4. The README renders without broken images, missing sections, or formatting errors on both the GitHub repository page and the PyPI project page
**Plans**: TBD

### Phase 28: Foundation and DSL Models
**Goal**: RSF-BUILDPRINT-JAVA.md contains the Maven project structure, SDK capability matrix, container-image deployment model, and all 8 state type DSL models as Java sealed interfaces with Jackson annotations
**Depends on**: Phase 24 (v1.4 complete; v1.6 starts here)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, DSL-01, DSL-02, DSL-03, DSL-04, DSL-05
**Success Criteria** (what must be TRUE):
  1. A reader can see the complete 8-module Maven parent POM structure with module names, dependency graph, and Jackson BOM placement without consulting any external source
  2. A reader can see Java class/interface definitions for all 8 state types (Task, Pass, Choice, Wait, Succeed, Fail, Parallel, Map) with correct `@JsonTypeInfo`/`@JsonSubTypes` annotations and understands how they replace Pydantic discriminated unions
  3. A reader can see the complete SDK feature gap matrix and knows exactly which primitives (step, wait) are available today versus which (parallel, map, waitForCallback, waitForCondition) require `runInChildContextAsync` workarounds
  4. A reader can see the container-image-only deployment constraint and why `runtime = "java21"` is forbidden, with the Dockerfile and ECR resource pattern as the required alternative
  5. A reader can see the Choice rule sealed interface hierarchy covering all 39 operators and 3 boolean combinators, plus the RetryPolicy and Catcher models with exponential backoff strategy
**Plans**: TBD

### Phase 29: Runtime Core
**Goal**: RSF-BUILDPRINT-JAVA.md contains the complete runtime layer blueprint: I/O pipeline, 18 intrinsic functions with recursive descent parser, handler registry annotations, JSONPath evaluator, variable store, and Mock SDK
**Depends on**: Phase 28
**Requirements**: RT-01, RT-02, RT-03, RT-04, RT-05, RT-06, RT-07
**Success Criteria** (what must be TRUE):
  1. A reader can see the 5-stage I/O pipeline (InputPath → Parameters → ResultSelector → ResultPath → OutputPath) implemented with Jayway JsonPath and `JacksonJsonNodeJsonProvider`, including the critical invariant that ResultPath merges into raw input
  2. A reader can see all 18 intrinsic functions mapped to Java method signatures with the `@FunctionalInterface IntrinsicFunction` registry pattern and the `IntrinsicParser` recursive descent class skeleton
  3. A reader can see the `@State` and `@Startup` annotation definitions with both classpath-scanning (Reflections library) and APT compile-time registry approaches documented, including why APT is preferred for production Lambda cold starts
  4. A reader can see the `MockDurableContext` class skeleton implementing `DurableContext`, with step/wait stubs executing immediately and Parallel/Map stubs throwing `UnsupportedOperationException` with a "pending SDK GA" note
  5. A reader can see the JSONPath evaluator approach for ASL-subset expressions and the `VariableStore` interface for `$$` context object and `$var` references, with `JsonNode.path()` used everywhere instead of `.get()`
**Plans**: TBD

### Phase 30: Code Generation
**Goal**: RSF-BUILDPRINT-JAVA.md contains the FreeMarker code generation blueprint: BFS traversal strategy, orchestrator and handler stub templates, Generation Gap pattern, and null-safety guard patterns
**Depends on**: Phase 29
**Requirements**: CODEGEN-01, CODEGEN-02, CODEGEN-03, CODEGEN-04, CODEGEN-05
**Success Criteria** (what must be TRUE):
  1. A reader can see the FreeMarker square-bracket syntax configuration (`SQUARE_BRACKET_TAG_SYNTAX`) that avoids Terraform `${}` conflicts, with the two separate `Configuration` instances (one for Java templates, one for HCL templates) clearly distinguished
  2. A reader can see the BFS state traversal algorithm and `StateMapping` record structure that drives code generation ordering, mirroring the Python BFS implementation
  3. A reader can see the `Orchestrator.java.ftl` template structure with the while-loop state machine, TypeToken usage for generic step results, and `UnsupportedOperationException` stubs for Parallel and Map states with FreeMarker null guards on every optional field
  4. A reader can see the Generation Gap pattern in Java: the `// DO NOT EDIT` first-line marker, the check-before-overwrite logic for handler stubs, and the golden-file testing strategy for asserting generated output
  5. A reader can see per-state-type code emission strategy for all 5 state categories (step, wait, conditional, parallel workaround, map workaround) with the correct `context.*` call for each
**Plans**: TBD

### Phase 31: Terraform and ASL Importer
**Goal**: RSF-BUILDPRINT-JAVA.md contains the Terraform HCL generator blueprint adapted for container-image deployment and the ASL JSON importer blueprint with Java-specific handler stub generation
**Depends on**: Phase 28
**Requirements**: TF-01, TF-02, TF-03, TF-04, IMP-01, IMP-02
**Success Criteria** (what must be TRUE):
  1. A reader can see all 6 generated Terraform file templates adapted for container-image deployment: `main.tf` with `package_type = "Image"`, ECR repository resource, and the Maven shade → fat JAR → Docker build → ECR push workflow
  2. A reader can see the IAM policy generation logic deriving required durable execution permissions, matching the Python version's IAM derivation strategy
  3. A reader can see the Dockerfile template generation for Lambda container image (base image selection, fat JAR copy, entry point configuration) and why this replaces the Python zip-based deployment
  4. A reader can see all 5 ASL-to-RSF YAML conversion rules plus the Java-specific 6th rule that generates `@State`-annotated Java handler class stubs instead of Python handler functions
**Plans**: TBD

### Phase 32: CLI and Web Backends
**Goal**: RSF-BUILDPRINT-JAVA.md contains the Picocli CLI blueprint for all 7 subcommands, Spring Boot backend blueprints for the graph editor and execution inspector, and the React UI sharing strategy
**Depends on**: Phase 30, Phase 31
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, WEB-01, WEB-02, WEB-03, WEB-04
**Success Criteria** (what must be TRUE):
  1. A reader can see all 7 CLI commands (init, generate, validate, deploy, import, ui, inspect) as Picocli `@Command` subcommands implementing `Callable<Integer>`, with the fat JAR configuration via maven-shade-plugin
  2. A reader can see `rsf init` producing a complete Maven project scaffold (parent POM, module directories, src/main/java layout, initial handler stub, Dockerfile) from a single command
  3. A reader can see the `rsf deploy` pipeline in sequence: Maven build → fat JAR → Docker image build → ECR push → Terraform apply, with each step's command shown
  4. A reader can see the Spring Boot graph editor backend with `TextWebSocketHandler` and REST endpoints maintaining the same API contract as the Python FastAPI backend, and the Spring Boot inspector backend with `SseEmitter` replacing Python SSE — both confirmed compatible with the existing React UIs without frontend changes
  5. A reader can see that Spring Boot appears only in `rsf-editor` and `rsf-inspector` Maven modules and is explicitly absent from `rsf-runtime`, with the Maven dependency boundary enforcing this constraint
**Plans**: TBD

### Phase 33: Testing Strategy and Document Assembly
**Goal**: RSF-BUILDPRINT-JAVA.md contains comprehensive JUnit 5 + Mockito + AssertJ test patterns for every module and is assembled as a complete, cross-referenced, self-contained document with table of contents
**Depends on**: Phase 32
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, DOC-01, DOC-02, DOC-03, DOC-04
**Success Criteria** (what must be TRUE):
  1. A reader can see JUnit 5 + Mockito + AssertJ test patterns for each of the 8 Maven modules, including DSL round-trip tests (serialize → deserialize → assert exact concrete class), FreeMarker golden-file tests with both fully-populated and minimal-fixture inputs, and I/O pipeline tests covering null inputs and all 5 pipeline stages
  2. A reader can see Maven Surefire (unit tests) and Failsafe (integration tests) plugin configuration with the separation strategy between fast local tests and slow AWS integration tests
  3. RSF-BUILDPRINT-JAVA.md opens with a table of contents linking to every section, and every section cross-references its Maven module, its Python equivalent component, and its direct dependencies
  4. RSF-BUILDPRINT-JAVA.md contains complete Maven dependency specifications (groupId, artifactId, version) for every library referenced in the document, Java code examples for every key pattern (sealed interface, FreeMarker template, Picocli command, Spring Boot handler), and a Python-to-Java migration notes section
**Plans**: TBD

## Progress

**Execution Order:** 28 → 29 → 30 → 31 (parallel with 30) → 32 → 33

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 25. Package & Version | v1.5 | 0/TBD | Paused | - |
| 26. CI/CD Pipeline | v1.5 | 0/TBD | Paused | - |
| 27. README as Landing Page | v1.5 | 0/TBD | Paused | - |
| 28. Foundation and DSL Models | v1.6 | 0/TBD | Not started | - |
| 29. Runtime Core | v1.6 | 0/TBD | Not started | - |
| 30. Code Generation | v1.6 | 0/TBD | Not started | - |
| 31. Terraform and ASL Importer | v1.6 | 0/TBD | Not started | - |
| 32. CLI and Web Backends | v1.6 | 0/TBD | Not started | - |
| 33. Testing Strategy and Document Assembly | v1.6 | 0/TBD | Not started | - |
