# Requirements: RSF Java Port Blueprint

**Defined:** 2026-02-28
**Core Value:** Comprehensive blueprint enabling a developer to port all RSF functionality to Java using idiomatic patterns, the AWS Lambda Durable Execution SDK for Java, annotations, and Maven builds.

## v1.6 Requirements

Requirements for RSF-BUILDPRINT-JAVA.md. Each maps to roadmap phases.

### Foundation

- [ ] **FOUND-01**: Blueprint specifies Maven multi-module project structure with module names, parent POM, and dependency graph
- [ ] **FOUND-02**: Blueprint maps all 8 ASL state types to Java sealed interfaces with Jackson @JsonTypeInfo/@JsonSubTypes annotations
- [ ] **FOUND-03**: Blueprint documents AWS Lambda Durable Execution SDK for Java API surface (DurableHandler, DurableContext, DurableFuture, StepConfig, TypeToken) with version and Maven coordinates
- [ ] **FOUND-04**: Blueprint specifies container-image deployment model (ECR, Dockerfile, base image) since Java SDK requires container-image-only deployment
- [ ] **FOUND-05**: Blueprint documents SDK feature gap matrix (parallel, map, waitForCallback, waitForCondition marked as "in development") with workaround patterns using runInChildContextAsync

### DSL Models

- [ ] **DSL-01**: Blueprint provides Java class/interface definitions for all 8 state type DTOs (Task, Pass, Choice, Wait, Succeed, Fail, Parallel, Map) using Jackson annotations
- [ ] **DSL-02**: Blueprint documents Choice rule discriminated union (39 operators + 3 boolean combinators + Condition) as Java sealed interface hierarchy
- [ ] **DSL-03**: Blueprint specifies RetryPolicy and Catcher models with exponential backoff, jitter strategy
- [ ] **DSL-04**: Blueprint documents semantic cross-state BFS validation strategy (reachability, terminal states, reference resolution)
- [ ] **DSL-05**: Blueprint specifies YAML/JSON parsing approach (Jackson YAML module or SnakeYAML) with thread-safety considerations

### Runtime Core

- [ ] **RT-01**: Blueprint documents 5-stage I/O processing pipeline implementation using Jackson JsonNode with critical invariant (ResultPath merges into RAW input)
- [ ] **RT-02**: Blueprint specifies all 18 intrinsic functions with Java method signatures and registry pattern
- [ ] **RT-03**: Blueprint documents recursive descent parser for intrinsic function expressions (States.Format, nested calls, JSONPath refs)
- [ ] **RT-04**: Blueprint specifies @State and @Startup annotation definitions with handler registration mechanism (compile-time APT recommended over runtime classpath scanning)
- [ ] **RT-05**: Blueprint documents JSONPath evaluator implementation for ASL-subset (dot/bracket notation, array indexing, $$ context, $var references)
- [ ] **RT-06**: Blueprint specifies variable store interface and context object model ($$)
- [ ] **RT-07**: Blueprint documents Mock SDK implementation for local testing of generated code (implements DurableContext interface)

### Code Generation

- [ ] **CODEGEN-01**: Blueprint specifies FreeMarker template strategy with square-bracket syntax to avoid Terraform ${} conflicts
- [ ] **CODEGEN-02**: Blueprint documents BFS state traversal and StateMapping data structure for code generation ordering
- [ ] **CODEGEN-03**: Blueprint provides FreeMarker template structure for generated DurableHandler<I,O> subclass with while-loop state machine
- [ ] **CODEGEN-04**: Blueprint documents Generation Gap pattern for handler stubs (generated once, never overwritten)
- [ ] **CODEGEN-05**: Blueprint specifies per-state-type code emission strategy (step, wait, conditional, parallel workaround, map workaround)

### Terraform & Infrastructure

- [ ] **TF-01**: Blueprint documents 6 generated Terraform files adapted for container-image deployment (main.tf with package_type="Image", ECR resources)
- [ ] **TF-02**: Blueprint specifies IAM policy generation with durable execution permissions
- [ ] **TF-03**: Blueprint documents Dockerfile template generation for Lambda container image (base image, fat JAR, entry point)
- [ ] **TF-04**: Blueprint specifies FreeMarker HCL templates with square-bracket syntax avoiding ${} conflicts

### ASL Importer

- [ ] **IMP-01**: Blueprint documents ASL JSON to RSF YAML conversion rules (same 5 rules as Python + Java-specific handler stub generation)
- [ ] **IMP-02**: Blueprint specifies handler stub generation producing @State-annotated Java classes

### CLI

- [ ] **CLI-01**: Blueprint documents all 7 CLI commands (init, generate, validate, deploy, import, ui, inspect) using Picocli @Command annotations
- [ ] **CLI-02**: Blueprint specifies rsf init project scaffolding producing Maven project structure (pom.xml, src/main/java, handlers, Dockerfile)
- [ ] **CLI-03**: Blueprint documents rsf deploy pipeline: Maven build → fat JAR → Docker build → ECR push → Terraform apply
- [ ] **CLI-04**: Blueprint specifies rsf generate invoking FreeMarker code generation with Generation Gap preservation

### Web Backends

- [ ] **WEB-01**: Blueprint documents Spring Boot graph editor backend with REST + WebSocket endpoints (same API contract as Python FastAPI)
- [ ] **WEB-02**: Blueprint specifies Spring Boot execution inspector backend with REST + SseEmitter (same API contract as Python FastAPI)
- [ ] **WEB-03**: Blueprint documents React UI sharing strategy (same React source, different backend, Vite build targeting Spring Boot static resources)
- [ ] **WEB-04**: Blueprint specifies Spring Boot module isolation (Spring Boot only in rsf-editor and rsf-inspector, never in rsf-runtime)

### Testing Strategy

- [ ] **TEST-01**: Blueprint documents JUnit 5 + Mockito + AssertJ test patterns for each module
- [ ] **TEST-02**: Blueprint specifies golden-file testing strategy for FreeMarker code generation output
- [ ] **TEST-03**: Blueprint documents integration test approach for real AWS container-image Lambda deployment
- [ ] **TEST-04**: Blueprint specifies Maven Surefire (unit) and Failsafe (integration) plugin configuration

### Document Structure

- [ ] **DOC-01**: RSF-BUILDPRINT-JAVA.md is a single self-contained document with table of contents, component-by-component sections, and dependency graph
- [ ] **DOC-02**: Blueprint includes complete Maven dependency specifications (groupId, artifactId, version) for all libraries
- [ ] **DOC-03**: Blueprint includes Java code examples for key patterns (sealed interface, annotation, FreeMarker template, etc.)
- [ ] **DOC-04**: Blueprint includes migration notes from Python patterns to Java equivalents

## Future Requirements

### Implementation

- **IMPL-01**: Actual Java code implementation of rsf-dsl module
- **IMPL-02**: Actual Java code implementation of rsf-runtime module
- **IMPL-03**: Actual Java code implementation of rsf-codegen module
- **IMPL-04**: Full Java RSF project as separate repository

## Out of Scope

| Feature | Reason |
|---------|--------|
| Actual Java code implementation | This milestone produces a blueprint document, not working code |
| Gradle build system | User specified Maven for all builds |
| Kotlin or Scala alternatives | User specified idiomatic Java |
| GraalVM native-image support | Premature optimization; container image cold start is sufficient |
| Java SDK GA features | SDK is in preview; blueprint documents current state + workarounds |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | TBD | Pending |
| FOUND-02 | TBD | Pending |
| FOUND-03 | TBD | Pending |
| FOUND-04 | TBD | Pending |
| FOUND-05 | TBD | Pending |
| DSL-01 | TBD | Pending |
| DSL-02 | TBD | Pending |
| DSL-03 | TBD | Pending |
| DSL-04 | TBD | Pending |
| DSL-05 | TBD | Pending |
| RT-01 | TBD | Pending |
| RT-02 | TBD | Pending |
| RT-03 | TBD | Pending |
| RT-04 | TBD | Pending |
| RT-05 | TBD | Pending |
| RT-06 | TBD | Pending |
| RT-07 | TBD | Pending |
| CODEGEN-01 | TBD | Pending |
| CODEGEN-02 | TBD | Pending |
| CODEGEN-03 | TBD | Pending |
| CODEGEN-04 | TBD | Pending |
| CODEGEN-05 | TBD | Pending |
| TF-01 | TBD | Pending |
| TF-02 | TBD | Pending |
| TF-03 | TBD | Pending |
| TF-04 | TBD | Pending |
| IMP-01 | TBD | Pending |
| IMP-02 | TBD | Pending |
| CLI-01 | TBD | Pending |
| CLI-02 | TBD | Pending |
| CLI-03 | TBD | Pending |
| CLI-04 | TBD | Pending |
| WEB-01 | TBD | Pending |
| WEB-02 | TBD | Pending |
| WEB-03 | TBD | Pending |
| WEB-04 | TBD | Pending |
| TEST-01 | TBD | Pending |
| TEST-02 | TBD | Pending |
| TEST-03 | TBD | Pending |
| TEST-04 | TBD | Pending |
| DOC-01 | TBD | Pending |
| DOC-02 | TBD | Pending |
| DOC-03 | TBD | Pending |
| DOC-04 | TBD | Pending |

**Coverage:**
- v1.6 requirements: 42 total
- Mapped to phases: 0
- Unmapped: 42 (awaiting roadmap)

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-02-28 after initial definition*
