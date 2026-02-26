# Phase 15: Integration Test Harness — Plan

## Goal

Build shared test infrastructure that all 5 examples will use for AWS integration testing: polling helper, log query helper, teardown fixture, UUID execution IDs, and single-command test runner.

## Requirements Covered

- HARN-01: poll_execution() with 3-5s polling, exponential backoff on throttle
- HARN-02: query_logs() with 15s propagation buffer and retry
- HARN-03: teardown fixture with terraform destroy + orphan log group cleanup
- HARN-04: Single command: `pytest tests/test_examples/ -m integration`
- HARN-06: UUID-suffixed execution IDs
- HARN-07: 15s IAM propagation buffer

## API Research Summary

**Validated APIs (from boto3 docs):**
- `list_durable_executions_by_function(FunctionName, DurableExecutionName, Statuses)` → returns `DurableExecutions[].Status` with values: RUNNING, SUCCEEDED, FAILED, TIMED_OUT, STOPPED
- `get_durable_execution_history(DurableExecutionArn)` → returns `Events[].EventType` including ExecutionSucceeded, ExecutionFailed
- `invoke(FunctionName, InvocationType='Event', Payload)` → async invocation for durable functions
- CloudWatch Logs Insights: `start_query()` + `get_query_results()`

**Polling strategy:** Use `list_durable_executions_by_function` filtered by `DurableExecutionName` to check status. Terminal states: SUCCEEDED, FAILED, TIMED_OUT, STOPPED.

## Plan

### 1. Create test_examples directory structure

```
tests/
  test_examples/
    __init__.py
    conftest.py          ← shared harness (poll, logs, teardown, UUID)
    test_order_processing.py    ← stub (Phase 16 fills in)
    test_data_pipeline.py       ← stub
    test_approval_workflow.py   ← stub
    test_retry_recovery.py      ← stub
    test_intrinsic_showcase.py  ← stub
```

### 2. Build conftest.py with harness components

**a) `make_execution_id(name)` function:**
- Format: `test-{name}-{YYYYMMDD}T{HHMMSS}-{uuid8}`
- Uses `uuid.uuid4().hex[:8]` for uniqueness

**b) `poll_execution(lambda_client, function_name, execution_name, timeout=300)` function:**
- Polls `list_durable_executions_by_function` every 5 seconds
- Exponential backoff on `ClientError` with code `TooManyRequestsException` (start 5s, max 30s)
- Returns execution summary dict when terminal state reached
- Raises `TimeoutError` if timeout exceeded

**c) `query_logs(logs_client, log_group, query, start_time, end_time=None, wait_seconds=15)` function:**
- Applies `wait_seconds` propagation buffer before first query
- Uses CloudWatch Logs Insights `start_query` / `get_query_results`
- Retries up to 5 times with 5s intervals until results are non-empty
- Returns list of result rows

**d) `terraform_deploy(example_dir)` fixture helper:**
- Runs `terraform init -input=false` + `terraform apply -auto-approve -input=false` in example's terraform/ dir
- Captures outputs via `terraform output -json`
- Returns dict of outputs (function_name, function_arn, log_group_name)

**e) `terraform_teardown(example_dir, logs_client, log_group_name)` fixture helper:**
- Runs `terraform destroy -auto-approve -input=false`
- Explicitly calls `logs_client.delete_log_group(logGroupName=log_group_name)` to clean orphaned log groups
- Swallows ResourceNotFoundException on log group delete

**f) `iam_propagation_wait()` helper:**
- 15-second sleep after terraform apply to let IAM propagate

**g) pytest markers:**
- Register `integration` marker in `conftest.py`
- Add `pytestmark = pytest.mark.integration` to all test_examples test files

### 3. Add pytest marker registration to pyproject.toml

```toml
[tool.pytest.ini_options]
markers = ["integration: AWS integration tests (require credentials and terraform)"]
```

### 4. Create stub integration test files for Phase 16

Each stub file will have the marker and a placeholder test so the structure works.

### 5. Write unit tests for harness components

Test `make_execution_id` format and uniqueness. Test `poll_execution` and `query_logs` logic with mocked boto3 clients.

## Success Criteria Verification

1. ✅ poll_execution() waits for terminal states with 5s polling + exponential backoff on throttle
2. ✅ query_logs() applies 15s buffer, retries until non-empty
3. ✅ teardown runs terraform destroy + deletes orphaned log groups
4. ✅ UUID-suffixed execution IDs via make_execution_id()
5. ✅ `pytest tests/test_examples/ -m integration` works as single command
