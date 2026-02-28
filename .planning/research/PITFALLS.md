# Pitfalls Research

**Domain:** Python-to-Java port of RSF (Replacement for Step Functions) using AWS Lambda Durable Execution SDK for Java (Preview)
**Researched:** 2026-02-28
**Confidence:** HIGH (SDK API facts verified against official AWS docs); MEDIUM (FreeMarker/Jackson patterns from multiple community sources); LOW (Preview SDK stability projections)

---

## Critical Pitfalls

### Pitfall 1: Java SDK Preview — `parallel`, `map`, `stepAsync`, `waitForCondition` Are Not Yet Implemented

**What goes wrong:**
The RSF Python SDK uses `context.parallel()` and `context.map()` for Parallel and Map state types — two of the eight ASL state types. The Java Durable Execution SDK (Developer Preview, announced February 2026) does not yet implement these primitives. The AWS docs explicitly state: "The following operations are still in development for Java: `waitForCondition`, `waitForCallback`, `parallel`, `map`." Any generated Java orchestrator code that calls these methods will fail to compile or throw a runtime error.

**Why it happens:**
The Python SDK is GA. The Java SDK is in Developer Preview. The blueprint author assumes feature parity between the two SDKs because conceptually the operations are the same. The GitHub README and official announcement omit the missing-features list unless you consult the supported-runtimes page directly.

**How to avoid:**
1. Verify the current state of the Java SDK's feature set at `https://docs.aws.amazon.com/lambda/latest/dg/durable-supported-runtimes.html` before designing any Parallel or Map state code generation.
2. Design the Java code generator to emit a `throw new UnsupportedOperationException("Parallel state requires Java SDK parallel() — not yet available in preview")` stub for Parallel and Map states, clearly flagging these as deferred until the SDK ships them GA.
3. Track the Java SDK GitHub (`aws/aws-durable-execution-sdk-java`) for new releases. Pin to a specific version in the Maven POM and upgrade deliberately, not via `LATEST` or `-SNAPSHOT`.
4. Phase the blueprint explicitly: Phase 1 covers step/wait/callback (available now); Parallel and Map states are flagged as Phase 2 pending SDK availability.

**Warning signs:**
- Blueprint claims full Parallel/Map support without citing SDK release notes
- Generated code imports `DurableFuture.allOf()` or calls `ctx.parallel()` without a GA SDK version reference
- Tests for Parallel/Map states that pass locally (using mocks) but have no real AWS integration test

**Phase to address:**
Phase 0 (SDK assessment and blueprint scoping). Before writing a single line of code generation, the phase must document what the Java SDK can and cannot do. Parallel/Map state support is explicitly gated on SDK GA.

---

### Pitfall 2: Java SDK — Container-Image-Only Deployment (No Managed Runtime)

**What goes wrong:**
Python durable functions deploy as standard ZIP packages using the `python3.13` managed runtime. Java durable functions in preview can only be deployed via container images — there is no `java21` or `java17` managed runtime for durable functions. The RSF Terraform generator produces `runtime = "python3.13"` in `main.tf`. A Java port that naively substitutes `runtime = "java21"` will fail with an AWS API error because Java is not a supported managed runtime for durable execution. The entire Terraform infrastructure generation strategy must change.

**Why it happens:**
Developers familiar with standard Java Lambda deployment (ZIP with managed runtime) apply the same pattern. The durable-functions-specific constraint — managed runtime unavailability for Java — is buried in the supported-runtimes documentation page rather than the main SDK docs.

**How to avoid:**
1. The Java Terraform generator must produce `package_type = "Image"` Lambda resources, not `package_type = "Zip"`.
2. The blueprint must include a Dockerfile template for the Java Lambda container image, not a `requirements.txt` / `pip install` approach.
3. The Maven build must produce a fat JAR (via `maven-shade-plugin` or `maven-assembly-plugin`) that gets COPY'd into the container image.
4. ECR repository creation must be part of the Terraform template (`aws_ecr_repository`), and the image push step added to the deploy workflow.
5. The `rsf generate` equivalent must include a `Dockerfile` output alongside the Java source files.

**Warning signs:**
- Terraform templates contain `runtime = "java21"` or `runtime = "java17"` for durable functions
- No `Dockerfile` in the generated project structure
- No ECR repository in the Terraform templates
- No container image build step in the deploy documentation

**Phase to address:**
Phase 1 (Core infrastructure and generated project structure). The deployment model must be correct before any functional code generation work begins.

---

### Pitfall 3: Type Erasure Breaks Jackson Deserialization of Parameterized Step Results

**What goes wrong:**
The Java SDK's `ctx.step()` returns a typed result: `ctx.step("step-name", List<Order>.class, ...)`. But `List<Order>.class` is a compile error — Java erases generic parameters at runtime. The result type `Class<T>` cannot represent `List<Order>`. Code that attempts `ctx.step("name", List.class, ...)` deserializes to `List<LinkedHashMap>` instead of `List<Order>`, causing `ClassCastException` when handler code accesses `Order` fields. This exact problem occurs in the intrinsic function dispatch table when the return type of a function is generic.

**Why it happens:**
Python has no type erasure. `list[Order]` at runtime is exactly what it says. Java generics are compile-time only. Developers porting Python type annotations to Java generic signatures write `List<Order>` then pass `List<Order>.class` to the SDK — which does not compile, or write `List.class` which silently deserializes wrong.

**How to avoid:**
1. Use `TypeToken<List<Order>>() {}.getType()` (Guava) or `new TypeReference<List<Order>>() {}` (Jackson) wherever the SDK accepts a type for deserialization of generic results.
2. The Java SDK uses `TypeToken` — verify the exact SDK API: if it accepts `Class<T>`, it cannot handle parameterized types; if it accepts `TypeToken<T>`, use the anonymous subclass form.
3. In the code generator FreeMarker templates, for states that return collections, emit `TypeToken<List<${handlerOutputType}>>() {}` rather than `${handlerOutputType}.class`.
4. Write a test: `ctx.step("test", new TypeToken<Map<String, Object>>(){}, () -> Map.of("a", 1))` and verify the result is `Map<String, Object>`, not `Map<String, LinkedHashMap>`.

**Warning signs:**
- `ClassCastException: class java.util.LinkedHashMap cannot be cast to class Order` at runtime
- Tests pass with `Object` result type but fail with specific types
- Generated code contains `.class` literal on a parameterized type (compile error if it's `List<Order>.class`, runtime type loss if it's `List.class`)

**Phase to address:**
Phase 1 (SDK integration and type mapping). Define a canonical type-mapping strategy for all generated step result types before any template work.

---

### Pitfall 4: Jackson Polymorphic Deserialization — Missing `@JsonSubTypes` Causes Silent Raw Map Deserialization

**What goes wrong:**
RSF's DSL models use Pydantic discriminated unions (e.g., `StateDefinition = TaskState | ChoiceState | WaitState | ...` with `type: Literal["Task"]` as discriminator). In Java, the equivalent is a `sealed interface StateDefinition` with `@JsonTypeInfo` on the interface and `@JsonSubTypes` listing all permitted types. If `@JsonSubTypes` is missing or incomplete, Jackson does not throw an error — it silently deserializes the JSON into a raw `Map<String, Object>` or fails with `InvalidTypeIdException` only when an unknown type discriminator is encountered. The first failure mode (silent Map) is the dangerous one: validation passes but the model object has no typed fields.

**Why it happens:**
The developer annotates the sealed interface with `@JsonTypeInfo(use = Id.NAME, property = "Type")` but forgets `@JsonSubTypes`. Jackson 2.x does not auto-discover permitted subclasses of sealed interfaces — that feature exists as a future proposal but is not yet in any released Jackson version (as of 2026). The contract seems complete because the code compiles cleanly.

**How to avoid:**
1. Every sealed interface (or abstract class) used as a DSL node type requires both `@JsonTypeInfo` and `@JsonSubTypes` with all permitted subtypes explicitly listed.
2. Do NOT use `@JsonTypeInfo(use = Id.CLASS)` — this is a security risk and breaks when class names change.
3. Use `include = JsonTypeInfo.As.EXISTING_PROPERTY, visible = true` when the discriminator field (`"Type"`) must remain in the deserialized object.
4. Write a round-trip test for every state type: serialize then deserialize, assert the exact concrete type (not `instanceof StateDefinition`).
5. Do not rely on Jackson 2.x to auto-detect sealed interface subtypes — register them all explicitly.

**Warning signs:**
- `InvalidDefinitionException: No _type id found from JSON` during deserialization
- Deserialized objects are `LinkedHashMap` instead of the expected concrete type
- Tests that only assert on the interface reference (not the concrete class) pass even with wrong configuration

**Phase to address:**
Phase 1 (DSL model design). Write the `@JsonTypeInfo`/`@JsonSubTypes` configuration and the round-trip tests before any downstream code (validator, code generator) consumes the DSL model.

---

### Pitfall 5: FreeMarker Null Safety — Strict `null` Handling Crashes Templates That Jinja2 Would Handle Gracefully

**What goes wrong:**
Jinja2 templates render `{{ variable }}` as an empty string when `variable` is `None`. FreeMarker by default throws `InvalidReferenceException: The following has evaluated to null or missing` for the equivalent `${variable}`. RSF's existing Jinja2 templates use optional fields extensively (e.g., `{{ state.comment }}` renders empty if comment is absent, `{{ state.retry }}` renders nothing if retry is None). A direct FreeMarker port that does not add null guards to every optional field will crash on templates that encounter any null model field.

**Why it happens:**
Jinja2's default behavior is permissive — undefined/null renders as empty. FreeMarker's default behavior is strict — undefined/null aborts rendering. Developers porting template logic do not realize the null-handling contract has reversed.

**How to avoid:**
1. Use `${variable!}` (default-empty-string operator) for every optional string field in FreeMarker templates.
2. Use `${variable!"default value"}` when a non-empty default is needed.
3. For null-checking before a block: `<#if variable??> ... </#if>` (double question mark = exists and not null).
4. For nested optional access: use parentheses — `(state.retry)![]` handles both `state` being null and `state.retry` being null. Without parentheses, `state.retry![]` only handles `retry` being null, not `state` being null.
5. Configure FreeMarker with `template_exception_handler = TemplateExceptionHandler.RETHROW_HANDLER` in tests to catch null errors immediately rather than suppressing them.

**Warning signs:**
- `freemarker.core.InvalidReferenceException: The following has evaluated to null or missing` during code generation
- Templates produce partial output and silently truncate at the first null field
- Tests that use fully-populated model objects pass but real DSL files (with optional fields absent) fail

**Phase to address:**
Phase 2 (Code generation — FreeMarker templates). Every template must be tested with minimal model objects (all optional fields null) before declaring the template complete.

---

### Pitfall 6: FreeMarker Whitespace — Generated Java Code Has Spurious Blank Lines and Indentation Artifacts

**What goes wrong:**
Jinja2 with `trim_blocks=True` and `lstrip_blocks=True` removes the newline after block tags and strips leading whitespace. RSF already uses custom delimiters (`<< >>`, `<% %>`) to avoid HCL conflicts. FreeMarker does not support custom delimiters in the same way and has different whitespace stripping behavior: it strips whitespace around FTL tags on lines that contain only FTL tags, but does not strip the newlines introduced by `<#list>` loops. Generated Java code ends up with extra blank lines between every list item (e.g., between each `if/else if` state branch), breaking formatting and sometimes producing compilation-affecting whitespace in string templates.

**Why it happens:**
FreeMarker's whitespace stripping is line-based and automatic for "tag-only lines" but does not extend to content lines within list loops. Jinja2's `trim_blocks` removes the trailing newline from every block tag. The behavior is similar but not identical — subtle differences cause visual (and sometimes functional) differences in generated output.

**How to avoid:**
1. Use `<#t>` (trim both sides) or `<#rt>` (trim right) directives on lines where trailing whitespace must be removed.
2. For list loops that generate code blocks, test the generated output with more than two iterations to expose the blank-line pattern.
3. Configure FreeMarker's `whitespace_stripping = true` (the default) and verify it handles all control structure lines.
4. Use golden-file tests: generate code from a reference DSL, commit the expected output, and fail the test if whitespace changes.
5. Do not use FreeMarker's `<#compress>` directive for Java code — it collapses all whitespace including significant indentation.

**Warning signs:**
- Generated Java files have double blank lines between every state handler block
- `javafmt` or the IDE formatter reports excessive blank lines in generated code
- Golden-file tests show diff output where only whitespace differs from expected

**Phase to address:**
Phase 2 (Code generation — FreeMarker templates). Establish golden-file tests from the first template, not after all templates are written.

---

### Pitfall 7: Python Decorator Registration vs. Java Annotation Scanning — Classpath Scanning Adds Lambda Cold Start Latency

**What goes wrong:**
Python's `@state("StateName")` decorator registers handlers at module import time — a deterministic, zero-reflection operation. In Java, `@State("StateName")` is an annotation. Annotations are not self-registering — something must discover them. The two options are: (A) compile-time annotation processing (APT), which generates a registry at build time; or (B) runtime classpath scanning with reflection (e.g., via `ClassGraph` or `Reflections`). Option B is the obvious first implementation — scan the classpath on cold start, find all classes with `@State`, register them. But classpath scanning at Lambda cold start adds 500ms–2s of initialization time, which compounds with Java's already-slow cold start. With a DurableHandler that must checkpoint on the first step call, a 2-second scan before any durable operation is executed is a significant regression from Python's near-zero registration overhead.

**Why it happens:**
Runtime reflection-based scanning is the default approach because it requires no build tooling changes. APT requires building a separate annotation processor module and wiring it into the Maven build, which feels like over-engineering during early development. The performance cost is discovered in production, not during unit testing (which runs with a warm JVM).

**How to avoid:**
1. Do NOT use runtime classpath scanning as the production handler registration mechanism. It is unacceptable for Lambda cold starts.
2. Use compile-time annotation processing (APT via `javax.annotation.processing`): the APT generates a `HandlerRegistry.java` file at build time that contains a static `Map<String, Class<?>>` of all `@State`-annotated classes. This is zero-reflection at runtime.
3. Alternatively, use explicit programmatic registration in the `DurableHandler.handleRequest` method: `registry.register("StateName", MyHandler::handle)` — explicit beats magic.
4. If APT is chosen, split into two Maven modules: `rsf-annotations` (contains only `@State`, `@Startup` annotations, no processor) and `rsf-annotation-processor` (contains the APT, depends on `rsf-annotations`). Consumer projects depend only on `rsf-annotations` at runtime; the processor is a provided/compile-only dependency.
5. Benchmark cold start with and without classpath scanning using a real Lambda function, not unit tests.

**Warning signs:**
- Lambda REPORT log shows `Init Duration: > 2000 ms` in CI after deploying with scanning
- `ClassGraph` or `Reflections` library appears in the Lambda deployment artifact (not just test scope)
- Handler registry is populated in an instance initializer block that calls `scanClasspath()`

**Phase to address:**
Phase 1 (Handler registry design). The registration mechanism must be decided and benchmarked before any example workflows are implemented.

---

### Pitfall 8: Java Cold Start — Spring Boot Classpath Scanning Makes DurableHandler Unusable

**What goes wrong:**
If Spring Boot is used as the framework for the Lambda handler (DurableHandler is wrapped in a Spring context), `@SpringBootApplication` triggers full classpath scanning (`@ComponentScan`) of the entire application package. A "Hello World" Spring Boot application loads approximately 5,900 classes at startup and may produce 4+ second cold starts before SnapStart. For the RSF graph editor and inspector backends (Spring Boot REST/WebSocket servers), this is acceptable because they are long-running processes. For the Lambda DurableHandler, Spring Boot is the wrong choice — the handler must start in under 500ms to maintain workflow responsiveness.

**Why it happens:**
Spring Boot is the dominant Java web framework. Developers who choose Spring Boot for the web backends naturally reach for it in the Lambda handler as well, because dependency injection and annotation-driven configuration feel consistent. The cold start penalty is not obvious until the first Lambda deployment.

**How to avoid:**
1. The Lambda DurableHandler must NOT use Spring Boot or any Spring `@ComponentScan`-based framework.
2. For the Lambda handler: use plain Java with explicit wiring, or Micronaut (AOT compilation, ~400ms cold start), or Dagger (compile-time DI). No Spring in the Lambda artifact.
3. For the web backends (graph editor, inspector): Spring Boot is fine — they are not Lambda functions.
4. Enable Lambda SnapStart for the Java handler by adding `SnapStart: ApplyOn: PublishedVersions` to the Lambda configuration. SnapStart snapshots the JVM after initialization and can reduce cold starts to ~200ms.
5. Caution with SnapStart: do not generate or cache unique values (UUIDs, random seeds, timestamps) during class initialization — they will be frozen in the snapshot and repeated across invocations. Generate all unique values inside `handleRequest`.

**Warning signs:**
- Spring Boot dependency appears in the Lambda handler module's `pom.xml` (not just the web backend module)
- `Init Duration` in Lambda logs exceeds 3000ms consistently
- Handler module's fat JAR exceeds 50MB (Spring Boot adds ~20MB of its own dependencies)

**Phase to address:**
Phase 1 (Maven multi-module structure). The Lambda handler module and web backend modules must be separate Maven modules with different dependency sets from day one.

---

### Pitfall 9: JSONPath Evaluation — Jackson `JsonNode.get()` Returns `null` for Missing Keys, Not `MissingNode`

**What goes wrong:**
RSF's Python JSONPath evaluator raises `JSONPathError` when a key is missing. Java's `JsonNode.get("key")` returns Java `null` for missing keys (not `MissingNode` — that's returned by `JsonNode.path()`). When the Java JSONPath evaluator chains accesses — `node.get("a").get("b")` — a missing "a" causes `NullPointerException` on the `.get("b")` call. This is the most common runtime error in Java JSON navigation and is subtly different from Python's `KeyError`, which fails loudly at the first missing key rather than producing a NullPointerException at the second access.

**Why it happens:**
`.get()` vs `.path()` is a Jackson API subtlety that is not obvious from method names. Python's dict raises `KeyError` immediately; Java's `.get()` returns null silently. The NPE happens one step later than expected, making the stack trace harder to diagnose.

**How to avoid:**
1. Use `JsonNode.path("key")` instead of `JsonNode.get("key")` for all chained access. `path()` returns `MissingNode` (never null), which can be checked with `.isMissingNode()`.
2. Write a helper: `JsonNode safeGet(JsonNode node, String key)` that throws `JSONPathError` explicitly when the key is missing, matching Python behavior.
3. For the JSONPath evaluator implementation, test every access step: `if (current.isMissingNode() || current.isNull()) throw new JSONPathError("Key '" + key + "' not found")`.
4. Test the pipeline with inputs that have missing optional fields — do not only test with fully-populated inputs.

**Warning signs:**
- `NullPointerException` with a stack trace pointing into the JSONPath evaluator at a chained `.get()` call
- Error message says "Cannot invoke method get() on null" — the outer `.get()` returned null
- Tests that use `{a: {b: 1}}` pass but tests with `{}` or `{a: null}` throw NPE

**Phase to address:**
Phase 1 (I/O pipeline implementation). The JSONPath evaluator is foundational — all 5 pipeline stages depend on it. Get null safety right before building any pipeline stage.

---

### Pitfall 10: Maven Multi-Module Structure — Jackson Version Conflicts Between Web Backend and Lambda Handler

**What goes wrong:**
The Maven multi-module project has (at minimum): `rsf-core` (DSL models, pipeline), `rsf-lambda` (DurableHandler), `rsf-web` (Spring Boot backends), `rsf-codegen` (FreeMarker code generator), `rsf-cli` (Picocli). Spring Boot imports its own Jackson BOM version (e.g., `2.17.x`). The Lambda handler uses the AWS SDK which imports a different Jackson version transitively. When `rsf-core` is shared between modules, Maven's "nearest definition wins" dependency mediation may resolve Jackson to the Spring Boot version in the Lambda fat JAR, pulling in Spring Boot's Jackson modules (like `jackson-module-kotlin` or `jackson-datatype-jsr310`) that add class loading overhead on Lambda cold start.

**Why it happens:**
Maven resolves dependency version conflicts using "nearest definition" (the version declared closest to the root POM). Without explicit `<dependencyManagement>` in the root POM, each module's transitive dependencies win based on declaration order — an order that changes when modules are added or reordered.

**How to avoid:**
1. Create a root-level `pom.xml` that uses `<dependencyManagement>` to pin ALL Jackson versions explicitly: `jackson-databind`, `jackson-core`, `jackson-annotations`, `jackson-dataformat-yaml`, `jackson-module-parameter-names`.
2. Import the Jackson BOM: `<dependency><groupId>com.fasterxml.jackson</groupId><artifactId>jackson-bom</artifactId><version>2.18.x</version><type>pom</type><scope>import</scope></dependency>` in the root `<dependencyManagement>`.
3. The Spring Boot parent POM also imports Jackson — use `<dependencyManagement>` to override Spring Boot's Jackson version after the Spring Boot BOM import if they conflict.
4. Run `mvn dependency:tree -Dincludes=com.fasterxml.jackson` after every new dependency addition to verify no unexpected version appears.
5. The Lambda handler module's `pom.xml` must use `<exclusions>` to explicitly remove any Spring Boot Jackson extras that the Spring Boot parent POM might inject transitively.

**Warning signs:**
- `mvn dependency:tree` shows two different Jackson versions in the same module
- `ClassNotFoundException: com.fasterxml.jackson.datatype.jsr310.JavaTimeModule` or version-mismatch runtime errors
- Lambda fat JAR contains `spring-boot-autoconfigure.jar` (Spring Boot loaded into Lambda artifact)

**Phase to address:**
Phase 0 (Maven project skeleton). The multi-module POM and `<dependencyManagement>` section must be established before any module adds dependencies. Retrofit is painful.

---

### Pitfall 11: Maven Plugin — Relative Path Resolution Against Working Directory, Not Project Base

**What goes wrong:**
The RSF code generator (equivalent of `rsf generate`) is implemented as a Maven plugin Mojo. The Mojo has a parameter `<inputFile>workflow.yaml</inputFile>`. When the user runs `mvn rsf:generate` from a subdirectory (or when Maven is invoked with `-f path/to/pom.xml`), `new File("workflow.yaml")` resolves against the JVM's current working directory — which is not the project's `${project.basedir}`. The Mojo silently reads from or writes to the wrong directory, producing either `FileNotFoundException` or overwriting unintended files.

**Why it happens:**
This is listed as a documented Maven plugin pitfall on the official Maven Plugin Developers guide. Developers assume `new File(relativePath)` resolves from the project root. It resolves from wherever `java` was launched.

**How to avoid:**
1. Declare all file path parameters as `java.io.File` type in the Mojo: `@Parameter(defaultValue = "${project.basedir}/workflow.yaml") private File inputFile`. Maven automatically resolves `File` parameters against the project base directory.
2. For dynamically constructed paths: `File resolved = new File(path); if (!resolved.isAbsolute()) { resolved = new File(project.getBasedir(), path); }`.
3. Inject `MavenProject project` into the Mojo via `@Component` to access `project.getBasedir()`.
4. Test the Mojo with `mvn -f subdir/pom.xml rsf:generate` to verify path resolution in non-root invocations.

**Warning signs:**
- `FileNotFoundException` when running the plugin from an IDE that sets a different working directory
- Plugin works from terminal (`mvn rsf:generate`) but fails in CI (which uses `-f` flag)
- Output files appear in the wrong directory in reactor builds

**Phase to address:**
Phase 3 (Maven plugin development). All file parameters must use `File` type from the first Mojo implementation.

---

### Pitfall 12: Preview SDK — `parallel()` and `map()` Absence Makes Parallel/Map State Code Generation Deferred, Not Blocked

**What goes wrong:**
The RSF blueprint promises full ASL feature parity. Parallel and Map states are two of the eight ASL state types. The Java SDK does not yet implement `parallel()` or `map()`. A blueprint that defers these states without a clear delivery path risks: (A) shipping a Java port that is publicly "feature-incomplete" with no timeline; or (B) incorrectly implementing Parallel/Map states using Java `CompletableFuture` directly (bypassing the durable SDK), which breaks checkpoint/replay semantics — completed branches are not checkpointed, so on replay they re-execute, causing duplicate side effects.

**Why it happens:**
The temptation to "fake" parallel execution with `CompletableFuture.allOf()` is high because it produces working results on the happy path. The checkpoint-replay failure only manifests on retries or when the Lambda function is interrupted mid-execution — which is exactly the scenario durable functions are designed to handle.

**How to avoid:**
1. Never implement Parallel or Map state semantics using `CompletableFuture` directly — this bypasses checkpoint/replay and silently breaks durability guarantees.
2. The blueprint must explicitly document: "Parallel and Map state code generation is blocked on Java SDK GA. The generated code emits a clear `UnsupportedOperationException` with a reference to the SDK tracking issue."
3. Monitor `https://github.com/aws/aws-durable-execution-sdk-java` releases. When `parallel()` and `map()` are added, implement them against the SDK primitives.
4. Use `runInChildContext()` (currently available) to model isolated sub-workflows as a temporary workaround — but document clearly that this is not equivalent to true parallel execution and will be replaced.

**Warning signs:**
- Generated code calls `CompletableFuture.allOf()` for Parallel state branches
- Integration test for Parallel state "passes" by re-executing branches on retry (no checkpoint protection)
- Blueprint claims "Parallel and Map states supported" without citing the SDK version that introduced `parallel()` and `map()`

**Phase to address:**
Phase 1 (SDK mapping and code generation design). Document the limitation explicitly in the blueprint and in generated code comments.

---

### Pitfall 13: Jackson ObjectMapper — Reconfiguration After First Use Silently Fails

**What goes wrong:**
Jackson's `ObjectMapper` is thread-safe after configuration is complete. The contract is: configure once, then use from any thread. If the Lambda handler configures the ObjectMapper in the `handleRequest` method (e.g., registers a module or sets a feature), that configuration may or may not take effect depending on whether the ObjectMapper was already used earlier in the same JVM invocation (e.g., during class initialization). In Lambda replay semantics, the handler is invoked multiple times in the same JVM. A module registered on the second invocation that was missed on the first invocation results in inconsistent deserialization behavior that only appears on specific replay sequences.

**Why it happens:**
The ObjectMapper is expensive to construct (~200ms for module scanning). Developers move construction to a static field but then add configuration in the handler body. Jackson's Javadoc says configuration changes "may or may not take effect" after first use — but this failure is silent, not an exception.

**How to avoid:**
1. Construct and fully configure the `ObjectMapper` as a `static final` field at class load time: all module registrations, feature flags, and date format settings go in the static initializer.
2. Never call any configuration method (`registerModule`, `configure`, `setFeature`) on the ObjectMapper inside `handleRequest` or any method called from it.
3. For Lambda SnapStart: the ObjectMapper static initialization happens during the INIT phase, which is snapshotted. This is correct — the configuration is consistent across all restore points.
4. If different parts of the codebase need different ObjectMapper configurations, create separate `static final ObjectMapper` instances with distinct configurations — do not share one instance and reconfigure it.

**Warning signs:**
- `ObjectMapper.registerModule()` called inside the handler body
- Inconsistent JSON deserialization results across Lambda invocations (some succeed, some throw `UnrecognizedPropertyException`)
- Module-specific types (e.g., Java 8 date/time) deserialize correctly on first invocation but fall back to raw types on replay

**Phase to address:**
Phase 1 (Core infrastructure). Define ObjectMapper initialization pattern in `rsf-core` as the canonical shared instance before any module uses it.

---

### Pitfall 14: FreeMarker `<#list>` Over Empty Java Collections — Different Behavior from Jinja2 `{% for %}`

**What goes wrong:**
In Jinja2, `{% for item in none_value %}` silently renders nothing (Python's `for x in None` would raise `TypeError`, but Jinja2 protects against it). In FreeMarker, `<#list nullCollection as item>` throws `InvalidReferenceException` because `nullCollection` is null. RSF's DSL fields like `retry`, `catch`, `branches`, and `parameters` are optional — they may be null in the Java model. FreeMarker templates that iterate over these fields without null guards crash on any DSL file that omits the optional sections.

**Why it happens:**
Same root cause as Pitfall 5 (FreeMarker strict null handling) but specifically for collection iteration. Developers familiar with Jinja2's `{% for item in optional_list or [] %}` pattern have no direct FreeMarker equivalent and miss the null check.

**How to avoid:**
1. Use `<#list (state.retry)![] as policy>` — the `![]` default provides an empty list when `retry` is null, avoiding the exception.
2. Or check before iterating: `<#if state.retry??><#list state.retry as policy>...</#list></#if>`.
3. The parentheses form `(state.retry)![]` is preferred — it handles both `state` being null AND `state.retry` being null with a single expression.
4. Add a dedicated template test where every optional list field is null, not just when every field is populated.

**Warning signs:**
- `InvalidReferenceException` in FreeMarker template evaluation during code generation for DSL files that omit optional fields
- Code generation works for the full example DSL but fails for minimal DSL files
- Template test only uses a fixture that populates all fields

**Phase to address:**
Phase 2 (Code generation templates). Every template must have both a "fully populated" and a "minimal required fields only" test fixture.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Runtime classpath scanning for `@State` discovery | Zero build tooling required | 500ms–2s Lambda cold start overhead; scales poorly as handler count grows | Never in production Lambda |
| Using `List.class` instead of `TypeToken<List<Order>>(){}` for step result types | Compiles immediately | Silent `List<LinkedHashMap>` at runtime; `ClassCastException` when fields accessed | Never |
| Spring Boot in the Lambda DurableHandler | Consistent DI framework across all modules | 3–5s cold start; 20MB+ fat JAR from Spring Boot autoconfigure | Never in Lambda |
| One `ObjectMapper` instance configured lazily | Simple initialization | Inconsistent deserialization on replay; silent configuration failures | Never; configure in static field |
| Implementing Parallel state with `CompletableFuture` | Parallel state tests pass on happy path | Breaks checkpoint/replay — duplicate side effects on retry | Never; wait for SDK `parallel()` |
| Skipping `@JsonSubTypes` and relying on Jackson auto-detection | Less boilerplate | Silent `LinkedHashMap` deserialization; no error until field access | Never |
| Single flat Maven module (no multi-module structure) | Simpler initial setup | Spring Boot transitive dependencies leak into Lambda artifact; impossible to exclude cleanly | Only for throw-away prototype |
| Using `new File(relativePath)` in Maven plugin | Works in standard invocation | Breaks with `-f` flag, IDE invocation, reactor builds | Never |
| Hardcoded `Class<T>` literal for generic step results | No TypeToken boilerplate | Type erasure produces wrong runtime type | Never |
| Using Spring Boot WebSocket + STOMP for graph editor | Rich messaging abstraction | STOMP overhead in a simple bidirectional sync use case; harder to test | Only if message broker features are needed |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Java SDK `ctx.step()` with generic result | Pass `List.class` as result type | Pass `new TypeToken<List<Order>>(){}` or `new TypeReference<List<Order>>(){}` |
| Jackson `@JsonTypeInfo` on sealed interface | Omit `@JsonSubTypes` assuming auto-detection | Always pair `@JsonTypeInfo` with `@JsonSubTypes` listing all permitted subtypes |
| FreeMarker optional fields | Access `${state.retry}` without null guard | Use `${(state.retry)!""}` or `<#if state.retry??>...</#if>` |
| Jackson `JsonNode` key access | Chain `.get("a").get("b")` — NPE if "a" missing | Use `.path("a").path("b")` — returns `MissingNode`, never null |
| Maven plugin file paths | `new File(parameter)` — resolves from JVM cwd | Declare as `java.io.File` type; Maven auto-resolves from `${project.basedir}` |
| Lambda DurableHandler cold start | Include Spring Boot for DI convenience | Use plain Java wiring or Micronaut; Spring Boot cold starts are 4–8x worse |
| SnakeYAML threads | Shared `Yaml` instance across threads | SnakeYAML is NOT thread-safe; create per-thread instance or use Jackson YAML |
| Java SDK Parallel/Map states | Call `ctx.parallel()` — SDK throws `UnsupportedOperationException` | Generate stub with explicit error message; defer until SDK GA |
| Java Lambda deployment | Set `runtime = "java21"` in Terraform | Java durable functions require `package_type = "Image"` — container image deployment only |
| ObjectMapper configuration | Call `registerModule()` inside handler body | Configure in `static final` initializer block; never reconfigure after first use |
| Jackson `@JsonTypeInfo` discriminator | Use `Id.CLASS` for type information | Use `Id.NAME` with explicit names; `Id.CLASS` is a security risk and breaks on rename |
| FreeMarker list iteration over optional | `<#list state.retry as r>` where retry may be null | `<#list (state.retry)![] as r>` — null-safe empty list default |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Runtime classpath scanning on every cold start | Lambda REPORT Init Duration > 2000ms; first request latency spike | Compile-time APT registry generation | Every cold start; worse with more handler classes |
| Spring Boot in Lambda handler | Init Duration 3000–8000ms; fat JAR > 50MB | Separate modules; use plain Java or Micronaut for Lambda | Every cold start |
| New `ObjectMapper` per invocation | GC pressure; Init Duration grows with request volume | Static final ObjectMapper configured once | Under any meaningful load |
| New `Yaml` (SnakeYAML) per invocation | Same as ObjectMapper; YAML parser is expensive | Jackson YAML (which is thread-safe) or per-thread SnakeYAML instances | Under concurrent requests in web backends |
| FreeMarker `Configuration` created per generate call | Code generation slow; multiple template compilations | Static singleton `Configuration` with template cache enabled | After first few generate calls with complex templates |
| ECR image push blocking deploy pipeline | Deploy takes 5+ minutes for small code changes | Multi-stage Docker build with layer caching; separate image build from Terraform apply | Every code change without layer caching |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `@JsonTypeInfo(use = Id.CLASS)` for DSL polymorphic types | Remote code execution via crafted YAML/JSON that instantiates arbitrary classes | Always use `Id.NAME` with explicit `@JsonSubTypes` |
| SnakeYAML `new Yaml().load()` on untrusted input | SnakeYAML pre-2.0 allows arbitrary Java object construction from YAML `!!java.lang.Runtime` | Use `new Yaml(new SafeConstructor(new LoaderOptions()))` or Jackson YAML (which is safe by default) |
| Hardcoded AWS account ID in generated Terraform templates | Account ID exposed in committed code | Use `data.aws_caller_identity.current.account_id` |
| Generated handler stubs logging full input event | Sensitive workflow payload appears in CloudWatch logs | Emit only state name and execution ID by default; truncate payload logs |

---

## "Looks Done But Isn't" Checklist

- [ ] **Type erasure in step results:** Generated code uses `TypeToken`/`TypeReference` for all parameterized result types — not raw `.class` literals. Verify with a step that returns `List<T>` and asserts the element type.
- [ ] **Jackson polymorphic DSL types:** Every sealed interface / abstract DSL class has both `@JsonTypeInfo` AND `@JsonSubTypes` with all subtypes listed. Verify with a round-trip test for every state type.
- [ ] **FreeMarker null guards:** Every optional field access in every template uses `!` default or `??` existence check. Verify by running code generation against a minimal DSL file with all optional fields absent.
- [ ] **FreeMarker list null guards:** Every `<#list>` over an optional collection uses `(collection)![]` form. Verify with a DSL state that has no Retry, no Catch, no Parameters.
- [ ] **JSONPath null safety:** JSONPath evaluator uses `JsonNode.path()` (not `.get()`) for all key access. Verify with a pipeline test where the first key in a chain is missing.
- [ ] **Lambda handler module — no Spring Boot:** Run `mvn dependency:tree` on the Lambda handler module and verify Spring Boot is absent. Verify fat JAR size is under 30MB.
- [ ] **ObjectMapper configured statically:** Search the Lambda handler module for any `objectMapper.configure()`, `objectMapper.registerModule()`, or `new ObjectMapper()` outside of a `static {}` block. There should be none.
- [ ] **Container image deployment in Terraform:** Generated Terraform for the Java Lambda uses `package_type = "Image"`, not `runtime = "java21"`. ECR repository resource is present.
- [ ] **Parallel/Map state stubs:** Generated code for Parallel and Map states throws `UnsupportedOperationException` with a clear message, not a no-op or a `CompletableFuture` workaround.
- [ ] **Maven plugin file paths:** All `@Parameter` file path annotations use `java.io.File` type. Zero `new File(stringParam)` calls in Mojo implementations.
- [ ] **SnakeYAML thread safety:** If SnakeYAML is used in web backends (which handle concurrent requests), `Yaml` instance is NOT shared across threads. Verify with a concurrent request test.
- [ ] **SDK version pinned:** The Java SDK version is pinned explicitly in the root POM `<dependencyManagement>` — no `LATEST` or `-SNAPSHOT`. The version is cited with a changelog reference.
- [ ] **Golden-file tests for templates:** Every FreeMarker template has at least one golden-file test with committed expected output. A whitespace-only change in a template triggers a test failure.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Runtime classpath scanning discovered in production | HIGH | Rewrite handler registration to APT-generated registry; rebuild and redeploy all Lambda images |
| Type erasure causing `ClassCastException` in step results | MEDIUM | Replace `.class` with `TypeToken`/`TypeReference` in all affected generated templates; regenerate and redeploy |
| Wrong Jackson version in Lambda JAR (Spring Boot conflict) | MEDIUM | Add explicit `<dependencyManagement>` version pin in root POM; run `dependency:tree` to verify; rebuild |
| FreeMarker null crash in production DSL file | LOW | Add null guard to specific template location; regenerate code; redeploy |
| Maven plugin resolving wrong file path | LOW | Change `@Parameter` to `File` type; bump plugin version; re-run generate |
| Parallel state faked with CompletableFuture (discovered after deployment) | HIGH | Rewrite Parallel state code generation using SDK `parallel()` once available; re-test all workflows using Parallel states |
| Container image deployment missing from Terraform | MEDIUM | Add ECR repository and image-based Lambda config to Terraform; first deploy will recreate the function |
| ObjectMapper configured inside handler (inconsistent behavior) | MEDIUM | Move all configuration to static initializer; requires Lambda redeployment |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Java SDK `parallel`/`map` not available | Phase 0 — SDK feature audit | SDK feature matrix documented; Parallel/Map stubs emit `UnsupportedOperationException` |
| Container image only deployment for Java | Phase 0 — SDK feature audit | Terraform templates use `package_type = Image`; no `runtime = java*` for durable Lambda |
| Type erasure in step results | Phase 1 — SDK integration & type mapping | Round-trip test: step returning `List<Order>` deserializes to `List<Order>`, not `List<LinkedHashMap>` |
| Jackson polymorphic deserialization | Phase 1 — DSL model design | Round-trip test for every state type: serialize then deserialize; assert concrete class |
| FreeMarker null safety | Phase 2 — Code generation templates | Minimal-fixture test: generate code from DSL with all optional fields absent; no exception |
| FreeMarker whitespace artifacts | Phase 2 — Code generation templates | Golden-file test: committed expected output; any whitespace change fails CI |
| FreeMarker list null guards | Phase 2 — Code generation templates | Minimal-fixture test: state with no Retry/Catch/Parameters; no `InvalidReferenceException` |
| Handler registry via classpath scanning | Phase 1 — Handler registry design | Lambda REPORT Init Duration < 500ms with 10+ registered handlers; no `ClassGraph` in production JAR |
| Spring Boot in Lambda handler | Phase 1 — Maven multi-module structure | `mvn dependency:tree` on Lambda module shows no `spring-boot-autoconfigure` |
| JSONPath null safety | Phase 1 — I/O pipeline implementation | Pipeline test: evaluate `$.missing.key` on `{}`; throws `JSONPathError`, not `NullPointerException` |
| Maven multi-module version conflicts | Phase 0 — Maven skeleton | `mvn dependency:tree -Dincludes=com.fasterxml.jackson` shows single version across all modules |
| Maven plugin path resolution | Phase 3 — Maven plugin development | Plugin test with `-f subdir/pom.xml` invocation; files created in correct directory |
| Preview SDK API stability risk | Ongoing — SDK version pinning | SDK version pinned in root POM; release notes reviewed before each upgrade |
| ObjectMapper configuration after first use | Phase 1 — Core infrastructure | Static analysis: grep for `objectMapper.configure()` outside `static {}` block returns zero results |

---

## Sources

- [AWS Lambda Durable Execution SDK for Java Developer Preview Announcement](https://aws.amazon.com/about-aws/whats-new/2026/02/lambda-durable-execution-java-preview/) — HIGH confidence (official AWS announcement, February 2026)
- [AWS Lambda Durable Functions — Supported Runtimes](https://docs.aws.amazon.com/lambda/latest/dg/durable-supported-runtimes.html) — HIGH confidence (official AWS docs; Java container-only, `parallel`/`map`/`waitForCondition`/`waitForCallback` still in development)
- [AWS Lambda Durable Execution SDK — Official Docs](https://docs.aws.amazon.com/lambda/latest/dg/durable-execution-sdk.html) — HIGH confidence (Java DurableHandler/DurableContext API reference)
- [Jackson Polymorphic Deserialization Wiki](https://github.com/FasterXML/jackson-docs/wiki/JacksonPolymorphicDeserialization) — HIGH confidence (official FasterXML documentation)
- [@JsonSubTypes vs Reflections for Polymorphic Deserialization](https://www.baeldung.com/java-jackson-polymorphic-deserialization) — MEDIUM confidence (Baeldung, multiple confirmed patterns)
- [Super Type Tokens in Java Generics](https://www.baeldung.com/java-super-type-tokens) — HIGH confidence (Baeldung, TypeToken / TypeReference pattern)
- [Jackson TypeReference for Generic Deserialization](https://medium.com/@poojaauma/enhancing-deserialization-safety-in-java-with-typereference-ea110ece6994) — MEDIUM confidence (community article, pattern verified against Jackson docs)
- [FreeMarker White-Space Handling](https://freemarker.apache.org/docs/dgui_misc_whitespace.html) — HIGH confidence (official FreeMarker documentation)
- [FreeMarker InvalidReferenceException and Null Handling](https://copyprogramming.com/howto/freemarker-the-following-has-evaluated-to-null-or-missing) — MEDIUM confidence (multiple community sources; FreeMarker official FAQ confirms behavior)
- [Maven Plugin Common Bugs and Pitfalls](https://maven.apache.org/plugin-developers/common-bugs.html) — HIGH confidence (official Maven documentation; File path resolution documented explicitly)
- [Java Lambda Cold Start Optimization](https://www.capitalone.com/tech/cloud/aws-lambda-java-tutorial-reduce-cold-starts/) — MEDIUM confidence (Capital One engineering blog; classpath scanning overhead figures consistent across multiple sources)
- [Jackson ObjectMapper Thread Safety](https://www.baeldung.com/java-jackson-objectmapper-static-field) — HIGH confidence (Baeldung; ObjectMapper Javadoc confirms thread-safety contract)
- [Common Pitfalls When Writing Maven Plugins](https://javanexus.com/blog/maven-plugin-pitfalls-avoidance) — MEDIUM confidence (community article from August 2024)
- [Common Pitfalls of Java Annotation Processors](https://medium.com/@tobias.stamann/common-pitfalls-of-implementing-java-annotation-processors-and-how-to-avoid-them-e48e99671033) — MEDIUM confidence (community article; split-module pattern verified against official APT guide)
- [Jackson JsonNode null handling issue (MissingNode vs null)](https://github.com/FasterXML/jackson-databind/issues/3389) — HIGH confidence (official GitHub issue confirming `.get()` returns null, `.path()` returns MissingNode)
- [SnakeYAML thread safety and pitfalls](https://snyk.io/blog/java-yaml-parser-with-snakeyaml/) — HIGH confidence (Snyk security advisory; thread safety issue confirmed in SnakeYAML Javadoc)
- [Lambda SnapStart — Static State Pitfalls](https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html) — HIGH confidence (official AWS docs; UUID/random/timestamp uniqueness during init is documented as the primary SnapStart gotcha)
- [RSF Project — PROJECT.md](.planning/PROJECT.md) — HIGH confidence (source of truth for current Python implementation details)

---

*Pitfalls research for: Java port of RSF using AWS Lambda Durable Execution SDK for Java (Preview)*
*Researched: 2026-02-28*
