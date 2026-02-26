# Roadmap: RSF — Replacement for Step Functions

## Milestones

- ✅ **v1.0 Core** — Phases 1-11 (shipped 2026-02-25)
- ✅ **v1.1 CLI Toolchain** — Phase 12 (shipped 2026-02-26)
- ✅ **v1.2 Comprehensive Examples & Integration Testing** — Phases 13-17 (shipped 2026-02-26)

## Phases

<details>
<summary>✅ v1.0 Core (Phases 1-11) — SHIPPED 2026-02-25</summary>

- [x] Phase 1: DSL Core (5/5 plans) — completed 2026-02-25
- [x] Phase 2: Code Generation (3/3 plans) — completed 2026-02-25
- [x] Phase 3: Terraform Generation (2/2 plans) — completed 2026-02-25
- [x] Phase 4: ASL Importer (2/2 plans) — completed 2026-02-25
- [x] Phase 6: Graph Editor Backend (2/2 plans) — completed 2026-02-25
- [x] Phase 7: Graph Editor UI (5/5 plans) — completed 2026-02-25
- [x] Phase 8: Inspector Backend (2/2 plans) — completed 2026-02-25
- [x] Phase 9: Inspector UI (5/5 plans) — completed 2026-02-25
- [x] Phase 10: Testing (9/9 plans) — completed 2026-02-25
- [x] Phase 11: Documentation (4/4 plans) — completed 2026-02-25

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 CLI Toolchain (Phase 12) — SHIPPED 2026-02-26</summary>

- [x] Phase 12: CLI Toolchain (4/4 plans) — completed 2026-02-26

Full details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

### ✅ v1.2 Comprehensive Examples & Integration Testing (Shipped 2026-02-26)

**Milestone Goal:** Prove RSF works end-to-end against real AWS by delivering 5 real-world example workflows with automated deploy-invoke-verify-teardown testing.

- [x] **Phase 13: Example Foundation** — Five complete examples: DSL YAML, handler code, and local mock SDK tests for all examples
- [x] **Phase 14: Terraform Infrastructure** — Per-example Terraform files with isolated local state, durable_config, and DynamoDB resources
- [x] **Phase 15: Integration Test Harness** — Shared polling, log query, teardown helpers and single-command test runner
- [x] **Phase 16: AWS Deployment and Verification** — All 5 examples deployed, invoked, and verified via dual-channel assertions on real AWS
- [x] **Phase 17: Cleanup and Documentation** — End-to-end teardown validated, example READMEs and top-level quick-start guide written

## Phase Details

### Phase 13: Example Foundation
**Goal**: All five example workflows are locally runnable — DSL YAML authored, handler code implemented with structured logging, and local mock SDK tests passing without AWS credentials
**Depends on**: Phase 12 (CLI toolchain)
**Requirements**: EXAM-01, EXAM-02, EXAM-03, EXAM-04, EXAM-05, EXAM-07, EXAM-08
**Success Criteria** (what must be TRUE):
  1. User can run `pytest examples/<name>/tests/test_local.py` for each of the 5 examples and all tests pass without AWS credentials
  2. All 8 state types (Task, Choice, Parallel, Map, Pass, Wait, Succeed, Fail) appear in at least one example's DSL YAML
  3. Each example's handler file emits structured JSON logs (via aws-lambda-powertools Logger) with step name and execution context fields
  4. The intrinsic-showcase example exercises 14+ intrinsic functions and all 5 I/O pipeline fields (InputPath, Parameters, ResultSelector, ResultPath, OutputPath) in its DSL
  5. The approval-workflow example uses Context Object ($$) references and Variables/Assign in its DSL YAML
**Plans**: 5 examples (order-processing, data-pipeline, approval-workflow, retry-and-recovery, intrinsic-showcase) — completed 2026-02-26

### Phase 14: Terraform Infrastructure
**Goal**: Every example has a generated Terraform directory with isolated local state, durable_config with retention_period=1, correct runtime, pinned AWS provider, and DynamoDB resources where needed — and `terraform plan` succeeds for all examples
**Depends on**: Phase 13
**Requirements**: EXAM-06, HARN-05
**Success Criteria** (what must be TRUE):
  1. Running `terraform plan` inside each example's `terraform/` directory succeeds with no errors
  2. Each example has its own `terraform.tfstate` file — no shared state file exists across examples
  3. Every Lambda resource in every example's `main.tf` includes a `durable_config` block with `retention_period = 1` and `runtime = "python3.13"`
  4. The data-pipeline and order-processing examples include DynamoDB table resources and IAM policies granting the Lambda the required DynamoDB actions
**Plans**: 1 plan (terraform infrastructure for all 5 examples) — completed 2026-02-26

### Phase 15: Integration Test Harness
**Goal**: The shared test infrastructure is built and independently validated — polling helper, log query helper, teardown helper, UUID execution IDs, IAM propagation buffer, and single-command test runner all exist in conftest.py and pass verification
**Depends on**: Phase 14
**Requirements**: HARN-01, HARN-02, HARN-03, HARN-04, HARN-06, HARN-07
**Success Criteria** (what must be TRUE):
  1. User can call `poll_execution()` from conftest.py and it waits for durable execution completion with 3-5s polling interval and exponential backoff on ThrottlingException, returning when any of the 4 terminal states (SUCCEEDED, FAILED, TIMED_OUT, STOPPED) is reached
  2. User can call `query_logs()` from conftest.py and it applies a 15-second propagation buffer before querying CloudWatch Logs Insights, retrying until results are non-empty
  3. User can call the teardown fixture and it runs `terraform destroy` followed by explicit `boto3 logs.delete_log_group()` — leaving no orphaned log groups after execution
  4. Every test invocation uses a UUID-suffixed execution ID (format: `test-<name>-<timestamp>-<uuid8>`) so parallel or sequential re-runs never collide
  5. User can run `pytest tests/test_examples/ -m integration` as a single command that executes the full integration suite
**Plans**: 1 plan (shared harness + test directory structure + 20 unit tests) — completed 2026-02-26

### Phase 16: AWS Deployment and Verification
**Goal**: All 5 examples deploy to real AWS, execute successfully, and pass dual-channel assertions — Lambda return value verification and CloudWatch log intermediate-state verification
**Depends on**: Phase 15
**Requirements**: VERF-01, VERF-02, VERF-03
**Success Criteria** (what must be TRUE):
  1. Each of the 5 examples reaches SUCCEEDED terminal state in real AWS execution as confirmed by `GetDurableExecution` return value assertion
  2. Each of the 5 examples has at least one CloudWatch log assertion confirming intermediate state transitions match expected handler execution sequence
  3. All 8 state types are observed in real AWS execution across the combined example set (confirmed by log and return value evidence in test output)
  4. The data-pipeline example performs real DynamoDB reads and writes during execution and the test verifies the expected items exist in the table after the workflow completes
**Plans**: 1 plan (5 integration test files with dual-channel assertions) — completed 2026-02-26

### Phase 17: Cleanup and Documentation
**Goal**: A developer with no prior context can clone the repo, run one command to execute the full integration suite, and have zero AWS resources remaining afterward — and each example has a README explaining what it demonstrates
**Depends on**: Phase 16
**Requirements**: DOCS-01, DOCS-02
**Success Criteria** (what must be TRUE):
  1. Each example directory contains a README that names which DSL features it demonstrates and provides the exact command to run it standalone
  2. The top-level `examples/README.md` lists all prerequisites (AWS credentials, Terraform binary, Python 3.13+, boto3>=1.42.0) and a quick-start command sequence a developer can follow without reading any other file
  3. After a full integration test run completes (pass or fail), no Lambda functions, CloudWatch log groups, DynamoDB tables, or IAM roles from the test suite remain in the AWS account
**Plans**: 1 plan (5 example READMEs + top-level quick-start guide) — completed 2026-02-26

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. DSL Core | v1.0 | 5/5 | Complete | 2026-02-25 |
| 2. Code Generation | v1.0 | 3/3 | Complete | 2026-02-25 |
| 3. Terraform Generation | v1.0 | 2/2 | Complete | 2026-02-25 |
| 4. ASL Importer | v1.0 | 2/2 | Complete | 2026-02-25 |
| 6. Graph Editor Backend | v1.0 | 2/2 | Complete | 2026-02-25 |
| 7. Graph Editor UI | v1.0 | 5/5 | Complete | 2026-02-25 |
| 8. Inspector Backend | v1.0 | 2/2 | Complete | 2026-02-25 |
| 9. Inspector UI | v1.0 | 5/5 | Complete | 2026-02-25 |
| 10. Testing | v1.0 | 9/9 | Complete | 2026-02-25 |
| 11. Documentation | v1.0 | 4/4 | Complete | 2026-02-25 |
| 12. CLI Toolchain | v1.1 | 4/4 | Complete | 2026-02-26 |
| 13. Example Foundation | v1.2 | 5/5 | Complete | 2026-02-26 |
| 14. Terraform Infrastructure | v1.2 | 1/1 | Complete | 2026-02-26 |
| 15. Integration Test Harness | v1.2 | 1/1 | Complete | 2026-02-26 |
| 16. AWS Deployment and Verification | v1.2 | 1/1 | Complete | 2026-02-26 |
| 17. Cleanup and Documentation | v1.2 | 1/1 | Complete | 2026-02-26 |
