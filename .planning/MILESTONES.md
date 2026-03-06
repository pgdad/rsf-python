# Milestones

## v3.2 Terraform Registry Modules Tutorial (Shipped: 2026-03-06)

**Phases completed:** 5 phases (56-60), 9 plans
**Authored code:** 889 LOC (Python, Terraform, YAML, Bash) + 861 LOC tutorial
**Requirements:** 21/21 complete
**Timeline:** 3 days (2026-03-04 → 2026-03-06)

**Key accomplishments:**
- Schema verification: Confirmed terraform-aws-modules/lambda v8.7.0 durable_config variables, Lambda alias convention ($LATEST workaround for provider issue #45800), and hybrid IAM approach — all 5 registry module versions pinned to exact strings
- Core example: Working registry-modules-demo example deploying Lambda Durable Functions via custom provider — deploy.sh reads RSF_METADATA_FILE via jq, zips generated source, runs terraform apply
- Full-stack registry modules: DynamoDB (for_each), SQS DLQ (conditional count), CloudWatch alarms (error_rate/duration/throttle), SNS topic — all via terraform-aws-modules with conditional creation and proper IAM wiring
- Test suite: 8 local unit tests (workflow parsing, handler registration) + real-AWS integration test with durable execution polling to SUCCEEDED and clean teardown verification via terraform state list
- Tutorial: 861-line tutorials/09-custom-provider-registry-modules.md with side-by-side HCL comparison (raw vs registry module), annotated WorkflowMetadata schema table, and 5 common pitfalls in Problem/Symptom/Fix format
- Quick tasks: Fixed all 7 examples end-to-end (195/195 tests), fixed rsf init/generate/deploy workflow, tagged releases v3.3-v3.5

---

## v3.0 Pluggable Infrastructure Providers (Shipped: 2026-03-03)

**Phases completed:** 5 phases (51-55), 17 plans
**Files changed:** 89 | **Net change:** +11,624 / -486 lines | **Source LOC:** ~36,400 Python + 8,900 TypeScript
**Timeline:** 6 days (2026-02-24 → 2026-03-02)
**Git range:** feat(51-01) → feat(55-04)

**Key accomplishments:**
- Abstract provider interface: InfrastructureProvider ABC with 5 abstract methods, ProviderContext dataclass, dict-dispatch registry, and shared `run_provider_command()` subprocess helper
- Metadata transport system: WorkflowMetadata dataclass capturing all DSL infrastructure fields + 3 transport mechanisms (JSON file with mode 0600, environment variables, CLI arg templates with `{placeholder}` substitution)
- Terraform provider refactor: TerraformProvider wrapping existing generator with zero behavior change; deploy_cmd refactored from ~80 LOC inline extraction to provider interface routing; `rsf.toml` project-wide config with YAML > toml > default cascade
- CDK provider: Full AWS CDK support with Jinja2-generated CDK apps (app.py, stack.py, cdk.json), bootstrap detection via boto3, and `npx aws-cdk@latest` invocation — no global CDK install required
- Custom provider: Security-hardened subprocess execution (`shell=False`, absolute path validation) for arbitrary external programs with configurable metadata transport selection per workflow
- Provider-aware CLI audit: doctor/diff/watch/export commands updated to handle any provider gracefully — Terraform checks become WARN for non-TF providers, diff gracefully declines, watch routes deploys through provider interface, export uses shared `create_metadata()` eliminating ~90 LOC duplication
- 29/29 requirements satisfied across 6 categories (Provider Abstraction, Metadata, Terraform Provider, CDK Provider, Custom Provider, Command Integration)

---

## v2.0 Comprehensive Enhancement Suite (Shipped: 2026-03-02)

**Phases completed:** 12 phases (39-50), 34 plans, 99 tasks
**Files changed:** 269 | **Source LOC:** ~9,900 Python + 2,300 TypeScript + 800 Jinja2
**Timeline:** 2 days (2026-03-01 → 2026-03-02)
**Git range:** feat(39-01) → feat(50-02)

**Key accomplishments:**
- Infrastructure decoupling: `--no-infra` flag makes Terraform generation optional; top-level workflow timeout enforcement added to DSL and orchestrator
- DSL extensions: EventBridge/SQS/SNS triggers, sub-workflow invocation, DynamoDB table definitions, CloudWatch alarms, Lambda DLQs, and multi-stage deployment (`--stage`)
- 9 new CLI commands: `rsf diff`, `rsf test`, `rsf watch`, `rsf logs`, `rsf doctor`, `rsf export`, `rsf cost`, `rsf init --template`, `rsf schema export`
- Observability suite: OpenTelemetry trace context injection in generated orchestrator, cost estimation CLI, CloudWatch metrics + Grafana dashboard example
- Advanced testing: Hypothesis property-based tests for I/O pipeline, ChaosFixture injection (`--chaos` flag on `rsf test`), snapshot golden-file tests for generated code
- IDE and CI integration: VS Code extension with LSP schema validation, go-to-definition, and inline graph preview; SchemaStore publication; reusable `rsf-action` GitHub Action; curated workflow templates
- 25/25 requirements satisfied across 7 categories (DSL, CLI, Observability, Testing, UI, Ecosystem, Infrastructure)

---

## v1.7 Lambda Function URL Support (Shipped: 2026-03-01)


**Phases completed:** 3 phases (36-38), 6 plans
**Files changed:** 35 | **Insertions:** 1,325
**Timeline:** 2026-03-01
**Git range:** 87bc283..526e7f1

**Key accomplishments:**
- LambdaUrlConfig DSL model with NONE/AWS_IAM auth types, Pydantic validation, and extra=forbid
- Lambda Function URL Terraform generation: lambda_url.tf.j2 template, conditional IAM InvokeFunctionUrl permission, conditional function_url output
- End-to-end deploy wiring: DSL lambda_url config → deploy_cmd.py → TerraformConfig → Jinja2 templates
- Working lambda-url-trigger example with 3-state webhook workflow, 19 local tests, and real-AWS integration test
- Tutorial Steps 12-14 extending docs/tutorial.md with Lambda URL YAML config, deploy, and curl POST walkthrough
- 779 total non-integration tests passing (16 new for Lambda URL features)

---

## v1.6 Ruff Linting Cleanup (Shipped: 2026-03-01)

**Phases completed:** 8 phases (28-35), 3 plans
**Timeline:** 2026-02-28 → 2026-03-01
**Git range:** d4cef53..5b7e7a9

**Key accomplishments:**
- Fixed all 61 F401 (unused import) violations across src/, tests/, examples/
- Fixed all F841, F541, E402, E741, E501 violations in single bulk pass (phases 29-34)
- Removed examples/ exclusion and all ignored rules from pyproject.toml ruff config
- Unified pytest configuration for 744 non-AWS tests in single invocation
- Applied ruff format to examples/ for consistent code style
- Zero ruff violations across entire codebase with no suppressions (except 2 intentional `noqa: F401` for side-effect imports)

---

## v1.5 PyPI Packaging & Distribution (Shipped: 2026-02-28)

**Phases completed:** 3 phases (25-27), 3 plans
**Files changed:** 25 | **Insertions:** 2,034
**Timeline:** 2026-02-28
**Git range:** 3f41271..3bb9b15

**Key accomplishments:**
- Installable Python package via `pip install rsf` with bundled React UI static assets and hatch-vcs git-tag versioning
- GitHub Actions CI workflow (ci.yml): ruff lint + pytest matrix (Python 3.12, 3.13) on every PR and push to main
- GitHub Actions release workflow (release.yml): React UI compile + wheel build + PyPI publish on v* tag push
- OIDC trusted publisher authentication for zero-secret PyPI publishing (no API tokens stored)
- Polished README landing page with PyPI/CI/License badges, quick-start guide, hero screenshots, and absolute URLs for PyPI compatibility
- `twine check` validation ensuring README renders correctly on both GitHub and PyPI

---

## v1.1 CLI Toolchain (Shipped: 2026-02-26)

**Phases completed:** 1 phase (12), 4 plans, 7 tasks
**CLI source:** 679 LOC Python | **Tests:** 1,038 LOC (49 tests)
**Git range:** feat(12-01) → feat(12-04)

**Key accomplishments:**
- Typer-based CLI entry point (`rsf`) with `--version` flag and 7 registered subcommands
- `rsf init` project scaffolding (workflow.yaml, handlers, tests, pyproject.toml, .gitignore) in ~78ms
- `rsf validate` with 3-stage validation pipeline and field-path error reporting
- `rsf generate` producing orchestrator + handler stubs with Generation Gap preservation
- `rsf deploy` with full Terraform pipeline and `--code-only` fast path for Lambda updates
- `rsf import`, `rsf ui`, and `rsf inspect` completing the full workflow lifecycle from terminal

---


## v1.2 Comprehensive Examples & Integration Testing (Shipped: 2026-02-26)

**Phases completed:** 5 phases (13-17), 9 plans
**Examples:** 5 workflows | **Integration tests:** 13 | **Local tests:** 152
**Lines of code:** ~8,261 (examples + test harness)
**Timeline:** 2 days (2026-02-24 to 2026-02-26)
**Git range:** 73c27ac..925e4a0

**Key accomplishments:**
- Five real-world example workflows covering all 8 ASL state types (order-processing, approval-workflow, data-pipeline, retry-and-recovery, intrinsic-showcase)
- Per-example Terraform infrastructure with isolated state, durable_config, DynamoDB integration
- Integration test harness: poll_execution, query_logs, terraform_teardown, UUID execution IDs, IAM propagation buffer
- 13 integration tests with dual-channel assertions (Lambda return values + CloudWatch logs) on real AWS
- 6 READMEs documenting DSL features, prerequisites, and quick-start guide
- Zero-resource teardown: terraform destroy + explicit delete_log_group ensures no orphaned AWS resources

---


## v1.3 Comprehensive Tutorial (Shipped: 2026-02-26)

**Phases completed:** 3 phases (18-20), 8 plans
**Tutorials:** 8 documents | **Lines:** 2,753 (Markdown)
**Timeline:** 2026-02-26
**Git range:** 1474b0e..40b83e3

**Key accomplishments:**
- 8 step-by-step tutorials covering all 7 RSF CLI commands (init, generate, validate, deploy, import, ui, inspect)
- `rsf init` + `rsf validate` tutorials with learn-by-breaking pattern and 3-stage error interpretation
- `rsf generate` tutorial with Generation Gap pattern, @state decorators, and multi-state workflow generation
- `rsf deploy` tutorial with all 6 Terraform files documented, IAM policy walkthrough, and AWS verification
- `--code-only` fast path, Lambda invocation testing both Choice branches, and zero-resource teardown
- `rsf import` tutorial with ASL JSON conversion and all 5 conversion rules documented
- `rsf ui` graph editor tutorial with bidirectional YAML↔graph sync and real-time validation
- `rsf inspect` tutorial with dedicated inspection workflow deployment, time machine scrubbing, and live SSE streaming

---


## v1.4 UI Screenshots (Shipped: 2026-02-27)

**Phases completed:** 4 phases (21-24), 5 plans
**Files changed:** 50 | **Insertions:** 4,820
**Timeline:** 2026-02-24 → 2026-02-27
**Git range:** ae0fe0c..fecee58

**Key accomplishments:**
- Playwright 1.58.2 installed as pinned devDependency with Chromium automation via tsx runner
- Mock execution fixtures and REST/SSE server for all 5 example workflows (no AWS dependency)
- Server lifecycle scripts (start-ui-server.ts, start-inspect-server.ts) with health-check and signal protocol
- 15 PNG screenshots captured via single `npm run screenshots` (graph, DSL editor, inspector × 5 examples)
- Screenshots embedded in all 5 example READMEs and 2 tutorial documents (07-graph-editor, 08-execution-inspector)

---

## v1.0 Core (Shipped: 2026-02-25)

**Phases completed:** 10 phases (1-11, no Phase 5), 39 plans
**Timeline:** 2026-02-24 → 2026-02-25
**Git range:** 2cd8309..35df889

**Key accomplishments:**
- YAML/JSON DSL with full ASL feature parity: 8 state types, 39 comparison operators, error handling, I/O processing, intrinsic functions, variables, context object — all with Pydantic v2 models and semantic BFS validation
- Python code generator (Jinja2) producing Lambda Durable Functions SDK orchestrator code with handler registry (`@state`, `@startup` decorators) and Generation Gap pattern
- 5-stage I/O processing pipeline (InputPath → Parameters → ResultSelector → ResultPath → OutputPath) with 18 intrinsic functions via recursive descent parser
- Terraform HCL generation with custom Jinja2 delimiters, IAM derivation, and ASL JSON importer
- React graph editor with bidirectional YAML↔graph sync, per-state-type nodes, ELK.js auto-layout, and AST-merge strategy
- React execution inspector with time machine scrubbing, live SSE updates, precomputed snapshots, and structural data diffs
- Comprehensive test suite: unit tests, integration tests, golden fixtures, vitest UI tests, 24 YAML fixtures
- Full documentation: README, MkDocs site, tutorial, DSL reference, migration guide

---
