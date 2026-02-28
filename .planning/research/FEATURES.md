# Feature Research

**Domain:** Java port of RSF (Replacement for Step Functions) — porting all Python RSF functionality to Java using the AWS Lambda Durable Execution SDK for Java (Preview)
**Researched:** 2026-02-28
**Confidence:** MEDIUM-HIGH (Java SDK is in Developer Preview as of February 2026; Java ecosystem equivalents are HIGH confidence; SDK-specific Java API details are MEDIUM confidence based on GitHub inspection and official announcements)

---

## Context: This Is a Port Blueprint Milestone

RSF v1.4 is complete. The full Python implementation covers 14+ components. This milestone (v1.6) produces RSF-BUILDPRINT-JAVA.md — a comprehensive blueprint document that answers: "How do all 14 RSF components map to idiomatic Java?" No Java code is shipped in this milestone; the output is a blueprint that guides a future Java implementation.

The feature map below answers the question component by component: what is the Python feature, what is the exact Java equivalent, what is the complexity of porting, and what dependencies between components exist.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features a credible Java RSF implementation must have. Missing any means Java RSF cannot function.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| DSL Models: Jackson DTOs with @JsonTypeInfo/@JsonSubTypes discriminated unions | Pydantic v2 discriminated unions are the DSL's type system; without a Java equivalent, YAML/JSON parsing cannot work | HIGH | Python uses `discriminator="Type"` on a `Union[TaskState, PassState, ...]`; Java uses `@JsonTypeInfo(use=NAME, property="Type")` + `@JsonSubTypes` on a sealed interface `StateDefinition`; Java 17 sealed interfaces enable exhaustive `switch` pattern matching; Jackson 2.x requires explicit `@JsonSubTypes` list; Jackson 3.x auto-detects sealed class subtypes |
| Code Generator: FreeMarker templates producing DurableHandler Java classes | The code generator is RSF's primary output; without it, users cannot generate Lambda code from DSL | HIGH | Python uses Jinja2 with `create_environment()` and custom `topyrepr` filter; Java uses FreeMarker 2.3.34 (`org.freemarker:freemarker:2.3.34`); FreeMarker `Configuration` uses `setTagSyntax(SQUARE_BRACKET_TAG_SYNTAX)` to avoid `<` conflicts with generics in Java source templates; custom directives replace Jinja2 filters |
| Handler Registry: @State/@Startup annotations + classpath scanning | The registry connects generated orchestrator code to user handler methods; without it, generated code cannot call handlers | MEDIUM | Python uses `@state("StateName")` decorator + `discover_handlers(directory)`; Java uses custom `@State(name="StateName")` annotation + Spring `ClassPathScanningCandidateComponentProvider` or `Reflections` library scanning; alternatively, a compile-time APT approach with `javax.annotation.processing.AbstractProcessor` generates a registry class; classpath scanning preferred for runtime discovery matching Python behavior |
| 5-Stage I/O Pipeline: InputPath → Parameters → ResultSelector → ResultPath → OutputPath using Jackson JsonNode | I/O pipeline transforms are the core data flow mechanism; all 5 stages must work correctly in Java | HIGH | Python uses `jsonpath-ng` for JSONPath evaluation; Java uses Jayway `JsonPath` library with `JacksonJsonNodeJsonProvider` for JSONPath evaluation on `JsonNode` trees; all 5 stage functions map directly: `evaluateJsonPath()`, `applyPayloadTemplate()`, `applyResultPath()`; critical invariant preserved: ResultPath merges into raw input, not effective input |
| Intrinsic Functions: 18 functions with recursive descent parser | All 18 intrinsic functions (States.Format, States.Array, States.MathAdd, etc.) must evaluate correctly | HIGH | Python uses `_Parser` class with recursive `parse_expression(depth)`; Java maps identically: `IntrinsicParser` class with `parseExpression(int depth)` method; function registry uses `Map<String, IntrinsicFunction>` where `IntrinsicFunction` is a `@FunctionalInterface`; no external parser library needed — the grammar is simple enough for a hand-written recursive descent parser |
| CLI Toolchain: Picocli with 7 subcommands (init, generate, validate, deploy, import, ui, inspect) | Users expect a CLI interface matching the Python `rsf` command | MEDIUM | Python uses Typer with one `@app.command()` per subcommand; Java uses Picocli 4.7.7 with `@Command(name="rsf", subcommands={Init.class, Generate.class, ...})`; each subcommand is an annotated class implementing `Callable<Integer>`; Rich console output maps to Picocli's built-in `@Spec CommandSpec` with `spec.commandLine().getOut()` for colored output via Jansi |
| ASL JSON Importer: Jackson-based parsing + same conversion rules | Users import existing AWS Step Functions definitions; must produce identical RSF YAML output | MEDIUM | Python uses `json.load()` + dict manipulation + `yaml.dump()`; Java uses `ObjectMapper.readTree()` producing `JsonNode` + tree manipulation + SnakeYAML `DumperOptions` for YAML emission; all 6 conversion rules map directly (inject rsf_version, reject Resource, strip Fail I/O, rename Iterator→ItemProcessor, warn on distributed Map fields, recurse on Parallel/Map) |
| Terraform HCL Generator: FreeMarker templates with square-bracket syntax | Terraform HCL generation is needed for deploy command; same 6 `.tf` file types must be generated | MEDIUM | Python uses Jinja2 with custom delimiters `<< >>` / `<% %>` to avoid `${}` HCL conflict; Java uses FreeMarker with `setTagSyntax(SQUARE_BRACKET_TAG_SYNTAX)` and `setInterpolationSyntax(SQUARE_BRACKET_INTERPOLATION_SYNTAX)` — same strategy, FreeMarker natively supports square-bracket mode; Generation Gap pattern (first-line marker `// DO NOT EDIT`) preserved identically |
| UI Backends: Spring Boot with @RestController, WebSocket (STOMP), SseEmitter | Graph editor and execution inspector require HTTP backends | HIGH | Python uses FastAPI + uvicorn; Java uses Spring Boot 3.x with `@RestController`, `@EnableWebSocketMessageBroker` with STOMP for graph editor bidirectional sync, `SseEmitter` for inspector live updates; static file serving via `ResourceHttpRequestHandler`; token bucket rate limiter maps to `RateLimiter` from Guava or custom `AtomicLong`-based implementation |
| Mock SDK: Implements DurableContext interface for local testing | Local testing without AWS requires a mock DurableContext; without it, unit tests cannot run | MEDIUM | Python provides `MockDurableContext` implementing the Python SDK interface; Java provides `MockDurableContext` implementing the `DurableContext` interface from `software.amazon.lambda.durable`; `DurableFuture<T>` mock wraps a `CompletableFuture<T>` that resolves immediately |
| Semantic Validator: BFS cross-state validator with Jakarta Bean Validation | Pydantic model-level validators and BFS semantic validator both must work in Java | MEDIUM | Python uses Pydantic `@model_validator(mode="after")` for field-level and `validate_definition(definition)` BFS traversal for cross-state; Java uses Jakarta Bean Validation (`jakarta.validation` 3.x) with `@NotNull`, `@AssertTrue` for field-level, and a separate `WorkflowValidator` class for BFS cross-state validation; 6 validation rules (dangling references, unreachable states, no terminal, States.ALL ordering, recursive Parallel/Map) map directly to Java BFS |
| JSON Schema Generation: victools jsonschema-generator from Jackson DTOs | Monaco editor in the graph editor requires a JSON Schema; must be generated from Java models | LOW | Python uses `pydantic.model_json_schema()`; Java uses `victools/jsonschema-generator` 4.x (`com.github.victools:jsonschema-generator` + `jsonschema-module-jackson`); generates Draft 2019-09 or 2020-12 from annotated Jackson DTOs; `@JsonTypeInfo`/`@JsonSubTypes` annotations are automatically respected |

### Differentiators (Competitive Advantage)

Features specific to the Java port that go beyond a straight translation and add value for Java users.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Java sealed interface for StateDefinition with pattern-matching switch | Exhaustive compile-time checking of all 8 state types; Pydantic's discriminated union provides runtime safety, Java sealed interface provides compile-time safety | LOW | `sealed interface StateDefinition permits TaskState, PassState, ChoiceState, WaitState, ParallelState, MapState, SucceedState, FailState` enables `switch (state) { case TaskState t -> ...; }` with compiler-enforced exhaustiveness; significantly better than Python's runtime `isinstance` dispatch |
| Maven multi-module layout with clear module boundaries | Java projects benefit from explicit module separation; enforces architectural boundaries that Python packages only suggest | MEDIUM | Parent POM + modules: `rsf-dsl` (Jackson models), `rsf-codegen` (FreeMarker), `rsf-cli` (Picocli), `rsf-runtime` (handler registry + I/O pipeline), `rsf-ui-server` (Spring Boot), `rsf-testing` (Mock SDK); Maven dependency graph enforces layering; `rsf-cli` and `rsf-ui-server` depend on all others; `rsf-dsl` has zero dependencies on framework code |
| Annotation Processing (APT) option for handler registry | Compile-time registry generation avoids classpath scanning overhead; useful for GraalVM native image compilation | HIGH | Standard Java `AbstractProcessor` generates `HandlerRegistry.java` at compile time from `@State` annotations; eliminates reflection at runtime; enables GraalVM native-image compatibility for faster cold starts — especially valuable given Lambda's cold start sensitivity |
| Java records for immutable DSL value objects | Java 16+ records provide concise, immutable value objects for sub-models like RetryPolicy, Catcher, ChoiceRule | LOW | Replace Python `@dataclass` models that are effectively immutable with Java records: `record RetryPolicy(List<String> errorEquals, int maxAttempts, double backoffRate) {}`; records auto-generate equals/hashCode/toString; Jackson supports records natively since Jackson 2.12 |
| TypeToken for generic DurableFuture type safety | Java's type erasure requires TypeToken to preserve `List<User>` generics at deserialization; Python has no equivalent problem | LOW | Java SDK `TypeToken` usage: `ctx.step("FetchUsers", this::fetchUsers, new TypeToken<List<User>>(){})` preserves full generic type at deserialization; Python SDK has no equivalent because Python has no type erasure; blueprint must document TypeToken usage patterns for Map and Parallel results |
| Spring Boot Actuator for UI backend health/metrics | FastAPI has no health endpoint by default; Spring Boot Actuator adds `/actuator/health` and `/actuator/metrics` with zero configuration | LOW | Add `spring-boot-starter-actuator` to `rsf-ui-server`; exposes `/actuator/health` for load balancer probes and `/actuator/metrics` for monitoring; equivalent Python setup would require manual FastAPI route |
| GraalVM native-image profile for CLI tool | CLI tools benefit from instant startup; Java's JVM startup is a liability for CLI tools | HIGH | Add `native-maven-plugin` with `spring-aot` or standalone GraalVM metadata; eliminates JVM startup overhead; requires reflection config for Jackson + FreeMarker; only feasible if APT-based registry is used (no runtime classpath scanning); defer to future Java implementation — blueprint notes feasibility |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem useful for the Java port but create disproportionate cost or risk.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Spring DI container in the generated Lambda handler | Spring Boot is the dominant Java framework; developers expect it | Lambda cold start: Spring Boot context initialization adds 2-5 seconds to cold start; DurableHandler already provides its own lifecycle; mixing two lifecycle systems creates complexity | Use plain Java in generated handlers; Spring Boot only in the UI server modules; generated `DurableHandler` subclasses use direct constructor injection |
| Kotlin as the implementation language for RSF-Java | Kotlin is increasingly popular; coroutines map naturally to durable steps | The blueprint targets Java; introducing Kotlin adds a second language, build complexity, and reader unfamiliarity for teams that chose Java specifically; coroutines ≠ `DurableFuture` | Java 17+ with records, sealed interfaces, and pattern matching provides sufficient modern syntax; Kotlin is a valid future direction but a separate blueprint |
| Hibernate/JPA for any persistence | Java developers reflexively reach for JPA | RSF generates Lambda code with no persistence layer; DSL models are pure in-memory objects; adding JPA implies database, schema migrations, connection pools — none of which RSF needs | Use Jackson ObjectMapper for all serialization/deserialization; no persistence needed |
| Full Spring Data REST for UI backends | Automatic REST from JPA repositories is convenient | The inspector backend is a thin proxy over AWS Lambda APIs; it has no entities to persist; Spring Data REST adds JPA + Hibernate + datasource config with no benefit | Plain `@RestController` + service classes calling AWS SDK v2; minimal Spring Boot slice |
| Separate microservice per RSF component | Enterprise Java shops deploy microservices | RSF is a local developer tool; splitting into microservices adds network overhead, service discovery, and deployment complexity for zero user benefit | Single JAR per tool command; multi-module Maven separates code boundaries without requiring separate deployments |
| XMLMapper alongside ObjectMapper | Java's Jackson supports XML; some teams want XML DSL support | RSF's DSL is YAML/JSON; XML support would require a new parser, new schema, new docs, and new tests for a format nobody asked for | YAML (via `jackson-dataformat-yaml`) + JSON (via `ObjectMapper`) only; match the Python implementation's supported formats |
| Runtime Jinja2 → Java port (JINJAVA) | Jinja2 templates already exist; JINJAVA would reduce rewriting | JINJAVA (HubSpot's Jinja2-for-Java) replicates Jinja2 semantics but is a third-party library with limited maintenance; FreeMarker is the idiomatic Java template engine with Spring integration, wider adoption, and a stable API | Rewrite templates in FreeMarker; the templates are small (< 300 lines each) and the FTL syntax is straightforward |

---

## Feature Dependencies

```
[DSL Models (Jackson sealed interface)]
    └──required by──> [Code Generator (FreeMarker)]
    └──required by──> [Semantic Validator (BFS)]
    └──required by──> [ASL Importer (Jackson parse → DSL models)]
    └──required by──> [JSON Schema Generator (victools)]
    └──required by──> [YAML Parser (jackson-dataformat-yaml)]

[I/O Pipeline (Jackson JsonNode + Jayway JsonPath)]
    └──required by──> [Code Generator] (generated code calls pipeline at runtime)
    └──required by──> [Mock SDK] (mock context must run pipeline for test accuracy)

[Intrinsic Function Parser (recursive descent)]
    └──required by──> [I/O Pipeline] (Parameters/ResultSelector template evaluation)
    └──required by──> [Code Generator] (intrinsic calls generated into orchestrator)

[Handler Registry (@State annotation + classpath scanning)]
    └──required by──> [Code Generator] (generated orchestrator calls registry.getHandler())
    └──required by──> [Mock SDK] (mock context discovers handlers for local test)

[Mock SDK (MockDurableContext)]
    └──required by──> [Test Suite] (unit tests for generated orchestrator code)

[Semantic Validator (BFS)]
    └──required by──> [CLI validate command]
    └──required by──> [CLI generate command] (validate before generating)

[ASL Importer]
    └──required by──> [CLI import command]

[Terraform HCL Generator (FreeMarker)]
    └──required by──> [CLI deploy command]

[UI Backends (Spring Boot)]
    └──required by──> [CLI ui command] (graph editor)
    └──required by──> [CLI inspect command] (execution inspector)
    └──depends on──> [JSON Schema Generator] (editor serves /api/schema)
    └──depends on──> [DSL Models] (editor parses YAML → DSL models)

[CLI (Picocli)]
    └──depends on──> [All other components] (CLI is the integration layer)

[Maven multi-module layout]
    └──enforces boundaries──> [All component dependencies above]
    (rsf-dsl has no framework deps; rsf-runtime depends on rsf-dsl;
     rsf-ui-server depends on rsf-dsl + rsf-runtime; rsf-cli depends on all)
```

### Dependency Notes

- **DSL Models are the foundation:** Every other component depends on `StateMachineDefinition` and its state types; define the Jackson sealed interface hierarchy first; all other work can proceed in parallel after that.

- **I/O Pipeline requires Jayway JsonPath with Jackson provider:** The Python `jsonpath-ng` library and Java Jayway `JsonPath` with `JacksonJsonNodeJsonProvider` behave identically for the subset of JSONPath used by ASL (`$`, `$.field`, `$[*]`); verify `$$.` context reference handling separately since it is RSF-specific.

- **Intrinsic parser is self-contained:** No external dependencies beyond Jackson for JSON literal parsing; Java functional interfaces (`@FunctionalInterface`) replace Python callable types directly; the recursive descent algorithm translates line-for-line from Python.

- **Handler registry has two valid Java strategies:** Classpath scanning (runtime, matches Python behavior, simpler) vs APT (compile-time, faster cold start, GraalVM-compatible); blueprint should document both; recommend classpath scanning for the initial port, APT as an optimization path.

- **UI backends depend on all DSL components:** Spring Boot `@RestController` for `/api/schema` must call the JSON schema generator; WebSocket handler must parse YAML using DSL models; these make Spring Boot the highest-dependency component.

---

## MVP Definition

### Launch With (Blueprint v1.6)

The blueprint document (RSF-BUILDPRINT-JAVA.md) is the deliverable. It must cover:

- [ ] DSL Models: Jackson DTO hierarchy with sealed interface, @JsonTypeInfo, @JsonSubTypes, Java records for sub-models — why this maps to Pydantic discriminated unions
- [ ] Code Generator: FreeMarker 2.3.34 setup, square-bracket tag syntax config, template structure for orchestrator + handler stubs, `toJavaLiteral()` filter equivalent
- [ ] Handler Registry: @State/@Startup annotation definition, ClassPathScanningCandidateComponentProvider usage, comparison to Python `@state` decorator + `discover_handlers()`
- [ ] I/O Pipeline: Jayway JsonPath + JacksonJsonNodeJsonProvider setup, 5-stage pipeline implementation, ResultPath merge invariant preservation
- [ ] Intrinsic Functions: `@FunctionalInterface IntrinsicFunction`, `Map<String, IntrinsicFunction>` registry, recursive descent `IntrinsicParser` class skeleton
- [ ] CLI: Picocli @Command + @Option + @Parameters for all 7 subcommands, Jansi for colored terminal output
- [ ] ASL Importer: Jackson `ObjectMapper.readTree()` + `JsonNode` manipulation + SnakeYAML emission, all 6 conversion rules
- [ ] Terraform Generator: FreeMarker square-bracket syntax setup, 6 template files, Generation Gap pattern in Java
- [ ] UI Backends: Spring Boot 3.x @RestController, STOMP WebSocket config, SseEmitter pattern, Guava RateLimiter for token bucket
- [ ] Mock SDK: MockDurableContext implementing DurableContext, step/wait/parallel/map stubs that execute immediately
- [ ] Validation: Jakarta Bean Validation annotations, BFS semantic validator class structure
- [ ] JSON Schema Gen: victools jsonschema-generator 4.x setup, integration with Jackson annotations
- [ ] Maven multi-module structure: parent POM + 6 module layout, dependency graph
- [ ] Testing strategy: JUnit 5.10+, Mockito 5.x, AssertJ 3.x; unit test patterns for each component

### Add After Validation (Post-Blueprint)

Features to add when actual Java implementation begins:

- [ ] GraalVM native-image profile for CLI — add when JVM cold start is measured to be a problem
- [ ] APT-based compile-time handler registry — add as optimization after classpath scanning works
- [ ] Spring Boot Actuator health/metrics endpoints — add when UI backends are implemented

### Future Consideration (v2+)

Deferred because they are Java-implementation concerns, not blueprint concerns:

- [ ] Java integration test harness against real AWS — defer until Java implementation is complete; reuse Python harness patterns
- [ ] Kotlin port of RSF-Java — defer; separate blueprint needed
- [ ] GraalVM native-image for full CLI — defer; requires APT registry first

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| DSL Models (Jackson sealed interface) | HIGH | HIGH | P1 |
| Code Generator (FreeMarker) | HIGH | HIGH | P1 |
| Handler Registry (@State annotation) | HIGH | MEDIUM | P1 |
| I/O Pipeline (Jayway JsonPath) | HIGH | HIGH | P1 |
| Intrinsic Functions (recursive descent) | HIGH | HIGH | P1 |
| CLI (Picocli 7 commands) | HIGH | MEDIUM | P1 |
| ASL Importer (Jackson) | MEDIUM | MEDIUM | P1 |
| Terraform HCL Generator (FreeMarker) | MEDIUM | MEDIUM | P1 |
| UI Backends (Spring Boot) | MEDIUM | HIGH | P1 |
| Mock SDK (MockDurableContext) | HIGH | MEDIUM | P1 |
| Semantic Validator (BFS) | HIGH | MEDIUM | P1 |
| JSON Schema Generator (victools) | MEDIUM | LOW | P1 |
| Maven multi-module layout | HIGH | LOW | P1 |
| Testing strategy (JUnit 5 / Mockito / AssertJ) | HIGH | LOW | P1 |
| Java sealed interface differentiator | MEDIUM | LOW | P2 |
| Java records for sub-models | MEDIUM | LOW | P2 |
| APT compile-time handler registry | LOW | HIGH | P3 |
| GraalVM native-image profile | LOW | HIGH | P3 |
| Spring Boot Actuator | LOW | LOW | P2 |

**Priority key:**
- P1: Must appear in the blueprint document
- P2: Should be mentioned as an idiomatic Java enhancement
- P3: Note as a future optimization path, do not blueprint in detail

---

## Component-by-Component Java Mapping

This section is the core research for the blueprint. It answers "Python X → Java Y" for each component.

### 1. DSL Models

| Python (Pydantic v2) | Java Equivalent | Confidence |
|---------------------|-----------------|------------|
| `class TaskState(BaseModel)` with `type: Literal["Task"]` | `record TaskState(...) implements StateDefinition` | HIGH |
| `Union[TaskState, PassState, ...]` discriminated by `Type` field | `@JsonTypeInfo(use=NAME, property="Type") sealed interface StateDefinition permits ...` | HIGH |
| `Field(alias="Next")` | `@JsonProperty("Next")` | HIGH |
| `model_config = {"extra": "forbid"}` | `@JsonIgnoreProperties(ignoreUnknown=false)` or fail on unknown properties via `DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES` | HIGH |
| `@model_validator(mode="after")` for field cross-checks | Custom `@AssertTrue` method or `ConstraintValidator<TaskState, TaskState>` | MEDIUM |
| `list[RetryPolicy]` | `List<RetryPolicy>` where `RetryPolicy` is a Java record | HIGH |
| `dict[str, Any]` for Parameters/Assign/Output | `Map<String, Object>` or `JsonNode` (prefer `JsonNode` for nested intrinsic function preservation) | HIGH |

**Key decision:** Use Java sealed interfaces rather than abstract classes. Sealed interfaces permit exhaustive `switch` pattern matching in the BFS validator and code generator, providing compile-time safety the Python version cannot offer.

### 2. Code Generator (FreeMarker)

| Python (Jinja2) | Java Equivalent | Confidence |
|----------------|-----------------|------------|
| `Environment(loader=FileSystemLoader(...))` | `Configuration cfg = new Configuration(VERSION_2_3_34); cfg.setDirectoryForTemplateLoading(templatesDir)` | HIGH |
| Custom `{{ VAR }}` delimiters / `<< >>` for HCL | `cfg.setTagSyntax(SQUARE_BRACKET_TAG_SYNTAX)` + `cfg.setInterpolationSyntax(SQUARE_BRACKET_INTERPOLATION_SYNTAX)` | HIGH |
| `env.filters["topyrepr"]` custom filter | `cfg.setSharedVariable("toJavaLiteral", new ToJavaLiteralMethod())` implementing `TemplateMethodModelEx` | MEDIUM |
| `template.render(**kwargs)` | `Template t = cfg.getTemplate("orchestrator.java.ftl"); t.process(dataModel, writer)` | HIGH |
| `GENERATED_MARKER = "# DO NOT EDIT"` | `// DO NOT EDIT — Generated by RSF` as first line; same Generation Gap pattern | HIGH |
| BFS state traversal for generation order | Same `ArrayDeque<String>` BFS in Java | HIGH |

**Template file extension:** Use `.ftl` (FreeMarker standard). Template files: `orchestrator.java.ftl`, `handler_stub.java.ftl`, `backend.tf.ftl`, `main.tf.ftl`, etc.

### 3. Handler Registry

| Python | Java Equivalent | Confidence |
|--------|-----------------|------------|
| `@state("ValidateOrder")` decorator | `@State(name = "ValidateOrder")` custom annotation on a class or method | HIGH |
| `@startup` decorator | `@Startup` custom annotation | HIGH |
| `_handlers: dict[str, Callable]` global dict | `Map<String, StateHandler>` where `StateHandler` is a `@FunctionalInterface` | HIGH |
| `discover_handlers(directory)` | `ClassPathScanningCandidateComponentProvider` scanning for `@State` annotation, or `Reflections` library | MEDIUM |
| `get_handler(name)` | `registry.getHandler(name)` returning `StateHandler` | HIGH |

**Recommended approach:** Use `org.reflections:reflections:0.10.2` for classpath scanning (simpler than Spring's `ClassPathScanningCandidateComponentProvider` without requiring a Spring context). For Spring-based handlers: `@Component` + custom annotation on method, discovered via `ApplicationContext.getBeansWithAnnotation()`.

### 4. I/O Pipeline

| Python | Java Equivalent | Confidence |
|--------|-----------------|------------|
| `jsonpath-ng` library | `com.jayway.jsonpath:json-path:2.9.0` with `JacksonJsonNodeJsonProvider` | HIGH |
| `evaluate_jsonpath(data, path)` | `JsonPath.using(config).parse(jsonNode).read(path, JsonNode.class)` | HIGH |
| `apply_payload_template(template, data, ...)` | Same logic: iterate `Map<String, Object>`, detect `.$` suffix for JSONPath resolution, detect `States.` prefix for intrinsic evaluation | HIGH |
| `apply_result_path(raw, result, path)` | Same merge logic using Jackson `ObjectNode.set(field, resultNode)` | HIGH |
| `VariableStoreProtocol` | `interface VariableStore { JsonNode get(String name); void set(String name, JsonNode value); }` | HIGH |

**JSONPath config:**
```java
Configuration config = Configuration.builder()
    .jsonProvider(new JacksonJsonNodeJsonProvider())
    .mappingProvider(new JacksonMappingProvider())
    .build();
```

### 5. Intrinsic Functions

| Python | Java Equivalent | Confidence |
|--------|-----------------|------------|
| `@intrinsic("States.Format")` decorator | `registry.register("States.Format", (args) -> statesFormat(args))` | HIGH |
| `_REGISTRY: dict[str, Callable]` | `Map<String, IntrinsicFunction>` where `@FunctionalInterface interface IntrinsicFunction { Object apply(List<Object> args); }` | HIGH |
| `class _Parser` with `parse_expression(depth)` | `class IntrinsicParser` with `Object parseExpression(int depth)` | HIGH |
| `evaluate_intrinsic(expression, data, context, variables)` | `IntrinsicEvaluator.evaluate(String expression, JsonNode data, ContextObject context, VariableStore variables)` | HIGH |
| 18 function implementations in `array.py`, `string.py`, `math.py`, `encoding.py`, `json_funcs.py`, `utility.py` | Same split: `ArrayFunctions.java`, `StringFunctions.java`, etc.; all registered in `IntrinsicRegistry` | HIGH |

### 6. CLI (Picocli)

| Python (Typer) | Java Equivalent (Picocli) | Confidence |
|----------------|--------------------------|------------|
| `app = typer.Typer(name="rsf", help="...")` | `@Command(name="rsf", mixinStandardHelpOptions=true, subcommands={Init.class, Generate.class, ...})` | HIGH |
| `@app.command(name="generate")` | Separate class `@Command(name="generate") class Generate implements Callable<Integer>` | HIGH |
| `typer.Option(...)` | `@Option(names={"--output", "-o"}, description="...")` | HIGH |
| `typer.Argument(...)` | `@Parameters(index="0", description="...")` | HIGH |
| `rich.console.Console()` for colored output | `CommandLine.Help.Ansi.AUTO.string(...)` or Jansi `Ansi.ansi()` | MEDIUM |
| `raise typer.Exit(0)` | `return 0` from `Callable<Integer>` | HIGH |
| Entry point: `app()` | `System.exit(new CommandLine(new RsfCli()).execute(args))` | HIGH |

**Maven shade plugin:** Use `maven-shade-plugin` to produce a fat JAR with a manifest `Main-Class` for direct `java -jar rsf.jar` execution.

### 7. ASL Importer

| Python | Java Equivalent | Confidence |
|--------|-----------------|------------|
| `json.load(file)` | `objectMapper.readTree(file)` returning `JsonNode` | HIGH |
| Dict manipulation via `dict.pop()`, `dict["key"] = value` | `ObjectNode.remove(field)`, `ObjectNode.put(field, value)` | HIGH |
| `yaml.dump(rsf_dict, Dumper=CustomDumper)` | SnakeYAML `Yaml(DumperOptions)` or `YAMLMapper.writeValueAsString()` | HIGH |
| `@dataclass ImportWarning` | Java record `record ImportWarning(String path, String field, String message, String severity)` | HIGH |
| All 6 conversion rules | Same logic, `JsonNode`-based tree manipulation | HIGH |

### 8. Terraform HCL Generator

| Python (Jinja2 + custom delimiters) | Java Equivalent (FreeMarker + square-bracket) | Confidence |
|-------------------------------------|----------------------------------------------|------------|
| Jinja2 `<< variable >>` in templates | FreeMarker `[= variable ]` with square-bracket interpolation | HIGH |
| Jinja2 `<% for x in list %>` | FreeMarker `[#list items as item]...[/#list]` | HIGH |
| Jinja2 `<% if condition %>` | FreeMarker `[#if condition]...[/#if]` | HIGH |
| Template files: `main.tf.j2`, `iam.tf.j2`, etc. | Template files: `main.tf.ftl`, `iam.tf.ftl`, etc. | HIGH |
| Generation Gap: first-line marker `# DO NOT EDIT` | Same: first comment in generated `.tf` file | HIGH |
| IAM policy derivation from state types | Same logic: iterate states, map type → IAM actions | HIGH |

**FreeMarker square-bracket config:**
```java
cfg.setTagSyntax(Configuration.SQUARE_BRACKET_TAG_SYNTAX);
cfg.setInterpolationSyntax(Configuration.SQUARE_BRACKET_INTERPOLATION_SYNTAX);
// Templates use [#if ...] and [= varName ] instead of <#if ...> and ${varName}
```

### 9. UI Backends (Spring Boot)

| Python (FastAPI) | Java Equivalent (Spring Boot 3.x) | Confidence |
|-----------------|-----------------------------------|------------|
| `@app.get("/api/schema")` | `@GetMapping("/api/schema") ResponseEntity<Map<String, Object>> getSchema()` | HIGH |
| `@app.websocket("/ws")` | STOMP WebSocket: `@MessageMapping("/update")` in `@Controller` | HIGH |
| `asyncio.Queue` for WebSocket messages | `SimpMessagingTemplate.convertAndSend("/topic/updates", message)` | HIGH |
| FastAPI `EventSourceResponse` / SSE | `SseEmitter` in `@GetMapping(produces=TEXT_EVENT_STREAM_VALUE)` | HIGH |
| `StaticFiles(directory=..., html=True)` | `ResourceHttpRequestHandler` + `WebMvcConfigurer.addResourceHandlers()` for SPA fallback | HIGH |
| Token bucket rate limiter (12 req/s) | `RateLimiter.create(12.0)` from Guava `com.google.guava:guava:33.x` | HIGH |
| `uvicorn.run(app, host="0.0.0.0", port=8080)` | `SpringApplication.run(RsfUiApplication.class, args)` with `server.port=8080` | HIGH |
| LambdaInspectClient (boto3) | AWS SDK v2: `LambdaClient` from `software.amazon.awssdk:lambda:2.x` | HIGH |

### 10. Mock SDK

| Python | Java Equivalent | Confidence |
|--------|-----------------|------------|
| `class MockDurableContext` | `class MockDurableContext implements DurableContext` | HIGH |
| `context.step(name, fn, input)` → calls fn(input) | `step(String name, Callable<O> fn)` calls `fn.call()` immediately | MEDIUM |
| `context.wait(name, duration)` → no-op | `wait(String name, Duration duration)` returns immediately | MEDIUM |
| `context.parallel(name, fns)` → calls all fns | `parallel(String name, List<Callable<?>> fns)` calls each immediately | MEDIUM |
| `context.map(name, fn, items)` → maps fn over items | `<I,O> map(String name, Function<I,O> fn, List<I> items)` | MEDIUM |
| `BatchResult.get_results()` | `DurableFuture<List<O>>.get()` — SDK Java uses `CompletableFuture` semantics | MEDIUM |

**Confidence note:** Java SDK is in Preview (February 2026); exact `DurableContext` interface method signatures should be verified against the GitHub repo (`aws/aws-durable-execution-sdk-java`) before implementing mock. The mock must implement the actual interface, not an assumed one.

### 11. Semantic Validator

| Python | Java Equivalent | Confidence |
|--------|-----------------|------------|
| `validate_definition(definition) -> list[ValidationError]` | `List<ValidationError> validate(StateMachineDefinition definition)` | HIGH |
| `@dataclass ValidationError` | Java record `record ValidationError(String message, String path, String severity)` | HIGH |
| `deque` BFS traversal | `ArrayDeque<String>` BFS traversal | HIGH |
| `isinstance(state, ChoiceState)` dispatch | `switch (state) { case ChoiceState c -> ...; }` pattern matching | HIGH |
| Recursive validation for Parallel/Map branches | Same recursion via `validateStateMachine(branch.states, branch.startAt)` helper | HIGH |
| 6 validation rules (dangling refs, unreachable, no terminal, States.ALL, recursive branches) | All 6 rules translate directly | HIGH |

### 12. JSON Schema Generation

| Python (Pydantic) | Java Equivalent (victools) | Confidence |
|------------------|---------------------------|------------|
| `StateMachineDefinition.model_json_schema()` | `SchemaGenerator.generateSchema(StateMachineDefinition.class)` | HIGH |
| Draft 2020-12 output | `SchemaVersion.DRAFT_2020_12` in `SchemaGeneratorConfigBuilder` | HIGH |
| `@JsonSubTypes` → `oneOf` in schema | `JacksonModule` from `jsonschema-module-jackson` handles this automatically | HIGH |
| `schema["$schema"] = "..."` added post-generation | `generatedSchema.put("$schema", "https://json-schema.org/draft/2020-12/schema")` | HIGH |

**Maven dependency:**
```xml
<dependency>
    <groupId>com.github.victools</groupId>
    <artifactId>jsonschema-generator</artifactId>
    <version>4.35.0</version>
</dependency>
<dependency>
    <groupId>com.github.victools</groupId>
    <artifactId>jsonschema-module-jackson</artifactId>
    <version>4.35.0</version>
</dependency>
```

---

## Java SDK Status Warning

**The AWS Lambda Durable Execution SDK for Java entered Developer Preview in February 2026.** Key implications:

- `waitForCallback`, `parallel`, `map`, and `waitForCondition` are listed as "still in development" in the preview documentation (as of the `durable-execution-sdk` docs page fetched 2026-02-28)
- The mock SDK must stub all four of these operations, but the actual Java signatures are unconfirmed
- Blueprint must include a "verify before implementing" flag on all mock SDK method signatures
- Maven coordinates version number is `VERSION` (unspecified) in current docs; must check GitHub releases before implementation

**Action required before Java implementation:** Check `github.com/aws/aws-durable-execution-sdk-java` releases for exact version and verify `DurableContext` interface method signatures.

---

## Sources

- [AWS Lambda Durable Execution SDK (Java SDK)](https://github.com/aws/aws-durable-execution-sdk-java) — DurableHandler, DurableContext, DurableFuture class structure — MEDIUM confidence (Preview)
- [AWS What's New: Lambda Durable Execution SDK for Java Preview](https://aws.amazon.com/about-aws/whats-new/2026/02/lambda-durable-execution-java-preview/) — Java 17+ requirement, steps/waits/durable futures confirmed — HIGH confidence
- [AWS Durable Execution SDK documentation](https://docs.aws.amazon.com/lambda/latest/dg/durable-execution-sdk.html) — parallel/map/waitForCallback still in development for Java — HIGH confidence
- [FreeMarker 2.3.34 download page](https://freemarker.apache.org/freemarkerdownload.html) — version 2.3.34 (2024-12-22), Java 8+ — HIGH confidence
- [FreeMarker Alternative (Square Bracket) Syntax](https://freemarker.apache.org/docs/dgui_misc_alternativesyntax.html) — SQUARE_BRACKET_TAG_SYNTAX and SQUARE_BRACKET_INTERPOLATION_SYNTAX — HIGH confidence
- [Picocli homepage](https://picocli.info/) — version 4.7.7, @Command, @Option, @Parameters — HIGH confidence
- [Picocli GitHub](https://github.com/remkop/picocli) — maintained, active — HIGH confidence
- [Jackson @JsonTypeInfo and sealed interfaces](https://github.com/FasterXML/jackson-databind/issues/3281) — Jackson 3.x auto-detects sealed classes; Jackson 2.x needs explicit @JsonSubTypes — HIGH confidence
- [victools/jsonschema-generator](https://github.com/victools/jsonschema-generator) — version 4.x, jsonschema-module-jackson, Draft 2020-12 support — HIGH confidence
- [Jayway JsonPath with JacksonJsonNodeJsonProvider](https://github.com/json-path/JsonPath) — json-path 2.9.0, JacksonJsonNodeJsonProvider — HIGH confidence
- [Spring Boot WebSocket + STOMP](https://www.toptal.com/java/stomp-spring-boot-websocket) — @EnableWebSocketMessageBroker, SimpMessagingTemplate — HIGH confidence
- [Spring Boot SseEmitter](https://howtodoinjava.com/spring-boot/spring-async-controller-sseemitter/) — SseEmitter pattern, CopyOnWriteArrayList for multi-client — HIGH confidence
- [SnakeYAML 2.2](https://mvnrepository.com/artifact/org.yaml/snakeyaml/2.2) — YAML parsing and emission — HIGH confidence
- [JUnit 5 + Mockito 5 + AssertJ 3 versions](https://www.javacodegeeks.com/2024/11/modern-java-testing-frameworks-exploring-junit-5-mockito-and-assertj.html) — JUnit 5.10.5, Mockito 5.11.0, AssertJ 3.27.7 — HIGH confidence
- RSF Python source code (direct inspection): `/home/esa/git/rsf-python/src/rsf/` — all component implementations — HIGH confidence

---

*Feature research for: RSF v1.6 — Java Port Blueprint (RSF-BUILDPRINT-JAVA.md)*
*Researched: 2026-02-28*
