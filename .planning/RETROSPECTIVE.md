# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.2 — Comprehensive Examples & Integration Testing

**Shipped:** 2026-02-26
**Phases:** 5 | **Plans:** 10

### What Was Built
- Five real-world example workflows covering all 8 ASL state types (order-processing, approval-workflow, data-pipeline, retry-and-recovery, intrinsic-showcase)
- Per-example Terraform infrastructure with isolated state, DynamoDB integration
- Shared integration test harness with poll_execution, query_logs, terraform_teardown
- 13 integration tests with dual-channel assertions (Lambda return values + CloudWatch logs)
- 6 READMEs with DSL feature tables and quick-start commands
- Zero-resource teardown mechanism

### What Worked
- Using use-case-driven examples (order processing, data pipeline, etc.) naturally exercised the full DSL feature surface without artificial test cases
- Class-scoped pytest fixtures cleanly handled deploy/teardown lifecycle per example
- Custom polling helper was simpler than adopting DurableFunctionCloudTestRunner
- Explicit delete_log_group after terraform destroy prevented orphaned resources

### What Was Inefficient
- Requirements traceability table checkboxes weren't updated during execution — had to bulk-update at milestone completion
- Phase 13 summary format differed from phases 14-17 (separate SUMMARY.md vs numbered SUMMARY files)

### Patterns Established
- Integration test pattern: terraform_deploy → iam_propagation_wait → invoke → poll_execution → query_logs → assertions → terraform_teardown
- UUID-suffixed execution IDs for collision avoidance
- 15s propagation buffer for CloudWatch log queries
- Per-example README format: DSL feature table + workflow path diagram + run commands

### Key Lessons
1. CloudWatch Logs Insights queries need a propagation buffer AND retry loop — logs can take 15-30s to appear
2. IAM role propagation after terraform apply needs an explicit wait — without it, Lambda invocations fail with permission errors
3. pytest conftest.py name collisions prevent running all examples' local tests with a single glob — for-loop workaround is needed

---

## Milestone: v1.3 — Comprehensive Tutorial

**Shipped:** 2026-02-26
**Phases:** 3 | **Plans:** 8

### What Was Built
- 8 step-by-step tutorials covering all 7 RSF CLI commands (init, generate, validate, deploy, import, ui, inspect)
- 2,753 lines of tutorial documentation
- Learn-by-breaking validation tutorial with 3-stage error interpretation
- Full AWS deployment tutorials with Terraform walkthrough and teardown verification
- ASL import tutorial with 5 conversion rules documented
- Graph editor tutorial with bidirectional sync walkthrough
- Execution inspector tutorial with time machine scrubbing and live SSE streaming

### What Worked
- Using actual CLI output (not idealized) in tutorials matches what users will actually see
- Learn-by-breaking pattern (intentionally introduce errors, then fix) teaches validation deeply
- Sequential tutorial chain (01→08) builds naturally — each tutorial picks up where the previous left off
- All 3 Phase 20 plans ran in parallel (Wave 1) since tutorials are independent documents — fast execution

### What Was Inefficient
- Summary one-liner extraction returned null for all summaries — the field wasn't populated during execution
- Phase 19 plans were forced sequential (3 waves) even though the tutorial documents could theoretically be written in parallel

### Patterns Established
- Tutorial format: prerequisites → numbered steps → verbatim CLI output → tips in blockquotes → forward pointer to next tutorial
- Textual UI descriptions (no screenshots) for Markdown-only tutorials
- Two test payloads per Choice branch to demonstrate both paths
- Command reference tables at end of tool tutorials

### Key Lessons
1. Documentation phases execute faster than code phases — 8 plans completed in minutes
2. Combining related requirements into single plans (DEPLOY-03 + DEPLOY-04 in one tutorial) produces more cohesive user experiences
3. Tutorial quality depends heavily on reading actual source code for CLI output — templated/idealized output would mislead users

---

## Milestone: v1.4 — UI Screenshots

**Shipped:** 2026-02-27
**Phases:** 4 | **Plans:** 5

### What Was Built
- Playwright 1.58.2 browser automation as pinned devDependency with tsx runner
- Mock execution fixtures and REST/SSE server for all 5 example workflows
- Server lifecycle scripts (start-ui-server.ts, start-inspect-server.ts) with health-check
- 15 PNG screenshots captured via single `npm run screenshots` command
- Screenshots embedded in 5 example READMEs and 2 tutorial documents

### What Worked
- Mock fixtures eliminated AWS dependency entirely — screenshots are free, fast, and reproducible
- Detached process groups in capture-screenshots.ts ensured reliable cleanup of spawned servers
- Signal protocol (SERVER_READY/SERVER_STOPPED) made server lifecycle scripts composable
- Phase 24 (documentation integration) was pure Markdown edits — completed in ~3 minutes

### What Was Inefficient
- Summary one-liner extraction still returned null — field format inconsistency across summaries
- Phase 22/23 progress table rows in ROADMAP.md had column alignment issues (milestone column missing)

### Patterns Established
- Screenshot naming convention: `{example}-{type}.png` (type: graph, dsl, inspector)
- Mock server pattern: Node built-in http module with fixture JSON files, matching production API contract
- Server lifecycle pattern: spawn → health-check poll → ready signal → work → stop signal
- Separate tsconfig.scripts.json for Node script execution (moduleResolution: node vs bundler)

### Key Lessons
1. Pinning exact versions (no caret) for tools with binary downloads prevents CI/CD surprises
2. Process group cleanup (negative PID) is essential when spawning child processes that spawn grandchildren (npx → vite)
3. Mock servers matching production API contracts enable offline testing without any infrastructure cost

---

## Milestone: v1.5 — PyPI Packaging & Distribution

**Shipped:** 2026-02-28
**Phases:** 3 | **Plans:** 3

### What Was Built
- Installable Python package via `pip install rsf` with bundled React UI static assets
- hatch-vcs git-tag versioning (v1.5.0 tag → 1.5.0 version, dev versions for untagged commits)
- GitHub Actions CI workflow: ruff lint + pytest matrix (Python 3.12, 3.13) on PRs and pushes to main
- GitHub Actions release workflow: React UI compile + wheel build + PyPI publish on v* tag push
- OIDC trusted publisher for zero-secret PyPI publishing
- Polished README landing page with three status badges, condensed quick-start, and hero screenshots

### What Worked
- Phase 25 (Package & Version) was completed as a direct implementation commit before GSD planning — simple enough for direct work
- Two-workflow architecture (ci.yml vs release.yml) cleanly separates concerns and permission scopes
- OIDC trusted publisher eliminates all secret management for PyPI — no API tokens to rotate or store
- `twine check` as a verification step caught rendering issues before PyPI upload
- Absolute URLs for all README images/links ensured PyPI compatibility from the start

### What Was Inefficient
- Phase 25 done outside GSD left no SUMMARY.md — milestone completion had to handle missing artifacts
- summary-extract one_liner field still returns null — this has been a recurring issue across v1.3, v1.4, and v1.5
- Research agent hallucinated actions/checkout@v6 version — plan checker flagged but deferred (research was self-consistent)

### Patterns Established
- PyPI OIDC trusted publisher pattern: `id-token: write` scoped to publish job only, `pypi` environment configured
- Two-job release workflow: build job (checkout + React + wheel) → publish job (download artifact + publish)
- Badge row pattern: shields.io for PyPI version + GitHub native for CI + shields.io static for license
- `raw.githubusercontent.com` absolute URLs for README images (PyPI requirement)

### Key Lessons
1. Simple packaging phases may be faster as direct implementation than GSD planning/research/execution
2. PyPI does not resolve relative paths — all images and links in README must use absolute URLs
3. `fetch-depth: 0` is mandatory when using hatch-vcs in CI — shallow checkout produces wrong versions
4. OIDC trusted publisher must be configured on PyPI.org before the first tag push (manual one-time step)

---

## Milestone: v2.0 — Comprehensive Enhancement Suite

**Shipped:** 2026-03-02
**Phases:** 12 | **Plans:** 34 | **Tasks:** 99

### What Was Built
- 7 DSL extensions (triggers, sub-workflows, DynamoDB, alarms, DLQ, timeout, multi-stage deploy)
- 9 new CLI commands (diff, test, watch, logs, doctor, export, cost, init --template, schema export)
- OpenTelemetry tracing injection in generated orchestrator code
- Property-based, chaos injection, and snapshot testing utilities
- Inspector execution replay with editable input
- VS Code extension with LSP, go-to-definition, and inline graph preview
- Reusable GitHub Action for CI/CD with PR comment plans
- SchemaStore catalog entry for automatic IDE auto-complete

### What Worked
- Wave-based parallel execution of independent plans reduced wall-clock time
- Milestone audit before completion caught 2 integration gaps and documentation holes — Phases 49 and 50 fixed them systematically
- Gap closure phases (49, 50) as a pattern: audit identifies issues, new phases close them before shipping
- Balanced model profile (sonnet for research/checking, inherit for planning/execution) kept costs reasonable
- Auto-advance (`--auto`) pipeline eliminated manual routing between plan, execute, and verify stages

### What Was Inefficient
- Earlier phases (39-42) shipped without VERIFICATION.md or SUMMARY frontmatter, requiring Phase 49 to backfill documentation
- Audit found 6 "unsatisfied" requirements that were actually implemented but had unchecked boxes — documentation discipline should be enforced during execution, not retrofitted
- Some phases had stale plan counts in ROADMAP.md (e.g., "0/TBD" for completed phases)

### Patterns Established
- Milestone audit, gap closure phases, re-verification is now the standard pre-ship workflow
- ChaosFixture wrapper pattern: inject failures inside retry/catch logic rather than bypassing it
- PRD-to-CONTEXT.md express path for well-defined gap closure phases

### Key Lessons
1. Documentation gates (VERIFICATION.md, SUMMARY frontmatter, REQUIREMENTS.md checkboxes) should be enforced by the executor, not deferred to a remediation phase
2. Integration testing across phase boundaries catches issues that per-phase verification misses — milestone audit is essential
3. Small surgical phases (50: 2 plans, 4 tasks) are highly effective for targeted fixes

### Cost Observations
- Model mix: ~30% opus (orchestration), ~60% sonnet (research, checking, execution), ~10% haiku (none used)
- Sessions: ~6 sessions across 2 days
- Notable: Auto-advance pipeline eliminated manual routing overhead

---

## Milestone: v3.0 — Pluggable Infrastructure Providers

**Shipped:** 2026-03-03
**Phases:** 5 | **Plans:** 17

### What Was Built
- InfrastructureProvider ABC with 5 abstract methods, ProviderContext, PrerequisiteCheck, and dict-dispatch registry
- WorkflowMetadata dataclass + 3 metadata transports (JSON file, env vars, CLI arg templates)
- TerraformProvider wrapping existing generator with full backward compatibility
- deploy_cmd refactored from ~80 LOC inline extraction to provider interface routing
- CDKProvider with Jinja2-generated CDK apps, bootstrap detection, and `npx aws-cdk@latest` invocation
- CustomProvider with security-hardened subprocess (`shell=False`, absolute path validation)
- Provider configuration via workflow YAML `infrastructure:` block and project-wide `rsf.toml`
- Provider-aware CLI: doctor/diff/watch/export handle any provider gracefully

### What Worked
- ABC + registry pattern cleanly separated interface from implementation — adding CDK and custom providers was straightforward once Phase 51 shipped
- Phase dependency chain (51 → 52 → 53/54 → 55) was correct — no circular dependencies or integration surprises
- `npx aws-cdk@latest` approach eliminated the need for users to manage CDK global install
- Security hardening (shell=False, absolute paths) was easy to test with subprocess mock fixtures
- Config cascade (YAML > rsf.toml > default "terraform") provided zero-config backward compat while enabling per-workflow overrides

### What Was Inefficient
- 17 of 29 requirements in REQUIREMENTS.md were never checked off during phases 51-52 — same documentation discipline issue as v2.0
- summary-extract one_liner field still returns null — recurring across all milestones, field format is not populated
- No milestone audit was performed before completion — audit recommended but skipped

### Patterns Established
- Provider pattern: ABC defines contract, each provider implements 5 methods (generate, deploy, teardown, check_prerequisites, validate_config)
- Metadata transport pattern: separate transport classes (File, Env, Args) for delivering structured data to external programs
- Config cascade pattern: workflow YAML > project config file > hardcoded default
- CLI graceful degradation pattern: detect active provider before executing provider-specific logic

### Key Lessons
1. Provider abstraction over infrastructure tools enables polyglot extensibility — custom provider + metadata transports let users use any language/tool
2. `shell=False` should be the default for all subprocess calls — explicit about what's being executed
3. Config cascade with explicit precedence (workflow > project > default) is the right pattern for tool configuration
4. Requirements checkbox discipline remains an issue — should be part of the executor's commit protocol, not a manual step

### Cost Observations
- Model mix: ~30% opus (orchestration), ~60% sonnet (research, checking, execution), ~10% haiku
- Sessions: ~4 sessions across 2 days
- Notable: 5-phase milestone completed quickly due to clear dependency chain and well-scoped phases

---

## Milestone: v3.2 — Terraform Registry Modules Tutorial

**Shipped:** 2026-03-06
**Phases:** 5 | **Plans:** 9

### What Was Built
- Schema verification of terraform-aws-modules/lambda v8.7.0 durable_config variables, alias convention, and IAM approach
- Working registry-modules-demo example deploying Lambda Durable Functions via custom provider with deploy.sh
- Full-stack Terraform registry modules: DynamoDB (for_each), SQS DLQ (conditional count), CloudWatch alarms, SNS
- 8 local unit tests + real-AWS integration test with durable execution polling and teardown verification
- 861-line tutorial with side-by-side HCL comparison, WorkflowMetadata schema table, and 5 common pitfalls
- 6 quick tasks: MIT license, test fixes, release tags (v3.1-v3.5), example fixes, pyproject.toml license update

### What Worked
- Schema verification phase (56) as prerequisite prevented downstream Terraform errors — durable_config variable names, alias convention, IAM approach all confirmed before writing code
- Custom provider deploy.sh reading RSF_METADATA_FILE via jq worked reliably — metadata transport system proved its value
- Quick tasks for operational work (release tags, test fixes) kept milestone phases focused on feature delivery
- Conditional Terraform resources (count on DLQ, for_each on DynamoDB, alarm_by_type map) kept module composition clean

### What Was Inefficient
- No milestone audit performed before completion — requirements all checked off but no formal cross-phase integration verification
- summary-extract one_liner field still returns null — recurring issue across all milestones
- Phase dates in ROADMAP.md compressed (all showing 2026-03-04/05) — actual work spanned 3 days but timestamps don't reflect session boundaries

### Patterns Established
- Custom provider deploy.sh pattern: bash script reading RSF_METADATA_FILE, generating terraform.tfvars.json via jq, invoking terraform
- Registry module conditional creation: count + conditional wiring for optional resources (DLQ, alarms)
- generate_tfvars() before both deploy AND destroy — Terraform needs vars even during destruction
- Side-by-side HCL comparison in tutorials: raw vs registry module code for the same resource

### Key Lessons
1. Registry modules add value for standardization but introduce indirection — tutorial must explain what the module does behind the scenes
2. deploy.sh tfvars.json generation is the critical translation layer between RSF metadata and Terraform variables
3. Pitfall documentation (Problem/Symptom/Fix format) is more useful than "best practices" lists
4. Quick tasks are effective for operational work (releases, fixes) that shouldn't block milestone phases

### Cost Observations
- Model mix: ~30% opus (orchestration), ~60% sonnet (research, checking, execution)
- Sessions: ~3 sessions across 3 days
- Notable: Smallest milestone yet (5 phases, 9 plans) — well-scoped tutorial milestones execute quickly

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 Core | 10 | 39 | Initial build — DSL, codegen, UI, testing, docs |
| v1.1 CLI | 1 | 4 | CLI toolchain unifying all commands |
| v1.2 Examples | 5 | 10 | Real AWS verification with automated testing |
| v1.3 Tutorial | 3 | 8 | 8 tutorials covering all CLI commands |
| v1.4 Screenshots | 4 | 5 | 15 automated screenshots in docs |
| v1.5 PyPI Packaging | 3 | 3 | pip install + CI/CD + README landing page |
| v1.6 Ruff Linting | 8 | 3 | Zero ruff violations, unified test suite |
| v1.7 Lambda URL | 3 | 8 | Lambda Function URL DSL + Terraform + example |
| v2.0 Enhancement Suite | 12 | 34 | Milestone audit + gap closure; auto-advance pipeline |
| v3.0 Pluggable Providers | 5 | 17 | Provider abstraction; config cascade; graceful CLI degradation |
| v3.2 Registry Modules Tutorial | 5 | 9 | Custom provider tutorial; registry module patterns; quick tasks for ops |

### Cumulative Quality

| Milestone | Tests Added | Key Metric |
|-----------|-------------|------------|
| v1.0 | Full unit + integration suite | DSL feature parity |
| v1.1 | 49 CLI tests | 7 subcommands |
| v1.2 | 152 local + 13 integration + 20 harness | All 8 state types on real AWS |
| v1.3 | 2,753 lines of tutorials | All 7 CLI commands documented |
| v1.4 | 15 screenshots + 18 image refs | All 5 examples with UI visuals |
| v1.5 | CI lint + test matrix | pip installable + PyPI publishing |
| v1.6 | 744 tests unified | Zero ruff suppressions |
| v1.7 | 779 tests (+35) | Lambda Function URL end-to-end |
| v2.0 | 976+ tests (+197) | 25/25 requirements verified via audit |
| v3.0 | ~1,100+ tests | 29/29 provider requirements delivered |
| v3.2 | 8 local + integration | 21/21 registry module requirements; 7 examples all passing |

### Top Lessons (Verified Across Milestones)

1. Use-case-driven examples are more effective than synthetic test cases for feature coverage
2. Explicit cleanup (delete_log_group) is needed beyond terraform destroy for AWS resources
3. Propagation delays in AWS services (IAM, CloudWatch) require explicit wait buffers in automated tests
4. Tutorials using actual CLI output (not idealized) build user trust and match reality
5. Mock servers matching production API contracts enable offline tooling without infrastructure cost
6. PyPI requires absolute URLs for all README images/links — relative paths break on the project page
7. OIDC trusted publisher eliminates secret management entirely for PyPI publishing
8. Milestone audit + gap closure phases before shipping catches cross-phase integration issues that per-phase testing misses
9. Documentation gates should be enforced during execution, not deferred to remediation phases
10. Provider abstraction (ABC + registry + config cascade) cleanly separates interface from implementation and enables polyglot extensibility
