# Codebase Structure

**Analysis Date:** 2026-03-11

## Directory Layout

```
/Users/esa/git/rsf-python/
├── src/rsf/                    # Main package source code (99 .py files)
│   ├── __init__.py             # Package entry point
│   ├── config.py               # Project configuration loader (rsf.toml)
│   ├── cli/                    # CLI command interface (Typer)
│   ├── cdk/                    # AWS CDK code generator provider
│   ├── codegen/                # Core code generation engine
│   ├── context/                # ASL context object model
│   ├── dsl/                    # DSL parsing and validation
│   ├── editor/                 # Visual workflow editor (FastAPI + React SPA)
│   ├── functions/              # Intrinsic functions (States.*)
│   ├── importer/               # ASL JSON to YAML converter
│   ├── inspect/                # Lambda execution inspector
│   ├── io/                     # I/O pipeline (JSONPath, payload templates)
│   ├── providers/              # Infrastructure providers (Terraform, CDK, Custom)
│   ├── registry/               # Handler and startup hook registry
│   ├── schema/                 # JSON schema generation
│   ├── terraform/              # Terraform code generator provider
│   ├── testing/                # Testing utilities (chaos injection, mock SDK)
│   └── variables/              # Variable resolution ($varName)
├── tests/                      # Test suite (24 subdirectories)
│   ├── test_cdk/               # CDK provider tests
│   ├── test_codegen/           # Code generation tests
│   ├── test_context/           # Context object tests
│   ├── test_dsl/               # DSL parsing tests
│   ├── test_examples/          # Integration tests for example workflows
│   ├── test_functions/         # Intrinsic function tests
│   ├── test_inspect/           # Inspector/editor tests
│   ├── test_integration/       # End-to-end AWS integration tests
│   ├── test_io/                # I/O pipeline tests
│   ├── test_mock_sdk/          # Mock SDK tests
│   ├── test_providers/         # Provider implementation tests
│   └── more...
├── examples/                   # Complete example workflows (7 projects)
│   ├── order-processing/       # Task → Choice → Parallel → Succeed/Fail
│   ├── data-pipeline/          # S3 event → Map → multiple tasks
│   ├── approval-workflow/      # Task → Wait → Task → Succeed
│   ├── intrinsic-showcase/     # Demonstrates States.* functions
│   ├── lambda-url-trigger/     # Lambda Function URL input
│   ├── retry-and-recovery/     # Retry + Catch error handling
│   └── registry-modules-demo/  # Multi-module handler registration
├── fixtures/                   # Test fixtures and sample data
├── docs/                       # Documentation (mkdocs)
├── tutorials/                  # Step-by-step guides
├── ui/                         # Electron app for editor/inspector UI
├── vscode-extension/           # VS Code extension for editor
├── action/                     # GitHub Actions (CI/CD workflows)
├── .github/                    # GitHub configuration
├── .planning/                  # GSD planning documents (auto-generated)
├── schema/                     # JSON schema files
├── schemas/                    # JSON schema definitions
├── pyproject.toml              # Project metadata, dependencies, build config
├── mkdocs.yml                  # Documentation site config
├── RSF-BLUEPRINT.md            # Architecture blueprint document
└── README.md                   # Project overview
```

## Directory Purposes

**`src/rsf/cli/`:**
- Purpose: CLI command interface for all user-facing operations
- Contains: Typer app with subcommands (init, generate, deploy, test, validate, watch, inspect, ui, export, import, logs, cost, diff, doctor, schema)
- Key files: `main.py` (Typer app), `generate_cmd.py`, `deploy_cmd.py`, `test_cmd.py`, `watch_cmd.py`, `inspect_cmd.py`
- Templates subdirectory: CRUD and S3 pipeline project templates

**`src/rsf/codegen/`:**
- Purpose: Transform validated DSL definitions into executable Python code
- Contains: State mapping engine, template rendering, orchestrator emission, handler stub generation
- Key files: `generator.py` (main entry point), `state_mappers.py` (state-to-code mapping), `emitter.py` (code block emission), `engine.py` (Jinja2 setup)
- Templates subdirectory: Jinja2 templates for orchestrator code (state blocks, imports, context setup)

**`src/rsf/dsl/`:**
- Purpose: Define and parse RSF workflow definitions in YAML/JSON
- Contains: Pydantic models for all state types, choice rule evaluation, retry/catch policies, validation
- Key files: `models.py` (8 state types + root), `parser.py` (YAML/JSON loading), `validator.py` (semantic validation), `choice.py` (choice rule logic), `errors.py` (Retry/Catch)

**`src/rsf/io/`:**
- Purpose: Implement ASL 5-stage I/O processing pipeline
- Contains: JSONPath evaluation, payload template application, result path merging
- Key files: `pipeline.py` (main pipeline), `jsonpath.py` (JSONPath evaluator), `payload_template.py` (template application), `result_path.py` (result merging)

**`src/rsf/functions/`:**
- Purpose: Implement ASL intrinsic functions (States.Format, States.StringConcat, etc.)
- Contains: Function registry with @intrinsic decorator, individual function implementations
- Key files: `registry.py` (decorator and lookup), `parser.py` (expression parsing), `string.py`, `array.py`, `math.py`, `json_funcs.py`, `encoding.py`, `utility.py`

**`src/rsf/providers/`:**
- Purpose: Abstract and implement infrastructure deployment backends
- Contains: Provider ABC, Terraform generator, CDK generator, custom provider, prerequisite checks
- Key files: `base.py` (InfrastructureProvider ABC), `terraform.py`, `cdk.py`, `custom.py`, `registry.py` (provider lookup), `metadata.py` (custom provider transport)

**`src/rsf/registry/`:**
- Purpose: Handler and startup hook registration at runtime
- Contains: Global registries for @state/@startup decorators, handler discovery from modules
- Key files: `registry.py` (decorator and lookup functions)

**`src/rsf/context/`:**
- Purpose: Model the ASL context object ($$) available in expressions
- Contains: Nested dataclasses for Execution, State, StateMachine, Task, Map contexts
- Key files: `model.py` (ContextObject, ExecutionContext, etc.)

**`src/rsf/variables/`:**
- Purpose: Track and resolve $varName references (distinct from JSONPath)
- Contains: Variable store, Assign field processing, pattern matching
- Key files: `resolver.py` (pattern matching and Assign application), `store.py` (variable storage)

**`src/rsf/inspect/`:**
- Purpose: Runtime execution inspection and live monitoring
- Contains: FastAPI server, Lambda inspection client, execution history/detail endpoints
- Key files: `server.py` (FastAPI app), `client.py` (Lambda inspection), `router.py` (API endpoints), `models.py` (data models)

**`src/rsf/editor/`:**
- Purpose: Visual workflow editor with live preview
- Contains: FastAPI server for editor, WebSocket for live updates, React SPA static files
- Key files: `server.py` (FastAPI), `websocket.py` (WebSocket handler)

**`src/rsf/cdk/`:**
- Purpose: AWS CDK code generator for infrastructure
- Contains: CDK provider implementation, template rendering
- Key files: `generator.py`, `engine.py`
- Templates subdirectory: CDK app and stack templates

**`src/rsf/terraform/`:**
- Purpose: Terraform code generator for infrastructure
- Contains: Terraform provider implementation, template rendering
- Key files: `generator.py`, `engine.py`
- Templates subdirectory: Terraform variable, resource, and output templates

**`src/rsf/importer/`:**
- Purpose: Convert AWS Step Functions ASL JSON to RSF YAML
- Contains: ASL JSON parser, YAML output generation
- Key files: `converter.py`

**`src/rsf/schema/`:**
- Purpose: Generate JSON schema for RSF workflow definitions
- Contains: Schema generation logic
- Key files: `generate.py`

**`src/rsf/testing/`:**
- Purpose: Testing utilities for RSF workflows
- Contains: Mock SDK, chaos injection for testing
- Key files: `chaos.py` (chaos injection)

**`tests/`:**
- Purpose: Complete test suite for all components
- Contains: Unit tests (100+), integration tests, example workflow tests
- Key directories: `test_cdk/`, `test_codegen/`, `test_dsl/`, `test_functions/`, `test_io/`, `test_examples/`, `test_integration/`

**`examples/`:**
- Purpose: Complete, runnable example workflows
- Contains: 7 fully implemented workflows with handlers, tests, and infrastructure code
- Key examples:
  - `order-processing/`: Multi-stage order processing (Task → Choice → Parallel → Succeed/Fail)
  - `data-pipeline/`: S3-triggered data transformation (Task → Map → Task chain)
  - `approval-workflow/`: Manual approval pattern (Task → Wait → Task)
  - `intrinsic-showcase/`: Demonstrates States.* functions

## Key File Locations

**Entry Points:**

- `src/rsf/cli/main.py`: Typer CLI app with subcommands
- `src/rsf/__init__.py`: Package export point (empty, version in __version__.py)
- Generated orchestrator: `src/generated/orchestrator.py` → `lambda_handler(context: DurableContext, event: dict)`

**Configuration:**

- `pyproject.toml`: Project metadata, dependencies, build config, pytest config
- `src/rsf/config.py`: rsf.toml loader (infrastructure config resolution)
- `src/rsf/dsl/models.py`: InfrastructureConfig model

**Core Logic:**

- `src/rsf/codegen/generator.py`: Main code generation entry point
- `src/rsf/dsl/parser.py`: YAML/JSON loading and validation
- `src/rsf/io/pipeline.py`: I/O pipeline orchestration
- `src/rsf/functions/registry.py`: Intrinsic function registry
- `src/rsf/registry/registry.py`: Handler and startup hook registry
- `src/rsf/providers/base.py`: Provider interface (ABC)

**Testing:**

- `tests/conftest.py`: Global pytest configuration
- `tests/mock_sdk.py`: Mock Lambda execution SDK
- `examples/*/tests/`: Integration tests for each example

## Naming Conventions

**Files:**

- Command modules: `{command}_cmd.py` (e.g., `generate_cmd.py`, `deploy_cmd.py`)
- State mappers: `state_mappers.py` (plural)
- Model/data files: `models.py` or `types.py`
- Utility/implementation: `{domain}.py` (e.g., `jsonpath.py`, `payload_template.py`)
- Providers: `{provider_name}.py` (e.g., `terraform.py`, `cdk.py`)

**Directories:**

- Commands: `cli/`
- Models/schemas: `dsl/`, `context/`
- Implementations: Domain-specific (e.g., `io/`, `functions/`, `providers/`)
- Tests: `test_{domain}/` (e.g., `test_codegen/`, `test_functions/`)

**Python Objects:**

- Pydantic models: PascalCase with suffix (e.g., `TaskState`, `ChoiceState`, `StateMachineDefinition`)
- Classes: PascalCase (e.g., `InfrastructureProvider`, `VariableStore`)
- Functions: snake_case (e.g., `generate()`, `process_jsonpath_pipeline()`, `get_handler()`)
- Constants: SCREAMING_SNAKE_CASE (e.g., `GENERATED_MARKER`, `TEMPLATES_DIR`)
- Private/internal: Leading underscore (e.g., `_IOFields`, `_handlers`, `_startup_hooks`)

## Where to Add New Code

**New State Type (rare):**
- Add Pydantic model to `src/rsf/dsl/models.py` with proper mixins (_IOFields, _TransitionFields, etc.)
- Add state mapper in `src/rsf/codegen/state_mappers.py` (StateMapping dataclass)
- Add code emitter in `src/rsf/codegen/emitter.py` (emit_state_block function)
- Add Jinja2 template to `src/rsf/codegen/templates/` if needed
- Add tests to `tests/test_codegen/` and `tests/test_dsl/`

**New Intrinsic Function:**
- Add function implementation to appropriate module in `src/rsf/functions/` (string.py, array.py, etc.)
- Decorate with `@intrinsic("States.FunctionName")`
- Add tests to `tests/test_functions/test_intrinsics.py`

**New CLI Command:**
- Create `src/rsf/cli/{command}_cmd.py` with a function decorated with `@app.command()`
- Import and register in `src/rsf/cli/main.py` (line 43-58)
- Add tests to `tests/test_cli/` or relevant test directory

**New Provider:**
- Create `src/rsf/providers/{provider_name}.py` inheriting from `InfrastructureProvider`
- Implement all abstract methods: `generate()`, `deploy()`, `teardown()`, `check_prerequisites()`, `validate_config()`
- Add provider to registry in `src/rsf/providers/registry.py`
- Add templates to `src/rsf/{provider_name}/templates/` if needed
- Add tests to `tests/test_providers/`

**New Handler Handler (for orchestrator):**
- Handlers are generated by codegen; custom logic goes in generated `handlers/` subdirectory of project
- Register with `@state("StateName")` decorator from `rsf.registry`
- Add tests alongside handler code

**Shared Utilities:**
- Generic utilities (not domain-specific): `src/rsf/` or appropriate existing module
- Example: If adding a new JSONPath feature, add to `src/rsf/io/jsonpath.py`

**Tests:**
- Unit tests: `tests/test_{domain}/{test_module}.py`
- Integration tests: `tests/test_integration/`
- Example tests: `examples/{example_name}/tests/test_{feature}.py`

## Special Directories

**`src/rsf/cli/templates/`:**
- Purpose: Project templates for `rsf init` and `rsf generate`
- Generated: No (committed to repo)
- Committed: Yes
- Contains: `api-gateway-crud/` and `s3-event-pipeline/` project templates with sample handlers and tests

**`src/rsf/codegen/templates/`:**
- Purpose: Jinja2 templates for generating orchestrator code
- Generated: No (committed to repo)
- Committed: Yes
- Contains: `orchestrator.jinja2` and state block templates

**`src/rsf/cdk/templates/`:**
- Purpose: Jinja2 templates for generating CDK infrastructure code
- Generated: No (committed to repo)
- Committed: Yes
- Contains: `app.jinja2`, `stack.jinja2`, etc.

**`src/rsf/terraform/templates/`:**
- Purpose: Jinja2 templates for generating Terraform code
- Generated: No (committed to repo)
- Committed: Yes
- Contains: `main.tf.jinja2`, `variables.tf.jinja2`, `outputs.tf.jinja2`

**`src/rsf/editor/static/`:**
- Purpose: Built React SPA for visual editor (hash routing)
- Generated: Yes (by Vite build in ui/ directory)
- Committed: Yes (built assets)
- Contains: Compiled JS/CSS, assets, index.html

**`examples/{example}/src/generated/`:**
- Purpose: Generated orchestrator and handler stubs from workflow.yaml
- Generated: Yes (by `rsf generate workflow.yaml`)
- Committed: Yes (so examples are runnable without regeneration)
- Contains: `orchestrator.py`, `handlers/{handler_name}.py`

**`examples/{example}/terraform/`:**
- Purpose: Generated Terraform infrastructure code
- Generated: Yes (by `rsf deploy`)
- Committed: Yes (so infrastructure is reproducible)
- Contains: `.tf` files with Lambda function, IAM roles, etc.

**`.planning/`:**
- Purpose: GSD (Goal System Design) planning documents
- Generated: Yes (by GSD orchestrator)
- Committed: Yes (for visibility)
- Contains: `ARCHITECTURE.md`, `STRUCTURE.md`, `CONVENTIONS.md`, `TESTING.md`, etc.

---

*Structure analysis: 2026-03-11*
