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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 Core | 10 | 39 | Initial build — DSL, codegen, UI, testing, docs |
| v1.1 CLI | 1 | 4 | CLI toolchain unifying all commands |
| v1.2 Examples | 5 | 10 | Real AWS verification with automated testing |

### Cumulative Quality

| Milestone | Tests Added | Key Metric |
|-----------|-------------|------------|
| v1.0 | Full unit + integration suite | DSL feature parity |
| v1.1 | 49 CLI tests | 7 subcommands |
| v1.2 | 152 local + 13 integration + 20 harness | All 8 state types on real AWS |

### Top Lessons (Verified Across Milestones)

1. Use-case-driven examples are more effective than synthetic test cases for feature coverage
2. Explicit cleanup (delete_log_group) is needed beyond terraform destroy for AWS resources
3. Propagation delays in AWS services (IAM, CloudWatch) require explicit wait buffers in automated tests
