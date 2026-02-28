# Project Research Summary

**Project:** RSF v1.6 — Java Port Blueprint (RSF-BUILDPRINT-JAVA.md)
**Domain:** Python-to-Java port of RSF (Replacement for Step Functions) — Lambda Durable Execution toolchain
**Researched:** 2026-02-28
**Confidence:** HIGH (stack and architecture); MEDIUM (Java SDK Preview features)

## Executive Summary

RSF v1.6 is a blueprint milestone, not a code milestone. The deliverable is RSF-BUILDPRINT-JAVA.md — a comprehensive document that maps all 14 Python RSF components to idiomatic Java equivalents, enabling a future Java implementation team to build without re-researching decisions. The Python v1.0–v1.4 implementation is frozen as the reference; this milestone documents exactly how each Python construct (Pydantic models, Jinja2 templates, Typer CLI, FastAPI backends, pytest) maps to its Java equivalent (Jackson sealed interfaces, FreeMarker templates, Picocli, Spring Boot, JUnit 5 + Mockito + AssertJ). The recommended approach is a Maven multi-module project (8 modules) with clear dependency boundaries, Java 17+ sealed interfaces as the type-safe DSL model foundation, and FreeMarker with square-bracket syntax as the template engine that avoids HCL interpolation conflicts — the same problem the Python version solves with custom `<< >>` Jinja2 delimiters.

The single largest risk is the AWS Lambda Durable Execution SDK for Java's Developer Preview status as of February 2026. The Java SDK does not yet implement `parallel()`, `map()`, `waitForCondition()`, or `waitForCallback()` — four primitives that directly correspond to two of the eight ASL state types (Parallel and Map). The blueprint must explicitly scope what can be fully specified now (Task, Choice, Wait, Pass, Succeed, Fail states plus all infrastructure) versus what must be flagged as pending SDK GA (Parallel and Map state code generation). Additionally, the Java SDK requires container-image-only Lambda deployment during Preview — the Terraform generator cannot emit a `runtime = "java21"` managed-runtime resource; it must emit `package_type = "Image"` with ECR repository creation and a Dockerfile template.

Beyond the SDK gaps, the critical implementation risks are type-erasure gotchas with Jackson generics, FreeMarker's strict null handling (opposite of Jinja2's permissive behavior), and the cold-start danger of using Spring Boot or runtime classpath scanning inside the Lambda DurableHandler. All three are documented with explicit prevention strategies. The Maven multi-module structure is itself a mitigation — isolating the Lambda runtime module (`rsf-runtime`) from Spring Boot dependencies prevents Spring Boot's classpath scanning from leaking into Lambda deployment artifacts and imposing 3–8 second cold starts.

## Key Findings

### Recommended Stack

The Java stack is a direct mapping of the Python stack with no technology choices left ambiguous. The parent POM uses Spring Boot 3.5.9 as its parent (for dependency management), Java 17 as the minimum runtime target (Java 21 recommended for production builds), and Jackson 2.18.5 as the sole JSON/YAML serialization library across all modules.

**Core technologies:**
- **Java 17 (minimum) / Java 21 (recommended):** Required by the AWS Lambda Durable Execution SDK for Java; Java 21 LTS is the target for ECR container base images (`public.ecr.aws/lambda/java:21`).
- **AWS Lambda Durable Execution SDK for Java (Preview):** The only SDK implementing checkpoint/replay semantics for Java Lambda durable functions. Developer Preview as of February 2026. Container-image deployment only. Maven coordinates: `software.amazon.lambda.durable:aws-durable-execution-sdk-java`.
- **Jackson Databind 2.18.5 + jackson-dataformat-yaml 2.18.5:** Replaces Pydantic v2 (models) and PyYAML (parsing). Uses `@JsonTypeInfo` + `@JsonSubTypes` on sealed interfaces to replicate Pydantic discriminated unions. One `ObjectMapper` handles both JSON and YAML via different mappers — no duplicate model code.
- **FreeMarker 2.3.34:** Replaces Jinja2 for code generation. `SQUARE_BRACKET_TAG_SYNTAX` mode uses `[#if x]` and `[= variable]` syntax, eliminating the `${...}` conflict with Terraform HCL interpolation. Two separate `Configuration` instances: one for Java orchestrator templates (angle-bracket or auto-detect), one for HCL Terraform templates (square-bracket).
- **Picocli 4.7.7:** Replaces Typer. Annotation-driven, typed subcommands, colored help, zero Spring context overhead. Handles all 7 RSF commands (init, generate, validate, deploy, import, ui, inspect). `picocli-codegen` goes in `<annotationProcessorPaths>` only — never as a runtime `<dependency>`.
- **Spring Boot 3.5.9:** Replaces FastAPI + uvicorn for the two web backends (graph editor, inspector). Provides `SseEmitter` (inspector live updates), raw `TextWebSocketHandler` (graph editor YAML-graph sync), `@RestController`, and static SPA file serving. Used ONLY in `rsf-editor` and `rsf-inspector` modules — never in the Lambda handler.
- **JUnit Jupiter 5.11.4 + Mockito 5.14.2 + AssertJ 3.27.7:** Replaces pytest. JUnit 6 (released September 2025) is explicitly rejected — Spring Boot Test 3.5.x, Mockito, and AssertJ have not migrated.
- **Maven 3.9+ with multi-module POM:** Replaces Python packaging. Eight modules with an explicit dependency graph that enforces architectural boundaries.

**Critical version constraints:**
- Do not use Jackson 3.0.x (RC) — Spring Boot, Hibernate Validator, and networknt json-schema-validator have not migrated.
- Do not use JUnit 6.0.x — Spring Boot Test has not migrated.
- Do not use AWS SDK for Java 1.x (`com.amazonaws`) — end-of-life December 31, 2025.
- Do not use `javax.*` namespace — Spring Boot 3.x requires `jakarta.*` throughout.
- Do not add `picocli-codegen` as a `<dependency>` — only valid in `<annotationProcessorPaths>`.

### Expected Features

All 14 RSF Python components must be documented in the blueprint. The deliverable is documentation, not code, so every component is P1 for the blueprint document.

**Must have (table stakes — blueprint must cover all):**
- DSL Models: Jackson sealed interface `State` with 8 subtypes via `@JsonTypeInfo`/`@JsonSubTypes`; Java records for sub-models (RetryPolicy, Catcher, ChoiceRule subtypes); round-trip tests asserting concrete class, not interface
- Code Generator: FreeMarker 2.3.34 templates producing `DurableHandler` Java subclasses; `Orchestrator.java.ftl` + `HandlerStub.java.ftl`; Generation Gap pattern (first-line `// DO NOT EDIT` marker); golden-file tests
- Handler Registry: `@State`/`@Startup` custom annotations; classpath scanning via Reflections library; APT compile-time alternative documented as optimization path
- 5-Stage I/O Pipeline: InputPath, Parameters, ResultSelector, ResultPath, OutputPath using Jayway JsonPath 2.9.0 with `JacksonJsonNodeJsonProvider`; `JsonNode.path()` for all chained access (never `.get()`)
- 18 Intrinsic Functions: Hand-written recursive descent `IntrinsicParser`; `@FunctionalInterface IntrinsicFunction`; same 6-file split as Python (`ArrayFunctions`, `StringFunctions`, `MathFunctions`, etc.)
- CLI: Picocli `@Command` with 7 subcommands implementing `Callable<Integer>`; fat JAR via maven-shade-plugin
- ASL Importer: Jackson `ObjectMapper.readTree()` + `JsonNode` tree manipulation + SnakeYAML/YAMLMapper emission; all 6 ASL-to-RSF conversion rules
- Terraform HCL Generator: FreeMarker with square-bracket syntax; 6 template files; container-image deployment model (`package_type = "Image"`, ECR, Dockerfile template) — no managed runtime
- UI Backends: Spring Boot with `TextWebSocketHandler` (graph editor), `SseEmitter` (inspector), `@RestController`, static SPA file serving via `ResourceHttpRequestHandler`
- Mock SDK: `MockDurableContext` implementing the Java `DurableContext` interface; step/wait stubs execute immediately; Parallel/Map stubs emit `UnsupportedOperationException` pending SDK GA
- Semantic Validator: Jakarta Bean Validation 3.1 for field-level; `ArrayDeque<String>` BFS for cross-state rules (all 6 Python rules map directly); pattern-matching `switch` over sealed `State`
- JSON Schema Generation: victools jsonschema-generator 4.35.0 with `jsonschema-module-jackson`; replaces `pydantic.model_json_schema()`; Draft 2020-12
- Maven multi-module structure: 8-module layout with dependency graph; Jackson BOM in root `<dependencyManagement>`
- Testing strategy: JUnit 5 + Mockito 5 + AssertJ 3; minimal-fixture tests alongside fully-populated fixtures for all FreeMarker templates

**Should have (idiomatic Java differentiators — mention in blueprint):**
- Java sealed interface exhaustive `switch` pattern matching (compiler-enforced, better than Python's runtime `isinstance`)
- Java records for all immutable sub-models (auto-generates equals/hashCode/toString)
- Spring Boot Actuator health/metrics for UI backends (`spring-boot-starter-actuator`, zero configuration)
- APT compile-time handler registry as documented optimization path (zero-reflection cold start)

**Defer (post-blueprint, implementation-time decisions):**
- GraalVM native-image profile for CLI (requires APT registry; defer until Java implementation begins)
- Kotlin port (separate blueprint required; not in scope)
- Java integration test harness against real AWS (reuse Python harness patterns when Java implementation ships)
- Parallel and Map state code generation (blocked on Java SDK GA; emit `UnsupportedOperationException` stubs)

**Explicit anti-features (document as "do not do" in blueprint):**
- Spring Boot inside the Lambda DurableHandler (3–8s cold start; 20MB+ JAR)
- Runtime classpath scanning in production Lambda (500ms–2s cold start overhead)
- `CompletableFuture.allOf()` as Parallel state substitute (breaks checkpoint/replay semantics)
- `javax.*` namespace (superseded by `jakarta.*` in Spring Boot 3.x)
- `runtime = "java21"` in Terraform for durable functions (managed runtime not supported; must use container image)

### Architecture Approach

The architecture is an 8-module Maven multi-module project with a clean dependency hierarchy. `rsf-dsl` has no upstream RSF dependencies and is the build-order root; `rsf-runtime` (I/O pipeline, annotations, registry) and `rsf-codegen` (FreeMarker code generation) both depend only on `rsf-dsl`; `rsf-terraform` and `rsf-importer` are sibling modules at the same layer; `rsf-editor` and `rsf-inspector` are Spring Boot applications depending on `rsf-dsl` and `rsf-runtime`; `rsf-cli` (Picocli) is the integration layer depending on all other modules and producing the fat JAR. The Lambda runtime module (`rsf-runtime`) is intentionally kept free of Spring Boot — it ships inside user Lambda deployment artifacts and must not carry Spring's classpath scanning overhead.

**Major components:**
1. `rsf-dsl` — Jackson `YAMLMapper` + `ObjectMapper`; sealed `State` interface with 8 subtypes; `StateMachineDefinition` root model; BFS semantic validator; victools JSON Schema generator
2. `rsf-codegen` — FreeMarker 2.3.34; BFS state traversal; `Orchestrator.java.ftl` + `HandlerStub.java.ftl`; Generation Gap pattern; golden-file test infrastructure
3. `rsf-terraform` — FreeMarker with `SQUARE_BRACKET_TAG_SYNTAX`; 6 HCL template files; container-image deployment model (ECR, Dockerfile template, `package_type = "Image"`)
4. `rsf-runtime` — `@State`/`@Startup` annotations; `HandlerRegistry` with classpath scanning; `IOPipeline` 5-stage; `IntrinsicRegistry` with 18 functions; `MockDurableContext`
5. `rsf-importer` — Jackson `readTree()` + 6 ASL-to-RSF conversion rules; SnakeYAML/YAMLMapper emission
6. `rsf-editor` — Spring Boot with `TextWebSocketHandler`; `SchemaController` serving victools-generated schema; React SPA in `resources/static/`
7. `rsf-inspector` — Spring Boot with `SseEmitter`; AWS SDK v2 `LambdaClient`; rate-limited polling (Guava `RateLimiter`); React SPA in `resources/static/`
8. `rsf-cli` — Picocli `@Command(subcommands={...})`; 7 subcommand classes implementing `Callable<Integer>`; maven-shade-plugin fat JAR

**Key patterns to follow:**
- Jackson Polymorphic Deserialization with Sealed Interface: `@JsonTypeInfo(use=NAME, property="Type")` + `@JsonSubTypes` listing all permitted subtypes on every discriminated union; never rely on auto-detection in Jackson 2.x
- DurableHandler Subclass with While-Loop State Machine: generated orchestrator is a while-loop over state names calling `context.step()`, `context.wait()`, etc.; Parallel and Map states emit `UnsupportedOperationException` stubs
- Generation Gap: first-line `// DO NOT EDIT — Generated by RSF` marker; check before overwriting; user handler stubs without marker are never touched
- FreeMarker Null Safety: `${(optional)!""}` for strings, `<#list (optionalList)![] as item>` for collections, `<#if field??>` for blocks — Jinja2 silently renders None as empty; FreeMarker throws `InvalidReferenceException` without these guards
- ObjectMapper as `static final`: configure once at class load time; never call `registerModule()` or `configure()` inside `handleRequest`
- Use `JsonNode.path()` not `.get()` for all chained JSON access — `.get()` returns Java `null`; `.path()` returns `MissingNode`, preventing `NullPointerException` chains

### Critical Pitfalls

1. **Java SDK Preview — `parallel`, `map`, `waitForCondition`, `waitForCallback` not implemented** — Generate `UnsupportedOperationException` stubs for Parallel and Map states; never use `CompletableFuture.allOf()` as a substitute (it bypasses checkpoint/replay, causing duplicate side effects on retry); monitor `aws/aws-durable-execution-sdk-java` releases for GA.

2. **Container-image-only deployment (no managed runtime)** — Terraform templates must emit `package_type = "Image"` + ECR repository + Dockerfile template; setting `runtime = "java21"` in `aws_lambda_function` for a durable function is an AWS API error during Preview.

3. **Type erasure breaks generic step result deserialization** — Never pass `List.class` to `ctx.step()`; use `TypeToken<List<Order>>(){}` for all parameterized types; FreeMarker templates must emit `TypeToken` form for collection-returning states.

4. **Jackson `@JsonSubTypes` missing causes silent `LinkedHashMap` deserialization** — Always pair `@JsonTypeInfo` with a complete `@JsonSubTypes` list; write round-trip tests for every state type asserting the exact concrete class (not just the sealed interface).

5. **FreeMarker strict null crashes on optional DSL fields** — Every optional field access in templates needs `!` or `??` guards; every template must have a "minimal required fields" test fixture, not only a fully-populated one.

6. **Spring Boot in Lambda DurableHandler adds 3–8s cold start** — The `rsf-runtime` Maven module must never have a Spring Boot dependency; Spring Boot belongs only in `rsf-editor` and `rsf-inspector`; enforce via Maven dependency graph.

7. **Runtime classpath scanning adds 500ms–2s Lambda cold start** — Classpath scanning with `Reflections` is acceptable for early development; blueprint must document APT compile-time registry as the production-grade replacement.

8. **Jackson version conflicts in multi-module Maven** — Root POM must import the Jackson BOM in `<dependencyManagement>` before any module declares Jackson; run `mvn dependency:tree -Dincludes=com.fasterxml.jackson` after every dependency addition.

## Implications for Roadmap

The blueprint document (RSF-BUILDPRINT-JAVA.md) should be authored in dependency order — each section builds on the previous, mirroring the Maven module dependency graph. The roadmap for this milestone is: "author each blueprint section in the order determined by component dependencies."

### Phase 1: Project Foundation and SDK Assessment

**Rationale:** Two foundational questions must be answered before any component section can be written: (1) What can the Java SDK actually do today, and (2) What is the Maven module structure that enforces all architectural constraints? Getting the SDK scope wrong would require rewriting all code generation sections. Getting the module structure wrong would require restructuring all component sections.

**Delivers:**
- SDK capability matrix: which primitives are available (step, wait, invoke, runInChildContext, createCallback) vs. blocked (parallel, map, waitForCondition, waitForCallback)
- Maven 8-module parent POM with Jackson BOM in `<dependencyManagement>`, Spring Boot parent, plugin management
- `rsf-dsl` blueprint: sealed `State` interface, all 8 subtypes as Java records, `@JsonTypeInfo`/`@JsonSubTypes` configuration, `YAMLMapper` setup, round-trip test patterns
- Container-image deployment model: Dockerfile template, ECR resource in Terraform, `package_type = "Image"` everywhere

**Addresses:** DSL Models (P1), Maven multi-module layout (P1)
**Avoids:** SDK parity assumption pitfall (#1), container deployment pitfall (#2), Jackson version conflict pitfall (#8), `@JsonSubTypes` silent LinkedHashMap pitfall (#4)

### Phase 2: Runtime Core — I/O Pipeline, Intrinsics, Registry

**Rationale:** The I/O pipeline and intrinsic functions are prerequisites for the code generator — the generated orchestrator code calls these at runtime. The handler registry is also called by generated code. All three must be blueprinted before the code generation section. These components have no dependency on Spring Boot or FreeMarker.

**Delivers:**
- `rsf-runtime` module blueprint: `@State`/`@Startup` annotation definitions, `HandlerRegistry` with classpath scanning + APT alternative documented, `HandlerFunction` functional interface
- I/O Pipeline blueprint: 5-stage pipeline with Jayway JsonPath + `JacksonJsonNodeJsonProvider`; `JsonNode.path()` null-safety pattern; `VariableStore` interface
- Intrinsic Functions blueprint: `IntrinsicParser` recursive descent class skeleton; `@FunctionalInterface IntrinsicFunction`; all 18 functions mapped to Java from Python
- Mock SDK blueprint: `MockDurableContext` implementing `DurableContext`; step/wait immediate execution; Parallel/Map `UnsupportedOperationException` stubs

**Uses:** Jackson 2.18.5, Jayway JsonPath 2.9.0, AWS Durable Execution SDK Java (Preview)
**Implements:** rsf-runtime component
**Avoids:** Type erasure pitfall (#3), JSONPath null safety (`JsonNode.path()` over `.get()`), classpath scanning cold start pitfall (#7)

### Phase 3: Code Generation — FreeMarker Templates

**Rationale:** Code generation is the primary user-facing output of RSF. It depends on DSL models (Phase 1) and the runtime types the generated code must call (Phase 2). FreeMarker's null-handling and whitespace behavior — both inverted from Jinja2 — are the highest-risk translation surface in the entire port.

**Delivers:**
- `rsf-codegen` blueprint: `CodeGenerator` class, `StateMapper` BFS traversal, `StateMapping` record
- `Orchestrator.java.ftl` template with null guards, Parallel/Map `UnsupportedOperationException` stubs, and TypeToken usage for generic results
- `HandlerStub.java.ftl` template
- FreeMarker `Configuration` setup: angle-bracket syntax for Java templates, square-bracket syntax for HCL templates (two separate `Configuration` instances)
- Golden-file testing strategy for generated code
- Generation Gap implementation in Java

**Uses:** FreeMarker 2.3.34
**Implements:** rsf-codegen component
**Avoids:** FreeMarker null crash pitfall (#5), FreeMarker whitespace pitfall, FreeMarker list-null pitfall — all prevented by mandatory minimal-fixture tests

### Phase 4: Terraform Generator and ASL Importer

**Rationale:** The Terraform generator and ASL importer are parallel concerns — neither depends on the other. Both depend on DSL models (Phase 1). The Java Terraform generator is substantially different from the Python version: it must emit container-image deployment resources, not ZIP-based managed runtime resources. This is a significant architectural change requiring careful documentation.

**Delivers:**
- `rsf-terraform` blueprint: FreeMarker square-bracket syntax setup; all 6 HCL template files; IAM derivation logic; Dockerfile template for Java Lambda container; ECR `aws_ecr_repository` resource; `package_type = "Image"` Lambda configuration; Maven shade plugin fat JAR build and ECR push workflow
- `rsf-importer` blueprint: Jackson `readTree()` + `ObjectNode` manipulation; all 6 ASL-to-RSF conversion rules; `ImportWarning` record; YAML emission via `YAMLMapper`
- Container image build workflow documentation (Maven shade → fat JAR → Docker build → ECR push)

**Uses:** FreeMarker 2.3.34 (square-bracket mode), Jackson 2.18.5
**Implements:** rsf-terraform, rsf-importer components
**Avoids:** Container deployment pitfall (#2), HCL `${...}` conflict (solved by square-bracket syntax)

### Phase 5: CLI and Web Backends

**Rationale:** The CLI is the integration layer — it depends on all other modules. The web backends depend on DSL models and JSON schema generation. Both can be blueprinted after the core library layer is specified. Web backends introduce Spring Boot, which must be kept strictly separated from the Lambda runtime module via Maven dependency boundaries.

**Delivers:**
- `rsf-cli` blueprint: Picocli `@Command` hierarchy for 7 subcommands; `Callable<Integer>` pattern; fat JAR configuration; maven-shade-plugin setup; Jansi colored output equivalent
- `rsf-editor` blueprint: Spring Boot `TextWebSocketHandler`; `SchemaController` (victools schema generation); React SPA serving from `resources/static/`; WebSocket configuration
- `rsf-inspector` blueprint: Spring Boot `SseEmitter`; `InspectorController` REST + SSE endpoints; `LambdaInspectClient` wrapping AWS SDK v2 `LambdaClient`; Guava `RateLimiter` (12 req/s); React SPA serving
- JSON Schema blueprint: victools jsonschema-generator 4.35.0; `SchemaGeneratorConfigBuilder` with `JacksonModule`; Draft 2020-12 output

**Uses:** Picocli 4.7.7, Spring Boot 3.5.9, AWS SDK v2, Guava
**Implements:** rsf-cli, rsf-editor, rsf-inspector components
**Avoids:** Spring Boot in Lambda pitfall (#6) — enforced by Maven; Spring Boot appears only in `rsf-editor` and `rsf-inspector`

### Phase 6: Testing Strategy and Blueprint Finalization

**Rationale:** The testing strategy section ties all component blueprints together with concrete test patterns. It must come last because it references patterns from all prior phases. The finalization step assembles RSF-BUILDPRINT-JAVA.md from all phase sections.

**Delivers:**
- Testing strategy: JUnit 5 + Mockito 5 + AssertJ 3 patterns for each component type
- DSL round-trip test pattern (serialize → deserialize → assert exact concrete type)
- FreeMarker golden-file test pattern with both fully-populated and minimal-fixture inputs
- I/O pipeline test patterns (null inputs, missing fields, all 5 stages)
- Mock SDK test fixtures for all available durable context operations
- RSF-BUILDPRINT-JAVA.md: consolidated, cross-referenced blueprint document

**Avoids:** Template testing gaps — mandating minimal-fixture tests alongside fully-populated fixtures catches all FreeMarker null pitfalls before implementation begins

### Phase Ordering Rationale

- DSL models come first because every other component depends on `StateMachineDefinition` and the `State` sealed interface hierarchy — it is the build-order root.
- SDK assessment is paired with DSL models (Phase 1) because the SDK's available primitives constrain what the code generator can emit; getting this wrong invalidates all downstream template design.
- Runtime core (Phase 2) comes before code generation (Phase 3) because generated code calls runtime classes — the blueprint cannot document what is generated without first documenting what it calls into.
- Terraform and importer (Phase 4) can be parallel work within the phase; they depend on DSL models and FreeMarker patterns but not on each other.
- CLI and web backends (Phase 5) come after core library blueprinting because they are the integration layer that references all prior components; Spring Boot separation is enforced here.
- The phase ordering directly mirrors the Maven module dependency graph: `rsf-dsl` → `rsf-runtime` / `rsf-codegen` → `rsf-terraform` / `rsf-importer` → `rsf-editor` / `rsf-inspector` → `rsf-cli`.

### Research Flags

Phases requiring additional investigation before or during blueprint authoring:

- **Phase 1 (SDK Assessment):** The Java SDK is in Developer Preview. Exact method signatures for `DurableContext` must be verified against `github.com/aws/aws-durable-execution-sdk-java` source before documenting. The Maven version number is unspecified in current AWS docs — the GitHub releases tab must be checked. Mark HIGH priority for pre-flight verification before authoring the Mock SDK section.
- **Phase 2 (Mock SDK):** `MockDurableContext` must implement the actual `DurableContext` interface. Signatures for `parallel`, `map`, `waitForCondition`, `waitForCallback` are unconfirmed during Preview; these must be stubbed with `UnsupportedOperationException` and flagged "verify when SDK ships GA."
- **Phase 4 (Container Deployment):** The Dockerfile pattern and ECR workflow are documented in AWS docs, but the current recommended ECR base image tag (Java 21 vs. Java 25) should be verified at blueprint-authoring time — both are referenced in AWS docs.

Phases with well-documented standard patterns (additional research not required):

- **Phase 3 (FreeMarker):** FreeMarker 2.3.34 is mature, fully documented. Square-bracket syntax is a single `setTagSyntax()` call. Standard patterns apply.
- **Phase 5 (CLI + Web Backends):** Picocli 4.7.7 and Spring Boot 3.5.9 are mature with extensive official documentation. `SseEmitter`, `TextWebSocketHandler`, and Picocli subcommand patterns are all well-documented. No additional research needed.
- **Phase 6 (Testing):** JUnit 5 + Mockito 5 + AssertJ is the industry-standard Java testing stack. No additional research needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All library versions verified against Maven Central, official docs, and GitHub releases. Spring Boot 3.5.9, Jackson 2.18.5, FreeMarker 2.3.34, Picocli 4.7.7 all confirmed current. AWS SDK for Java 2.x BOM-managed. Version incompatibilities (JUnit 6, Jackson 3.x, AWS SDK 1.x) explicitly documented. |
| Features | MEDIUM-HIGH | Python-to-Java mapping for 12 of 14 components is HIGH confidence (both stacks are mature). Mock SDK and Parallel/Map feature stubs are MEDIUM confidence due to Java SDK Preview status and unconfirmed interface method signatures. |
| Architecture | HIGH | Maven multi-module structure, module boundaries, data flow, and all 7 architectural patterns are well-established Java patterns verified against official Spring Boot, Picocli, FreeMarker, and Jackson documentation. The Lambda module isolation pattern is a known best practice. |
| Pitfalls | HIGH (facts) / MEDIUM (SDK projections) | All 14 documented pitfalls are verified against official documentation, Jackson GitHub issues, and Maven plugin developer guides. SDK Preview stability and GA timeline projections are MEDIUM — based on Preview announcement, not a confirmed AWS roadmap. |

**Overall confidence:** HIGH for everything except Java SDK Preview feature gaps (MEDIUM)

### Gaps to Address

- **Java SDK `DurableContext` exact interface signatures:** Must verify all method signatures by reading `aws/aws-durable-execution-sdk-java` source before writing the Mock SDK section. The Maven version number is `VERSION` (unspecified) in current AWS docs — find the actual release tag on GitHub.
- **Parallel/Map state workaround:** The blueprint documents `runInChildContext()` as a temporary workaround for parallel sub-workflows. This is not semantically equivalent to true parallel execution (no checkpoint isolation between branches). Blueprint must clearly warn users and set expectations about GA timing.
- **Java 25 vs. Java 21 ECR base image:** AWS docs reference both `public.ecr.aws/lambda/java:21` and `public.ecr.aws/lambda/java:25` as base images. Blueprint should verify which is current and recommended at authoring time.
- **victools jsonschema-generator 4.35.0 compatibility with Jackson 2.18.5:** Verify on Maven Central that victools 4.35.0 is compatible with Jackson 2.18.5 specifically before recommending this version combination in the blueprint.
- **SnakeYAML thread safety in web backends:** `Yaml` (raw SnakeYAML) instances are NOT thread-safe. Blueprint must explicitly recommend `jackson-dataformat-yaml`'s `YAMLMapper` for the web backend's DSL parsing — it is thread-safe because it shares the thread-safe `ObjectMapper` pipeline.

## Sources

### Primary (HIGH confidence)

- AWS Lambda Durable Execution SDK for Java Developer Preview Announcement — Java 17+ requirement, Preview status, Maven coordinates `software.amazon.lambda.durable:aws-durable-execution-sdk-java`
- AWS Lambda Durable Supported Runtimes documentation — Container-image-only deployment, `DurableContext` API method availability, `parallel`/`map`/`waitForCondition`/`waitForCallback` "still in development" statement
- `github.com/aws/aws-durable-execution-sdk-java` — Full API class list (DurableHandler, DurableContext, DurableFuture, DurableCallbackFuture, StepConfig, CallbackConfig, InvokeConfig, DurableConfig, TypeToken, RetryStrategies); package name `software.amazon.lambda.durable`
- FreeMarker 2.3.34 official docs — Version (2024-12-22 release), `setTagSyntax(SQUARE_BRACKET_TAG_SYNTAX)`, `setInterpolationSyntax(SQUARE_BRACKET_INTERPOLATION_SYNTAX)`, null-handling operators (`!`, `??`)
- Picocli 4.7.7 official site + GitHub — Subcommand pattern, annotation processor (`picocli-codegen`), fat JAR configuration, `Callable<Integer>` pattern
- Spring Boot 3.5.9 docs + blog — `SseEmitter`, `TextWebSocketHandler`, `@EnableWebSocket`, `@RestController`, static resource handler
- Jackson 2.18.5 Maven Central + FasterXML GitHub — `@JsonTypeInfo`/`@JsonSubTypes` on sealed interfaces; Jackson 2.x requires explicit `@JsonSubTypes` (no auto-detection for sealed classes); Jackson 3.x would auto-detect (not yet adopted by ecosystem)
- Hibernate Validator 9.1.0.Final — Jakarta Validation 3.1, Java 17+ requirement, `jakarta.*` namespace
- JUnit Jupiter 5.11.4, Mockito 5.14.2, AssertJ 3.27.7 — Maven Central version confirmation
- networknt json-schema-validator 1.5.6 — Draft 2020-12 support, February 2025 release
- RSF Python source code (direct inspection at `/home/esa/git/rsf-python/src/rsf/`) — all 14 component implementations as ground truth for mapping decisions

### Secondary (MEDIUM confidence)

- `github.com/victools/jsonschema-generator` 4.35.0 — JSON schema generation from Jackson DTOs; Draft 2020-12 support; `jsonschema-module-jackson` compatibility
- `github.com/json-path/JsonPath` 2.9.0 — `JacksonJsonNodeJsonProvider` pattern; JSONPath evaluation; `JsonNode.path()` null-safety
- Spring Boot WebSocket + SSE tutorials — `TextWebSocketHandler`, `SseEmitter` lifecycle management, executor service pattern
- Java Code Geeks: Spring Boot vs. Quarkus vs. Micronaut 2025 — framework selection rationale for developer tools vs. serverless workloads

### Tertiary (LOW confidence)

- Java SDK Preview stability projections — Timeline for `parallel()`/`map()` GA is not officially announced; projections based on Preview announcement cadence and Python SDK feature completeness as precedent only.

---
*Research completed: 2026-02-28*
*Ready for roadmap: yes*
