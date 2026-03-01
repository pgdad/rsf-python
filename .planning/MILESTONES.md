# Milestones

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

