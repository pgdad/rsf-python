# Architecture

**Analysis Date:** 2026-03-11

## Pattern Overview

**Overall:** RSF (Replacement for Step Functions) is a **DSL-to-code generation framework** that transforms YAML workflow definitions into Python Lambda handler orchestration code. The architecture follows a **pipeline pattern**: parse DSL → validate → map states → generate orchestrator and handlers → deploy infrastructure.

**Key Characteristics:**
- **Generator-centric**: Codegen is the core responsibility—YAML DSL in, Python code out
- **Multi-target deployment**: Supports Terraform, AWS CDK, and custom providers
- **AWS-native primitives**: Executes on Lambda using Durable Functions SDK for state management
- **Stateless state machine**: Handler registry + context object enable orchestration without external state store

## Layers

**DSL & Validation Layer:**
- Purpose: Parse and validate workflow YAML/JSON definitions
- Location: `src/rsf/dsl/` (parser, models, validator, types, choice, errors)
- Contains: Pydantic models for all ASL state types (Task, Pass, Choice, Parallel, Map, Wait, Succeed, Fail), choice rule evaluation, retry/catch policies
- Depends on: pydantic, pyyaml
- Used by: Codegen, Config resolution, all downstream processors

**Code Generation Layer:**
- Purpose: Transform validated StateMachineDefinition into executable Python code
- Location: `src/rsf/codegen/` (generator, engine, state_mappers, emitter)
- Contains: State-to-code mapping engine, Jinja2 template rendering, handler stub generation, orchestrator emission
- Depends on: DSL models, Jinja2, pathlib
- Used by: CLI generate command, deployment pipeline

**Handler Registry & Runtime Layer:**
- Purpose: Register handler functions at runtime and resolve them during orchestration
- Location: `src/rsf/registry/` (registry.py - @state/@startup decorators), `src/rsf/context/` (ContextObject, ExecutionContext)
- Contains: Global handler registry, startup hook registration, ASL context object ($$) modeling
- Depends on: importlib (for handler discovery)
- Used by: Generated orchestrator code, handler execution

**I/O Processing Pipeline:**
- Purpose: Implement ASL 5-stage I/O processing (InputPath → Parameters → [Task] → ResultSelector → ResultPath → OutputPath)
- Location: `src/rsf/io/` (pipeline.py, jsonpath.py, payload_template.py, result_path.py)
- Contains: JSONPath evaluation, payload template application, result merging logic
- Depends on: jsonpath-ng (implied), intrinsic function evaluator
- Used by: Generated orchestrator (via templates), task execution

**Variable Resolution Layer:**
- Purpose: Track and resolve $varName references (not JSONPath, not $$ context)
- Location: `src/rsf/variables/` (resolver.py, store.py)
- Contains: Variable store backed by dict, Assign field processing, variable pattern matching
- Depends on: regex for pattern matching
- Used by: I/O pipeline when resolving variables in payload templates

**Intrinsic Functions:**
- Purpose: Implement ASL intrinsic functions (States.Format, States.StringConcat, States.ArrayLength, etc.)
- Location: `src/rsf/functions/` (registry.py, parser.py, array.py, string.py, math.py, json_funcs.py, encoding.py, utility.py)
- Contains: @intrinsic decorator registry, function parsers for expression language
- Depends on: json, base64, urllib
- Used by: Payload template evaluation, I/O pipeline

**Infrastructure Providers:**
- Purpose: Abstract deployment backends (Terraform, CDK, Custom)
- Location: `src/rsf/providers/` (base.py, terraform.py, cdk.py, custom.py, registry.py, metadata.py, transports.py)
- Contains: InfrastructureProvider ABC, provider implementations, prerequisite checks, metadata transport (for custom providers)
- Depends on: provider-specific tools (terraform CLI, CDK library, etc.)
- Used by: CLI deploy, teardown, diff commands

**Inspector & Editor Layer:**
- Purpose: Runtime execution inspection and visual workflow editor
- Location: `src/rsf/inspect/` (server.py, router.py, client.py, models.py), `src/rsf/editor/` (server.py, websocket.py)
- Contains: FastAPI servers, Lambda inspection client, WebSocket live updates, React SPA static files
- Depends on: FastAPI, uvicorn, boto3
- Used by: CLI inspect/ui commands

**Importer Layer:**
- Purpose: Convert AWS Step Functions ASL JSON to RSF YAML
- Location: `src/rsf/importer/` (converter.py)
- Contains: ASL JSON parsing and YAML output generation
- Depends on: DSL models
- Used by: CLI import command

**CLI Command Layer:**
- Purpose: User-facing command interface via Typer
- Location: `src/rsf/cli/` (main.py, individual command files)
- Contains: init, generate, deploy, test, validate, watch, inspect, ui, export, import, logs, cost, diff, doctor, schema commands
- Depends on: All other layers
- Used by: Direct user invocation via `rsf` CLI

## Data Flow

**Workflow Execution Flow (Runtime):**

1. User invokes generated `lambda_handler(context: DurableContext, event: dict)`
2. Handler calls startup hooks (once per cold start)
3. Loop through states based on current_state:
   - Resolve handler via `registry.get_handler(state_name)`
   - Call `context.step(state_name, handler, input_data)` (Durable Functions SDK)
   - Apply I/O pipeline: InputPath → Parameters → [result from handler] → ResultSelector → ResultPath → OutputPath
   - Evaluate Choice rules or transition to Next state
   - Handle Catch/Retry via exception handling
4. Exit when reaching terminal state (Succeed/Fail)

**Code Generation Flow:**

1. User runs `rsf generate workflow.yaml`
2. Parse YAML → DSL validation → StateMachineDefinition
3. Map states via BFS: Task/Choice/Parallel/Map/Wait/Pass/Succeed/Fail
4. For each state, generate StateBlock via Jinja2 templates
5. Render orchestrator.py with state blocks + I/O pipeline calls
6. Create handler stubs in `handlers/` directory (skipped if already exist)
7. Write to output directory

**State Management:**

- **No external state store**: Orchestrator is stateless; state passed through input_data variable
- **Single execution path**: current_state variable controls which state block runs
- **Result threading**: I/O pipeline merges handler results back into raw input
- **Context injection**: ASL context object ($$) available in all JSONPath evaluations

## Key Abstractions

**StateMachineDefinition:**
- Purpose: Root Pydantic model representing the entire workflow
- Examples: `src/rsf/dsl/models.py` lines 424+
- Pattern: Pydantic v2 with aliases for ASL naming (e.g., `next` → "Next"), extra fields forbidden

**State Models (8 types):**
- Purpose: Type-safe representation of ASL state types
- Examples: `src/rsf/dsl/models.py` (TaskState, ChoiceState, ParallelState, MapState, PassState, WaitState, SucceedState, FailState)
- Pattern: Mixin composition (_IOFields for I/O, _TransitionFields for Next/End, _AssignOutput for variables)

**InfrastructureProvider:**
- Purpose: Abstract interface for deployment backends
- Examples: `src/rsf/providers/base.py` (ABC), implementations in terraform.py, cdk.py, custom.py
- Pattern: Single-argument ProviderContext passed to all lifecycle methods (validate_config → check_prerequisites → generate → deploy → teardown)

**ContextObject:**
- Purpose: ASL context ($$) available in JSONPath and JSONata expressions
- Examples: `src/rsf/context/model.py` (ExecutionContext, StateContext, StateMachineContext, TaskContext, MapContext)
- Pattern: Nested dataclasses with factory method for initialization

**VariableStore:**
- Purpose: Track $varName references across state transitions
- Examples: `src/rsf/variables/store.py`
- Pattern: Dict-backed store with get/set methods

**Payload Template:**
- Purpose: Apply JSONPath + intrinsic function expressions to data
- Examples: `src/rsf/io/payload_template.py`
- Pattern: Recursive evaluation of dicts/lists, detecting and applying intrinsic functions

## Entry Points

**CLI:**
- Location: `src/rsf/cli/main.py`
- Triggers: User runs `rsf [command]`
- Responsibilities: Subcommand routing (init, generate, deploy, test, validate, watch, inspect, ui, export, import, logs, cost, diff, doctor, schema)

**Lambda Handler (Generated Code):**
- Location: Generated as `src/generated/orchestrator.py` → `lambda_handler`
- Triggers: AWS Lambda invocation
- Responsibilities: State machine orchestration via while loop, handler invocation, I/O pipeline application, error handling

**Durable Functions SDK Integration:**
- Location: Called from generated code via `context.step()` and `context.parallel()`
- Triggers: Orchestrator needs to execute a handler or parallel branches
- Responsibilities: State durability, replay detection, async task handling

## Error Handling

**Strategy:** Multi-layered exception propagation with explicit catch/retry semantics

**Patterns:**

1. **Retry Policy** (DSL-defined):
   - Caught in Retry block with ErrorEquals matching
   - Exponential backoff via BackoffRate
   - Max attempts enforced
   - Pattern in generated code: try/except with error type matching

2. **Catch Policy** (DSL-defined):
   - Caught after Retry exhaustion or immediate error
   - ErrorEquals matching (supports "States.ALL" wildcard)
   - ResultPath merges error into input
   - Transitions to Next state or raises WorkflowError

3. **Validation Errors**:
   - Pydantic validation errors raised during DSL parsing
   - User must fix YAML before generation

4. **Handler Errors**:
   - Custom exceptions raised by handler functions caught by orchestrator
   - Matched against Retry/Catch ErrorEquals lists
   - If unmatched, propagates as WorkflowError

5. **WorkflowError**:
   - Raised by Fail states to terminate execution
   - Constructed with error name and cause message

## Cross-Cutting Concerns

**Logging:**
- Approach: Python `logging` module (no explicit handlers in framework code)
- Generated code imports logging; users configure via standard Python config
- Optional: OpenTelemetry tracing support (auto-injected in generated orchestrator if available)

**Validation:**
- Approach: Pydantic v2 models enforce schema at parse time
- All DSL input validated via StateMachineDefinition.model_validate()
- Provider configs validated via InfrastructureConfig.model_validate()

**Authentication & Authorization:**
- Approach: Delegated to AWS IAM (Lambda execution role)
- No explicit auth in framework; assumes Lambda role has necessary permissions
- Provider implementations check prerequisites (AWS credentials, Terraform, CDK CLI)

**Metrics & Observability:**
- CloudWatch: Optional—generated orchestrator includes _emit_metric() pattern (example code)
- OpenTelemetry: Optional—auto-enabled if opentelemetry-api is installed
- Both are no-op safe (errors swallowed to not break execution)

---

*Architecture analysis: 2026-03-11*
