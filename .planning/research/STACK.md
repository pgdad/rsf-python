# Stack Research

**Domain:** Java port of RSF (Replacement for Step Functions) — Lambda Durable Execution toolchain
**Researched:** 2026-02-28
**Confidence:** HIGH (AWS SDK via official docs + GitHub; all library versions verified on Maven Central)

---

## Context: Scope of This Research

This file covers stack decisions for **porting RSF to Java**. The Python implementation (v1.0–v1.4) is validated and frozen as the reference. This Java port must:

1. Map all Python DSL models (Pydantic v2) → Java sealed interface hierarchies (Jackson DTOs)
2. Map Jinja2 code generation → FreeMarker templates
3. Map Typer CLI → Picocli
4. Map FastAPI REST/WebSocket/SSE → Spring Boot
5. Map `aws_lambda_durable_execution_sdk_python` → `aws-durable-execution-sdk-java` (Preview)
6. Map pytest → JUnit 5 + Mockito + AssertJ

Do not re-add Python tooling. Do not add Go/Kotlin/Scala. Java 17+ only.

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Java | 17 (minimum) | Runtime | AWS Lambda Durable Execution SDK for Java requires Java 17+. Container image deployment uses Java 21 or Java 25 ECR base images. Java 17 is the LTS floor; use Java 21 for production builds. |
| AWS Lambda Durable Execution SDK (Java) | Preview | Orchestrator runtime in generated code | The only SDK implementing checkpoint/replay semantics for Lambda Durable Functions in Java. Developer Preview as of February 2026. Container-image deployment only (no managed runtime). |
| Jackson Databind | 2.18.5 | JSON parsing, DTO models, polymorphic deserialization | Industry standard Java JSON library. Version 2.18.x is LTS. Handles both JSON and YAML (via `jackson-dataformat-yaml`). `@JsonTypeInfo`/`@JsonSubTypes` are the idiomatic Java equivalent of Pydantic discriminated unions. |
| jackson-dataformat-yaml | 2.18.5 | YAML DSL file parsing | Wraps SnakeYAML 2.x (compatible since 2.14.x). Allows the same `ObjectMapper` used for JSON to also parse YAML — no duplicate mapping code. Raw SnakeYAML requires JavaBeans convention; Jackson handles arbitrary annotated POJOs/records. |
| FreeMarker | 2.3.34 | Code generation (Java orchestrator classes + Terraform HCL) | Mature Apache project. Released 2024-12-22, requires Java 8+. Key feature: configurable tag syntax — `SQUARE_BRACKET_TAG_SYNTAX` uses `[#if x]...[/#if]` and `[=variable]` interpolation, which avoids the `${...}` conflict with Terraform HCL interpolation. Same reason the Python version uses custom `<< >>` Jinja2 delimiters. |
| Picocli | 4.7.7 | CLI framework (7 commands: init, generate, validate, deploy, import, ui, inspect) | Best Java CLI library: typed subcommands, colored help, GraalVM native support, annotation-based with zero Spring context overhead. JCommander lacks typed positional parameters, negatable options, and argument groups. Spring Shell requires a full Spring ApplicationContext — excessive for a standalone CLI tool. |
| Spring Boot | 3.5.9 | REST + WebSocket + SSE backends (graph editor + inspector) | Provides `SseEmitter` (inspector live updates), `spring-boot-starter-websocket` (graph editor STOMP), and static file serving. All needed features in one starter hierarchy. Largest ecosystem and most real-world WebSocket+SSE examples. Quarkus/Micronaut offer faster cold start — irrelevant for a developer tool that runs continuously on localhost. |
| JUnit Jupiter | 5.11.4 | Unit and integration testing | Standard JUnit 5 API. JUnit 6 (released September 2025) has breaking API changes and an immature ecosystem — Spring Boot Test 3.5.x has not migrated. Stay on 5.11.x. |
| Mockito | 5.14.2 | Mocking in unit tests | Industry-standard Java mock framework. Version 5.x requires Java 11+ and supports modern features: records, sealed classes, final classes. |
| AssertJ | 3.27.7 | Fluent test assertions | More expressive than JUnit's built-in assertions. Essential for asserting complex DSL model trees and generated code content. Reads naturally: `assertThat(state.getType()).isEqualTo("Task")`. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| networknt json-schema-validator | 1.5.6 | JSON Schema validation of DSL input files | Validate `workflow.yaml` against a JSON Schema spec (mirrors Pydantic v2 schema export in the Python version). Supports draft 2020-12. Integrates with Jackson's `JsonNode` — same `ObjectMapper` pipeline. Released February 2025. |
| Hibernate Validator | 9.1.0.Final | Jakarta Bean Validation 3.1 on DTO model fields | Use for `@NotNull`, `@NotBlank`, `@Size`, and custom `@Constraint` validators on DSL model classes. Implements Jakarta Validation 3.1 (Java 17+ only). Pulls in `jakarta.validation-api:3.1.1` transitively. |
| jakarta.el-api | 6.0.1 | EL expression evaluation (Hibernate Validator dependency) | Required by Hibernate Validator for constraint violation message interpolation. Include explicitly to avoid classpath ambiguity in non-application-server environments. |
| spring-boot-starter-web | 3.5.9 | HTTP REST endpoints + SseEmitter for inspector | Graph editor REST API + inspector REST + SSE live updates. Includes Jackson, embedded Tomcat, Spring MVC. |
| spring-boot-starter-websocket | 3.5.9 | WebSocket/STOMP for graph editor backend | Bidirectional YAML↔graph sync in graph editor. Mirrors FastAPI WebSocket in the Python version. |
| AWS SDK for Java 2.x (BOM) | 2.x (BOM-managed) | Lambda control plane API for inspector | `listDurableExecutionsByFunction`, `getDurableExecution`, `invoke` — same operations as Python's boto3 calls. Use the AWS SDK BOM for consistent version management across SDK modules. |
| picocli-codegen | 4.7.7 | Annotation processor (NOT a runtime dependency) | Generates GraalVM native image configuration files at compile time. Add ONLY in `<annotationProcessorPaths>` of maven-compiler-plugin, never as a `<dependency>`. |
| jackson-module-parameter-names | 2.18.5 | Preserve constructor parameter names for Jackson | Required when using `@JsonCreator` with constructor injection and no per-parameter `@JsonProperty`. Add alongside Jackson core. |

### Build / Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Maven 3.9+ | Build system, dependency management, multi-module orchestration | Multi-module layout with parent POM. Each module is a `<jar>`. Only `rsf-cli` (shade plugin) and `rsf-web` (spring-boot-maven-plugin) produce executables. |
| maven-compiler-plugin 3.13+ | Java 17+ compilation + annotation processing | Set `<release>17</release>`. Add Picocli annotation processor in `<annotationProcessorPaths>`. |
| maven-shade-plugin 3.6+ | Fat JAR for CLI distribution | Produces a single executable JAR for `rsf-cli`. Configure `<mainClass>` in manifest transform. |
| spring-boot-maven-plugin 3.5.9 | Executable JAR for web backends | Repackages Spring Boot web module into a runnable JAR with embedded Tomcat. Apply ONLY on the `rsf-web` module. |
| maven-surefire-plugin | 3.5.4 | Run unit tests (JUnit 5) | Required for JUnit Jupiter — Maven's built-in Surefire does not auto-detect Jupiter without this plugin. |
| maven-failsafe-plugin | 3.5.4 | Run integration tests separately | Separate lifecycle (`verify` phase). Use `*IT.java` naming convention for integration test classes. |

---

## AWS Lambda Durable Execution SDK for Java — Full API Reference

**Status:** Developer Preview (announced February 2026)
**Deployment:** Container image only (no managed runtime support during Preview)
**GitHub:** `https://github.com/aws/aws-durable-execution-sdk-java`
**License:** Apache 2.0
**Java requirement:** 17+

### Maven Coordinates

```xml
<!-- Core SDK (in generated Lambda orchestrator module) -->
<dependency>
    <groupId>software.amazon.lambda.durable</groupId>
    <artifactId>aws-durable-execution-sdk-java</artifactId>
    <version>${durable.sdk.version}</version>
</dependency>

<!-- Testing utilities (for mock SDK module) -->
<dependency>
    <groupId>software.amazon.lambda.durable</groupId>
    <artifactId>aws-durable-execution-sdk-java-testing</artifactId>
    <version>${durable.sdk.version}</version>
    <scope>test</scope>
</dependency>
```

The version number is not pinned in official docs during Preview. Check the GitHub releases tab for the current tag. Pin as a property `${durable.sdk.version}` in the parent POM so all modules use the same version.

### Core API Classes

| Class | Package | Description |
|-------|---------|-------------|
| `DurableHandler<I, O>` | `software.amazon.lambda.durable` | Base class for all durable Lambda handlers. `I` = input type, `O` = output type. Override `handleRequest(I input, DurableContext ctx)`. Maps to Python's `DurableHandler` base. |
| `DurableContext` | `software.amazon.lambda.durable` | Main interface for durable operations within `handleRequest`. All orchestration primitives accessed here. Maps to Python's `DurableContext`. |
| `DurableFuture<T>` | `software.amazon.lambda.durable` | Represents an async step result. Returned by `ctx.stepAsync()` and `ctx.runInChildContextAsync()`. Maps to Python's awaitable from `parallel()`/`map()`. |
| `DurableCallbackFuture<T>` | `software.amazon.lambda.durable` | Specialized future for external event-based resumption via callbacks. |
| `StepConfig` | `software.amazon.lambda.durable` | Builder for per-step configuration: retry strategies, execution semantics, custom serialization. Maps to Python's `StepConfig`. |
| `CallbackConfig` | `software.amazon.lambda.durable` | Builder for `createCallback()`: timeout `Duration`, heartbeat settings. |
| `InvokeConfig` | `software.amazon.lambda.durable` | Configuration for `ctx.invoke()` (child Lambda invocations). |
| `DurableConfig` | `software.amazon.lambda.durable` | Global SDK configuration: custom Lambda client, serialization settings, thread pools. |
| `TypeToken<T>` | `software.amazon.lambda.durable` | Required when step return type is a parameterized generic (e.g., `List<Order>`). Equivalent to Jackson's `TypeReference<T>` and Python's implicit generic handling. |
| `RetryStrategies` | `software.amazon.lambda.durable` | Factory for retry policies. Provides exponential backoff with jitter and `NO_RETRY` preset. |

### DurableContext Method Signatures

```java
// Execute with checkpoint — blocks until complete
<T> T step(String name, Class<T> resultClass, Callable<T> fn);

// Execute with checkpoint — for parameterized types (List<T>, Map<K,V>)
<T> T step(String name, TypeToken<T> typeToken, Callable<T> fn);

// Launch step asynchronously
<T> DurableFuture<T> stepAsync(String name, Class<T> resultClass, Callable<T> fn);

// Suspend without compute charges
void wait(Duration duration);

// Wait for external system callback
<T> DurableCallbackFuture<T> createCallback(String name, Class<T> resultClass, CallbackConfig config);

// Call another Lambda function with result tracking
<T> T invoke(String name, String functionArn, Object input, Class<T> resultClass, InvokeConfig config);

// Execute isolated work with separate checkpoint log
<T> T runInChildContext(String name, Class<T> resultClass, Function<DurableContext, T> fn);

// Launch child context concurrently
<T> DurableFuture<T> runInChildContextAsync(String name, Class<T> resultClass, Function<DurableContext, T> fn);
```

### Canonical Handler Pattern

```java
import software.amazon.lambda.durable.DurableContext;
import software.amazon.lambda.durable.DurableHandler;

public class OrderOrchestrator extends DurableHandler<OrderInput, OrderResult> {
    @Override
    protected OrderResult handleRequest(OrderInput input, DurableContext ctx) {
        String validated = ctx.step("ValidateOrder", String.class, () -> validate(input));
        String charged   = ctx.step("ChargePayment", String.class, () -> charge(validated));
        return ctx.step("ShipOrder", OrderResult.class, () -> ship(charged));
    }
    // ...business logic methods...
}
```

### Preview Limitations (as of 2026-02-28)

The following operations are listed as not yet implemented in the Java Preview:
- `waitForCondition`
- `waitForCallback` (partially available via `DurableCallbackFuture`)
- `parallel` (concurrent child contexts via `runInChildContextAsync` + `DurableFuture` instead)
- `map` (implement as a loop of `runInChildContextAsync`)

The Java port blueprint must document these gaps and provide workaround patterns for `Parallel` and `Map` state types.

### Container Deployment (required during Preview)

```dockerfile
FROM --platform=linux/amd64 public.ecr.aws/lambda/java:21
RUN dnf install -y maven
WORKDIR /var/task
COPY pom.xml .
COPY src ./src
RUN mvn clean package -DskipTests
RUN mv target/*.jar lib/
CMD ["com.example.rsf.GeneratedOrchestrator::handleRequest"]
```

---

## Maven Multi-Module Project Structure

```
rsf-java/
├── pom.xml                      (parent POM: <packaging>pom</packaging>, Spring Boot parent, depMgmt)
├── rsf-dsl/
│   └── pom.xml                  (DSL models: Jackson sealed interfaces, validators, JSON Schema)
├── rsf-codegen/
│   └── pom.xml                  (FreeMarker templates, code generator, HCL generator)
├── rsf-cli/
│   └── pom.xml                  (Picocli commands; maven-shade-plugin → fat JAR)
├── rsf-web/
│   └── pom.xml                  (Spring Boot; spring-boot-maven-plugin → executable JAR)
└── rsf-testing/
    └── pom.xml                  (shared test utilities: mock SDK, DSL fixtures, test helpers)
```

Parent POM (`rsf-java/pom.xml`) key sections:

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.5.9</version>
    <relativePath/>
</parent>

<modules>
    <module>rsf-dsl</module>
    <module>rsf-codegen</module>
    <module>rsf-cli</module>
    <module>rsf-web</module>
    <module>rsf-testing</module>
</modules>
```

Module dependency chain: `rsf-dsl` ← `rsf-codegen` ← `rsf-cli`. `rsf-web` depends on `rsf-dsl` for model inspection APIs. `rsf-testing` is a test-scope dependency across all modules.

---

## Installation (pom.xml Snippets)

```xml
<!-- ===== Core Jackson ===== -->
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
    <version>2.18.5</version>
</dependency>
<dependency>
    <groupId>com.fasterxml.jackson.dataformat</groupId>
    <artifactId>jackson-dataformat-yaml</artifactId>
    <version>2.18.5</version>
</dependency>
<dependency>
    <groupId>com.fasterxml.jackson.module</groupId>
    <artifactId>jackson-module-parameter-names</artifactId>
    <version>2.18.5</version>
</dependency>

<!-- ===== FreeMarker ===== -->
<dependency>
    <groupId>org.freemarker</groupId>
    <artifactId>freemarker</artifactId>
    <version>2.3.34</version>
</dependency>

<!-- ===== CLI ===== -->
<dependency>
    <groupId>info.picocli</groupId>
    <artifactId>picocli</artifactId>
    <version>4.7.7</version>
</dependency>

<!-- ===== Spring Boot Web (rsf-web module only) ===== -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
    <!-- version managed by spring-boot-starter-parent 3.5.9 -->
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-websocket</artifactId>
</dependency>

<!-- ===== Validation ===== -->
<dependency>
    <groupId>org.hibernate.validator</groupId>
    <artifactId>hibernate-validator</artifactId>
    <version>9.1.0.Final</version>
</dependency>
<dependency>
    <groupId>jakarta.el</groupId>
    <artifactId>jakarta.el-api</artifactId>
    <version>6.0.1</version>
</dependency>

<!-- ===== JSON Schema ===== -->
<dependency>
    <groupId>com.networknt</groupId>
    <artifactId>json-schema-validator</artifactId>
    <version>1.5.6</version>
</dependency>

<!-- ===== AWS Durable Execution SDK ===== -->
<dependency>
    <groupId>software.amazon.lambda.durable</groupId>
    <artifactId>aws-durable-execution-sdk-java</artifactId>
    <version>${durable.sdk.version}</version>
</dependency>

<!-- ===== Testing ===== -->
<dependency>
    <groupId>org.junit.jupiter</groupId>
    <artifactId>junit-jupiter</artifactId>
    <version>5.11.4</version>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.mockito</groupId>
    <artifactId>mockito-core</artifactId>
    <version>5.14.2</version>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.assertj</groupId>
    <artifactId>assertj-core</artifactId>
    <version>3.27.7</version>
    <scope>test</scope>
</dependency>

<!-- ===== Build Plugins (in parent POM <build><pluginManagement>) ===== -->

<!-- Picocli annotation processor — in maven-compiler-plugin, NOT as <dependency> -->
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-compiler-plugin</artifactId>
    <version>3.13.0</version>
    <configuration>
        <release>17</release>
        <annotationProcessorPaths>
            <path>
                <groupId>info.picocli</groupId>
                <artifactId>picocli-codegen</artifactId>
                <version>4.7.7</version>
            </path>
        </annotationProcessorPaths>
    </configuration>
</plugin>

<!-- Unit tests -->
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-surefire-plugin</artifactId>
    <version>3.5.4</version>
</plugin>

<!-- Integration tests (*IT.java classes, verify phase) -->
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-failsafe-plugin</artifactId>
    <version>3.5.4</version>
    <executions>
        <execution>
            <goals>
                <goal>integration-test</goal>
                <goal>verify</goal>
            </goals>
        </execution>
    </executions>
</plugin>

<!-- Fat JAR for CLI (rsf-cli module only) -->
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-shade-plugin</artifactId>
    <version>3.6.0</version>
    <executions>
        <execution>
            <phase>package</phase>
            <goals><goal>shade</goal></goals>
            <configuration>
                <transformers>
                    <transformer implementation="org.apache.maven.plugins.shade.resource.ManifestResourceTransformer">
                        <mainClass>com.example.rsf.cli.RsfMain</mainClass>
                    </transformer>
                </transformers>
            </configuration>
        </execution>
    </executions>
</plugin>
```

---

## Jackson Polymorphic Deserialization — DSL State Types

The Python version uses Pydantic discriminated unions keyed on `"type"` for 8 DSL state types. The Java equivalent uses Jackson annotations on a sealed interface:

```java
@JsonTypeInfo(
    use = JsonTypeInfo.Id.NAME,
    include = JsonTypeInfo.As.PROPERTY,
    property = "type"
)
@JsonSubTypes({
    @JsonSubTypes.Type(value = TaskState.class,    name = "Task"),
    @JsonSubTypes.Type(value = ChoiceState.class,  name = "Choice"),
    @JsonSubTypes.Type(value = WaitState.class,    name = "Wait"),
    @JsonSubTypes.Type(value = SucceedState.class, name = "Succeed"),
    @JsonSubTypes.Type(value = FailState.class,    name = "Fail"),
    @JsonSubTypes.Type(value = PassState.class,    name = "Pass"),
    @JsonSubTypes.Type(value = ParallelState.class,name = "Parallel"),
    @JsonSubTypes.Type(value = MapState.class,     name = "Map")
})
public sealed interface State
    permits TaskState, ChoiceState, WaitState, SucceedState,
            FailState, PassState, ParallelState, MapState {}
```

Sealed interfaces (Java 17+) allow exhaustive switch expressions over state types — the compiler catches missing cases. Jackson reads the `"type"` field from YAML/JSON and routes to the correct implementation class.

For parameterized return types in `ctx.step()` calls, use Jackson `TypeReference<T>` (maps to the SDK's `TypeToken`):

```java
List<Order> orders = mapper.readValue(json, new TypeReference<List<Order>>() {});
```

---

## FreeMarker Configuration for HCL Generation

The Python version avoids Jinja2's `${...}` conflict with Terraform HCL by using custom `<< >>` delimiters. FreeMarker's square-bracket tag syntax eliminates this problem completely:

```java
Configuration cfg = new Configuration(Configuration.VERSION_2_3_34);

// For HCL templates: use square bracket tag syntax
// [#if x]...[/#if]  —  no conflict with Terraform ${...}
cfg.setTagSyntax(Configuration.SQUARE_BRACKET_TAG_SYNTAX);

// Optionally: change interpolation syntax too
// [=variable]  —  replaces ${variable}
cfg.setInterpolationSyntax(Configuration.SQUARE_BRACKET_INTERPOLATION_SYNTAX);

// For Java orchestrator templates: use default angle bracket syntax
Configuration javaCfg = new Configuration(Configuration.VERSION_2_3_34);
// (no setTagSyntax — defaults to auto-detect or angle bracket)
```

Two separate `Configuration` instances: one for Java orchestrator templates (angle bracket or auto-detect), one for HCL Terraform templates (square bracket). Both use the same FreeMarker library — no separate template engine needed.

---

## Alternatives Considered

| Category | Recommended | Alternative | When to Use Alternative |
|----------|-------------|-------------|-------------------------|
| YAML parsing | jackson-dataformat-yaml 2.18.5 | SnakeYAML 2.x directly | Only if you need YAML anchors/aliases unsupported by Jackson, or want zero Jackson dependency. For RSF, Jackson is already required for JSON — one mapper for both avoids duplicate models. |
| Code generation | FreeMarker 2.3.34 | JavaPoet 1.13 (Square) or Palantir fork | JavaPoet when generating Java source with strong type guarantees and no string concatenation risk. However: JavaPoet cannot generate Terraform HCL (only Java source). RSF needs both. Original Square JavaPoet is deprecated; Palantir fork is active but adds fork-dependency risk. FreeMarker handles Java + HCL in a single engine. |
| Code generation | FreeMarker 2.3.34 | Apache Velocity 2.4 | Velocity when you need extremely lightweight text templates. FreeMarker is preferred because undefined variables fail loudly (not silently render empty as in Velocity), has better IDE tooling support, and is more actively maintained. The `${...}` conflict with HCL also exists in Velocity — FreeMarker's square-bracket syntax is unique. |
| CLI | Picocli 4.7.7 | Spring Shell 3.x | Spring Shell when the CLI is embedded in a Spring Boot application and needs REPL (shell-mode) interaction. RSF CLI is a standalone tool — loading a full Spring ApplicationContext for argument parsing is wasteful and adds 500ms+ startup overhead. |
| CLI | Picocli 4.7.7 | JCommander 1.82 | Never prefer JCommander — it lacks typed positional parameters, negatable options, argument groups, and has lower community activity than Picocli. Picocli is a strict superset. |
| Web backend | Spring Boot 3.5.9 | Quarkus 3.x | Quarkus when deploying to Kubernetes with GraalVM native image for sub-100ms cold start. RSF web backends run continuously on a developer's machine — cold-start irrelevant. Spring's larger ecosystem has more documented WebSocket + SSE patterns. |
| Web backend | Spring Boot 3.5.9 | Micronaut 4.x | Micronaut when you need the fastest startup and smallest binary for IoT/serverless. Same reasoning as Quarkus — not justified for a developer tool. |
| Template engine (HCL) | FreeMarker 2.3.34 | Pebble 4.1.1 | Pebble when you prefer Jinja/Twig-style syntax. However: Pebble's custom delimiter support is undocumented and unverified for non-HTML text generation use cases. FreeMarker's square-bracket syntax is documented and designed exactly for this use case. |
| Validation | Hibernate Validator 9.1.0 + custom | Custom validators only | Custom-only when you want zero framework dependency. For RSF Java, Hibernate Validator provides `@NotNull`, `@Pattern`, `@Size` on DSL field definitions for free. Custom validators implement cross-state semantic checks (BFS reachability, dangling transitions) that framework annotations cannot express. |
| JSON Schema | networknt 1.5.6 | Everit json-schema 1.14 | Everit is less actively maintained and does not support JSON Schema draft 2020-12. networknt is the dominant Java JSON Schema validator with active releases into 2025. |
| Testing | JUnit 5.11.4 | JUnit 6.0.x | JUnit 6 when it reaches stable ecosystem support. JUnit 6.0.3 was released February 2026 — Spring Boot Test, Mockito, and AssertJ have not migrated. Stay on 5.11.x until ecosystem catches up. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| AWS SDK for Java 1.x (`com.amazonaws:aws-java-sdk`) | End-of-life December 31, 2025. No security patches. | AWS SDK for Java 2.x (`software.amazon.awssdk`) |
| SnakeYAML directly (without Jackson wrapper) | Requires JavaBeans convention (no-arg constructors, public getters/setters) — conflicts with immutable record-style DTOs. No integration with Jackson annotation ecosystem (`@JsonTypeInfo`, etc.). | `jackson-dataformat-yaml` which works with any Jackson-annotated class. |
| Apache Velocity for HCL generation | `${...}` is Velocity's interpolation syntax — same conflict with Terraform HCL as Jinja2 (which the Python version solved with custom delimiters). | FreeMarker with `SQUARE_BRACKET_TAG_SYNTAX` + `SQUARE_BRACKET_INTERPOLATION_SYNTAX`. |
| JavaPoet for Terraform HCL templates | JavaPoet generates only `.java` source files. Cannot produce `.tf` HCL content. | FreeMarker, which handles both Java orchestrator templates AND HCL templates. |
| Spring Shell for CLI | Requires full Spring ApplicationContext startup (500ms+). Designed for REPL mode, not single-shot subcommands. | Picocli 4.7.7. |
| JUnit 4 (`junit:junit`) | Legacy API. Spring Boot 3.x test starters do not include JUnit 4 transitively. No nested tests, no parameterized test improvements, no `@DisplayName`. | JUnit Jupiter 5.11.4. |
| Jackson 3.0.x (Release Candidate) | Breaking API changes from 2.x. Spring Boot, Hibernate Validator, and networknt json-schema-validator have not migrated. | Jackson 2.18.5 (LTS). |
| picocli-codegen as a `<dependency>` (not annotation processor) | It must be in `<annotationProcessorPaths>` only. Adding it as a regular dependency pulls unused runtime classes into the fat JAR. | Add exclusively to `maven-compiler-plugin` `<annotationProcessorPaths>`. |
| `javax.validation` namespace | Superseded by `jakarta.validation` in Jakarta EE 9+. Spring Boot 3.x, Hibernate Validator 9.x, and the SDK all use `jakarta.*`. Mixing namespaces causes `ClassNotFoundException` at runtime. | `jakarta.validation-api:3.1.1` (pulled transitively by Hibernate Validator 9.x). |

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Spring Boot 3.5.9 | Java 17–21, Jackson 2.18.x, JUnit 5.11.x | Spring Boot 3.x requires Jakarta EE 10 (`jakarta.*` namespace). Do not mix `javax.*` artifacts. |
| Hibernate Validator 9.1.0.Final | Jakarta Validation 3.1.1, Java 17+, Spring Boot 3.5.x | Pulls `jakarta.validation-api:3.1.1` transitively. Spring Boot's `spring-boot-starter-validation` brings this automatically. |
| JUnit Jupiter 5.11.4 | Mockito 5.14.2, AssertJ 3.27.7, Spring Boot Test 3.5.9 | All three are designed to work together. Spring Boot Test autoconfigures the JUnit 5 platform. |
| maven-surefire-plugin 3.5.4 | JUnit Platform 1.11.x (bundled with JUnit 5.11) | Surefire < 2.22 requires an explicit JUnit Platform provider dependency. 3.5.4 auto-detects Jupiter. |
| FreeMarker 2.3.34 | Java 8+, Spring Boot 3.5.9 | No version conflict with Java 17/21. Works on both classpath and module path builds. Spring Boot includes a FreeMarker autoconfiguration starter — use that only for `rsf-web` if templating web views; use the standalone `Configuration` for code generation in `rsf-codegen`. |
| jackson-dataformat-yaml 2.18.5 | SnakeYAML 2.5 (transitive), Jackson 2.18.5 | SnakeYAML 2.x resolves CVE-2022-1471. Version pulled transitively — do NOT override to SnakeYAML 1.x. |
| Picocli 4.7.7 | Java 8+, Spring Boot (optional) | Works on Java 17/21 classpath and module path. Compatible with Spring Boot — can inject Spring beans into Picocli commands via `@Autowired` if needed, but prefer keeping `rsf-cli` Spring-free for startup speed. |
| networknt json-schema-validator 1.5.6 | Jackson 2.18.x, Java 11+ | Uses Jackson's `JsonNode` internally. Same Jackson version as the rest of the stack — no conflict. |

---

## Sources

- [AWS Lambda Durable Execution SDK for Java — Developer Preview Announcement](https://aws.amazon.com/about-aws/whats-new/2026/02/lambda-durable-execution-java-preview/) — Java 17+ requirement, Preview status (HIGH confidence)
- [AWS Lambda Durable Supported Runtimes](https://docs.aws.amazon.com/lambda/latest/dg/durable-supported-runtimes.html) — Container-image-only deployment, Maven coordinates `software.amazon.lambda.durable:aws-durable-execution-sdk-java`, Dockerfile pattern with Java 25 ECR base image (HIGH confidence)
- [AWS Durable Execution SDK Java GitHub](https://github.com/aws/aws-durable-execution-sdk-java) — Full API class list (DurableHandler, DurableContext, DurableFuture, DurableCallbackFuture, StepConfig, CallbackConfig, InvokeConfig, DurableConfig, TypeToken, RetryStrategies), package name `software.amazon.lambda.durable`, Preview limitations (HIGH confidence)
- [FreeMarker Maven Download](https://freemarker.apache.org/freemarkerdownload.html) — Version 2.3.34, `org.freemarker:freemarker` coordinates (HIGH confidence)
- [FreeMarker Square Bracket Syntax Docs](https://freemarker.apache.org/docs/dgui_misc_alternativesyntax.html) — `Configuration.setTagSyntax(SQUARE_BRACKET_TAG_SYNTAX)` configuration (HIGH confidence)
- [Picocli GitHub](https://github.com/remkop/picocli) + [picocli.info](https://picocli.info/) — Version 4.7.7, `info.picocli:picocli` Maven coordinates, annotation processor pattern (HIGH confidence)
- [Picocli vs JCommander wiki](https://github.com/remkop/picocli/wiki/picocli-vs-JCommander) — Feature gap rationale (HIGH confidence)
- [Spring Boot 3.5.x blog](https://spring.io/blog/2025/10/23/spring-boot-3-5-7-available-now/) — Latest 3.5.9 version confirmed (HIGH confidence)
- [Jackson 2.18.5 Maven Central](https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-databind/) — LTS status and version coordinates (HIGH confidence)
- [jackson-dataformat-yaml Maven Repository](https://mvnrepository.com/artifact/com.fasterxml.jackson.dataformat/jackson-dataformat-yaml) — 2.18.5 coordinates, SnakeYAML 2.x compatibility note (HIGH confidence)
- [Hibernate Validator Releases](https://hibernate.org/validator/releases/) — 9.1.0.Final, Jakarta Validation 3.1.1, Java 17+ requirement (HIGH confidence)
- [Jakarta Validation 3.1 spec](https://jakarta.ee/specifications/bean-validation/3.1/) — Namespace and API changes (HIGH confidence)
- [JUnit Jupiter 5.11.4 Maven Repository](https://mvnrepository.com/artifact/org.junit.jupiter/junit-jupiter-api/5.11.4) — Version confirmed (HIGH confidence)
- [Mockito GitHub Releases](https://github.com/mockito/mockito/releases) — 5.14.2 confirmed (HIGH confidence)
- [AssertJ 3.27.7 Maven Repository](https://mvnrepository.com/artifact/org.assertj/assertj-core) — Version confirmed (HIGH confidence)
- [networknt json-schema-validator 1.5.6 Maven](https://mvnrepository.com/artifact/com.networknt/json-schema-validator/1.5.6) — February 2025 release, draft 2020-12 support (HIGH confidence)
- [Maven Failsafe Plugin 3.5.4](https://maven.apache.org/surefire/maven-failsafe-plugin/) — September 2025 release (HIGH confidence)
- [Pebble Templates 4.1.1 Maven](https://mvnrepository.com/artifact/io.pebbletemplates/pebble) — Evaluated and rejected: custom delimiter support for HCL generation unverified (MEDIUM confidence)
- [Spring Boot vs Quarkus vs Micronaut 2025](https://www.javacodegeeks.com/2025/12/spring-boot-vs-quarkus-vs-micronaut-the-ultimate-2026-showdown.html) — Framework comparison rationale (MEDIUM confidence — third-party analysis)

---

*Stack research for: RSF v1.6 Java Port Blueprint*
*Researched: 2026-02-28*
