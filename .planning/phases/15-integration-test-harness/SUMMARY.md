# Phase 15: Integration Test Harness — Summary

## Completed: 2026-02-26

## What Was Built

### Shared test harness (`tests/test_examples/conftest.py`)

1. **`make_execution_id(name)`** — UUID-suffixed execution ID generator
   - Format: `test-{name}-{YYYYMMDD}T{HHMMSS}-{uuid8}`
   - Prevents collisions across parallel or sequential re-runs (HARN-06)

2. **`poll_execution(lambda_client, function_name, execution_name)`** — Durable execution polling helper
   - Uses `list_durable_executions_by_function` API filtered by DurableExecutionName
   - 5-second base polling interval
   - Exponential backoff on TooManyRequestsException/ThrottlingException (max 30s)
   - Returns on terminal states: SUCCEEDED, FAILED, TIMED_OUT, STOPPED
   - Raises TimeoutError after configurable timeout (default 300s) (HARN-01)

3. **`query_logs(logs_client, log_group, query, start_time)`** — CloudWatch Logs Insights query helper
   - 15-second propagation buffer before first query (HARN-07)
   - CloudWatch Logs Insights `start_query` / `get_query_results` API
   - Retries up to 5 times with 5s intervals until results are non-empty (HARN-02)

4. **`terraform_deploy(example_dir)`** — Terraform deploy helper
   - `terraform init -input=false` + `terraform apply -auto-approve -input=false`
   - Returns outputs via `terraform output -json`

5. **`terraform_teardown(example_dir, logs_client, log_group_name)`** — Teardown with orphan cleanup
   - `terraform destroy -auto-approve -input=false`
   - Explicit `delete_log_group()` for orphaned CloudWatch log groups
   - Swallows ResourceNotFoundException (HARN-03)

6. **`iam_propagation_wait()`** — 15-second IAM propagation buffer (HARN-07)

### Test directory structure

```
tests/test_examples/
  __init__.py
  conftest.py                     ← shared harness
  test_harness.py                 ← 20 unit tests for harness components
  test_order_processing.py        ← integration stub (Phase 16)
  test_data_pipeline.py           ← integration stub (Phase 16)
  test_approval_workflow.py       ← integration stub (Phase 16)
  test_retry_recovery.py          ← integration stub (Phase 16)
  test_intrinsic_showcase.py      ← integration stub (Phase 16)
```

### pytest configuration

- `integration` marker registered in pyproject.toml and conftest.py
- `pytest tests/test_examples/ -m integration` collects all 5 integration stubs (HARN-04)
- Harness unit tests run without `-m integration` and don't require AWS credentials

## Test Results

- 20 harness unit tests passing (poll_execution, query_logs, teardown, UUID)
- 592 total tests passing (572 existing + 20 new), 5 integration stubs deselected
- Zero regressions in existing test suite

## Requirements Satisfied

| Requirement | Description | Status |
|-------------|-------------|--------|
| HARN-01 | poll_execution with 3-5s polling, exponential backoff on throttle | ✅ |
| HARN-02 | query_logs with 15s propagation buffer and retry loop | ✅ |
| HARN-03 | teardown with terraform destroy + orphan log group cleanup | ✅ |
| HARN-04 | Single command: `pytest tests/test_examples/ -m integration` | ✅ |
| HARN-06 | UUID-suffixed execution IDs | ✅ |
| HARN-07 | 15s IAM propagation buffer | ✅ |

## API Research Findings

- **Polling API:** `list_durable_executions_by_function(FunctionName, DurableExecutionName)` returns `Status` field with values: RUNNING, SUCCEEDED, FAILED, TIMED_OUT, STOPPED
- **History API:** `get_durable_execution_history(DurableExecutionArn)` provides step-level event data with EventType enum
- **No `get_durable_execution` API exists** — the inspector's client.py uses this but it maps to `list_durable_executions_by_function` for status checking
- Invocation uses `InvocationType='Event'` (async) for durable functions
