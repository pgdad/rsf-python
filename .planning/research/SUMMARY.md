# Project Research Summary

**Project:** RSF v1.2 — Comprehensive Examples and Integration Testing
**Domain:** Automated AWS integration testing for Lambda Durable Functions workflows
**Researched:** 2026-02-26
**Confidence:** HIGH

## Executive Summary

RSF v1.2 is a mature second milestone built on top of a complete v1.1 CLI toolchain. The goal is to prove the framework works end-to-end against real AWS by building a library of 5 real-world use-case example workflows and an automated test harness that deploys, invokes, verifies, and tears down each example. The research is unusually high-confidence because the existing codebase was inspected directly, all relevant AWS APIs (Lambda Durable Functions, CloudWatch Logs Insights) are documented at official sources, and the library versions were verified against PyPI as of the research date. The recommended approach: author examples as self-contained RSF projects, generate and deploy each independently via Terraform with local state, invoke asynchronously via `InvocationType=Event`, and verify workflow correctness through two independent channels — the Lambda return value (via `GetDurableExecution`) and intermediate state via structured CloudWatch log queries.

The core complexity of this milestone is not in the application logic but in the test harness plumbing. Lambda Durable Functions are a re:Invent 2025 feature; many common testing patterns from standard Lambda do not apply. Synchronous invocation (`RequestResponse`) does not work. Mocking tools (moto, LocalStack) do not support the durable execution checkpoint/replay mechanism. Log verification requires accounting for 5-30 second propagation delays. IAM policies require a 15-second propagation window after `terraform apply` before the first invocation. Each of these is a well-documented pitfall that, if not addressed in the test harness design upfront, will cause flaky CI and false-positive tests. The research identified 10 critical pitfalls — all preventable by building the polling helper, log query helper, and teardown helper correctly the first time.

The recommended stack is minimal: the existing `boto3`, `pytest`, `subprocess`, and Terraform binary cover 90% of the harness. The only net-new dependencies are `aws-lambda-powertools>=3.24.0` (structured JSON logging in example handlers) and `pytest-timeout>=2.4.0` (prevents CI hangs on network-bound tests). The milestone does not require modifying any existing `src/rsf/` source code — all new components live in `examples/`, `tests/test_examples/`, and `scripts/`.

## Key Findings

### Recommended Stack

The existing RSF stack already provides everything needed for the test harness infrastructure: `boto3>=1.28` for AWS API calls, `pytest>=7.0` for test organization, and `subprocess.run` for Terraform lifecycle management. The version floor for `boto3` must be bumped to `>=1.42.0` to guarantee access to `ListDurableExecutionsByFunction` and `GetDurableExecution` APIs added after re:Invent 2025. Two new additions are needed: `aws-lambda-powertools>=3.24.0` installs into each Lambda deployment package to emit structured JSON logs that CloudWatch Logs Insights can query by key, and `pytest-timeout>=2.4.0` provides per-test and global timeout enforcement that works at the process level and can interrupt hanging Terraform or boto3 network calls. The `pytest-asyncio` floor is bumped to `>=1.3.0` for `asyncio_mode = "auto"` stability, but the integration test polling loops should remain synchronous (`time.sleep`) — there is no benefit to async when calling synchronous boto3 APIs.

**Core technologies:**
- `boto3>=1.42.0`: Lambda and CloudWatch Logs API access — the only client library needed for the test harness; polling helpers use `list_durable_executions_by_function`, `get_durable_execution`, and `logs.start_query` / `logs.get_query_results`
- `aws-lambda-powertools>=3.24.0`: Structured JSON logging in example Lambda handlers — auto-injects Lambda context fields; produces JSON directly queryable by CloudWatch Logs Insights without custom parsing
- `pytest-timeout>=2.4.0`: Per-test and global timeout for integration tests — works at process level, catches hanging subprocess (terraform) and network calls that `asyncio.wait_for` cannot reach
- `terraform` binary (existing): Invoked via `subprocess.run` using the identical pattern established by `rsf deploy` — no Python wrapper library needed or recommended
- `subprocess.run` (existing): Terraform init, apply, output, destroy — the pattern already in `deploy_cmd.py` is correct and sufficient

**Critical version requirements:**
- `boto3>=1.42.0` — `ListDurableExecutionsByFunction` and `GetDurableExecution` require a post-re:Invent 2025 build
- `pytest-asyncio>=1.3.0` — v1.x changed `asyncio_mode` default; add `asyncio_mode = "auto"` to `pyproject.toml`
- AWS Terraform provider `>=6.25.0` — required for `durable_config` block support in `aws_lambda_function`
- Python 3.13+ runtime in Lambda — only supported runtime for Lambda Durable Functions

### Expected Features

5 real-world use-case examples must be delivered: `order-processing` (Task, Choice, Parallel, Succeed, Fail with Retry/Catch and DynamoDB), `data-pipeline` (Task, Pass, Map with DynamoDB service integration), `approval-workflow` (Task, Wait, Choice, Pass with Context Object `$$` coverage), `retry-and-recovery` (Task, Choice, Pass with multi-Catch and JitterStrategy), and `intrinsic-showcase` (Pass, Task — exercises 14 of 18 intrinsic functions and all 5 I/O pipeline fields). These 5 examples together cover all 8 state types, all 6 comparison operator families, ~14 intrinsic functions in real execution (remaining 4 are covered by v1.0 unit tests), the complete I/O pipeline, Variables/Assign/Output, and the Context Object. The test harness must execute each example end-to-end with a single command: `pytest tests/test_examples/ -m integration`.

**Must have (table stakes):**
- 5 complete example workflows with DSL YAML + real handler code + Terraform files — without all three an example cannot be deployed
- Coverage of all 8 state types across the example set — the DSL supports all 8; any gap signals an untested code path
- Error handling coverage (Retry with BackoffRate/JitterStrategy + multi-Catch) — most-used production feature; must fire real exceptions
- I/O processing pipeline coverage (InputPath, Parameters, ResultSelector, ResultPath, OutputPath) — non-trivial generated code; must be verified via real execution
- Automated deploy-invoke-verify-teardown cycle — core value proposition of the milestone; manual steps disqualify it
- Dual verification per example: Lambda return value assertion AND CloudWatch log assertion — return value proves output; logs prove intermediate state
- Single-command test runner: `pytest tests/test_examples/ -m integration`
- Real AWS execution with real teardown — local mock tests already exist; v1.2 is the real-AWS tier
- Structured JSON logging in all handler files — required for reliable log assertions; unstructured logs are unparseable

**Should have (differentiators):**
- Real-world scenario naming (order-processing, data-pipeline) over abstract names — readers understand why each state type exists
- DynamoDB integration in one example — proves RSF works with real stateful AWS services inside handlers
- Context Object (`$$`) coverage in deployed execution — real execution provides real `$$.Execution.Id` values that expose bugs mocks cannot
- Variables/Assign/Output coverage in a deployed workflow — Assign generates Python dict mutation; real execution verifies the generated code path

**Defer to v1.2.x or v2+:**
- CI/CD GitHub Actions workflow — add after examples are stable and cost is understood
- Second AWS service example (SQS/S3) — add after DynamoDB example is validated
- LocalStack support — defer until LocalStack confirms durable execution compatibility
- Parallel CI execution of integration tests — defer until per-example cost and timing is understood

### Architecture Approach

The architecture is additive: zero changes to the existing `src/rsf/` source tree. New components live exclusively in `examples/`, `tests/test_examples/`, and `scripts/`. Each example is a self-contained RSF project — a complete `workflow.yaml`, `handlers/`, `src/` layout (for Lambda packaging), `terraform/` (generated by `rsf deploy` with local state), and `tests/test_local.py` (mock SDK). This mirrors exactly what a user would create with `rsf init`, so examples serve as both test fixtures and documentation. The AWS integration tests live in the project-level `tests/test_examples/` and share a `conftest.py` with polling helpers, log query helpers, and boto3 fixtures. A `scripts/run_integration_tests.sh` shell script manages the deploy-test-teardown lifecycle and CI invocation. Terraform state is per-example and local (no S3 backend), which prevents cross-example state collisions and avoids the need for shared infrastructure to run the test suite.

**Major components:**
1. `examples/<name>/` — Self-contained RSF project per example; contains DSL YAML, handler implementations with structured logging, Terraform files with local state, and a local mock test
2. `tests/test_examples/conftest.py` — Shared AWS test infrastructure: `poll_execution()` helper with 3-5s interval and exponential backoff on 429, `query_logs()` helper with 15s propagation buffer and retry loop, `get_tf_outputs()` helper reading resource names from `terraform output -json`, invocation helper generating UUID-suffixed execution IDs
3. `tests/test_examples/test_<name>.py` — Per-example pytest files with dual-channel verification (return value + logs)
4. `scripts/run_integration_tests.sh` — Lifecycle orchestration: per-example `terraform apply`, pytest, `terraform destroy`, followed by explicit `delete_log_group()` boto3 cleanup

### Critical Pitfalls

1. **No polling after async invocation** — `InvocationType=Event` returns HTTP 202 with an empty body. Tests that read the invoke response directly get false positives. Build the polling helper first and validate it before writing any example tests. Poll for all four terminal states: SUCCEEDED, FAILED, TIMED_OUT, STOPPED.

2. **CloudWatch log propagation delay** — Logs are not queryable for 5-30 seconds after execution completes. Tests that call `filter_log_events` or `get_query_results` immediately after SUCCEEDED detection return empty results and fail intermittently. Always assert the Lambda return value first (available immediately on SUCCEEDED), then wait a fixed 15-second propagation buffer before querying logs.

3. **IAM propagation race after `terraform apply`** — IAM policies take up to 15 seconds to propagate globally after `terraform apply` returns. Invoking the Lambda immediately produces `AccessDeniedException` in the first execution. Always add a 15-second sleep (or retry on AccessDeniedException) between `terraform apply` and the first test invocation.

4. **Shared Terraform state across examples** — A single `terraform.tfstate` ties all examples together. One failed example blocks teardown of all others. Use per-example isolated local state: each example has its own `terraform/` directory with its own `terraform.tfstate`. Never run `terraform apply` from a shared root.

5. **Lambda control plane rate limit throttling** — The Lambda control plane enforces 15 req/s account-wide. Polling multiple concurrent examples at 1-second intervals hits this limit, causing 429 ThrottlingException that manifests as flaky failures. Set minimum polling interval to 3-5 seconds. Run examples sequentially. Add exponential backoff on `TooManyRequestsException`.

6. **Orphaned CloudWatch log groups blocking re-deploy** — Lambda auto-creates `/aws/lambda/<name>` log groups. `terraform destroy` may not remove them if Lambda flushed late buffers during teardown. `terraform apply` on the next run fails with `LogGroupAlreadyExistsException`. Follow every `terraform destroy` with explicit `boto3 logs.delete_log_group()` in the test harness teardown step.

7. **Checkpoint storage cost accumulation** — Each durable execution generates checkpoint data retained for the default 14-day period. Running the test suite daily accumulates 14x the data. Set `retention_period = 1` in `durable_config` for all test examples.

8. **Execution ID collisions** — Fixed execution names collide with prior runs within the retention window, producing `ResourceConflictException`. Always generate execution IDs with a timestamp + UUID suffix: `f"test-{example_name}-{int(time.time())}-{uuid4().hex[:8]}"`.

## Implications for Roadmap

Based on combined research, the build ordering is dictated by two rules:
- Local (mock SDK) tests must pass before any AWS deployment — local tests are the gate to the real-AWS tier
- Test harness helpers (polling, log query, teardown) must be built and validated before example-specific tests can use them

### Phase 1: Example Foundation — DSL, Handlers, Local Tests

**Rationale:** Examples must be authorable and locally testable before any AWS infrastructure is created. This phase has no AWS dependency and can be validated entirely with the existing `MockDurableContext`. It also forces all DSL authoring to be complete before Terraform files are generated, ensuring the generated code is stable. Starting here avoids the cost and latency of deploying broken examples.

**Delivers:** Complete `workflow.yaml` + handler implementations + `test_local.py` for each of the 5 examples. All local tests passing. DSL exercises all 8 state types, all 5 I/O pipeline fields, Variables/Assign, Context Object references, and error handling constructs.

**Addresses from FEATURES.md:** Complete example artifacts (DSL + handlers), all 8 state types, error handling, I/O pipeline, Variables/Assign, Context Object, structured JSON logging convention in handlers.

**Avoids from PITFALLS.md:** Generating handler stubs over user-authored handlers (keep `src/generated/` and `handlers/` directories separate from the start); `durable_config` missing from initial deploy (template structure decided here).

**Research flag:** Standard patterns — example DSL authoring uses the existing RSF DSL which is fully documented; no additional research needed.

---

### Phase 2: Terraform Infrastructure Per Example

**Rationale:** Once examples have valid DSL, `rsf deploy` can generate Terraform files. This phase establishes the per-example Terraform directory structure, configures `durable_config` with `retention_period = 1`, sets `runtime = python3.13`, pins the AWS provider to `>=6.25.0`, and adds DynamoDB IAM/resources for the `data-pipeline` example. This phase does not run `terraform apply` — it validates that `terraform plan` succeeds and that the state isolation structure is correct.

**Delivers:** Per-example `terraform/` directories with generated Terraform files. `durable_config` present in all examples from the first commit. `retention_period = 1` set in all examples. AWS provider version pinned. DynamoDB resources in `data-pipeline` and `order-processing`. `.gitignore` updated for `terraform.tfstate`, `src/generated/`, `.terraform/`.

**Addresses from FEATURES.md:** Per-example independent Terraform state, DynamoDB integration example, Terraform lifecycle automation.

**Avoids from PITFALLS.md:** Shared Terraform state collisions, `durable_config` missing on initial deploy (can never be added to an existing function — it must be present from v1), checkpoint storage accumulation (`retention_period = 1` from day one), orphaned log groups (Terraform `depends_on` for log group before Lambda creation).

**Research flag:** Standard patterns — RSF's existing Terraform generator and the `main.tf.j2` template are the source of truth; no additional research needed.

---

### Phase 3: Integration Test Harness Infrastructure

**Rationale:** The test harness shared helpers must exist and be independently validated before any example-specific tests are written. This is the highest-risk phase because the polling, log query, and teardown patterns are where most integration test pitfalls occur. Building and testing these helpers in isolation (against a single deployed example) validates the entire harness before the other four examples exercise it.

**Delivers:** `tests/test_examples/conftest.py` with: `poll_execution()` (3-5s interval, exponential backoff on 429, handles all 4 terminal states), `query_logs()` (15s propagation buffer, retry loop, `startTime` set to invocation timestamp), `get_tf_outputs()` (reads resource names from `terraform output -json`), invocation helper (UUID-suffixed execution IDs), IAM propagation buffer (15s sleep after apply). `scripts/run_integration_tests.sh` skeleton. `pyproject.toml` updated with `integration` extras group and `-m integration` marker.

**Addresses from FEATURES.md:** Automated deploy-invoke-verify-teardown cycle, single-command test runner, teardown on failure.

**Avoids from PITFALLS.md:** No polling after async invocation (polling helper is the entire purpose of this phase), rate limit throttling (3-5s minimum interval + backoff), CloudWatch propagation delay (15s buffer baked into log query helper), IAM propagation race (15s sleep in deploy-to-invoke sequence), execution ID collision (UUID-suffixed IDs in invocation helper), orphaned log groups (explicit `delete_log_group()` in teardown step).

**Research flag:** Needs research-phase attention — the `GetDurableExecution` result extraction API and the relationship between `ListDurableExecutionsByFunction` response fields are documented at MEDIUM confidence. Specifically: the FEATURES.md research flagged `GetDurableExecutionState` as an internal SDK API used for replay; the correct external API for result retrieval is `GetDurableExecution`. Validate the exact response shape and field names (`Result`, `Status`, `Error`) against the boto3 client before writing the polling helper.

---

### Phase 4: Example AWS Deployment and Test Verification

**Rationale:** With the harness in place, deploy each example to AWS in sequence and write the test assertions. The order of examples should match deployment complexity: start with `order-processing` (most representative, covers the most surface area), then `retry-and-recovery` (verifies error handling is wired correctly), then `intrinsic-showcase` (validates I/O pipeline and intrinsic function coverage), then `approval-workflow` (adds Context Object and Wait state), and finally `data-pipeline` (DynamoDB integration — most dependencies).

**Delivers:** `tests/test_examples/test_<name>.py` for all 5 examples, each with dual-channel verification (return value assertion + CloudWatch log assertion). All 5 examples passing `pytest tests/test_examples/ -m integration`. Example README files documenting what each example demonstrates.

**Addresses from FEATURES.md:** Dual verification (return value + CW logs), real AWS execution, coverage of all 8 state types, coverage of all 6 operator families, DynamoDB integration, Context Object, Variables/Assign.

**Avoids from PITFALLS.md:** Using CloudWatch Logs as the only verification channel (return value is always the primary assertion), Lambda cold start timing (polling timeout set to 120s minimum to accommodate cold starts; warm-up invocation added if needed), hardcoding Lambda function names in tests (all resource names read from `terraform output -json`).

**Research flag:** Standard patterns for the pure-Lambda examples. The DynamoDB integration example may benefit from a brief research-phase check on IAM policy specifics for the DynamoDB actions needed by the `data-pipeline` example.

---

### Phase 5: Cleanup and Documentation

**Rationale:** After all examples are verified, ensure the test suite is reproducible by a developer with no prior context. This means validating the single-command workflow (`pytest tests/test_examples/ -m integration`), confirming `terraform destroy` + `delete_log_group()` leaves no residual AWS resources, and documenting the prerequisite setup (AWS credentials, Terraform binary, boto3 version).

**Delivers:** `scripts/run_integration_tests.sh` fully wired, verified teardown leaves no orphaned resources, `examples/README.md` with quick-start instructions, pyproject.toml `integration` extras documented.

**Addresses from FEATURES.md:** Single-command test runner (validated end-to-end), teardown on failure (verified with forced failure scenario).

**Avoids from PITFALLS.md:** Using production AWS credentials (account ID assertion in test harness startup), checkpoint storage accumulation (verified `retention_period = 1` across all examples).

**Research flag:** Standard patterns — documentation and cleanup; no research needed.

---

### Phase Ordering Rationale

- **Local before cloud:** Examples must be locally testable before any AWS deployment. This prevents spending Terraform apply/destroy cycles on broken workflows.
- **Harness before tests:** The polling, log query, and teardown helpers are shared infrastructure. Building them first means every subsequent example test can immediately rely on correct, validated primitives.
- **Sequential AWS deployment:** Examples deploy and verify one at a time to stay well within the Lambda control plane 15 req/s rate limit and to isolate failures.
- **DynamoDB example last:** The `data-pipeline` example has the most AWS dependencies (DynamoDB table + IAM). It comes last so the simpler examples validate the harness first.

### Research Flags

Phases needing deeper research during planning:
- **Phase 3 (Test Harness):** Validate exact `GetDurableExecution` response schema — specifically `Result`, `Status`, and `Error` field names and the format of `Result` (JSON string vs. dict) before writing the polling helper. The FEATURES.md research flagged this at MEDIUM confidence because `GetDurableExecutionState` (an internal API) was confused with the external `GetDurableExecution` API. One boto3 test call against the actual API will resolve this definitively.
- **Phase 4, DynamoDB example:** Confirm minimum IAM actions required for the `data-pipeline` example — `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:Query` are expected, but verify against the specific table access patterns before generating the IAM policy.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Examples):** RSF DSL is the existing, fully-documented interface. Handler implementations use standard Python. No unknowns.
- **Phase 2 (Terraform):** RSF Terraform generator is the source of truth. All templates verified by direct codebase inspection.
- **Phase 5 (Cleanup):** Documentation and script wiring. No research needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All library versions verified against PyPI as of 2026-02-26; AWS API patterns verified against official docs; existing codebase inspected directly |
| Features | HIGH | AWS Lambda Durable Functions APIs confirmed in official docs; RSF source code inspected directly; one MEDIUM flag on `GetDurableExecutionState` (internal API) vs `GetDurableExecution` (public API) — see gaps |
| Architecture | HIGH | Based on direct inspection of existing `src/rsf/` source tree, Jinja2 templates, and existing test organization; zero inference required |
| Pitfalls | HIGH (core); MEDIUM (cost/billing) | Core pitfalls verified against official docs and confirmed GitHub issues; checkpoint storage cost structure verified at MEDIUM confidence via third-party analysis |

**Overall confidence:** HIGH

### Gaps to Address

- **`GetDurableExecution` response schema (MEDIUM confidence):** The FEATURES.md research references two distinct APIs — `GetDurableExecution` (public, for test result retrieval) and `GetDurableExecutionState` (internal SDK API, used for checkpoint replay). The exact shape of the `GetDurableExecution` response (specifically whether `Result` is a JSON string or a pre-parsed dict, and which fields are present for FAILED vs. SUCCEEDED) should be validated with a single boto3 test call before writing the polling helper. Resolve during Phase 3 planning.

- **`DurableFunctionCloudTestRunner` viability (MEDIUM confidence):** The FEATURES.md research mentions `aws-durable-execution-sdk-python-testing` which provides a `DurableFunctionCloudTestRunner` that wraps the poll-until-complete pattern. If this library is production-quality and on PyPI, adopting it could eliminate the custom polling helper entirely. Validate during Phase 3 planning by checking PyPI status and last release date. If it is as lightly maintained as `pytest-terraform` was (last release 2023), skip it and use the custom helper.

- **`$LATEST` vs. versioned ARN invocation for durable functions (LOW confidence):** The PITFALLS.md notes that `AllowInvokeLatest = true` is required (non-default) when invoking `$LATEST`. Verify whether the RSF-generated `iam.tf` includes this permission and whether the test harness should invoke `$LATEST` or a specific version. Resolve during Phase 2 Terraform structure review.

## Sources

### Primary (HIGH confidence)
- [boto3 1.42.57 on PyPI](https://pypi.org/project/boto3/) — current version, API availability for durable execution calls
- [ListDurableExecutionsByFunction API Reference](https://docs.aws.amazon.com/lambda/latest/api/API_ListDurableExecutionsByFunction.html) — request parameters, response fields, status values
- [GetDurableExecution API Reference](https://docs.aws.amazon.com/lambda/latest/api/API_GetDurableExecution.html) — result payload, error details, status enum
- [Invoking durable Lambda functions](https://docs.aws.amazon.com/lambda/latest/dg/durable-invocation.html) — InvocationType=Event requirement, async invocation pattern
- [AWS Lambda Durable Functions configuration](https://docs.aws.amazon.com/lambda/latest/dg/durable-configuration.html) — retention_period range, execution_timeout, AllowInvokeLatest
- [Deploy Lambda Durable Functions with IaC](https://docs.aws.amazon.com/lambda/latest/dg/durable-getting-started-iac.html) — durable_config block, AWS provider >=6.25.0 requirement
- [Monitoring durable functions](https://docs.aws.amazon.com/lambda/latest/dg/durable-monitoring.html) — CloudWatch metrics, execution ARN format, log group naming
- [aws-lambda-powertools 3.24.0 on PyPI](https://pypi.org/project/aws-lambda-powertools/) — version, Logger docs, JSON field list
- [pytest-timeout 2.4.0 on PyPI](https://pypi.org/project/pytest-timeout/) — version, per-test timeout mechanism
- [pytest-asyncio 1.3.0 on PyPI](https://pypi.org/project/pytest-asyncio/) — version, asyncio_mode changes
- [CloudWatch Log Group Destroy Issues — terraform-provider-aws #29247](https://github.com/hashicorp/terraform-provider-aws/issues/29247) — confirmed limitation causing orphaned log groups
- [boto3 filter_log_events timing issue — GitHub #1524](https://github.com/boto/boto3/issues/1524) — confirmed propagation delay causing empty results
- RSF source code (direct inspection): `src/rsf/`, `src/rsf/terraform/templates/`, `tests/`, `.planning/PROJECT.md` — all architecture and pattern findings

### Secondary (MEDIUM confidence)
- [Testing Lambda durable functions (AWS docs)](https://docs.aws.amazon.com/lambda/latest/dg/durable-testing.html) — local vs. cloud testing modes, DurableFunctionCloudTestRunner
- [aws-durable-execution-sdk-python-testing (GitHub)](https://github.com/aws/aws-durable-execution-sdk-python-testing) — cloud runner poll-until-complete pattern
- [GetDurableExecutionState API (boto3)](https://docs.aws.amazon.com/boto3/latest/reference/services/lambda/client/get_durable_execution_state.html) — internal SDK API; external use for test result extraction is undocumented
- [Terraform AWS Provider — Lambda issue #45354](https://github.com/hashicorp/terraform-provider-aws/issues/45354) — durable_config support added in provider v6.25.0
- [aws-samples/sample-ai-workflows-in-aws-lambda-durable-functions (GitHub)](https://github.com/aws-samples/sample-ai-workflows-in-aws-lambda-durable-functions) — real-world workflow pattern examples

### Tertiary (LOW confidence)
- [Lambda Durable Functions cost analysis — thecandidstartup.org](https://www.thecandidstartup.org/2026/01/12/aws-lambda-durable-functions.html) — checkpoint storage cost structure; third-party analysis, needs validation against AWS pricing page

---
*Research completed: 2026-02-26*
*Ready for roadmap: yes*
