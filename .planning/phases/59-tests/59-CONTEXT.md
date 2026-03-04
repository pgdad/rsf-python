# Phase 59: Tests - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Local unit tests and real-AWS integration test for the registry-modules-demo example. Local tests verify workflow YAML parsing, handler registration, and handler business logic without AWS credentials. Integration test deploys via `rsf deploy` (custom provider pipeline), invokes a durable execution, polls to SUCCEEDED, verifies CloudWatch logs, and tears down via `rsf deploy --teardown` with empty state verification.

</domain>

<decisions>
## Implementation Decisions

### Integration deployment path
- Deploy via `rsf deploy` subprocess call — exercises the full custom provider pipeline: rsf.toml → CustomProvider → FileTransport → deploy.sh → terraform apply
- Run `rsf generate` first (also as subprocess) to create src/generated/ that deploy.sh zips
- Full test fixture sequence: `rsf generate` → `rsf deploy` → [test assertions] → `rsf deploy --teardown`
- All RSF CLI calls via subprocess (not Python API imports) — tests exactly what users run

### Lambda invocation
- Use boto3 `lambda_client.invoke()` with `InvocationType='Event'` and `DurableExecutionName` targeting the alias ARN
- Parse alias ARN from `rsf deploy` output or from terraform output in the terraform/ dir
- Poll with `list_durable_executions_by_function` until SUCCEEDED (matching existing integration test pattern)

### Teardown verification
- Dedicated test method `test_teardown_leaves_empty_state` runs `rsf deploy --teardown` and asserts `terraform state list` returns empty — visible, reportable test result matching TEST-03
- Delete orphaned CloudWatch log group `/aws/lambda/{function_name}` after teardown (established pattern from test_harness.py)
- Fallback: if `rsf deploy --teardown` fails, fall back to direct `terraform destroy` in fixture cleanup to prevent stuck AWS resources — test still FAILs the teardown assertion but cleanup happens

### Local test organization
- `examples/registry-modules-demo/tests/test_handlers.py` already has 16 handler business logic tests — keep as-is
- Create `examples/registry-modules-demo/tests/test_local.py` for workflow YAML parsing and handler registration tests (new scope per TEST-01)
- conftest.py already exists with path setup + registry clear pattern — reuse

### Claude's Discretion
- Integration test payload (image processing input to trigger happy path)
- Which handler names to assert in CloudWatch log queries
- Whether to test error path (InvalidImageError → ProcessingFailed) in integration or leave that to local tests
- Exact terraform state list invocation method (subprocess in terraform/ dir)
- How to parse alias ARN from rsf deploy output vs. terraform output -raw
- Local test count and specific assertions for workflow YAML parsing and handler registration

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/test_examples/conftest.py`: Integration test harness with `make_execution_id()`, `poll_execution()`, `query_logs()`, `terraform_deploy()`, `terraform_teardown()`, `iam_propagation_wait()`, shared boto3 fixtures
- `tests/test_examples/test_order_processing.py`: Reference integration test pattern — class-based, scoped deployment fixture, happy + error path assertions, CloudWatch log verification
- `examples/registry-modules-demo/tests/test_handlers.py`: 16 existing handler unit tests across 4 handler classes
- `examples/registry-modules-demo/tests/conftest.py`: Path setup, registry clear, module cache purge fixture
- `examples/registry-modules-demo/deploy.sh`: Custom provider script with deploy/destroy dispatch and tfvars.json generation

### Established Patterns
- Integration tests use `pytest.mark.integration` marker
- Class-based test organization with `scope="class"` deployment fixture
- Deployment fixture does setup in yield body, teardown after yield
- `make_execution_id()` for UUID-suffixed collision-free execution names
- `poll_execution()` with exponential backoff on throttle
- `query_logs()` with 15s propagation buffer and retry
- `iam_propagation_wait(15s)` after deploy before invocation
- Handler unit tests use deferred imports (`from handlers.X import Y` inside test methods)

### Integration Points
- New integration test: `tests/test_examples/test_registry_modules_demo.py`
- New local tests: `examples/registry-modules-demo/tests/test_local.py`
- `rsf generate` and `rsf deploy` invoked as subprocess from test fixture
- `rsf deploy --teardown` invoked for cleanup
- `terraform state list` invoked in terraform/ dir for teardown verification
- boto3 Lambda client for durable execution invocation and polling
- boto3 CloudWatch Logs client for log group cleanup and log assertions

</code_context>

<specifics>
## Specific Ideas

- The integration test should be the first integration test that exercises `rsf deploy` / `rsf deploy --teardown` subprocess calls rather than direct terraform — this validates the custom provider end-to-end
- Teardown fallback to direct terraform destroy is a safety net only — the test should still FAIL if `rsf deploy --teardown` exits non-zero, just ensure cleanup happens regardless
- test_local.py should import and parse the example's workflow.yaml to verify RSF can read it, and verify handler registration discovers all 4 handlers

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 59-tests*
*Context gathered: 2026-03-04*
