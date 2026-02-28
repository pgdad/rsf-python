# Architecture Research

**Domain:** Java port of RSF (Replacement for Step Functions) — Lambda Durable Functions SDK for Java
**Researched:** 2026-02-28
**Confidence:** HIGH for Java SDK API and multi-module Maven structure; MEDIUM for parallel/map operations (still in development in Java preview SDK)

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        CLI Layer (rsf-cli)                            │
│  init | generate | validate | deploy | import | ui | inspect          │
│  Picocli subcommands — delegates to rsf-codegen, rsf-terraform, etc.  │
└──────────┬──────────────────────────────────────────────────────────┘
           │ calls
┌──────────▼──────────────────────────────────────────────────────────┐
│                     Core Library Layer                               │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐ │
│  │ rsf-dsl  │ │rsf-cogen │ │rsf-terrafrm│ │rsf-imprt │ │rsf-runtim│ │
│  │          │ │          │ │            │ │          │ │          │ │
│  │SnakeYAML │ │FreeMarker│ │FreeMarker  │ │Jackson   │ │DurableH  │ │
│  │+Jackson  │ │templates │ │HCL tmpls   │ │ASL parse │ │ andler   │ │
│  └──────────┘ └──────────┘ └───────────┘ └──────────┘ └──────────┘ │
└──────────┬──────────────────────────────────────────────────────────┘
           │ serves
┌──────────▼──────────────────────────────────────────────────────────┐
│                  Web UI Layer                                        │
│  ┌────────────────────────┐  ┌───────────────────────────────────┐  │
│  │  rsf-editor            │  │  rsf-inspector                    │  │
│  │  Spring Boot           │  │  Spring Boot                      │  │
│  │  TextWebSocketHandler  │  │  SseEmitter + REST controllers    │  │
│  │  Serves editor React   │  │  Serves inspector React SPA       │  │
│  └────────────────────────┘  └───────────────────────────────────┘  │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  Shared React UIs (same source, built once, bundled per module) │ │
│  │  Graph Editor SPA  |  Execution Inspector SPA                  │ │
│  │  (same React/TypeScript code as Python version — zero changes)  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `rsf-dsl` | Parse YAML/JSON DSL to typed Java model objects; validate semantic constraints | Jackson `YAMLMapper` + `ObjectMapper` with `@JsonTypeInfo`/`@JsonSubTypes` sealed interfaces; BFS validator |
| `rsf-codegen` | BFS state traversal; FreeMarker template rendering to Java source; Generation Gap pattern | FreeMarker 2.3.x; `StateMapping` records; `CodeGenerator` service class |
| `rsf-terraform` | FreeMarker HCL template rendering; IAM derivation; Generation Gap for Terraform files | FreeMarker with custom delimiters `<< >>` `<% %>`; `TerraformConfig` record |
| `rsf-importer` | Parse ASL JSON; convert to RSF YAML; emit handler stubs | Jackson `ObjectMapper`; calls `rsf-codegen` stub renderer |
| `rsf-runtime` | `@State`/`@Startup` annotation definitions; handler registry; 5-stage I/O pipeline; 18 intrinsic functions; JSONPath evaluator | Annotations + classpath scanning; `HandlerRegistry` singleton; `IOPipeline` service |
| `rsf-editor` | Spring Boot server: REST (`/api/schema`), raw WebSocket (`/ws`), static files | `TextWebSocketHandler`; Spring MVC; embedded React SPA in `resources/static/` |
| `rsf-inspector` | Spring Boot server: REST (`/api/inspect/**`), SSE (`/api/inspect/stream`), static files | `SseEmitter`; `@RestController`; embedded React SPA; AWS SDK v2 Lambda client |
| `rsf-cli` | Picocli entry point; `rsf` command with 7 subcommands; process lifecycle | Picocli 4.x; `@Command`/`@Subcommand` annotations; `exec-maven-plugin` for generate |

---

## Recommended Project Structure

```
rsf-java/
├── pom.xml                          # Parent POM: groupId=io.rsf, version management
│
├── rsf-dsl/                         # DSL models and parser
│   ├── pom.xml
│   └── src/main/java/io/rsf/dsl/
│       ├── model/
│       │   ├── StateMachineDefinition.java   # Root model
│       │   ├── State.java                    # sealed interface
│       │   ├── TaskState.java                # implements State
│       │   ├── PassState.java
│       │   ├── ChoiceState.java
│       │   ├── WaitState.java
│       │   ├── SucceedState.java
│       │   ├── FailState.java
│       │   ├── ParallelState.java
│       │   ├── MapState.java
│       │   ├── BranchDefinition.java
│       │   ├── choice/
│       │   │   ├── ChoiceRule.java           # sealed interface
│       │   │   ├── DataTestRule.java
│       │   │   ├── AndRule.java
│       │   │   ├── OrRule.java
│       │   │   └── NotRule.java
│       │   └── errors/
│       │       ├── RetryPolicy.java
│       │       └── Catcher.java
│       ├── parser/
│       │   └── DslParser.java               # YAMLMapper + ObjectMapper entry point
│       └── validator/
│           └── DslValidator.java            # BFS cross-state validator
│
├── rsf-codegen/                     # Code generator
│   ├── pom.xml
│   └── src/main/
│       ├── java/io/rsf/codegen/
│       │   ├── CodeGenerator.java           # Orchestrates BFS + FreeMarker rendering
│       │   ├── StateMapper.java             # BFS traversal → StateMapping list
│       │   ├── StateMapping.java            # record: stateName, stateType, sdkPrimitive, params
│       │   └── GenerationResult.java        # record: orchestratorPath, handlerPaths, skipped
│       └── resources/templates/
│           ├── Orchestrator.java.ftl        # DurableHandler subclass with while-loop SM
│           └── HandlerStub.java.ftl         # User handler stub template
│
├── rsf-terraform/                   # Terraform HCL generator
│   ├── pom.xml
│   └── src/main/
│       ├── java/io/rsf/terraform/
│       │   ├── TerraformGenerator.java
│       │   └── TerraformConfig.java         # record: workflowName, region, namePrefix, backend
│       └── resources/templates/
│           ├── main.tf.ftl
│           ├── variables.tf.ftl
│           ├── iam.tf.ftl
│           ├── outputs.tf.ftl
│           ├── cloudwatch.tf.ftl
│           └── backend.tf.ftl
│
├── rsf-importer/                    # ASL JSON importer
│   ├── pom.xml
│   └── src/main/java/io/rsf/importer/
│       ├── AslImporter.java
│       ├── AslConverter.java
│       ├── ImportResult.java        # record: rsfDict, yamlText, warnings, taskStateNames
│       └── ImportWarning.java       # record: path, field, message, severity
│
├── rsf-runtime/                     # Runtime: annotations, registry, I/O pipeline
│   ├── pom.xml
│   └── src/main/java/io/rsf/runtime/
│       ├── annotation/
│       │   ├── State.java           # @State("StateName") annotation
│       │   └── Startup.java         # @Startup annotation
│       ├── registry/
│       │   ├── HandlerRegistry.java # Singleton; classpath scanning
│       │   └── HandlerFunction.java # Functional interface: Object apply(Object input)
│       ├── io/
│       │   ├── IOPipeline.java      # 5-stage I/O processing
│       │   ├── JsonPathEvaluator.java
│       │   ├── PayloadTemplate.java
│       │   └── ResultPath.java
│       └── functions/
│           ├── IntrinsicRegistry.java
│           ├── IntrinsicFunction.java   # Functional interface
│           └── impl/                   # 18 intrinsic function implementations
│
├── rsf-editor/                      # Graph editor Spring Boot server
│   ├── pom.xml
│   └── src/main/
│       ├── java/io/rsf/editor/
│       │   ├── EditorApplication.java      # @SpringBootApplication
│       │   ├── SchemaController.java       # GET /api/schema
│       │   └── EditorWebSocketHandler.java # TextWebSocketHandler at /ws
│       └── resources/
│           ├── application.yml
│           └── static/                    # React editor SPA build output
│
├── rsf-inspector/                   # Execution inspector Spring Boot server
│   ├── pom.xml
│   └── src/main/
│       ├── java/io/rsf/inspector/
│       │   ├── InspectorApplication.java    # @SpringBootApplication
│       │   ├── InspectorController.java     # REST + SSE endpoints
│       │   ├── LambdaInspectClient.java     # AWS SDK v2 Lambda client wrapper
│       │   └── ExecutionModels.java         # DTOs: ExecutionSummary, EventEntry
│       └── resources/
│           ├── application.yml
│           └── static/                     # React inspector SPA build output
│
└── rsf-cli/                         # Picocli CLI entry point
    ├── pom.xml
    └── src/main/java/io/rsf/cli/
        ├── RsfCli.java              # @Command(name="rsf", subcommands={...})
        ├── InitCommand.java         # @Command(name="init")
        ├── GenerateCommand.java     # @Command(name="generate")
        ├── ValidateCommand.java     # @Command(name="validate")
        ├── DeployCommand.java       # @Command(name="deploy")
        ├── ImportCommand.java       # @Command(name="import")
        ├── UiCommand.java           # @Command(name="ui")
        └── InspectCommand.java      # @Command(name="inspect")
```

### Structure Rationale

- **`rsf-dsl` as foundation:** All other modules depend on `rsf-dsl` for the `StateMachineDefinition` type. It has no upstream RSF dependencies, making it the correct build-order root.
- **`rsf-runtime` isolated:** The `@State`/`@Startup` annotations and handler registry are runtime-only — they ship in user Lambda deployment packages. They must not pull in codegen or Spring Boot dependencies.
- **`rsf-editor` and `rsf-inspector` as separate Spring Boot apps:** Each embeds its own React SPA in `resources/static/`. They are never deployed together — `rsf ui` starts the editor, `rsf inspect` starts the inspector.
- **`rsf-cli` depends on everything:** The CLI module is the only module allowed to depend on all other modules. This creates a clean star topology with rsf-cli at the center.
- **FreeMarker templates in `resources/`:** Templates live beside the Java source in the same module to keep codegen and terraform modules self-contained. `FreeMarker.getTemplate()` loads from classpath.

---

## Architectural Patterns

### Pattern 1: Jackson Polymorphic Deserialization with Sealed Interface

**What:** The DSL `State` type is a Java 17 sealed interface. Jackson discriminates on the `"Type"` field using `@JsonTypeInfo` + `@JsonSubTypes`. The Python version uses Pydantic discriminated unions — the Java equivalent is this annotation-driven pattern.

**When to use:** Anywhere the DSL has a type-discriminated union: `State` (8 types), `ChoiceRule` (4 types — DataTest, And, Or, Not).

**Trade-offs:** `@JsonSubTypes` requires explicitly listing every subtype — Java 17 sealed classes do not auto-register in Jackson 2.x. Jackson 3.x (not yet standard) would auto-discover sealed subtypes. Use explicit `@JsonSubTypes` for compatibility. The `jackson-modules-java17-sealed-classes` module is an alternative but adds a dependency.

**Example:**
```java
// State.java — sealed interface
@JsonTypeInfo(use = JsonTypeInfo.Id.NAME, property = "Type")
@JsonSubTypes({
    @JsonSubTypes.Type(value = TaskState.class,    name = "Task"),
    @JsonSubTypes.Type(value = PassState.class,    name = "Pass"),
    @JsonSubTypes.Type(value = ChoiceState.class,  name = "Choice"),
    @JsonSubTypes.Type(value = WaitState.class,    name = "Wait"),
    @JsonSubTypes.Type(value = SucceedState.class, name = "Succeed"),
    @JsonSubTypes.Type(value = FailState.class,    name = "Fail"),
    @JsonSubTypes.Type(value = ParallelState.class, name = "Parallel"),
    @JsonSubTypes.Type(value = MapState.class,     name = "Map"),
})
public sealed interface State
    permits TaskState, PassState, ChoiceState, WaitState,
            SucceedState, FailState, ParallelState, MapState {}

// TaskState.java — concrete type
@JsonIgnoreProperties(ignoreUnknown = false) // strict: reject unknown fields
public record TaskState(
    @JsonProperty("Type")          String type,
    @JsonProperty("Next")          String next,
    @JsonProperty("End")           Boolean end,
    @JsonProperty("Comment")       String comment,
    @JsonProperty("TimeoutSeconds") Integer timeoutSeconds,
    @JsonProperty("Retry")         List<RetryPolicy> retry,
    @JsonProperty("Catch")         List<Catcher> catch_
) implements State {}

// Parsing — DslParser.java
YAMLMapper mapper = new YAMLMapper();
mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, true);
StateMachineDefinition definition = mapper.readValue(yamlFile, StateMachineDefinition.class);
```

**Circular reference:** Python broke circular imports via late binding in `__init__.py`. In Java, `BranchDefinition` referencing `Map<String, State>` is fine — Java has no circular import issue. `StateMachineDefinition.states` is `Map<String, State>` and Jackson deserializes each value via the `State` discriminator at parse time.

---

### Pattern 2: DurableHandler Subclass with While-Loop State Machine

**What:** The generated orchestrator is a Java class extending `DurableHandler<Map<String,Object>, Map<String,Object>>`. The `handleRequest` method implements the same while-loop state machine pattern as the Python generated code, calling `context.step()`, `context.wait()`, etc.

**When to use:** This is the core output of `rsf generate`. Every workflow produces exactly one `DurableHandler` subclass.

**Trade-offs:** `parallel()` and `map()` are not yet available in the Java preview SDK as of 2026-02. FreeMarker templates must emit `TODO` comments with runtime exceptions for Parallel and Map states until the SDK adds them. Blueprint the template now; implement when SDK ships.

**Example (FreeMarker template `Orchestrator.java.ftl`):**
```java
// DO NOT EDIT — Generated by RSF v${rsfVersion} on ${timestamp}
// Source: ${dslFile} (SHA-256: ${dslHash})
package ${packageName};

import software.amazon.lambda.durable.DurableContext;
import software.amazon.lambda.durable.DurableHandler;
import io.rsf.runtime.registry.HandlerRegistry;
import java.util.Map;

public class ${className} extends DurableHandler<Map<String,Object>, Map<String,Object>> {

    private static boolean startupDone = false;

    @Override
    protected Map<String,Object> handleRequest(Map<String,Object> event, DurableContext context) {
        if (!startupDone) {
            HandlerRegistry.runStartupHooks();
            startupDone = true;
        }

        String currentState = "${startAt}";
        Map<String,Object> inputData = event;

        while (currentState != null) {
            <#list stateBlocks as block>
            <#if block?is_first>if<#else>} else if</#if> ("${block.name}".equals(currentState)) {
${block.code}
            </#list>
            } else {
                throw new IllegalStateException("Unknown state: " + currentState);
            }
        }
        return inputData;
    }
}
```

**State block example for Task state (emitter output inside the while-loop):**
```java
// Task state: ProcessOrder
HandlerFunction handler = HandlerRegistry.getHandler("ProcessOrder");
inputData = (Map<String,Object>) context.step("ProcessOrder", Object.class,
    () -> handler.apply(inputData));
currentState = "ValidatePayment";
```

**Java SDK mapping from Python SDK:**

| Python | Java |
|--------|------|
| `context.step(name, func, input)` | `context.step(name, Class<T>, CheckedSupplier<T>)` |
| `context.wait(name, Duration.seconds(n))` | `context.wait(name, Duration.ofSeconds(n))` |
| `context.parallel(name, branches, input)` | NOT YET AVAILABLE — emit `throw new UnsupportedOperationException("Parallel not yet in Java SDK")` |
| `context.map(name, func, items)` | NOT YET AVAILABLE — same |
| `BatchResult.get_results()` | N/A until parallel/map ships |

---

### Pattern 3: Annotation-Based Handler Registry with Classpath Scanning

**What:** Users annotate handler methods with `@State("StateName")` and `@Startup`. At Lambda cold start, `HandlerRegistry` scans classpath for annotated classes (using Spring's `ClassPathScanningCandidateComponentProvider` or Reflections library), registers each handler function. This mirrors the Python `@state("name")` decorator + `discover_handlers()` pattern.

**When to use:** This pattern lives in `rsf-runtime` and is used by the generated `DurableHandler` subclass.

**Trade-offs:** Full classpath scanning at cold start adds ~50-150ms. For Lambda, this is acceptable since it only happens on cold start. Alternative: compile-time annotation processing to generate a static registry, but this adds build complexity. Use runtime scanning for simplicity in preview.

**Example:**
```java
// User-authored handler (not generated):
package handlers;

import io.rsf.runtime.annotation.State;
import io.rsf.runtime.annotation.Startup;
import java.util.Map;

public class ProcessOrderHandler {

    @State("ProcessOrder")
    public Map<String, Object> processOrder(Map<String, Object> input) {
        // user business logic
        return Map.of("status", "processed", "orderId", input.get("orderId"));
    }

    @Startup
    public static void warmUp() {
        // cold-start initialization (e.g., DB connection pooling)
    }
}

// HandlerRegistry.java (in rsf-runtime):
public class HandlerRegistry {
    private static final Map<String, HandlerFunction> handlers = new HashMap<>();
    private static final List<Runnable> startupHooks = new ArrayList<>();

    public static void scanPackage(String basePackage) {
        // Use Reflections library or Spring ClassPathScanningCandidateComponentProvider
        Reflections reflections = new Reflections(basePackage);
        Set<Method> stateMethods = reflections.getMethodsAnnotatedWith(State.class);
        for (Method method : stateMethods) {
            String name = method.getAnnotation(State.class).value();
            Object instance = method.getDeclaringClass().getDeclaredConstructor().newInstance();
            handlers.put(name, input -> method.invoke(instance, input));
        }
        // Similar for @Startup methods
    }

    public static HandlerFunction getHandler(String stateName) {
        HandlerFunction fn = handlers.get(stateName);
        if (fn == null) throw new IllegalStateException("No handler for state: " + stateName);
        return fn;
    }

    public static void runStartupHooks() {
        startupHooks.forEach(Runnable::run);
    }
}
```

**Alternative — ServiceLoader approach:** Instead of classpath scanning, require users to register handlers via `META-INF/services/io.rsf.runtime.registry.HandlerProvider`. More explicit, zero reflection cost, but more user ceremony. Reserve this as an optimization path if cold start scanning proves too slow.

---

### Pattern 4: FreeMarker Templates for Code and HCL Generation

**What:** Replaces Jinja2 (Python) with FreeMarker (Java) for both code generation (`Orchestrator.java.ftl`, `HandlerStub.java.ftl`) and Terraform HCL generation (`main.tf.ftl`, etc.). Custom delimiters `[=...]`, `[#...]` syntax is available in FreeMarker but not needed — HCL uses `${}` which FreeMarker 2.x does NOT conflict with by default (FreeMarker uses `${...}` in templates, but HCL also uses `${...}` — this IS a conflict).

**When to use:** All template rendering in `rsf-codegen` and `rsf-terraform`.

**Trade-offs:** HCL `${}` conflicts with FreeMarker `${}` default syntax. Python solved this with custom Jinja2 delimiters (`<< >>`, `<% %>`). FreeMarker solution: use the `[=...]` alternate expression syntax (`[#ftl][= variable ]`) or escape HCL interpolations as `${"$"}{...}` in templates. The escape approach is less readable but simpler to configure. Use `[=...]` alternate syntax for all FreeMarker expressions in HCL templates.

**Example:**
```
[#-- main.tf.ftl — use [=...] syntax to avoid ${ } conflict with HCL --]
# DO NOT EDIT - Generated by RSF
resource "aws_lambda_function" "[=resourceId]" {
  filename      = "${aws_s3_object.function_zip.key}"
  function_name = "${local.function_name}"
  role          = aws_iam_role.lambda_role.arn
  handler       = "generated.Orchestrator"
  runtime       = "java25"

  durable_config {
    enabled          = true
    retention_period = 1
  }
}
```

**FreeMarker configuration in Java:**
```java
Configuration cfg = new Configuration(Configuration.VERSION_2_3_32);
cfg.setClassForTemplateLoading(TerraformGenerator.class, "/templates");
cfg.setTagSyntax(Configuration.SQUARE_BRACKET_TAG_SYNTAX); // use [#...] and [=...]
cfg.setDefaultEncoding("UTF-8");
Template template = cfg.getTemplate("main.tf.ftl");
```

---

### Pattern 5: Spring Boot with Raw WebSocket (No STOMP) and SseEmitter

**What:** The graph editor uses `TextWebSocketHandler` (raw WebSocket, no STOMP) for bidirectional YAML ↔ graph sync messages. The inspector uses `SseEmitter` in a `@RestController` for live execution updates. This directly mirrors the Python FastAPI WebSocket and SSE implementations.

**When to use:** `rsf-editor` and `rsf-inspector` modules.

**Trade-offs:** Raw WebSocket is simpler than STOMP for a point-to-point (1 client, 1 server) use case. `SseEmitter` requires careful lifecycle management — always call `emitter.complete()` or `emitter.completeWithError()` to release threads. Use a dedicated `ExecutorService` for SSE event dispatch.

**Graph Editor WebSocket (rsf-editor):**
```java
@Configuration
@EnableWebSocket
public class EditorWebSocketConfig implements WebSocketConfigurer {
    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(editorWebSocketHandler(), "/ws").setAllowedOrigins("*");
    }
    @Bean public EditorWebSocketHandler editorWebSocketHandler() { return new EditorWebSocketHandler(); }
}

public class EditorWebSocketHandler extends TextWebSocketHandler {
    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        // Parse JSON message: {type: "yaml_to_graph" | "graph_to_yaml", payload: ...}
        // Apply DSL parsing + validation; send response back via session.sendMessage()
    }
}
```

**Inspector SSE (rsf-inspector):**
```java
@RestController
@RequestMapping("/api/inspect")
public class InspectorController {
    private final LambdaInspectClient client;
    private final ExecutorService sseExecutor = Executors.newCachedThreadPool();

    @GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter streamExecutions(@RequestParam String functionName) {
        SseEmitter emitter = new SseEmitter(Long.MAX_VALUE);
        sseExecutor.submit(() -> {
            try {
                while (!Thread.interrupted()) {
                    List<ExecutionSummary> executions = client.listExecutions(functionName);
                    emitter.send(SseEmitter.event()
                        .name("executions")
                        .data(executions, MediaType.APPLICATION_JSON));
                    Thread.sleep(1000); // token bucket: max 12 req/s, 1s interval is safe
                }
            } catch (Exception e) {
                emitter.completeWithError(e);
            }
        });
        return emitter;
    }

    @GetMapping("/executions")
    public List<ExecutionSummary> listExecutions(@RequestParam String functionName) { ... }

    @GetMapping("/executions/{arn}")
    public ExecutionDetail getExecution(@PathVariable String arn) { ... }
}
```

---

### Pattern 6: Generation Gap Pattern in Java

**What:** Generated Java files have `// DO NOT EDIT — Generated by RSF` as the first line. The `CodeGenerator` checks this marker before overwriting. User handler stubs without the marker are never touched on subsequent `rsf generate` runs. Identical semantics to the Python implementation.

**When to use:** Both `rsf-codegen` (Java source generation) and `rsf-terraform` (HCL generation).

**Trade-offs:** None — same proven pattern from Python implementation.

**Implementation:**
```java
private boolean shouldOverwrite(Path path) throws IOException {
    if (!Files.exists(path)) return true;
    try (BufferedReader reader = Files.newBufferedReader(path)) {
        String firstLine = reader.readLine();
        return firstLine != null && firstLine.stripLeading().startsWith("// DO NOT EDIT — Generated by RSF");
    }
}
```

---

### Pattern 7: Maven exec-maven-plugin for `rsf generate` Integration

**What:** The `rsf generate` command can be wired into the Maven build lifecycle via `exec-maven-plugin`, so users can run `mvn rsf:generate` or bind it to the `generate-sources` phase. This provides the same DX as `rsf generate` CLI but integrated into Maven builds.

**When to use:** As an optional convenience in `rsf-cli`. The primary interface remains the `rsf generate` CLI command. The Maven integration is a secondary option for CI/CD pipelines.

**Trade-offs:** A custom Maven Mojo would be cleaner but requires a separate `rsf-maven-plugin` module and Maven plugin project boilerplate. `exec-maven-plugin` is sufficient and avoids the extra module. Use `exec:java` goal to run `io.rsf.cli.RsfCli generate` as a Maven-integrated invocation.

**Example `pom.xml` snippet for user projects:**
```xml
<plugin>
    <groupId>org.codehaus.mojo</groupId>
    <artifactId>exec-maven-plugin</artifactId>
    <version>3.3.0</version>
    <executions>
        <execution>
            <id>rsf-generate</id>
            <phase>generate-sources</phase>
            <goals><goal>java</goal></goals>
            <configuration>
                <mainClass>io.rsf.cli.RsfCli</mainClass>
                <arguments>
                    <argument>generate</argument>
                    <argument>${project.basedir}/workflow.yaml</argument>
                    <argument>--output</argument>
                    <argument>${project.build.directory}/generated-sources/rsf</argument>
                </arguments>
            </configuration>
        </execution>
    </executions>
</plugin>
```

---

## Data Flow

### DSL Parsing Flow

```
workflow.yaml
    │
    ▼
DslParser.parse(Path yamlFile)
    │  YAMLMapper.readValue() → Jackson dispatches on "Type" field
    ▼
StateMachineDefinition
    ├── startAt: String
    └── states: Map<String, State>  ← each State is sealed interface subtype
            ├── "Validate": TaskState
            ├── "Route":    ChoiceState
            └── "Done":     SucceedState
    │
    ▼
DslValidator.validate(StateMachineDefinition)
    │  BFS from startAt; check reachability, transition targets, mutual exclusions
    ▼
ValidationResult (errors list; throws DslValidationException if non-empty)
```

### Code Generation Flow

```
StateMachineDefinition
    │
    ▼
StateMapper.mapStates(definition)   ← BFS traversal; same algorithm as Python
    │  Returns List<StateMapping> in BFS visit order
    ▼
List<StateMapping>
    │
    ▼
CodeGenerator.generate(definition, mappings, dslPath, outputDir)
    │
    ├── renderOrchestrator(mappings)
    │       │  FreeMarker: Orchestrator.java.ftl
    │       ▼
    │   src/generated/Orchestrator.java     (always overwritten — has marker)
    │
    └── renderHandlerStubs(taskMappings)
            │  FreeMarker: HandlerStub.java.ftl
            ▼
        src/handlers/ProcessOrder.java      (skipped if no marker — user file)
        src/handlers/ValidatePayment.java   (skipped if no marker — user file)
```

### Runtime Execution Flow (Generated Code)

```
Lambda invocation → DurableHandler.handleRequest(event, context)
    │
    ├── [cold start] HandlerRegistry.scanPackage("handlers")
    │       └── Reflections: find @State/@Startup methods → register
    │
    ├── [cold start] HandlerRegistry.runStartupHooks()
    │
    └── while-loop state machine:
            currentState = "ProcessOrder"
            │
            ├── "ProcessOrder" → context.step("ProcessOrder", Object.class,
            │                       () -> registry.getHandler("ProcessOrder").apply(inputData))
            │   inputData = result; currentState = "Validate"
            │
            ├── "Validate" → ... (next state)
            │
            └── null → return inputData
```

### UI Backend API Flow

```
rsf ui (editor):
  Browser → GET /api/schema → SchemaController → JSON Schema of DSL (from Jackson models)
  Browser → WS /ws → EditorWebSocketHandler →
      receive: {type:"yaml_to_graph", yaml:"..."} → DslParser → graph elements JSON
      receive: {type:"graph_to_yaml", graph:{...}} → YAML merge → emit updated YAML

rsf inspect (inspector):
  Browser → GET /api/inspect/executions?functionName=X → LambdaInspectClient → AWS Lambda
  Browser → GET /api/inspect/stream?functionName=X → SseEmitter → polling loop → SSE events
  Browser → GET /api/inspect/executions/{arn} → LambdaInspectClient → execution detail JSON
```

### Cross-Module Dependency Flow

```
rsf-dsl        (no RSF deps)
    ▲
    │ depends on
rsf-codegen    (depends on rsf-dsl for StateMachineDefinition, StateMapping)
rsf-terraform  (depends on rsf-dsl for workflow metadata)
rsf-importer   (depends on rsf-dsl for model types; calls rsf-codegen for stubs)
rsf-runtime    (no RSF deps — ships in Lambda; @State/@Startup annotations)
rsf-editor     (depends on rsf-dsl for DslParser, JSON Schema generation)
rsf-inspector  (depends on rsf-dsl for model types; uses AWS SDK directly)
    ▲
    │ depends on all above
rsf-cli        (depends on all modules; Picocli entry point)
```

---

## Build Order

The Maven Reactor resolves build order from `<dependencies>` in each module's `pom.xml`. Declare the correct dependencies and Maven handles ordering automatically:

```
1. rsf-dsl          (no RSF deps → builds first)
2. rsf-runtime      (no RSF deps → builds in parallel with rsf-dsl)
3. rsf-codegen      (depends on rsf-dsl)
4. rsf-terraform    (depends on rsf-dsl)
5. rsf-importer     (depends on rsf-dsl, rsf-codegen)
6. rsf-editor       (depends on rsf-dsl)
7. rsf-inspector    (depends on rsf-dsl)
8. rsf-cli          (depends on all above → builds last)
```

React UI build (if embedding in Spring Boot JARs): run `npm run build` via `frontend-maven-plugin` in `rsf-editor` and `rsf-inspector` modules before the Java compilation phase.

---

## Sharing React UIs Between Editor and Inspector Backends

The Python version has two separate FastAPI servers — the graph editor and the execution inspector — each bundled with its own React SPA build. The React source code is shared (single `ui/` directory), but the build outputs are separate (embedded in the Python package's `editor/static/` and `inspect/static/` respectively).

**Java approach — same principle:**

The React source code is unchanged (zero React code modifications). The same `ui/` directory from the Python project produces two build outputs via Vite. Each Spring Boot module embeds its own SPA:

```
ui/                             ← shared React source (unchanged from Python version)
├── src/
│   ├── main.tsx               ← entry point: mounts EditorApp or InspectorApp based on URL
│   ├── App.tsx                ← graph editor
│   └── inspector/
│       └── InspectorApp.tsx   ← execution inspector
├── vite.config.ts
└── package.json

Build outputs:
  npm run build:editor   → rsf-editor/src/main/resources/static/
  npm run build:inspector → rsf-inspector/src/main/resources/static/
```

**Vite configuration for two build targets:**
```typescript
// vite.config.ts — add a --mode flag to select entry point
export default defineConfig(({ mode }) => ({
  build: {
    rollupOptions: {
      input: mode === 'inspector' ? 'src/inspector-entry.html' : 'index.html',
      outDir: mode === 'inspector' ? '../rsf-java/rsf-inspector/src/main/resources/static'
                                   : '../rsf-java/rsf-editor/src/main/resources/static',
    }
  }
}));
```

**Maven integration via frontend-maven-plugin:**
```xml
<!-- In rsf-editor/pom.xml and rsf-inspector/pom.xml -->
<plugin>
    <groupId>com.github.eirslett</groupId>
    <artifactId>frontend-maven-plugin</artifactId>
    <version>1.15.0</version>
    <executions>
        <execution>
            <id>build-react</id>
            <phase>generate-resources</phase>
            <goals><goal>npm</goal></goals>
            <configuration>
                <workingDirectory>../ui</workingDirectory>
                <arguments>run build:editor</arguments>  <!-- or build:inspector -->
            </configuration>
        </execution>
    </executions>
</plugin>
```

**API contract (unchanged from Python):** The React code communicates with the backend over the same REST/WebSocket/SSE API routes. The only change is the URL base path shifts from `http://127.0.0.1:8765` (Python FastAPI) to `http://127.0.0.1:8765` (Spring Boot) — same port, same paths. Zero React changes required.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| AWS Lambda Durable SDK | `DurableHandler<I,O>` base class; `DurableContext` injected | Maven: `software.amazon.lambda.durable:aws-durable-execution-sdk-java`; Java 17+; container-image deploy only |
| AWS SDK v2 (Lambda client) | `LambdaAsyncClient` or `LambdaClient` in rsf-inspector | For `listDurableExecutionsByFunction`, `getDurableExecution` calls |
| Terraform CLI | `ProcessBuilder` invocation in `DeployCommand`; same pattern as Python `subprocess.run` | rsf-cli calls `terraform init`, `terraform apply`, `terraform output -json`, `terraform destroy` |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `rsf-dsl` → `rsf-codegen` | `StateMapping` records and `StateMachineDefinition` passed directly (same JVM) | No serialization needed across module boundary |
| `rsf-codegen` → `rsf-terraform` | No direct dependency; both depend on `rsf-dsl` | `rsf-cli` orchestrates both |
| `rsf-editor` ↔ React UI | HTTP REST + WebSocket at `/api/schema`, `/ws` | Same API contract as Python FastAPI |
| `rsf-inspector` ↔ React UI | HTTP REST + SSE at `/api/inspect/**` | Same API contract as Python FastAPI |
| `rsf-runtime` → generated code | `HandlerRegistry` accessed at Lambda runtime; classpath must include `rsf-runtime` JAR | Generated `Orchestrator.java` imports `io.rsf.runtime.registry.HandlerRegistry` |
| `rsf-importer` → `rsf-codegen` | Calls `CodeGenerator.renderHandlerStub(stateName)` for stub generation | Reuse, no duplication |

### New vs Modified Components

**New (created from scratch in Java):**
- All 8 Maven modules with `pom.xml` and Java sources
- `State.java` sealed interface + 8 concrete record types
- `ChoiceRule.java` sealed interface + 4 concrete record types
- `HandlerRegistry.java` with reflection-based classpath scanning
- `@State`/`@Startup` annotation types
- `IOPipeline.java` — 5-stage pipeline (Java port of Python `rsf/io/pipeline.py`)
- `JsonPathEvaluator.java` — JSONPath evaluation (consider Jayway JsonPath library instead of reimplementing)
- `IntrinsicRegistry.java` + 18 intrinsic function implementations
- `EditorWebSocketHandler.java` — raw WebSocket handler (replaces FastAPI WebSocket)
- `InspectorController.java` with `SseEmitter` (replaces sse-starlette + FastAPI)
- `LambdaInspectClient.java` — AWS SDK v2 wrapper (port of Python `rsf/inspect/client.py`)
- FreeMarker templates (`*.ftl`) replacing Jinja2 templates (`*.j2`)
- Parent `pom.xml` with version management

**Modified (adapted from Python source):**
- React UIs: add `vite.config.ts` multi-build support (`build:editor`, `build:inspector`)
- Terraform HCL templates: update `runtime` from `python3.13` to `java25`; update `handler` to `io.rsf.generated.Orchestrator`; add container image support

**Not modified:**
- React source code (`ui/src/**`) — zero changes
- Terraform HCL template logic (IAM statements, CloudWatch, outputs) — same structure, only runtime/handler differ
- DSL YAML format — 100% identical to Python; same `.yaml` files parse correctly in Java

---

## Deployment Constraint: Container Image Required

**Critical:** The Java Durable Execution SDK preview (as of 2026-02) only supports container image deployment. There is no managed `java25` runtime with durable function support — only container images using `public.ecr.aws/lambda/java:25` as the base.

This means:
1. `rsf-terraform` templates must generate a `Dockerfile` and ECR repository resource instead of zip-based Lambda
2. `rsf deploy` in Java must build and push a Docker image before `terraform apply`
3. The Terraform `aws_lambda_function` resource uses `package_type = "Image"` instead of `filename`

**Generated Dockerfile template:**
```dockerfile
FROM --platform=linux/amd64 public.ecr.aws/lambda/java:25
RUN dnf install -y maven
WORKDIR /var/task
COPY pom.xml .
COPY src ./src
RUN mvn clean package -DskipTests
RUN mv target/*.jar lib/
CMD ["io.rsf.generated.Orchestrator::handleRequest"]
```

This is a significant architectural difference from the Python version (which uses zip-based Lambda). The deploy pipeline in `rsf-cli`'s `DeployCommand` must orchestrate: `docker build` → `docker push` (to ECR) → `terraform apply`.

---

## Anti-Patterns

### Anti-Pattern 1: Putting Spring Boot in rsf-runtime

**What people do:** Add `spring-context` or Spring's classpath scanner to `rsf-runtime` for handler discovery.
**Why it's wrong:** `rsf-runtime` ships inside the Lambda deployment package. Spring Boot adds ~10-20MB and significant cold start overhead to every Lambda function that uses RSF. Users would pay the Spring cold start tax even for the simplest workflows.
**Do this instead:** Use Reflections library (`org.reflections:reflections`) in `rsf-runtime` for classpath scanning — it is lightweight (~500KB) and has no Spring dependency. Reserve Spring for `rsf-editor` and `rsf-inspector` only.

### Anti-Pattern 2: Using Jackson for HCL Generation

**What people do:** Build a Java object model for HCL and serialize it to Terraform format.
**Why it's wrong:** HCL is not JSON. Terraform's `${}` syntax, `<<EOT` heredocs, and block syntax cannot be expressed as a Jackson tree. The template approach (FreeMarker) is correct and proven.
**Do this instead:** FreeMarker templates with `[=...]` alternate expression syntax to avoid `${}` conflicts with HCL interpolations.

### Anti-Pattern 3: Synchronous Lambda Invocation in Inspector

**What people do:** Call `LambdaClient.invoke()` with `InvocationType = RequestResponse` expecting to get durable execution results.
**Why it's wrong:** Durable Lambda functions require `InvocationType = Event` (async). Synchronous invocation returns immediately with an empty body — it does not wait for the durable orchestrator to complete.
**Do this instead:** `InvocationType = Event` → poll `listDurableExecutionsByFunction` → `getDurableExecution` for result. The `LambdaInspectClient` must enforce this pattern.

### Anti-Pattern 4: One Spring Boot App Serving Both UIs

**What people do:** Combine `rsf-editor` and `rsf-inspector` into one Spring Boot application.
**Why it's wrong:** The editor has no AWS dependency and can run without AWS credentials. The inspector requires AWS credentials and a function name. Combining them forces the editor to carry AWS SDK dependencies and credential configuration. Users run `rsf ui` and `rsf inspect` as separate processes.
**Do this instead:** Two separate Spring Boot apps (`rsf-editor` on port 8765, `rsf-inspector` on port 8766). Each embeds its own React SPA. `rsf-cli` starts the correct one based on the subcommand.

### Anti-Pattern 5: Ignoring parallel/map SDK Gaps

**What people do:** Generate code that calls `context.parallel()` or `context.map()` as if they work in the Java preview SDK.
**Why it's wrong:** As of 2026-02, `parallel` and `map` are explicitly "still in development" in the Java SDK. Generated code that calls them will throw `UnsupportedOperationException` at runtime.
**Do this instead:** FreeMarker templates for Parallel and Map states emit a clear `throw new UnsupportedOperationException("Parallel state not yet supported in Java SDK preview — track aws/aws-durable-execution-sdk-java#XXX")` with a generation-time warning. The blueprint documents this gap explicitly so the roadmap includes a phase to add them once the SDK ships support.

---

## Scaling Considerations

RSF is a developer-local tool. Scaling means "more users installing it" not "more traffic." The main scaling considerations are cold start latency (for Lambda) and build time (for Maven).

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Single developer | Current multi-module Maven structure is correct. `mvn install` from root builds everything. |
| Team adoption | Publish modules to a Maven repository (Nexus/Artifactory or GitHub Packages). Users add `rsf-runtime` to their Lambda `pom.xml` as a dependency. `rsf-cli` distributed as a fat JAR or native GraalVM binary. |
| Cold start optimization | Replace Reflections classpath scanning with compile-time annotation processing (APT) generating a static `HandlerRegistration.java`. Eliminates runtime reflection entirely. |

---

## Sources

- [AWS Lambda Durable Execution SDK for Java — Developer Preview announcement](https://aws.amazon.com/about-aws/whats-new/2026/02/lambda-durable-execution-java-preview/) (HIGH confidence)
- [Durable Execution SDK — AWS Lambda docs](https://docs.aws.amazon.com/lambda/latest/dg/durable-execution-sdk.html) — Java API reference (HIGH confidence)
- [Supported runtimes for durable functions](https://docs.aws.amazon.com/lambda/latest/dg/durable-supported-runtimes.html) — container image requirement for Java (HIGH confidence)
- [aws/aws-durable-execution-sdk-java — GitHub](https://github.com/aws/aws-durable-execution-sdk-java/) — DurableHandler, DurableContext, TypeToken, DurableFuture API (HIGH confidence)
- [Jackson Polymorphic Deserialization — FasterXML wiki](https://github.com/FasterXML/jackson-docs/wiki/JacksonPolymorphicDeserialization) — @JsonTypeInfo/@JsonSubTypes pattern (HIGH confidence)
- [Jackson modules for Java 17 sealed classes — GitHub](https://github.com/sigpwned/jackson-modules-java-17-sealed-classes) — 2.x module for sealed class support (MEDIUM confidence — third party)
- [Jackson Release 2.17](https://github.com/FasterXML/jackson/wiki/Jackson-Release-2.17) — confirmed sealed class auto-detection is Jackson 3.x only (HIGH confidence)
- [Apache FreeMarker — Download](https://freemarker.apache.org/freemarkerdownload.html) — current version, Java 8+ compatible (HIGH confidence)
- [FreeMarker alternate tag syntax](https://freemarker.apache.org/docs/dgui_misc_alternativesyntax.html) — `[#...]`/`[=...]` to avoid HCL `${}` conflict (HIGH confidence)
- [Picocli — quick guide](https://picocli.info/quick-guide.html) — subcommand pattern, annotation API (HIGH confidence)
- [Spring Boot WebSocket without STOMP — DevGlan](https://www.devglan.com/spring-boot/spring-websocket-integration-example-without-stomp) — TextWebSocketHandler pattern (MEDIUM confidence)
- [Spring Boot SseEmitter — Baeldung](https://www.baeldung.com/spring-mvc-sse-streams) — SseEmitter lifecycle, ExecutorService pattern (HIGH confidence)
- [Maven multi-module guide — maven.apache.org](https://maven.apache.org/guides/mini/guide-multiple-modules.html) — Reactor build ordering (HIGH confidence)
- [exec-maven-plugin — exec:java goal](https://www.mojohaus.org/exec-maven-plugin/java-mojo.html) — mainClass, arguments configuration (HIGH confidence)
- [frontend-maven-plugin — GitHub](https://github.com/eirslett/frontend-maven-plugin) — npm build in Maven lifecycle (HIGH confidence)
- [Serving React SPA from Spring Boot — Medium](https://medium.com/@AlexanderObregon/serving-frontend-builds-from-spring-boot-backends-63177bbd0b74) — static file serving pattern (MEDIUM confidence)
- [Reflections library — GitHub/classgraph](https://github.com/classgraph/classgraph) — classpath scanning for annotations (HIGH confidence)
- RSF Python source code (direct inspection): `src/rsf/` — all Python-to-Java mapping decisions derived from codebase inspection

---
*Architecture research for: RSF v1.6 Java Port Blueprint*
*Researched: 2026-02-28*
