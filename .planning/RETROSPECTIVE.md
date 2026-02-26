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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 Core | 10 | 39 | Initial build — DSL, codegen, UI, testing, docs |
| v1.1 CLI | 1 | 4 | CLI toolchain unifying all commands |
| v1.2 Examples | 5 | 10 | Real AWS verification with automated testing |
| v1.3 Tutorial | 3 | 8 | 8 tutorials covering all CLI commands |

### Cumulative Quality

| Milestone | Tests Added | Key Metric |
|-----------|-------------|------------|
| v1.0 | Full unit + integration suite | DSL feature parity |
| v1.1 | 49 CLI tests | 7 subcommands |
| v1.2 | 152 local + 13 integration + 20 harness | All 8 state types on real AWS |
| v1.3 | 2,753 lines of tutorials | All 7 CLI commands documented |

### Top Lessons (Verified Across Milestones)

1. Use-case-driven examples are more effective than synthetic test cases for feature coverage
2. Explicit cleanup (delete_log_group) is needed beyond terraform destroy for AWS resources
3. Propagation delays in AWS services (IAM, CloudWatch) require explicit wait buffers in automated tests
4. Tutorials using actual CLI output (not idealized) build user trust and match reality
