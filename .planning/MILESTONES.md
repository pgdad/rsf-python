# Milestones

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

