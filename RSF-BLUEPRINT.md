# RSF — Replacement for Step Functions: Full Blueprint

> **Purpose:** This document is a complete project specification for recreating RSF from scratch in a new workspace using the `/gsd:new-project` workflow. It describes every feature, architecture decision, data model, template strategy, API endpoint, and testing pattern needed to rebuild the project without access to the original codebase.
>
> **Scope:** Python-only implementation. No Go/multi-language support.

---

## What This Is

RSF is a complete replacement for AWS Step Functions built on **AWS Lambda Durable Functions** (launched at re:Invent 2025). It provides:

1. A **YAML/JSON-based DSL** for defining state machines with all 8 ASL state types
2. A **Python code generator** that produces Lambda Durable Functions SDK code from the DSL
3. A **React-based visual graph editor** with bidirectional YAML ↔ graph synchronization
4. **Terraform infrastructure generation** for Lambda + supporting AWS resources
5. An **ASL JSON importer** for migrating existing Step Functions workflows
6. A **CLI toolchain** (`rsf init`, `rsf generate`, `rsf validate`, `rsf deploy`, `rsf import`, `rsf ui`, `rsf inspect`)
7. An **execution inspector** with time machine scrubbing, live updates, and structural data diffs

Users define workflows in the DSL, generate deployment-ready Lambda code, connect business logic via `@state` decorators, deploy via Terraform, and inspect execution state with a web-based debugger. Five real-world example workflows with integration tests prove end-to-end correctness on real AWS. Eight step-by-step tutorials cover all CLI commands. Automated Playwright screenshots provide visual documentation.

## Core Value

Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.

## Who It's For

Developers building workflows on AWS who want the power of Step Functions with the flexibility of Lambda Durable Functions, using a local-first dev tool (no hosted service, no auth complexity).

## What "Done" Looks Like

A developer can:
1. `rsf init my-project` → scaffold a complete project
2. Edit `workflow.yaml` (or use the graph editor via `rsf ui`)
3. `rsf generate` → produce Python Lambda handler code
4. Implement business logic in handler files using `@state("StateName")` decorators
5. `rsf deploy` → deploy to AWS via Terraform
6. `rsf inspect` → debug running/past executions with time machine
7. `rsf import asl.json` → migrate an existing Step Functions workflow

---

## Technical Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| DSL Models | Pydantic v2 | Latest | Schema validation, serialization, discriminated unions |
| DSL Parsing | PyYAML | Latest | YAML/JSON file parsing |
| Code Generation | Jinja2 | Latest | Template-based Python code rendering |
| CLI | Typer | Latest | Command-line interface with subcommands |
| Web Backend | FastAPI | Latest | REST + WebSocket + SSE server |
| SSE | sse-starlette | Latest | Server-sent events for inspector live updates |
| ASGI Server | uvicorn | Latest | Serves FastAPI app |
| AWS SDK | boto3 | Latest | Lambda API, durable execution API |
| IaC | Terraform | >= 1.0 | Infrastructure generation (HCL templates) |
| UI Framework | React | 19.x | Graph editor + inspector SPA |
| Graph Library | @xyflow/react | 12.x | Directed graph visualization, drag-drop, zoom/pan |
| State Mgmt | Zustand | 5.x | Lightweight React state management |
| Code Editor | @monaco-editor/react | 4.x | YAML editor with schema validation |
| YAML Support | monaco-yaml | 5.x | Monaco language features for YAML |
| Graph Layout | elkjs | 0.11.x | Sugiyama layered auto-layout algorithm |
| Immutable | immer | 11.x | Immutable state updates in Zustand |
| YAML (JS) | js-yaml | 4.x | Client-side YAML parse/stringify |
| Build | Vite | Latest | React app bundling |
| Test (Python) | pytest | Latest | Unit + integration tests |
| Test (JS) | vitest | Latest | React component + logic tests |
| Screenshot | @playwright/test | 1.58.2 | Browser automation for screenshot capture |
| TS Runner | tsx | 4.19.4 | Node TypeScript execution for scripts |

**Runtime Requirement:** Python 3.13+ (Lambda Durable Functions SDK requirement)

---

## AWS Lambda Durable Functions

### What It Is

Lambda Durable Functions (launched re:Invent 2025) adds checkpoint/replay to AWS Lambda. The SDK provides two primitives:

- **`context.step(name, func, *args)`** — Automatic checkpointing. Executes `func`, checkpoints the result. On replay, returns the checkpointed result without re-executing.
- **`context.wait(duration)`** — Suspend without compute cost. The Lambda stops, resumes after the duration (up to 1 year).

Additional primitives:
- **`context.parallel(branches)`** — Execute multiple functions concurrently, returns `BatchResult` (call `.get_results()` for plain list)
- **`context.map(items, func)`** — Map a function over items, returns `BatchResult`

### SDK Package

```
aws_lambda_durable_execution_sdk_python
```

Key imports:
- `DurableContext` — injected into the handler
- `durable_execution` — decorator for the Lambda entry point
- `Duration` — duration specification for waits (lives in `aws_lambda_durable_execution_sdk_python.config`)

### Lambda Configuration

The Lambda function resource requires a `durable_config` block:

```hcl
resource "aws_lambda_function" "workflow" {
  # ... standard config ...

  durable_config {
    execution_timeout = var.execution_timeout  # 1-31622400 seconds
    retention_period  = var.retention_period    # 1-90 days
  }
}
```

**AWS provider >= 6.25.0 required** for the `durable_config` block.

### Durable Execution APIs

For the inspector, these boto3 Lambda APIs are used:
- `list_durable_executions_by_function(FunctionName=...)` — List executions with status filter
- `get_durable_execution(FunctionName=..., ExecutionId=...)` — Execution detail
- Events are embedded in execution detail (history of state transitions)

**Rate limiting:** Lambda control plane has a 15 req/s limit. Use a token bucket rate limiter (12 req/s ceiling) to prevent throttling.

### Invocation Pattern

Durable Lambda invocation uses **Event type** (async). Poll `list_durable_executions_by_function` to check completion status.

---

## Directory Structure

```
rsf/
├── src/rsf/
│   ├── __init__.py              # Package version
│   ├── cli/                     # Typer CLI application
│   │   ├── main.py              # App with --version, subcommands
│   │   ├── config.py            # Project configuration (rsf.yaml)
│   │   ├── console.py           # Rich console utilities
│   │   ├── init_cmd.py          # rsf init
│   │   ├── generate_cmd.py      # rsf generate
│   │   ├── validate_cmd.py      # rsf validate
│   │   ├── deploy_cmd.py        # rsf deploy
│   │   ├── import_cmd.py        # rsf import
│   │   ├── ui_cmd.py            # rsf ui
│   │   ├── inspect_cmd.py       # rsf inspect
│   │   └── templates/           # Project scaffolding templates
│   │       ├── workflow.yaml.j2
│   │       ├── pyproject.toml.j2
│   │       ├── handler_example.py.j2
│   │       ├── test_example.py.j2
│   │       └── gitignore.j2
│   ├── dsl/                     # Pydantic v2 DSL models
│   │   ├── __init__.py          # State union assembly (breaks circular imports)
│   │   ├── models.py            # 8 state types + StateMachineDefinition
│   │   ├── choice.py            # Choice rules (39 operators, boolean logic)
│   │   ├── errors.py            # RetryPolicy, Catcher
│   │   ├── types.py             # QueryLanguage, COMPARISON_OPERATORS
│   │   ├── parser.py            # YAML/JSON loading + Pydantic validation
│   │   └── validator.py         # Semantic cross-state validation (BFS)
│   ├── codegen/                 # Jinja2 code generation
│   │   ├── engine.py            # Jinja2 environment setup
│   │   ├── generator.py         # Orchestrator: parse → map → render
│   │   ├── state_mappers.py     # State → SDK primitive mapping (BFS)
│   │   └── templates/
│   │       ├── workflow.py.j2   # Generated orchestrator
│   │       ├── handler_stub.py.j2  # Per-task handler stub
│   │       └── _macros.j2       # State-specific render macros
│   ├── terraform/               # HCL generation
│   │   ├── engine.py            # Jinja2 env with custom HCL delimiters
│   │   ├── generator.py         # Generation Gap + template rendering
│   │   ├── iam.py               # IAM permission derivation
│   │   └── templates/
│   │       ├── main.tf.j2       # Lambda + durable_config
│   │       ├── variables.tf.j2  # Input variables with validation
│   │       ├── iam.tf.j2        # IAM role + policy
│   │       ├── outputs.tf.j2    # function_arn, function_name, role_arn
│   │       ├── cloudwatch.tf.j2 # Log group
│   │       └── backend.tf.j2    # Optional S3 remote state
│   ├── importer/                # ASL JSON import pipeline
│   │   ├── parser.py            # JSON parsing with error detail
│   │   ├── converter.py         # ASL dict → RSF dict + warnings
│   │   ├── emitter.py           # Dict → YAML output
│   │   └── stubs.py             # Handler stub generation from import
│   ├── inspect/                 # Execution inspector
│   │   ├── models.py            # ExecutionSummary, HistoryEvent, etc.
│   │   ├── lambda_client.py     # Async boto3 wrapper with rate limiting
│   │   └── router.py            # FastAPI router (/api/inspect/*)
│   ├── io/                      # I/O processing pipeline
│   │   ├── pipeline.py          # 5-stage JSONPath pipeline
│   │   ├── jsonpath.py          # ASL-subset JSONPath evaluator
│   │   ├── payload_template.py  # Parameter/ResultSelector resolution
│   │   ├── result_path.py       # ResultPath merge logic
│   │   ├── jsonata.py           # JSONata expression evaluator
│   │   └── types.py             # VariableStoreProtocol
│   ├── functions/               # ASL intrinsic functions
│   │   ├── registry.py          # @intrinsic decorator + registry
│   │   ├── parser.py            # Recursive descent intrinsic parser
│   │   ├── array.py             # States.Array, States.ArrayPartition, etc.
│   │   ├── encoding.py          # States.Base64Encode/Decode, States.Hash
│   │   ├── json_funcs.py        # States.JsonToString, States.StringToJson
│   │   ├── math.py              # States.MathRandom, States.MathAdd
│   │   ├── string.py            # States.Format, States.StringSplit
│   │   └── utility.py           # States.UUID
│   ├── context/                 # ASL Context Object
│   │   └── model.py             # ExecutionContext, StateContext, etc.
│   ├── registry/                # Handler + startup registries
│   │   ├── registry.py          # @state, @startup decorators
│   │   └── discovery.py         # Auto-import handlers from directory
│   ├── variables/               # Variable store & resolver
│   │   ├── resolver.py          # $varName detection
│   │   └── store.py             # Runtime variable store
│   └── schema/                  # JSON Schema generation
│       └── generate.py          # Extract schema from Pydantic models
├── ui/                          # React SPA (built separately)
│   ├── src/
│   │   ├── App.tsx              # Main editor app
│   │   ├── InspectApp.tsx       # Inspector app
│   │   ├── main.tsx             # Entry point
│   │   ├── components/          # React components
│   │   ├── nodes/               # Per-state-type graph nodes
│   │   ├── edges/               # Custom transition edges
│   │   ├── store/               # Zustand stores (flow + inspect)
│   │   ├── sync/                # WebSocket, SSE, AST↔Flow converters
│   │   ├── layout/              # ELK.js auto-layout
│   │   └── types/               # TypeScript type definitions
│   ├── scripts/                 # Screenshot automation (TypeScript)
│   │   ├── capture-screenshots.ts   # Main orchestration: 15 PNGs via Playwright
│   │   ├── start-ui-server.ts       # Graph editor server lifecycle
│   │   ├── start-inspect-server.ts  # Mock inspect server lifecycle
│   │   ├── mock-inspect-server.ts   # HTTP server emulating inspect API
│   │   ├── smoke-test.ts            # Playwright connectivity check
│   │   └── fixtures/                # Mock execution data (1 JSON per example)
│   │       ├── order-processing.json
│   │       ├── approval-workflow.json
│   │       ├── data-pipeline.json
│   │       ├── retry-and-recovery.json
│   │       └── intrinsic-showcase.json
│   ├── tsconfig.scripts.json    # Separate tsconfig for Node scripts (moduleResolution: node)
│   ├── package.json
│   └── vite.config.ts
├── examples/                    # 5 real-world example workflows
│   ├── README.md                # Quick-start guide with example summary table
│   ├── order-processing/        # Core state types + error handling + parallel
│   ├── approval-workflow/       # Context Object, Variables/Assign, Wait, looping
│   ├── data-pipeline/           # Map state, full I/O pipeline, DynamoDB
│   ├── retry-and-recovery/      # Multi-Retry, JitterStrategy, multi-Catch
│   └── intrinsic-showcase/      # 14+ intrinsic functions, all I/O stages
│   # Each example contains:
│   # ├── workflow.yaml           # DSL definition
│   # ├── handlers/               # Python handler functions (@state decorated)
│   # ├── src/handlers/           # Same handlers for deployment packaging
│   # ├── src/generated/          # Auto-generated orchestrator
│   # ├── terraform/              # Per-example Terraform (Lambda, IAM, CloudWatch, DynamoDB)
│   # ├── tests/
│   # │   ├── conftest.py         # clean_registry fixture
│   # │   └── test_local.py       # YAML parsing + handler unit + workflow simulation
│   # └── README.md               # DSL features table + workflow diagram + screenshots
├── tutorials/                   # 8 step-by-step tutorials (v1.3)
│   ├── 01-project-setup.md          # rsf init
│   ├── 02-workflow-validation.md     # rsf validate (learn-by-breaking)
│   ├── 03-code-generation.md         # rsf generate
│   ├── 04-deploy-to-aws.md           # rsf deploy (Terraform walkthrough)
│   ├── 05-iterate-invoke-teardown.md # --code-only, invoke, teardown
│   ├── 06-asl-import.md              # rsf import (ASL conversion rules)
│   ├── 07-graph-editor.md            # rsf ui (bidirectional sync)
│   └── 08-execution-inspector.md     # rsf inspect (time machine, SSE)
├── tests/                       # Python test suite
│   ├── test_dsl/                # DSL model + parser + validator tests
│   ├── test_codegen/            # Code generation tests
│   ├── test_terraform/          # Terraform generation tests
│   ├── test_io/                 # I/O pipeline tests
│   ├── test_functions/          # Intrinsic function tests
│   ├── test_context/            # Context object tests
│   ├── test_inspect/            # Inspector tests
│   ├── test_examples/           # Integration tests (real AWS deploy/invoke/teardown)
│   │   ├── conftest.py          # Shared harness: poll_execution, query_logs, terraform helpers
│   │   ├── test_order_processing.py
│   │   ├── test_approval_workflow.py
│   │   ├── test_data_pipeline.py
│   │   ├── test_retry_recovery.py
│   │   └── test_intrinsic_showcase.py
│   └── mock_sdk/                # Mock durable execution SDK
├── fixtures/                    # Shared test fixtures
│   ├── valid/                   # 22+ valid DSL YAML files
│   └── invalid/
│       ├── pydantic/            # Model validation failures
│       └── semantic/            # Referential/reachability failures
├── schema/                      # Generated JSON Schema
│   ├── rsf-dsl.schema.json      # Draft 2020-12 from Pydantic
│   ├── api-contract.yaml        # OpenAPI 3.1 for GUI backend
│   └── validation-rules.yaml    # Cross-field rules
├── docs/
│   ├── index.md
│   ├── tutorial.md              # Quick-start overview (all 11 steps)
│   ├── migration-guide.md
│   ├── images/                  # Playwright screenshots (15 PNGs)
│   │   ├── {example}-graph.png      # Graph editor full layout
│   │   ├── {example}-dsl.png        # DSL editor + graph side by side
│   │   └── {example}-inspector.png  # Execution inspector view
│   └── reference/
│       ├── dsl.md
│       └── state-types.md
├── mkdocs.yml
├── README.md
└── LICENSE                      # Apache-2.0
```

---

## DSL Specification

### Overview

The DSL is a YAML/JSON format achieving full AWS Step Functions ASL (Amazon States Language) feature parity. It covers:
- 8 state types: Task, Pass, Choice, Wait, Succeed, Fail, Parallel, Map
- Error handling: Retry policies with exponential backoff, Catch handlers with error routing
- I/O processing: 5-stage pipeline (InputPath → Parameters → ResultSelector → ResultPath → OutputPath)
- 39 comparison operators for Choice rules
- 18 intrinsic functions (States.Format, States.Array, States.UUID, etc.)
- JSONPath and JSONata query languages
- Variables (Assign/Output)
- Context object (`$$`)

### Root Structure

```yaml
rsf_version: "1.0"
Comment: "Optional description"
StartAt: FirstState
QueryLanguage: JSONPath  # or JSONata (default: JSONPath)
TimeoutSeconds: 3600     # Optional workflow timeout
Version: "1.0"           # Optional version string
States:
  FirstState:
    Type: Task
    # ...
```

### Pydantic v2 Model Architecture

**Key configuration on all models:**
- `extra="forbid"` — rejects unknown fields with clear errors
- `populate_by_name=True` — accepts both snake_case and PascalCase
- PascalCase field aliases (e.g., `start_at: str = Field(alias="StartAt")`)
- `mode="json"` serialization with `exclude_none=True` in `model_dump()`

**State type discrimination:**

```python
# Assembled in dsl/__init__.py to break circular imports
State = Annotated[
    Union[TaskState, PassState, ChoiceState, WaitState,
          SucceedState, FailState, ParallelState, MapState],
    Field(discriminator="type"),  # "type" maps to alias "Type"
]

# Inject into models module and rebuild forward refs
models.State = State
StateMachine.model_rebuild()
```

This pattern is critical because `ChoiceState` references `State` (via choice rules) and `State` references `ChoiceState`, creating a circular dependency that's broken by late binding in `__init__.py`.

### State Types

#### TaskState
Executes a handler function. **No Resource field** — RSF creates the Lambda; handlers are bound via `@state` decorators.

```yaml
MyTask:
  Type: Task
  Comment: "Optional"
  InputPath: "$.input"           # JSONPath to filter input
  Parameters:                     # Payload template
    key.$: "$.value"
  ResultSelector:                 # Filter task result
    selected.$: "$.data"
  ResultPath: "$.taskResult"     # Where to place result in raw input
  OutputPath: "$.output"         # Filter final output
  TimeoutSeconds: 300            # Or TimeoutSecondsPath
  HeartbeatSeconds: 60           # Or HeartbeatSecondsPath (mutually exclusive pairs)
  Retry:                         # Retry policies
    - ErrorEquals: ["TransientError"]
      IntervalSeconds: 2
      MaxAttempts: 3
      BackoffRate: 2.0
      MaxDelaySeconds: 60
      JitterStrategy: FULL       # FULL or NONE
  Catch:                         # Error handlers
    - ErrorEquals: ["States.ALL"]
      Next: HandleError
      ResultPath: "$.error"
  Next: NextState                # Or End: true
```

**Validators:**
- TimeoutSeconds XOR TimeoutSecondsPath (mutual exclusion)
- HeartbeatSeconds XOR HeartbeatSecondsPath (mutual exclusion)
- Heartbeat must be less than timeout

#### PassState
Passes input to output, optionally injecting a static result.

```yaml
InjectData:
  Type: Pass
  Result:
    status: "approved"
    amount: 100
  ResultPath: "$.injected"
  Next: ProcessData
```

#### ChoiceState
Branches based on conditions. No `End` or `Next` — uses `Default` as fallback.

```yaml
RoutePayment:
  Type: Choice
  Choices:
    - Variable: "$.amount"
      NumericGreaterThan: 1000
      Next: HighValueApproval
    - Variable: "$.type"
      StringEquals: "refund"
      Next: ProcessRefund
    - And:
        - Variable: "$.verified"
          BooleanEquals: true
        - Variable: "$.amount"
          NumericLessThanEquals: 100
      Next: AutoApprove
  Default: ManualReview
```

**39 Comparison Operators:**
- Equality: `StringEquals`, `NumericEquals`, `BooleanEquals`, `TimestampEquals` (+ `*Path` variants)
- Ordering: `StringGreaterThan`, `StringLessThan`, `NumericGreaterThan`, `NumericLessThan`, `TimestampGreaterThan`, `TimestampLessThan` (+ `*OrEquals` + `*Path` variants)
- Pattern: `StringMatches` (+ `*Path`)
- Type checking: `IsBoolean`, `IsNull`, `IsNumeric`, `IsPresent`, `IsString`, `IsTimestamp`
- Boolean logic: `And`, `Or`, `Not` (recursive)
- JSONata: `Condition` (expression-based)

**Choice rule discrimination:** Uses a callable discriminator function (`discriminate_choice_rule()`) because choice rules have no natural `Type` field. The discriminator inspects which keys are present to determine the rule type.

**Exactly-one-operator validation:** A `@model_validator` ensures exactly one of the 39 operators is set on each `DataTestRule`.

#### WaitState
Delays execution. Exactly one time specification required.

```yaml
WaitForApproval:
  Type: Wait
  Seconds: 300              # Static seconds
  # OR: Timestamp: "2024-01-01T00:00:00Z"
  # OR: SecondsPath: "$.waitTime"
  # OR: TimestampPath: "$.deadline"
  Next: CheckApproval
```

**Validator:** Exactly one of `Seconds`, `Timestamp`, `SecondsPath`, `TimestampPath` must be set.

#### SucceedState
Terminal success state.

```yaml
Done:
  Type: Succeed
```

#### FailState
Terminal failure state. **Inherits from BaseModel, NOT StateBase** — ASL spec says Fail states do not process I/O (no InputPath, OutputPath, etc.).

```yaml
OrderFailed:
  Type: Fail
  Error: "OrderError"          # Or ErrorPath: "$.errorCode"
  Cause: "Validation failed"   # Or CausePath: "$.errorDetail"
```

**Validator:** Error XOR ErrorPath; Cause XOR CausePath (independent mutual exclusion pairs).

#### ParallelState
Concurrent execution with multiple branches. Each branch is a sub-state machine.

```yaml
ProcessBoth:
  Type: Parallel
  Branches:
    - StartAt: ValidateAddress
      States:
        ValidateAddress:
          Type: Task
          End: true
    - StartAt: CheckInventory
      States:
        CheckInventory:
          Type: Task
          End: true
  ResultPath: "$.parallel_results"
  Retry:
    - ErrorEquals: ["States.ALL"]
      MaxAttempts: 2
  Catch:
    - ErrorEquals: ["States.ALL"]
      Next: HandleParallelError
  Next: MergeResults
```

#### MapState
Iterates over an array. Uses `ItemProcessor` with a sub-state machine.

```yaml
ProcessItems:
  Type: Map
  ItemsPath: "$.orders"
  ItemProcessor:
    ProcessorConfig:
      Mode: INLINE              # Or DISTRIBUTED
    StartAt: ProcessOneOrder
    States:
      ProcessOneOrder:
        Type: Task
        End: true
  MaxConcurrency: 10            # 0 = unlimited
  ItemSelector:                 # Transform each item before processing
    orderId.$: "$$.Map.Item.Value.id"
    index.$: "$$.Map.Item.Index"
  ResultPath: "$.processed"
  Retry:
    - ErrorEquals: ["States.ALL"]
      MaxAttempts: 3
  Catch:
    - ErrorEquals: ["States.ALL"]
      Next: HandleMapError
  Next: AggregateResults
```

### StateMachineDefinition (Root Model)

```python
class StateMachineDefinition(BaseModel):
    rsf_version: str = Field(alias="rsf_version", default="1.0")
    comment: str | None = Field(None, alias="Comment")
    start_at: str = Field(alias="StartAt")
    states: dict[str, State] = Field(alias="States")
    version: str | None = Field(None, alias="Version")
    timeout_seconds: int | None = Field(None, alias="TimeoutSeconds")
    query_language: QueryLanguage | None = Field(None, alias="QueryLanguage")
```

### Semantic Validation (BFS)

The validator performs cross-state validation after Pydantic model validation:

1. **DSL-04: All references resolve** — every `Next`, `Default`, and `Catch.Next` points to an existing state
2. **DSL-05: All states reachable** — BFS from `StartAt` must visit every state (no orphans)
3. **DSL-06: Terminal state exists** — at least one `Succeed`, `Fail`, or `End: true` state
4. **States.ALL must be last** — in Retry/Catch arrays, `States.ALL` entries must be the final catch-all
5. **Recursive branch validation** — all rules apply recursively to Parallel branches and Map ItemProcessor

Returns a list of `ValidationError` dataclasses with message, path, and severity.

---

## I/O Processing Pipeline

### 5-Stage JSONPath Pipeline

```
Raw Input → InputPath → Parameters → [Task Execution] → ResultSelector → ResultPath → OutputPath → Final Output
```

**Critical invariant:** ResultPath merges into the **raw input** (before InputPath filtering), not the effective input.

```python
def process_jsonpath_pipeline(raw_input, task_result, input_path, parameters, result_selector, result_path, output_path, context, variables):
    # Stage 1: InputPath filters raw_input → effective_input
    effective_input = apply_jsonpath(raw_input, input_path)

    # Stage 2: Parameters payload template on effective_input
    if parameters:
        effective_input = apply_payload_template(parameters, effective_input, context, variables)

    # Stage 3: ResultSelector payload template on task_result
    effective_result = task_result
    if result_selector:
        effective_result = apply_payload_template(result_selector, task_result, context, variables)

    # Stage 4: ResultPath merges into RAW input (not effective!)
    merged = apply_result_path(raw_input, effective_result, result_path)

    # Stage 5: OutputPath filters merged output
    return apply_jsonpath(merged, output_path)
```

### JSONPath Evaluator

ASL-subset JSONPath (not full RFC 9535). Supports:
- Root: `$`
- Dot notation: `$.field.subfield`
- Bracket notation: `$['field name']`
- Array indexing: `$.array[0]`
- Variable references: `$varName`, `$varName.field`

Does NOT support: filters, wildcards (`*`), recursive descent (`..`), functions.

### Payload Templates

Keys ending with `.$` are resolved:
- `$.field` → JSONPath reference into input
- `$$.Execution.Id` → Context object reference
- `States.UUID()` → Intrinsic function call
- Static keys pass through unchanged

### ResultPath

- `"$"` → result replaces entire output
- `"$.field"` → deep merge result at path into copy of raw input
- `null` → discard result, return copy of raw input
- Always deep-copies to prevent mutation

---

## Intrinsic Functions

18 intrinsic functions registered via `@intrinsic(name)` decorator pattern:

| Function | Purpose |
|----------|---------|
| `States.Format(template, ...args)` | String interpolation with `{}` placeholders |
| `States.StringToJson(str)` | Parse JSON string |
| `States.JsonToString(obj)` | Serialize to JSON string |
| `States.Array(...items)` | Create array from arguments |
| `States.ArrayPartition(array, size)` | Split array into chunks |
| `States.ArrayContains(array, value)` | Check membership |
| `States.ArrayRange(start, end, step)` | Generate numeric range |
| `States.ArrayGetItem(array, index)` | Get item by index |
| `States.ArrayLength(array)` | Array length |
| `States.ArrayUnique(array)` | Deduplicate |
| `States.Base64Encode(str)` | Base64 encode |
| `States.Base64Decode(str)` | Base64 decode |
| `States.Hash(data, algorithm)` | Hash with algorithm (SHA-256, etc.) |
| `States.MathRandom(start, end)` | Random integer |
| `States.MathAdd(a, b)` | Addition |
| `States.StringSplit(str, delimiter)` | Split string |
| `States.UUID()` | Generate UUID v4 |

### Intrinsic Parser

Recursive descent parser supporting:
- Nested function calls: `States.Format('Hello {}', States.UUID())`
- String escaping: `States.Format('It\'s a test')`
- Path references as arguments: `$.field`
- Context references: `$$.Execution.Id`
- JSON literals (numbers, booleans, null)
- Max nesting depth: 10

---

## Context Object

The ASL context object is accessible as `$$` in JSONPath mode or `$states.context` in JSONata mode.

```python
class ContextObject:
    Execution: ExecutionContext    # Id, Input, Name, RoleArn, StartTime, RedriveCount
    State: StateContext           # EnteredTime, Name, RetryCount
    StateMachine: StateMachineContext  # Id, Name
    Task: TaskContext             # Token (for callback patterns)
    Map: MapContext               # Item (Index, Key, Value, Source)
```

---

## Handler Registry

### @state Decorator

```python
from rsf.registry import state, startup, get_handler

@state("ValidateOrder")
def validate_order(input_data: dict) -> dict:
    """Business logic for the ValidateOrder task state."""
    return {"valid": True, "orderId": input_data["orderId"]}

@startup
def init_resources():
    """Called once per Lambda cold start, before any handler."""
    global dynamodb
    dynamodb = boto3.resource("dynamodb")
```

**Implementation details:**
- `@state(name)` validates non-empty string, raises `ValueError` on duplicate
- `@startup` takes no arguments, mirrors `@state` pattern
- `get_handler(name)` raises `KeyError` with list of registered states
- `registered_states()` returns `frozenset` of names
- `clear()` and `clear_startup_hooks()` for test isolation
- `discover_handlers(directory)` imports all `.py` files to trigger decorator registration

---

## Code Generation

### Architecture

1. **Parse** DSL file → `StateMachineDefinition`
2. **Validate** (Pydantic + semantic validator)
3. **Map states** → SDK primitives via BFS traversal from StartAt
4. **Render** orchestrator template with state mappings
5. **Create handler stubs** (only if they don't exist — Generation Gap)

### State Mappers (BFS Traversal)

```python
@dataclass
class StateMapping:
    state_name: str
    state_type: str           # Task, Pass, Choice, etc.
    sdk_primitive: str        # context.step, context.wait, conditional, etc.
    params: dict              # State-specific parameters
```

**BFS traversal** from `StartAt` collects all reachable states, including:
- Choice branches (all `Next` targets + `Default`)
- Loop targets (states that jump backward)
- Catch handlers (error routing targets)

Mapping rules:
| State Type | SDK Primitive | Key Params |
|-----------|---------------|------------|
| Task | `context.step` | has_retry, has_catch, catch_policies |
| Wait | `context.wait` | seconds/timestamp variants |
| Choice | conditional | mapped rule tree (recursive) |
| Pass | passthrough | result, result_path |
| Succeed | return | — |
| Fail | raise WorkflowError | error, cause (+ path variants) |
| Parallel | `context.parallel` | branches (sub-functions), retry/catch |
| Map | `context.map` | items_path, item_processor, max_concurrency |

### Jinja2 Template: Generated Orchestrator

The generated `orchestrator.py` uses:

```python
# DO NOT EDIT - Generated by RSF v{version} on {timestamp}
# Source: {dsl_file} (SHA-256: {hash})

from aws_lambda_durable_execution_sdk_python import DurableContext, durable_execution
from aws_lambda_durable_execution_sdk_python.config import Duration
from rsf.registry import get_handler, get_startup_hooks

# Import handler modules to trigger @state registration
from handlers import validate_order
from handlers import process_payment
# ...

class WorkflowError(Exception):
    def __init__(self, error, cause=None):
        self.error = error
        self.cause = cause
        super().__init__(f"{error}: {cause}" if cause else error)

_startup_done = False

@durable_execution
def lambda_handler(context: DurableContext, event: dict) -> dict:
    global _startup_done
    if not _startup_done:
        for hook in get_startup_hooks():
            hook()
        _startup_done = True

    current_state = "ValidateOrder"  # StartAt
    input_data = event

    while current_state is not None:
        if current_state == "ValidateOrder":
            handler = get_handler("ValidateOrder")
            input_data = context.step("ValidateOrder", handler, input_data)
            current_state = "CheckAmount"

        elif current_state == "CheckAmount":
            # Choice state: conditional routing
            if input_data.get("amount", 0) > 1000:
                current_state = "HighValueApproval"
            else:
                current_state = "StandardProcess"  # Default

        elif current_state == "HighValueApproval":
            handler = get_handler("HighValueApproval")
            try:
                input_data = context.step("HighValueApproval", handler, input_data)
                current_state = "Done"
            except Exception as e:
                # Catch: States.ALL → HandleError
                input_data["error"] = {"Error": type(e).__name__, "Cause": str(e)}
                current_state = "HandleError"

        # ... more states ...

        elif current_state == "Done":
            return input_data  # Succeed state

    return input_data
```

### Custom `topyrepr` Filter

Python literal serialization (not JSON):
- `True` not `true`
- `False` not `false`
- `None` not `null`
- Strings properly quoted
- Recursive for dicts/lists

This filter is critical — using `tojson` for Python code causes `NameError` at runtime because Python doesn't recognize `true`/`false`/`null`.

### Handler Stub Template

```python
from rsf.registry import state

@state("ValidateOrder")
def validate_order(input_data: dict) -> dict:
    """Handler for the ValidateOrder task state.

    Implement your business logic here.
    """
    raise NotImplementedError("Implement ValidateOrder handler")
```

**Generation Gap:** Handler files are only created if they don't exist. The orchestrator is always regenerated (marked with `# DO NOT EDIT`).

---

## Terraform Generation

### Custom Jinja2 Delimiters for HCL

Standard Jinja2 `{{ }}` conflicts with Terraform's `${}` interpolation and `{}` block syntax. RSF uses:

| Purpose | Standard Jinja2 | RSF HCL Delimiters |
|---------|-----------------|-------------------|
| Variables | `{{ var }}` | `<< var >>` |
| Blocks | `{% if %}` | `<% if %>` |
| Comments | `{# note #}` | `<# note #>` |

### Generation Gap Pattern

```python
GENERATED_MARKER = "# DO NOT EDIT - Generated by RSF"

def _should_overwrite(path: Path) -> bool:
    """Return True if path doesn't exist OR first line matches marker."""
    if not path.exists():
        return True
    first_line = path.read_text().split("\n", 1)[0]
    return first_line.strip() == GENERATED_MARKER
```

- Files with the marker in their first line are always regenerated
- Files without the marker (user-modified) are never touched
- This is checked per-file, not per-directory

### IAM Permission Derivation

Returns exactly 3 base IAM statements (no service-specific derivation — Task states have no Resource field):

1. **CloudWatch Logs:** `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`
2. **Lambda self-invoke:** `lambda:InvokeFunction` (for durable execution callbacks)
3. **Durable execution:** `lambda:CheckpointDurableExecution`, `lambda:GetDurableExecution`, `lambda:ListDurableExecutionsByFunction`

### Terraform Templates

**main.tf.j2 — Key resources:**

```hcl
# DO NOT EDIT - Generated by RSF

locals {
  function_name = "${var.name_prefix}-${var.workflow_name}"
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${var.source_dir}/src"
  output_path = "${path.module}/${var.workflow_name}.zip"
}

resource "aws_lambda_function" "<< resource_id >>" {
  function_name = local.function_name
  handler       = "generated.orchestrator.lambda_handler"
  runtime       = "python3.13"
  role          = aws_iam_role.lambda_exec.arn
  filename      = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout       = var.timeout
  memory_size   = var.memory_size

  durable_config {
    execution_timeout = var.execution_timeout
    retention_period  = var.retention_period
  }

  lifecycle {
    ignore_changes = [last_modified]
  }
}
```

**variables.tf.j2 — Input variables with validation:**
- `aws_region` (string)
- `name_prefix` (string, regex validated: `^[a-zA-Z][a-zA-Z0-9_-]*$`)
- `workflow_name` (string)
- `timeout` (number, default 900)
- `memory_size` (number, default 256)
- `source_dir` (string, default "..")
- `log_retention_days` (number, default 14)
- `execution_timeout` (number, range 1-31622400, default 86400)
- `retention_period` (number, range 1-90, default 14)

**outputs.tf.j2:**
- `function_arn` — `aws_lambda_function.<resource_id>.arn`
- `function_name` — `aws_lambda_function.<resource_id>.function_name`
- `role_arn` — `aws_iam_role.lambda_exec.arn`
- `log_group_name` — `aws_cloudwatch_log_group.lambda_logs.name`

**Naming pattern:**
```python
def _sanitize_name(name: str) -> str:
    """PascalCase/kebab-case → valid Terraform identifier (lowercase, underscores)."""
    # e.g., "My-Workflow" → "my_workflow"
```

Lambda function name: `${var.name_prefix}-${var.workflow_name}` (e.g., `rsf-my-workflow`)

---

## ASL Importer

### Pipeline

```
ASL JSON file → parse_asl_json() → convert_asl_to_rsf() → emit_yaml() → RSF YAML file
```

### Conversion Rules

1. Inject `rsf_version: "1.0"` at root
2. **Reject Resource field** — Task states with `Resource` raise `ValueError` with guidance to use `@state` decorators instead
3. Strip Fail state I/O fields (InputPath, OutputPath, etc.) — ASL allows them but RSF's `extra=forbid` rejects them
4. Rename legacy `Iterator` → `ItemProcessor` (older ASL format)
5. Warn on distributed Map fields (`ItemReader`, `ItemBatcher`, `ResultWriter`)
6. Recursive conversion for Parallel branches and Map ItemProcessor sub-machines

### Import Warnings

```python
@dataclass
class ImportWarning:
    path: str       # e.g., "States.MyTask.Resource"
    field: str      # e.g., "Resource"
    message: str    # Human-readable guidance
    severity: str   # "warning" or "error"
```

### Handler Stub Generation

After import, generate handler stubs for every Task state found in the imported workflow.

---

## FastAPI Backend (Graph Editor)

### Server Architecture

Single FastAPI app serving:
1. **Static files** — Built React SPA (index.html, JS/CSS assets)
2. **REST endpoint** — `GET /api/schema` returns JSON Schema for the DSL
3. **WebSocket endpoint** — `/ws` for bidirectional DSL operations

### WebSocket Protocol

**Client → Server messages:**

| Type | Payload | Response |
|------|---------|----------|
| `parse` | `{ yaml: string }` | `parsed` with AST + errors |
| `validate` | `{ yaml: string }` | `validated` with errors only |
| `load_file` | `{ path: string }` | `file_loaded` with contents |
| `save_file` | `{ path: string, yaml: string }` | `file_saved` confirmation |
| `get_schema` | `{}` | `schema` with JSON Schema |

**Server → Client messages:**

| Type | Payload |
|------|---------|
| `parsed` | `{ ast, yaml, errors }` |
| `validated` | `{ errors }` |
| `file_loaded` | `{ yaml, path }` |
| `file_saved` | `{ path }` |
| `schema` | `{ json_schema }` |
| `error` | `{ message }` |

**On connect:** If a workflow file path was configured, auto-send `file_loaded`.

### Launch

```python
def launch(workflow_path=None, port=8765, open_browser=True):
    """Start uvicorn server, optionally open browser."""
    app = create_app(workflow_path)
    uvicorn.run(app, host="127.0.0.1", port=port)
```

---

## FastAPI Backend (Inspector)

### Router: `/api/inspect`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/inspect/executions` | GET | List durable executions (query: status, max_items) |
| `/api/inspect/execution/{arn}` | GET | Get execution detail + history |
| `/api/inspect/execution/{arn}/history` | GET | History events only |
| `/api/inspect/execution/{arn}/stream` | GET (SSE) | Live updates for running executions |

### SSE Stream Protocol

Named events (not default `message`):

| Event | When | Data |
|-------|------|------|
| `execution_info` | On connect + each poll | `ExecutionDetail` JSON |
| `history` | Once on connect | Full `HistoryEvent[]` |
| `history_update` | During polling (if new events) | New `HistoryEvent[]` only |

Stream lifecycle: connect → initial events → poll every 5s → close on terminal status.

### Lambda Client

Async boto3 wrapper with:
- Token bucket rate limiter (12 req/s ceiling, stays under 15 req/s Lambda control plane limit)
- Timestamp normalization (seconds → UTC datetime)
- Pagination for execution list

### Data Models

```python
class ExecutionStatus(Enum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    STOPPED = "STOPPED"

class ExecutionSummary:
    arn: str
    name: str
    status: ExecutionStatus
    function_arn: str
    start_time: datetime
    end_time: datetime | None

class ExecutionDetail(ExecutionSummary):
    input_payload: dict | None
    result: dict | None
    error: ExecutionError | None

class HistoryEvent:
    event_id: int
    timestamp: datetime
    event_type: str     # StepStarted, StepSucceeded, StepFailed, etc.
    sub_type: str | None
    details: dict

class ParsedArn:
    region: str
    account: str
    function_name: str
    qualifier: str | None
    execution_name: str
    execution_id: str
```

### ARN Discovery

Inspector discovers the Lambda ARN automatically:
1. **Primary:** `terraform output -raw function_arn` (run in terraform directory)
2. **Override:** `rsf inspect --arn <explicit-arn>` overrides all discovery

---

## React Graph Editor UI

### Application Architecture

Two separate React apps sharing components:
- **`App.tsx`** — Graph editor (edit workflows visually)
- **`InspectApp.tsx`** — Execution inspector (debug executions)
- **`main.tsx`** — Entry point that chooses which app to render

### Zustand Stores

#### Flow Store (Editor)

```typescript
interface FlowState {
  nodes: FlowNode[]
  edges: FlowEdge[]
  yamlContent: string
  validationErrors: ValidationError[]
  selectedNodeId: string | null
  syncSource: 'editor' | 'graph' | null  // Prevents ping-pong
  needsLayout: boolean
  lastAst: Record<string, unknown> | null

  // Actions
  onNodesChange(changes): void
  onEdgesChange(changes): void
  onConnect(connection): void
  updateFromAst(ast, errors): void
  addState(type, position): void
  updateStateProperty(nodeId, field, value): void
  removeState(nodeId): void
  selectNode(nodeId): void
  setSyncSource(source): void
}
```

#### Inspect Store

```typescript
interface InspectState {
  functionName: string | null
  executions: ExecutionSummary[]
  selectedExecution: ExecutionDetail | null
  events: HistoryEvent[]
  nodes: FlowNode[]
  edges: FlowEdge[]
  nodeOverlays: Map<string, NodeOverlay>
  edgeOverlays: Map<string, EdgeOverlay>
  selectedNodeId: string | null
  playbackIndex: number | null      // Time machine position

  // Actions
  setDefinition(ast): void
  setSelectedExecution(execution, events): void
  addEvents(newEvents): void       // SSE update
  setPlaybackIndex(index): void    // Time machine scrub
  recomputeOverlays(): void
}
```

### Bidirectional YAML ↔ Graph Sync

**This is the most complex UI feature. The key challenge is preventing infinite loops when YAML changes trigger graph updates and vice versa.**

#### Direction 1: YAML → Graph

```
User edits YAML in Monaco
  → handleEditorChange() sets syncSource = 'editor'
  → Debounce 300ms
  → WebSocket: { type: 'parse', yaml }
  → Server parses → sends 'parsed' with AST + errors
  → astToFlowElements(ast) → { nodes, edges }
  → setNodes/setEdges with position preservation
  → syncSource = 'editor' prevents graph→YAML loopback
  → Clear syncSource after microtask (queueMicrotask)
```

#### Direction 2: Graph → YAML

```
User modifies graph (add/move/connect/delete)
  → onGraphChange() fires
  → Check syncSource !== 'editor' (prevent loop)
  → mergeGraphIntoYaml(lastAst, nodes, edges)
    • Clone lastAst
    • Update only transitions (Next/Default/End)
    • Preserve complex data (Choice rules, Parallel branches, Catch arrays)
    • Falls back to buildYamlFromNodes() if no prior AST
  → setYamlContent(yaml)
  → WebSocket: { type: 'parse', yaml }
  → Server validates, errors mapped to nodes
```

**Critical: `syncSource` pattern**
- Set before mutation, cleared after microtask via `queueMicrotask()`
- Prevents infinite update loops between editor and graph
- Both directions check this flag and early-return if the opposite side initiated the change

#### AST → Flow Conversion

```typescript
function astToFlowElements(ast): { nodes: FlowNode[], edges: FlowEdge[] }
```

1. Iterate `States` map
2. For each state: create `FlowNode` with state-type-specific data
3. Mark `isStart` if name === `StartAt`
4. For Parallel: create child nodes for each branch (set `parentId`)
5. For Map: create child nodes from ItemProcessor (set `parentId`)
6. Create edges: `Next` transitions, Choice rule targets, Catch targets (dashed style)

#### Graph → YAML Merge

The **AST-merge strategy** is key: instead of building YAML from scratch (which would lose Choice rules, Catch arrays, Parallel branches, etc.), we:

1. Clone `lastAst` (the most recently parsed AST)
2. Update only structural changes (transitions, new/deleted states)
3. Preserve all complex state data that the graph view can't represent
4. Fall back to `buildYamlFromNodes()` only if no prior AST exists

### Graph Nodes

Per-state-type React components:

| Node | Unique Features |
|------|-----------------|
| `TaskNode` | Retry/Catch badges, timeout indicator |
| `PassNode` | Result indicator |
| `ChoiceNode` | Rule count display, Default indicator |
| `WaitNode` | Duration display |
| `SucceedNode` | Terminal style (green) |
| `FailNode` | Terminal style (red) |
| `ParallelNode` | Expandable container, branch count |
| `MapNode` | Expandable container, concurrency display |

All nodes use `@xyflow/react` `Handle` components for connection points.

### Auto-Layout

ELK.js with Sugiyama layered algorithm:

```typescript
function getLayoutedElements(nodes, edges) {
  // Top-to-bottom direction
  // Supports hierarchical layout (parent → children)
  // Options: layered, DOWN direction, 80px between layers, 40px between nodes
  // LAYER_SWEEP crossing minimization
}
```

Triggered on: first load, node add/remove, explicit layout request.

### Custom Edges

`TransitionEdge`: Bezier curve with:
- Solid style for normal transitions
- Dashed style for Catch transitions
- "Catch" label on error edges
- Default styling for Choice default branch

### Components

| Component | Purpose |
|-----------|---------|
| `GraphCanvas` | @xyflow/react canvas, drag-drop, minimap, controls, background |
| `MonacoEditor` | YAML editor with monaco-yaml schema validation + autocompletion |
| `Palette` | 8 state type buttons for drag-to-create |
| `Inspector` | Selected node property editor (field inputs) |
| `ValidationOverlay` | Error badges on canvas nodes |

---

## Execution Inspector UI

### Layout

Three-panel layout:
1. **Left:** Execution list with status filter + search
2. **Center:** Graph with execution overlays + execution header
3. **Right:** Event timeline + state detail panel

### Execution Overlays

Events are mapped to node/edge visual states:

```typescript
interface NodeOverlay {
  status: 'pending' | 'running' | 'succeeded' | 'failed' | 'caught'
  enteredAt?: string
  exitedAt?: string
  durationMs?: number
  input?: string
  output?: string
  error?: string
  cause?: string
  attempt?: number  // For retries
}

interface EdgeOverlay {
  traversed: boolean
  traversedAt?: string
}
```

**Event → Status mapping:**
| Event Type | Status |
|-----------|--------|
| StepStarted / ExecutionStarted | running |
| StepSucceeded / ExecutionSucceeded | succeeded |
| StepFailed / ExecutionFailed | failed |
| WaitStarted | running |
| WaitSucceeded | succeeded |
| No events | pending |

### Time Machine

**Precomputed snapshots** for O(1) scrubbing:

```typescript
interface TransitionSnapshot {
  eventIndex: number
  event: HistoryEvent
  nodeOverlays: Map<string, NodeOverlay>
  edgeOverlays: Map<string, EdgeOverlay>
}
```

1. On execution load: `buildSnapshots(events, nodes, edges)` computes overlay state at each transition event
2. Timeline scrubber selects an event index
3. Inspector renders the frozen overlay state at that point
4. Instant scrubbing (no O(n) recomputation per position)

### Data Diff

Structural JSON diff between state transitions:
- Shows input vs output for selected state
- Color-coded additions/removals
- Flat path comparison (no external npm dependency — lightweight inline implementation)

### Live Updates

SSE subscription for running executions:
- EventSource to `/api/inspect/execution/{arn}/stream`
- Named events: `execution_info`, `history`, `history_update`
- Auto-close on terminal status
- Pauses when browser tab hidden (visibility change)

### Components

| Component | Purpose |
|-----------|---------|
| `ExecutionList` | Sidebar with status filter, search, color-coded status icons |
| `ExecutionHeader` | Name, status, timing, ARN display |
| `InspectGraphCanvas` | Graph with execution overlays (colored nodes/edges) |
| `EventTimeline` | Vertical timeline of events, click to select |
| `TimelineScrubber` | Slider for time machine playback |
| `StateDetailPanel` | Input/output/error for selected node |
| `DataDiffPanel` | Structural comparison between states |

---

## CLI Commands

### `rsf init <project-name>`

Scaffolds a new RSF project:
- Creates directory structure (`handlers/`, `generated/`, `terraform/`)
- Renders templates: `workflow.yaml`, `pyproject.toml`, handler example, test example, `.gitignore`
- Reports created/skipped files

### `rsf generate <workflow.yaml> [--output-dir .]`

Generates Python code from DSL:
1. Parse + validate DSL
2. Map states to SDK primitives (BFS)
3. Render orchestrator template → `generated/orchestrator.py`
4. Create handler stubs → `handlers/<state_name>.py` (only if missing)
5. Maintain `handlers/__init__.py` imports

### `rsf validate <workflow.yaml>`

Validates DSL without generating code:
- Pydantic model validation
- Semantic cross-state validation
- Reports errors with paths

### `rsf deploy [--code-only]`

Deploys to AWS via Terraform:
1. Generate Terraform HCL (if needed)
2. `terraform init` (first time)
3. `terraform apply`
4. `--code-only` skips infra (just re-packages and updates Lambda code)

### `rsf import <asl.json> [--output workflow.yaml]`

Imports Step Functions ASL JSON:
1. Parse ASL JSON
2. Convert to RSF format (reject Resource, strip Fail I/O, etc.)
3. Emit YAML
4. Generate handler stubs for imported Task states

### `rsf ui [workflow.yaml] [--port 8765]`

Launches graph editor:
1. Start FastAPI server (REST + WebSocket)
2. Serve React SPA
3. Auto-open browser
4. If workflow file provided, auto-load on connect

### `rsf inspect [--arn <lambda-arn>] [--port 8766]`

Launches execution inspector:
1. Discover Lambda ARN (terraform output or --arn override)
2. Start FastAPI server (REST + SSE)
3. Serve inspector React SPA
4. Auto-open browser

---

## Mock SDK for Testing

A mock implementation of `aws_lambda_durable_execution_sdk_python` that enables running generated code locally without AWS:

```python
class MockDurableContext:
    """Synchronous mock that executes steps immediately."""

    def step(self, name, func, *args):
        return func(*args)

    def wait(self, duration):
        pass  # No-op in tests

    def parallel(self, branches):
        results = [branch() for branch in branches]
        return results  # Returns plain list (real SDK returns BatchResult)

    def map(self, items, func):
        results = [func(item) for item in items]
        return results
```

**Note:** Real SDK's `parallel()` and `map()` return `BatchResult`; call `.get_results()` for a plain list. The mock returns plain lists directly for simplicity.

---

## Testing Strategy

### Test Organization

```
tests/
├── test_dsl/          # DSL parsing, validation, all state types
├── test_codegen/      # Code generation, state mapping, templates
├── test_terraform/    # Terraform HCL generation
├── test_io/           # JSONPath, payload templates, result path, pipeline
├── test_functions/    # Intrinsic function parsing + execution
├── test_context/      # Context object model
├── test_inspect/      # Inspector models, router, Lambda client
├── test_examples/     # Integration tests: deploy/invoke/teardown on real AWS
│   ├── conftest.py    # Shared harness (poll_execution, query_logs, terraform helpers)
│   ├── test_order_processing.py
│   ├── test_approval_workflow.py
│   ├── test_data_pipeline.py
│   ├── test_retry_recovery.py
│   └── test_intrinsic_showcase.py
└── mock_sdk/          # Mock durable execution SDK
```

Plus per-example local tests: `examples/{name}/tests/test_local.py`

### Test Patterns

- **Unit tests:** pytest with fixtures, 152+ local tests
- **Integration tests:** Marked `@pytest.mark.integration`, deploy/invoke/teardown on real AWS
- **Golden fixtures:** Generated code compared against known-good output
- **Conformance fixtures:** 22+ valid + 8+ invalid DSL files
- **Mock SDK tests:** Execute generated orchestrator code locally via MockDurableContext
- **Example local tests:** Per-example YAML parsing + handler unit tests + workflow simulation
- **UI tests:** vitest, ~28 tests for React components and sync logic

### Key Test Categories

1. **DSL Model Tests** — Every state type, every field, every validator, every error case
2. **Choice Rule Tests** — All 39 operators, boolean combinations, edge cases
3. **Code Generation Tests** — All 8 state types generate valid Python, BFS traversal correctness
4. **Replay Safety Tests** — Generated code is deterministic (same DSL → same output)
5. **Regeneration Safety Tests** — Generation Gap preserves user files
6. **I/O Pipeline Tests** — All 5 stages, edge cases (null paths, deep merge, etc.)
7. **Intrinsic Function Tests** — All 18 functions with various argument types
8. **Terraform Tests** — HCL generation, IAM derivation, variable validation
9. **Importer Tests** — ASL conversion, Resource rejection, warning generation
10. **Inspector Tests** — Model serialization, API endpoints, SSE streaming
11. **SDK Integration Tests** — Generated code executes correctly via mock SDK
12. **Example Local Tests** — Per-example YAML parsing, handler units, workflow simulation
13. **AWS Integration Tests** — Deploy → Invoke → Assert Lambda result + CloudWatch logs → Teardown

### Fixture Naming Convention

- Valid: `fixtures/valid/simple-task.yaml`, `payment-routing.yaml`, `nested-parallel-map.yaml`, etc.
- Invalid (Pydantic): `fixtures/invalid/pydantic/task-both-timeouts.yaml`
- Invalid (Semantic): `fixtures/invalid/semantic/bad-reference.yaml`, `orphan-state.yaml`

---

## JSON Schema Generation

Extract JSON Schema (Draft 2020-12) from Pydantic v2 models:

```python
schema = StateMachineDefinition.model_json_schema()
```

This produces a complete schema with `$defs` for all state types, choice rules, retry policies, catchers, etc. The schema is:
- Used by the Monaco editor for YAML autocompletion and validation
- Served via `GET /api/schema`
- Stored as `schema/rsf-dsl.schema.json`

---

## Key Design Patterns Summary

### 1. Pydantic v2 Discriminated Union (State Types)
Break circular imports via late binding in `__init__.py`. Use `Field(discriminator="type")` on the union.

### 2. Decorator Registries
`@state(name)`, `@startup`, `@intrinsic(name)` — all follow the same pattern: decorator registers callable in a module-level dict, lookup function retrieves it.

### 3. Generation Gap
First-line marker `# DO NOT EDIT - Generated by RSF` determines overwritability. Generated code always overwritten; user code never touched.

### 4. BFS Traversal for Code Generation
Breadth-first search from StartAt ensures all reachable states (including Choice branches and loop targets) are included in the generated orchestrator.

### 5. AST-Merge for Graph→YAML Sync
Clone last parsed AST, update only transitions, preserve complex state data. Prevents data loss when the graph view (which can't represent all DSL features) drives changes.

### 6. syncSource Flag
Prevents infinite YAML↔Graph update loops. Set before mutation, cleared after microtask.

### 7. Precomputed Snapshots for Time Machine
Compute overlay state at each transition event upfront. O(1) scrubbing instead of O(n) recomputation.

### 8. Custom Jinja2 Delimiters for HCL
`<< >>` for variables, `<% %>` for blocks — avoids `${}` conflict with Terraform interpolation.

### 9. Token Bucket Rate Limiter
12 req/s ceiling for Lambda API calls. Prevents 429 throttling on the 15 req/s control plane limit.

### 10. Separate Zustand Stores
Flow store (editor) and Inspect store (inspector) are completely independent. No cross-contamination of concerns.

---

## Example Workflows (5 Real-World Examples)

### Overview

Five example workflows demonstrate all 8 ASL state types, all DSL features, and all error handling patterns. Each example is self-contained with workflow YAML, handler implementations, local tests, per-example Terraform infrastructure, and integration tests on real AWS.

### The 5 Examples

| Example | State Types | Key Features |
|---------|------------|--------------|
| **order-processing** | Task, Choice, Parallel, Succeed, Fail | Retry/Catch, TimeoutSeconds, concurrent branches, ResultPath |
| **approval-workflow** | Task, Wait, Choice, Pass, Succeed, Fail | Context Object (`$$`), Variables/Assign, intrinsics in Assign, looping |
| **data-pipeline** | Task, Pass, Map | ItemProcessor, ItemsPath, MaxConcurrency, all 5 I/O pipeline stages, DynamoDB |
| **retry-and-recovery** | Task, Pass, Succeed, Fail | Multi-Retry (3 policies), JitterStrategy (FULL/NONE), MaxDelaySeconds, multi-Catch (4 catchers) |
| **intrinsic-showcase** | Task, Pass, Choice, Succeed | 14+ intrinsic functions across 4 categories, full I/O pipeline |

**Combined coverage:** All 8 ASL state types, all 5 I/O pipeline stages, all error handling patterns, intrinsic functions, variables, context object.

### Handler Implementation Pattern

Every handler follows the same pattern:

```python
from rsf.registry import state
import logging
import json

logger = logging.getLogger(__name__)

def _log(step_name: str, message: str, **extra):
    """Structured logging for CloudWatch Logs Insights queries."""
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))

@state("StateName")
def handler_function(input_data: dict) -> dict:
    _log("StateName", "Starting operation", key=value)
    # Business logic here
    _log("StateName", "Operation complete", result=result)
    return result_dict
```

Key characteristics:
- **`@state("StateName")`** decorator registers in handler registry
- **Pure functions** — deterministic, testable without AWS
- **Custom exceptions** for error routing (match Catch ErrorEquals)
- **Structured JSON logging** via `_log()` helper for CloudWatch Logs Insights queries
- **Dict in, dict out** — keys match downstream state consumption

### Per-Example Terraform Infrastructure

Each example has a complete Terraform module:

| File | Contents |
|------|----------|
| `main.tf` | Lambda function with `durable_config` block, archive_file data source |
| `iam.tf` | IAM role + policy (CloudWatch, Lambda self-invoke, durable execution APIs) |
| `cloudwatch.tf` | CloudWatch Log Group with configurable retention |
| `variables.tf` | aws_region, name_prefix, workflow_name, timeout, memory_size, execution_timeout, retention_period |
| `outputs.tf` | function_arn, function_name, role_arn, log_group_name |
| `backend.tf` | S3/DynamoDB remote state config |
| `versions.tf` | Terraform >= 1.0, AWS provider >= 6.25.0 |
| `dynamodb.tf` | (data-pipeline only) DynamoDB table for pipeline results |

Lambda packaging: `data.archive_file` zips `src/` directory → handler path is `generated.orchestrator.lambda_handler`.

### Local Test Pattern (3 sections per example)

```python
# Section 1: Workflow YAML Parsing Tests
class TestWorkflowParsing:
    # Verify StartAt, all states present, state types, retry/catch config,
    # choice rules, parallel branches — proves DSL parses correctly

# Section 2: Individual Handler Unit Tests
class TestValidateOrderHandler:
    # Discover handlers, get handler by name, call with test data,
    # verify return values, verify custom exceptions raised

# Section 3: Full Workflow Simulation (MockDurableContext)
class TestStandardOrderWorkflow:
    # Step through states sequentially using MockDurableContext
    # ctx.step(), ctx.parallel(), ctx.map() with real handlers
    # Verify SDK call sequence via ctx.calls list
```

### Integration Test Pattern (Real AWS)

Each example has an integration test in `tests/test_examples/` that:

1. **Deploy** — `terraform_deploy(example_dir)` → returns outputs dict
2. **Wait** — `iam_propagation_wait(15s)` for IAM role propagation
3. **Invoke** — `lambda_client.invoke(InvocationType="Event", DurableExecutionName=unique_id)`
4. **Poll** — `poll_execution(lambda_client, fn, exec_id, timeout=300)` with exponential backoff
5. **Assert Lambda result** — Verify terminal status is SUCCEEDED or FAILED as expected
6. **Assert CloudWatch logs** — `query_logs()` with Insights query verifying handler step names
7. **Teardown** — `terraform_teardown()` + explicit `delete_log_group()` for orphan cleanup

```python
@pytest.mark.integration
class TestOrderProcessingIntegration:
    @pytest.fixture(scope="class")
    def deployment(self, lambda_client, logs_client):
        outputs = terraform_deploy(self.EXAMPLE_DIR)
        iam_propagation_wait()
        exec_id = make_execution_id("order-processing")  # test-order-processing-{ts}-{uuid8}
        lambda_client.invoke(FunctionName=outputs["function_name"],
                             InvocationType="Event",
                             Payload=json.dumps(self.HAPPY_EVENT),
                             DurableExecutionName=exec_id)
        execution = poll_execution(lambda_client, outputs["function_name"], exec_id)
        yield {"execution": execution, "outputs": outputs, ...}
        terraform_teardown(self.EXAMPLE_DIR, logs_client, outputs["log_group_name"])

    def test_execution_succeeds(self, deployment):
        assert deployment["execution"]["Status"] == "SUCCEEDED"

    def test_handler_log_entries(self, deployment, logs_client):
        results = query_logs(logs_client, log_group, query, start_time)
        for step in ("ValidateOrder", "ProcessPayment", "ReserveInventory", "SendConfirmation"):
            assert step in messages
```

### Integration Test Harness Utilities

Located in `tests/test_examples/conftest.py`:

| Utility | Purpose |
|---------|---------|
| `make_execution_id(name)` | `test-{name}-{YYYYMMDD}T{HHMMSS}-{uuid8}` — unique, collision-free |
| `poll_execution(client, fn, exec_id, timeout=300)` | Poll `list_durable_executions_by_function` every 5s, exponential backoff on throttle |
| `query_logs(client, group, query, start_time)` | 15s propagation wait, retry until results non-empty (max 5 retries) |
| `terraform_deploy(example_dir)` | `terraform init` + `terraform apply`, returns outputs dict |
| `terraform_teardown(example_dir, logs_client, log_group)` | `terraform destroy` + explicit `delete_log_group()` for orphan cleanup |
| `iam_propagation_wait(seconds=15)` | Sleep for IAM role/policy propagation after deploy |

Shared session fixtures: `aws_region` (us-east-2), `lambda_client`, `logs_client`.

### Example README Format

Each example README follows a consistent structure:

1. **Title + description** — One-line summary of what the example demonstrates
2. **DSL Features Demonstrated** — Table of features with usage descriptions
3. **Workflow Path** — ASCII flowchart showing state transitions
4. **Screenshots** — Graph editor, DSL editor, execution inspector (3 images)
5. **Run Locally (No AWS)** — `pytest examples/{name}/tests/test_local.py -v`
6. **Run Integration Test (AWS)** — `pytest tests/test_examples/test_{name}.py -m integration -v`

---

## Tutorial Documentation (8 Tutorials)

### Overview

8 step-by-step tutorials cover all 7 RSF CLI commands. Each tutorial builds on the previous, using the same "Order Processing" workflow as the running example (tutorials 1-7). Tutorial 8 uses a dedicated "Inspection Demo" workflow.

### Tutorial Index

| # | Title | Command | Key Learning |
|---|-------|---------|-------------|
| 01 | Project Setup | `rsf init` | Scaffold project, understand file structure |
| 02 | Workflow Validation | `rsf validate` | 3-stage validation pipeline, learn-by-breaking |
| 03 | Code Generation | `rsf generate` | Orchestrator + handler stubs, Generation Gap pattern |
| 04 | Deploy to AWS | `rsf deploy` | Terraform walkthrough (6 files), IAM policy, verification |
| 05 | Iterate, Invoke, Teardown | `rsf deploy --code-only` | Fast path, Lambda invocation, Choice branch testing, cleanup |
| 06 | ASL Import | `rsf import` | ASL JSON → RSF YAML, 5 conversion rules |
| 07 | Visual Editing | `rsf ui` | Graph editor, bidirectional YAML↔graph sync, validation |
| 08 | Execution Inspection | `rsf inspect` | Deploy demo workflow, time machine, data diffs, live SSE |

### Tutorial Format (Consistent Across All 8)

Every tutorial follows this structure:

1. **"What You'll Learn"** — Bullet-point learning objectives
2. **"Prerequisites"** — Required tools, prior tutorials, AWS account if needed
3. **Numbered Steps** — Each step has:
   - Exact command to run (copy-pasteable)
   - Expected output (code blocks with sample output)
   - Explanation of what happened and why
   - Tips/notes in blockquote callouts
4. **"What's Next"** — Forward pointer to next tutorial
5. **Footer** — "Tutorial N of 8 — RSF Comprehensive Tutorial Series"

### Tutorial Dependency Chain

```
Tutorial 1 (Init) → 2 (Validate) → 3 (Generate) → 4 (Deploy) → 5 (Iterate)
                                                                  ├→ 6 (Import)
                                                                  ├→ 7 (Graph Editor, no AWS needed)
                                                                  └→ 8 (Inspect, requires Tutorials 1-5)
```

Tutorials 1-5 are strictly sequential. Tutorials 6-8 can be done in any order after Tutorial 5 (though 7 and 8 only need Tutorial 1 for basic use).

### Key Pedagogical Patterns

- **Learn-by-breaking** (Tutorial 2): Intentionally introduce 3 types of errors (YAML syntax, Pydantic structural, semantic) to teach the validation pipeline
- **Progressive complexity**: Offline-only (1-3) → AWS deployment (4-5) → Advanced tools (6-8)
- **Consistent running example**: Same "Order Processing" workflow builds up across tutorials 1-7
- **Two test payloads per Choice branch** (Tutorial 5): Invoke with different data to exercise both paths
- **Complete development lifecycle** (Tutorial 8 summary): init → validate → generate → deploy → iterate → invoke → inspect → edit → teardown

### Tutorial Artifacts (All Inline)

All code examples are embedded inline in Markdown (no separate files):
- YAML workflow definitions
- Python handler implementations with `@state` decorators
- Terraform HCL (6 generated files explained)
- ASL JSON (1 example for import)
- Bash commands (100+ CLI examples across all tutorials)
- Command reference tables (Tutorial 7)
- Error reference table (Tutorial 2)

---

## Screenshot Automation (Playwright)

### Overview

Automated Playwright-based screenshot capture produces 15 PNG files (3 per example × 5 examples) via a single `npm run screenshots` command. Screenshots are embedded in example READMEs and tutorial documents.

### Technical Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Browser automation | @playwright/test | 1.58.2 (pinned exact, no caret) |
| TypeScript runner | tsx | 4.19.4 |
| Browser | Chromium (installed via `npx playwright install chromium`) |
| Viewport | 1440×900 pixels |

### Screenshot Types (3 per example)

| Type | Filename Pattern | What It Shows |
|------|-----------------|--------------|
| Graph | `{example}-graph.png` | Graph editor full layout (graph only, editor/palette hidden) |
| DSL | `{example}-dsl.png` | YAML editor panel alongside graph (full editor view) |
| Inspector | `{example}-inspector.png` | Execution inspector with timeline and state data |

### Capture Process (`capture-screenshots.ts`)

For each of 5 examples:

**Graph + DSL screenshots:**
1. Spawn `rsf ui {workflow.yaml} --port 8765 --no-browser`
2. Health-check `http://127.0.0.1:8765/` (30 attempts, 500ms intervals)
3. Navigate Playwright to URL, wait for `.react-flow__node` selector (15s timeout)
4. Wait 2s for ELK layout stabilization
5. Capture full page → `{example}-dsl.png` (includes editor, palette, graph)
6. Hide `.editor-pane`, `.palette`, `.inspector-panel` via JavaScript injection
7. Wait 1s for reflow, capture → `{example}-graph.png`
8. Kill rsf ui server

**Inspector screenshots:**
1. Spawn mock inspect server on port 8766 (loads fixture JSON)
2. Spawn Vite dev server on port 5199
3. Navigate to `http://127.0.0.1:5199/#/inspector`
4. Wait for `.execution-list-item` selector (15s), click first execution
5. Wait for `.inspector-center .react-flow__node` (15s)
6. Wait for `.timeline-event` (10s, non-blocking on failure)
7. Wait 2s for layout/SSE completion, capture → `{example}-inspector.png`
8. Kill servers

**Validation:** All 15 files must exist and be > 10 KB (prevents blank screenshots).

### Mock Inspect Server (`mock-inspect-server.ts`)

HTTP server emulating the RSF inspect API using Node built-in `http` module (zero external dependencies):

```
GET  /api/inspect/executions              → { executions, next_token }
GET  /api/inspect/execution/:id           → execution_detail object
GET  /api/inspect/execution/:id/history   → { execution_id, events }
GET  /api/inspect/execution/:id/stream    → SSE stream (text/event-stream)
OPTIONS *                                  → CORS preflight (204)
```

SSE stream sends two events then closes: `execution_info` (detail without history), `history` (array of events).

### Mock Fixture Schema

Each fixture JSON file (`ui/scripts/fixtures/{example}.json`) contains:

```json
{
  "executions": [{
    "execution_id": "string",
    "name": "string",
    "status": "SUCCEEDED",
    "function_name": "string",
    "start_time": "ISO-8601",
    "end_time": "ISO-8601"
  }],
  "execution_detail": {
    "execution_id": "string",
    "name": "string",
    "status": "SUCCEEDED",
    "function_name": "string",
    "start_time": "ISO-8601",
    "end_time": "ISO-8601",
    "input_payload": { ... },
    "result": { ... },
    "error": null,
    "history": [{
      "event_id": 1,
      "timestamp": "ISO-8601",
      "event_type": "StateEntered|StateSucceeded|StateFailed",
      "sub_type": null,
      "details": {
        "stateName": "string",
        "input": { ... },
        "output": { ... }
      }
    }]
  }
}
```

History events contain full state input/output payloads for timeline rendering.

### Server Lifecycle Scripts

**`start-ui-server.ts`** — Spawns `rsf ui`, health-checks, outputs `SERVER_READY`/`SERVER_STOPPED` signals.

**`start-inspect-server.ts`** — Spawns mock inspect server, health-checks `/api/inspect/executions`, outputs `SERVER_READY`/`SERVER_STOPPED` signals.

Both use the same pattern: CLI args (`--example`, `--port`), spawn child process, poll health endpoint, signal protocol for downstream automation.

### Process Management

- Child processes tracked in `Set<ChildProcess>`
- Detached process groups for reliable cleanup (kills grandchildren like npx → vite)
- SIGINT/SIGTERM handlers kill all children
- Graceful shutdown: SIGTERM with 3s timeout → SIGKILL fallback
- Port availability checked with `lsof` before launch

### rsf CLI Resolution

Multi-stage fallback for finding the `rsf` binary:
1. `.venv/bin/rsf` (venv in project root)
2. PATH lookup
3. `.venv/bin/python -m rsf` (venv Python fallback)

### TypeScript Configuration

Separate `tsconfig.scripts.json` for Node scripts (vs bundler-mode app tsconfig):

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "node",
    "types": ["node"],
    "strict": true,
    "esModuleInterop": true
  },
  "include": ["scripts"]
}
```

### Documentation Embedding

**Example READMEs** (`examples/{name}/README.md`):

```markdown
## Screenshots

### Graph Editor
![{Name} — Graph Editor](../../docs/images/{example}-graph.png)

### DSL Editor
![{Name} — DSL Editor](../../docs/images/{example}-dsl.png)

### Execution Inspector
![{Name} — Execution Inspector](../../docs/images/{example}-inspector.png)
```

**Tutorial 07** (`tutorials/07-graph-editor.md`): Graph + DSL screenshots inline at contextual points (after Step 2 and Step 3).

**Tutorial 08** (`tutorials/08-execution-inspector.md`): Inspector screenshot inline after Step 6.

---

## Known Gaps (Optional Future Work)

- `context.parallel()` / `context.map()` return `BatchResult` in real SDK but mock returns plain list
- No Catch workflow in AWS integration tests (covered by 12 unit tests)
- Integration tests with real Lambda are slow (~9 min) — consider a faster feedback loop

---

## Constraints

- **Runtime:** Python 3.13+ (Lambda Durable Functions SDK requirement)
- **Infrastructure:** Terraform for IaC (not CDK/SAM/CloudFormation)
- **UI Framework:** React with @xyflow/react for graph visualization
- **Graph Layout:** elkjs Sugiyama algorithm for auto-layout
- **Import Format:** AWS Step Functions ASL JSON as input format
- **Feature Parity:** All AWS Step Functions features in the DSL (8 state types, 39 operators, error handling, I/O processing, intrinsic functions, variables, context object)
- **Local-first:** No hosted service, no authentication — runs on developer's machine

## Out of Scope

- Go or other language runtime support
- Team collaboration features (multi-user editing, permissions)
- Hosted web service with authentication
- VS Code extension
- Direct AWS Console integration
- Real-time chat or collaboration
- Mobile app

---

## Documentation

### Documentation Files

| File | Contents |
|------|----------|
| `docs/tutorial.md` | Quick-start overview (11 steps: install through graph editor) |
| `docs/migration-guide.md` | How to import existing Step Functions workflows |
| `docs/reference/dsl.md` | Complete field reference for all state types |
| `docs/reference/state-types.md` | Detailed examples with YAML + generated Python code |
| `docs/index.md` | Documentation home page |
| `tutorials/01-08` | 8 step-by-step tutorials covering all 7 CLI commands |
| `examples/README.md` | Quick-start guide with example summary table and prerequisites |
| `examples/{name}/README.md` | Per-example READMEs with feature tables, workflow diagrams, screenshots |
| `README.md` | Project overview, quickstart, architecture, contributing guide |
| `LICENSE` | Apache-2.0 |

### Screenshots (15 PNGs)

Automated Playwright screenshots in `docs/images/`:
- `{example}-graph.png` — Graph editor full layout (graph nodes + edges only)
- `{example}-dsl.png` — YAML editor panel alongside graph
- `{example}-inspector.png` — Execution inspector with timeline and state data

Generated via `npm run screenshots` in `ui/` directory. Embedded in:
- All 5 example READMEs (3 screenshots each)
- Tutorial 07 (2 graph editor screenshots)
- Tutorial 08 (1 inspector screenshot)

Build docs with MkDocs Material theme (admonition, code tabs, superfences, syntax highlighting).

---

*This blueprint contains sufficient detail to recreate the complete RSF project using `/gsd:new-project`. When presented with this document, the GSD workflow should derive requirements, create a phased roadmap, and execute each phase to produce a functionally equivalent implementation.*
