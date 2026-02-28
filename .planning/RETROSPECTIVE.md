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

### Cumulative Quality

| Milestone | Tests Added | Key Metric |
|-----------|-------------|------------|
| v1.0 | Full unit + integration suite | DSL feature parity |
| v1.1 | 49 CLI tests | 7 subcommands |
| v1.2 | 152 local + 13 integration + 20 harness | All 8 state types on real AWS |
| v1.3 | 2,753 lines of tutorials | All 7 CLI commands documented |
| v1.4 | 15 screenshots + 18 image refs | All 5 examples with UI visuals |
| v1.5 | CI lint + test matrix | pip installable + PyPI publishing |

### Top Lessons (Verified Across Milestones)

1. Use-case-driven examples are more effective than synthetic test cases for feature coverage
2. Explicit cleanup (delete_log_group) is needed beyond terraform destroy for AWS resources
3. Propagation delays in AWS services (IAM, CloudWatch) require explicit wait buffers in automated tests
4. Tutorials using actual CLI output (not idealized) build user trust and match reality
5. Mock servers matching production API contracts enable offline tooling without infrastructure cost
6. PyPI requires absolute URLs for all README images/links — relative paths break on the project page
7. OIDC trusted publisher eliminates secret management entirely for PyPI publishing
