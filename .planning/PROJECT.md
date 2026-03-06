# RSF — Replacement for Step Functions

## What This Is

RSF is a complete development platform for AWS Lambda Durable Functions (launched at re:Invent 2025), replacing AWS Step Functions. It provides a YAML/JSON DSL for defining state machines with event triggers, sub-workflows, DynamoDB tables, CloudWatch alarms, dead letter queues, and multi-stage deployment. Infrastructure provisioning is handled by a pluggable provider system (Terraform default, CDK and custom providers supported) — any external program can serve as an infrastructure provider via structured metadata passing. A Python code generator produces Lambda Durable Functions SDK code with OpenTelemetry tracing. The CLI toolchain includes 16 commands covering the full lifecycle: init, validate, generate, deploy, diff, test (with chaos injection), watch, logs, doctor, export, cost, import, ui, inspect, schema, and templated project scaffolding. A React-based graph editor, execution inspector with replay, VS Code extension with LSP, and a reusable GitHub Action round out the ecosystem. Six real-world example workflows with automated integration testing prove end-to-end correctness on real AWS.

## Core Value

Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.

## Current State

v3.6 shipped (2026-03-06). RSF is a full development platform installable via `pip install rsf` with bundled React UIs, git-tag versioning (hatch-vcs), and CI/CD publishing to PyPI. 16 CLI commands, 7 DSL extensions, pluggable infrastructure providers (Terraform, CDK, custom), OpenTelemetry tracing, VS Code extension, GitHub Action, and all requirements satisfied through v3.6. ~36,400 LOC Python source + ~8,041 LOC TypeScript (ui/src) + comprehensive test suite (112 vitest UI tests). The graph editor is now fully interactive: users can select/delete edges and nodes, expand any of the 8 state types to edit properties inline with live YAML sync, and benefit from required-field validation with radio group selectors for mutually exclusive fields. Seven real-world example workflows with automated integration testing prove end-to-end correctness on real AWS. Nine tutorials covering all CLI commands and the custom provider system.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ YAML/JSON DSL with full ASL feature parity (8 state types, 39 comparison operators, error handling, I/O processing, intrinsic functions, variables, context object) — v1.0
- ✓ Pydantic v2 models for all DSL elements with semantic cross-state validation (BFS) — v1.0
- ✓ Python code generator (Jinja2) producing Lambda Durable Functions SDK orchestrator code — v1.0
- ✓ Handler registry with `@state` and `@startup` decorators and auto-discovery — v1.0
- ✓ 5-stage I/O processing pipeline (InputPath → Parameters → ResultSelector → ResultPath → OutputPath) — v1.0
- ✓ 18 intrinsic functions with recursive descent parser — v1.0
- ✓ ASL Context Object model (`$$`) — v1.0
- ✓ Terraform HCL generation with custom Jinja2 delimiters, IAM derivation, and Generation Gap pattern — v1.0
- ✓ ASL JSON importer (parse → convert → emit YAML + handler stubs) — v1.0
- ✓ FastAPI backend for graph editor (REST + WebSocket + static file serving) — v1.0
- ✓ React graph editor with bidirectional YAML ↔ graph sync, per-state-type nodes, ELK.js auto-layout — v1.0
- ✓ FastAPI backend for execution inspector (REST + SSE) — v1.0
- ✓ React execution inspector with time machine scrubbing, live updates, structural data diffs — v1.0
- ✓ JSON Schema generation from Pydantic models for Monaco editor validation — v1.0
- ✓ Mock SDK for local testing of generated code — v1.0
- ✓ Comprehensive test suite (unit tests, integration tests, golden fixtures) — v1.0
- ✓ CLI toolchain: `rsf init`, `rsf generate`, `rsf validate`, `rsf deploy`, `rsf import`, `rsf ui`, `rsf inspect` — v1.1
- ✓ Five example workflows covering all 8 state types with DSL YAML, Python handlers, and local tests — v1.2
- ✓ Per-example Terraform infrastructure with isolated state, durable_config, and DynamoDB integration — v1.2
- ✓ Integration test harness: poll_execution, query_logs, terraform_teardown, UUID execution IDs — v1.2
- ✓ Dual-channel AWS verification: Lambda return values + CloudWatch log assertions on real AWS — v1.2
- ✓ Example documentation: per-example READMEs + top-level quick-start guide — v1.2
- ✓ 8 step-by-step tutorials covering all 7 CLI commands (init, generate, validate, deploy, import, ui, inspect) — v1.3
- ✓ Hands-on walkthroughs with working code users can follow step-by-step — v1.3
- ✓ Real AWS deployment tutorials with complete Terraform and provisioning scripts — v1.3
- ✓ Self-contained tutorial artifacts (handler code, YAML workflows, test scripts) — v1.3
- ✓ Automated Playwright screenshot capture for graph editor and execution inspector — v1.4
- ✓ Screenshot assets for all 5 example workflows (15 PNGs via `npm run screenshots`) — v1.4
- ✓ Example READMEs updated with embedded screenshots — v1.4
- ✓ Tutorial docs (07-graph-editor, 08-execution-inspector) updated with screenshots — v1.4
- ✓ PyPI package with bundled React UI static assets and hatch-vcs git-tag versioning — v1.5
- ✓ GitHub Actions CI/CD pipeline (lint + test on PR, build + publish on tag push) — v1.5
- ✓ OIDC trusted publisher for zero-secret PyPI publishing — v1.5
- ✓ README as polished landing page with badges, quick-start, and hero screenshots — v1.5
- ✓ Zero ruff linting violations with no ignored rules or exclusions — v1.6
- ✓ All 744 non-AWS tests pass in unified pytest invocation — v1.6
- ✓ Optional lambda_url DSL field with NONE/AWS_IAM auth types and Pydantic validation — v1.7
- ✓ Lambda Function URL Terraform generation (lambda_url.tf, conditional IAM, conditional outputs) — v1.7
- ✓ Lambda URL trigger example workflow with 19 local tests and real-AWS integration test — v1.7
- ✓ Tutorial Steps 12-14 covering Lambda URL YAML config, deploy, and curl POST invocation — v1.7
- ✓ Optional infrastructure generation (`--no-infra` flag decouples code gen from Terraform) — v2.0
- ✓ Top-level workflow timeout with DSL validation and orchestrator enforcement — v2.0
- ✓ EventBridge/SQS/SNS trigger sources with Terraform generation — v2.0
- ✓ Sub-workflow invocation as nested durable execution — v2.0
- ✓ DynamoDB table definitions with auto-generated Terraform and IAM — v2.0
- ✓ CloudWatch alarms (error rate, duration, throttle) with SNS targets — v2.0
- ✓ Dead letter queues for Lambda functions with SQS DLQ Terraform — v2.0
- ✓ Multi-stage deployment (`--stage dev/staging/prod`) with variable overrides — v2.0
- ✓ `rsf diff` for local vs deployed workflow comparison — v2.0
- ✓ `rsf test` for local execution with chaos injection (`--chaos` flag) — v2.0
- ✓ `rsf watch` for auto-validate/regenerate with optional `--deploy` — v2.0
- ✓ `rsf logs` for CloudWatch log tailing correlated by execution ID — v2.0
- ✓ `rsf doctor` for environment/project health diagnostics — v2.0
- ✓ `rsf export --format cloudformation` for SAM/CloudFormation templates — v2.0
- ✓ `rsf cost` for estimated monthly AWS cost breakdown — v2.0
- ✓ OpenTelemetry trace context injection in generated orchestrator — v2.0
- ✓ CloudWatch metrics + Grafana dashboard example — v2.0
- ✓ Inspector execution replay with editable input payload — v2.0
- ✓ JSON Schema published to SchemaStore for IDE auto-complete — v2.0
- ✓ Hypothesis property-based tests for I/O pipeline invariants — v2.0
- ✓ ChaosFixture test utilities for timeout/exception/throttle injection — v2.0
- ✓ Snapshot tests for generated orchestrator golden files — v2.0
- ✓ VS Code extension with LSP schema validation, go-to-definition, inline graph preview — v2.0
- ✓ `rsf init --template` with curated workflow templates (api-gateway-crud, s3-event-pipeline) — v2.0
- ✓ Reusable `rsf-action` GitHub Action for CI/CD with PR comment plans — v2.0
- ✓ Abstract infrastructure provider interface (InfrastructureProvider ABC) with pluggable registry — v3.0
- ✓ WorkflowMetadata dataclass + 3 metadata transports (JSON file, env vars, CLI arg templates) — v3.0
- ✓ TerraformProvider wrapping existing generator with zero behavior change; deploy_cmd refactored to provider interface — v3.0
- ✓ CDK provider with Jinja2-generated CDK apps, bootstrap detection, and `npx aws-cdk@latest` invocation — v3.0
- ✓ Custom provider with security-hardened subprocess (`shell=False`, absolute path validation) and configurable metadata transport — v3.0
- ✓ Provider configuration in workflow YAML `infrastructure:` block and project-wide `rsf.toml` with cascade — v3.0
- ✓ Provider-aware CLI: doctor/diff/watch/export handle any provider gracefully — v3.0
- ✓ Custom provider deploy.sh reading WorkflowMetadata via FileTransport and invoking terraform apply — v3.2
- ✓ Registry-modules-demo example deploying Lambda Durable Functions via terraform-aws-modules registry modules — v3.2
- ✓ Full-stack registry modules: DynamoDB, SQS DLQ, CloudWatch alarms, SNS via conditional terraform-aws-modules — v3.2
- ✓ Local unit tests and real-AWS integration test with durable execution polling and teardown verification — v3.2
- ✓ Tutorial 09: Custom provider with registry modules (side-by-side HCL comparison, schema table, pitfalls) — v3.2
- ✓ Edge selection with visual highlight and edge deletion via Delete/Backspace key (preserves nodes) — v3.6
- ✓ Node deletion with cascade removal of all connected edges, StartAt reassignment, and YAML sync — v3.6
- ✓ Expandable inline property editors on all 8 state type nodes with live YAML sync — v3.6
- ✓ Type-appropriate inputs (text, number, boolean, textarea) with debounced sync and focus guard — v3.6
- ✓ Required field validation enforced in the UI editor with shake animation and toast feedback — v3.6
- ✓ Radio group selectors for mutually exclusive fields (Wait duration, Task timeout/heartbeat, Fail error/cause) — v3.6

### Active

<!-- Current scope. Building toward these. -->

(None — planning next milestone)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Go or other language runtime support — Python-only implementation
- Team collaboration features — local-first tool, no multi-user editing
- Hosted web service with authentication — runs on developer's machine
- Direct AWS Console integration — operates independently
- Mobile app — desktop developer tool
- LocalStack / moto mocking of durable functions — Lambda Durable Functions (re:Invent 2025) not supported by either framework
- Parallel CI test execution — need cost and timing data from sequential runs first
- Java port — moved to separate rsf-java repo

## Context

- **Lambda Durable Functions SDK:** `aws_lambda_durable_execution_sdk_python` provides `context.step()`, `context.wait()`, `context.parallel()`, `context.map()` primitives with checkpoint/replay semantics
- **Runtime requirement:** Python 3.13+ (SDK requirement)
- **AWS provider >= 6.25.0** required for `durable_config` block in Terraform
- **Lambda control plane rate limit:** 15 req/s — inspector uses token bucket rate limiter at 12 req/s ceiling
- **Durable Lambda invocation:** Uses Event type (async), poll `list_durable_executions_by_function` for completion
- **Key SDK note:** `parallel()` and `map()` return `BatchResult` — call `.get_results()` for plain list
- The DSL achieves full AWS Step Functions ASL feature parity
- Shipped v1.2 with ~8,261 LOC in examples + test harness (Python, YAML, Terraform, Markdown)
- Shipped v1.3 with 2,753 lines of tutorial documentation across 8 tutorials
- Shipped v1.4 with 15 automated Playwright screenshots embedded in example READMEs and tutorials
- Shipped v1.5 with PyPI packaging, CI/CD, and README landing page
- Shipped v1.6 with zero ruff violations and 744 non-AWS tests passing
- Shipped v1.7 with Lambda Function URL support (DSL, Terraform, example, tutorial) and 779 non-AWS tests
- Shipped v2.0 with 12 phases, 34 plans, 25 requirements: full CLI toolchain (16 commands), 7 DSL extensions, observability, advanced testing, VS Code extension, GitHub Action, and workflow templates. 976+ non-AWS tests.
- Shipped v3.0 with 5 phases, 17 plans, 29 requirements: pluggable infrastructure providers (Terraform, CDK, custom), metadata transport system, provider-aware CLI commands, rsf.toml project config.
- Shipped v3.2 with 5 phases, 9 plans, 21 requirements: Terraform registry modules tutorial and example, custom provider deploy.sh, full-stack registry modules (Lambda, DynamoDB, SQS, CloudWatch, SNS), local and integration tests.
- Shipped v3.6 with 3 phases, 7 plans, 10 requirements: interactive graph editor with edge/node selection and deletion, expandable property editors on all 8 state types, radio group selectors, required-field validation, and live bidirectional YAML sync. 112 vitest UI tests.

## Constraints

- **Runtime:** Python 3.13+ — Lambda Durable Functions SDK requirement
- **Infrastructure:** Pluggable provider system (Terraform default, CDK and custom providers supported)
- **UI Framework:** React 19.x with @xyflow/react 12.x for graph visualization
- **Graph Layout:** elkjs 0.11.x Sugiyama layered algorithm
- **Import Format:** AWS Step Functions ASL JSON as input format
- **Feature Parity:** All AWS Step Functions features in the DSL
- **Local-first:** No hosted service, no authentication
- **License:** MIT

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Pydantic v2 discriminated unions for state types | Type-safe parsing with clear error messages; circular import broken via late binding in `__init__.py` | ✓ Good |
| BFS traversal for code generation | Ensures all reachable states (including Choice branches and loop targets) are included | ✓ Good |
| AST-merge strategy for Graph→YAML sync | Preserves complex state data (Choice rules, Catch arrays, Parallel branches) that the graph view can't represent | ✓ Good |
| Custom Jinja2 delimiters (`<< >>`, `<% %>`) for HCL | Avoids `${}` conflict with Terraform interpolation | ✓ Good |
| syncSource flag for bidirectional sync | Prevents infinite YAML↔Graph update loops; set before mutation, cleared after microtask | ✓ Good |
| Precomputed snapshots for time machine | O(1) scrubbing instead of O(n) recomputation per position | ✓ Good |
| Generation Gap pattern (first-line marker) | Generated code always overwritten; user code never touched | ✓ Good |
| Token bucket rate limiter (12 req/s) | Stays under 15 req/s Lambda control plane limit | ✓ Good |
| Separate Zustand stores (Flow + Inspect) | No cross-contamination between editor and inspector concerns | ✓ Good |
| Mock SDK for testing | Enables local execution of generated code without AWS | ✓ Good |
| Custom polling helper over DurableFunctionCloudTestRunner | Simpler, fewer dependencies, polling `list_durable_executions_by_function` by DurableExecutionName | ✓ Good |
| CloudWatch Logs Insights with 15s propagation buffer | Handles log delivery delays; retry loop ensures eventual consistency | ✓ Good |
| UUID-suffixed execution IDs (test-{name}-{ts}-{uuid8}) | Prevents collision across parallel/sequential re-runs | ✓ Good |
| Explicit delete_log_group after terraform destroy | Catches orphaned log groups that Terraform may miss | ✓ Good |
| hatchling + hatch-vcs for packaging | Git-tag-derived versioning, simple config, standard PEP 517 build | ✓ Good |
| Separate ci.yml and release.yml workflows | Different triggers, different permission scopes (id-token: write only on publish) | ✓ Good |
| OIDC trusted publisher for PyPI | Zero secrets stored in repo; PyPI and GitHub exchange OIDC token at publish time | ✓ Good |
| Absolute URLs in README for PyPI | PyPI does not resolve relative paths; raw.githubusercontent.com for images | ✓ Good |
| snake_case alias for RSF extension fields | `lambda_url` uses snake_case (matching `rsf_version`), distinguishing RSF extensions from PascalCase ASL fields | ✓ Good |
| Required enabled + auth_type fields (no defaults) | Forces explicit configuration; prevents accidental public endpoints | ✓ Good |
| Conditional Terraform file generation | lambda_url.tf skipped entirely when disabled, rather than rendered empty | ✓ Good |
| `--no-infra` flag for infrastructure decoupling | Separates code generation from Terraform; users who don't want IaC can still use RSF | ✓ Good |
| Wrapper approach for ChaosFixture in LocalRunner | Chaos-injected failures participate in retry/catch logic rather than bypassing it | ✓ Good |
| `rsf test --chaos STATE:TYPE` syntax | Repeatable flag with explicit state targeting; intuitive for users | ✓ Good |
| SchemaStore catalog entry for workflow.yaml | Automatic IDE auto-complete without manual schema configuration | ✓ Good |
| VS Code LSP-based extension | Reuses Pydantic validation via Python subprocess; consistent with `rsf validate` | ✓ Good |
| GitHub Action with composite + shell approach | No Docker dependency; faster startup; works on any runner OS | ✓ Good |
| Milestone audit + gap closure phases (49, 50) | Systematic verification ensured 25/25 requirements satisfied before shipping | ✓ Good |
| `abc.ABC` over `typing.Protocol` for provider interface | RSF owns all providers; ABC gives runtime TypeError on missing methods vs silent failure | ✓ Good |
| WorkflowMetadata in DSL/workflow semantics, not IaC tool semantics | Prevents leaky abstraction; providers translate to their own concepts | ✓ Good |
| Default provider `"terraform"` with zero config | v2.0 workflows work unchanged; no migration required | ✓ Good |
| Config cascade: workflow YAML > rsf.toml > hardcoded default | Explicit per-workflow overrides with project-wide defaults; stdlib `tomllib` for toml | ✓ Good |
| `npx aws-cdk@latest` instead of global CDK binary | No global install needed; always uses latest CDK version | ✓ Good |
| Custom provider `shell=False` + absolute path validation | Security hardened: no shell injection, program must exist and be executable | ✓ Good |
| Terraform doctor check WARN (not FAIL) for non-TF providers | Informational only; missing terraform is not an error when using CDK or custom | ✓ Good |
| FileTransport as canonical metadata transport for tutorials | ArgsTransport cannot handle list/dict fields reliably; FileTransport is universal | ✓ Good |
| Exact version pinning for registry modules (not ~> ranges) | Terraform does not lock module versions in .terraform.lock.hcl | ✓ Good |
| Lambda alias convention (never $LATEST) | Workaround for Terraform provider issue #45800 (AllowInvokeLatest unresolved) | ✓ Good |
| Hybrid IAM: managed policy + inline supplement | AWSLambdaBasicDurableExecutionRolePolicy covers base, inline adds InvokeFunction/ListDurable/GetDurable | ✓ Good |
| deploy.sh generates terraform.tfvars.json from RSF metadata via jq | Dynamic translation from RSF WorkflowMetadata to Terraform variables at deploy time | ✓ Good |
| Expandable nodes (not inspector panel) for property editing | Editing stays in graph context; no context switch to a side panel | ✓ Good |
| Live sync on every keystroke (no explicit save) | Text fields debounce 300ms, number/boolean sync immediately; minimal friction | ✓ Good |
| Radio groups for one-of fields (e.g., Wait duration type) | Enforces exactly one value selected; clears partner field on switch | ✓ Good |
| TRANSITION_MANAGED_KEYS guard in mergeGraphIntoYaml | Prevents stateData overwrites of transition-controlled fields (Next, End, Default, Choices, Catch, Retry) | ✓ Good |
| CustomEvent('rsf-graph-change') bridge for sync | Decouples node components from GraphCanvas; no prop threading needed | ✓ Good |
| Focus guard pattern (useEffect skips sync if input focused) | Prevents YAML updates from clobbering active typing in expanded property editors | ✓ Good |
| Single expandedNodeId (accordion) for expanded nodes | One expanded node at a time; prevents visual clutter and state complexity | ✓ Good |
| Keyboard listener on graph-container div (not document) | Prevents Delete/Backspace from triggering graph deletion while typing in Monaco editor | ✓ Good |

---
*Last updated: 2026-03-06 after v3.6 milestone*
