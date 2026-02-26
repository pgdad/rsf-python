# Stack Research

**Domain:** Automated AWS integration testing for Lambda Durable Functions workflows
**Researched:** 2026-02-26
**Confidence:** HIGH (all library versions verified against PyPI as of research date; AWS API patterns verified against official docs)

---

## Context: What Already Exists

The RSF project already ships these relevant pieces (do not re-add):

- `boto3>=1.28` — already a core dependency; used by `rsf inspect` for `list_durable_executions_by_function` and `get_durable_execution` calls
- `pytest>=7.0` + `pytest-asyncio>=0.21` — already in `dev` optional deps; used for existing unit/integration tests
- `subprocess` — already used in `rsf deploy` (terraform init/apply) and `rsf deploy --code-only`
- `MockDurableContext` in `tests/mock_sdk.py` — existing mock; keeps tests passing without AWS

The new milestone adds **a second test tier**: real AWS deployments verified with CloudWatch Logs Insights queries and Lambda return value inspection. The stack additions below are strictly for that tier.

---

## Recommended Stack

### Core Technologies (New Additions)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `aws-lambda-powertools` | `>=3.24.0` | Structured JSON logging in example handlers | Outputs queryable JSON fields (`level`, `service`, `function_name`, `function_request_id`) automatically. CloudWatch Logs Insights auto-discovers JSON keys. Industry standard for Lambda structured logging. Verified: v3.24.0 released 2026-01-05. |
| `pytest-timeout` | `>=2.4.0` | Per-test timeout for AWS deploy+verify tests | Integration tests talk to real AWS and can hang indefinitely (Terraform apply, CloudWatch query polling). `@pytest.mark.timeout(300)` prevents CI hangs without killing the whole suite. Verified: v2.4.0 released 2025-05-05. |
| `boto3` | `>=1.42.0` | CloudWatch Logs Insights queries + durable execution APIs | Already a dependency; version floor bumped to get `ListDurableExecutionsByFunction`, `GetDurableExecution`, and `logs.start_query` / `logs.get_query_results`. Verified: v1.42.57 released 2026-02-25. |

### Supporting Libraries (New Additions)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest-asyncio` | `>=1.3.0` | Async test functions for CloudWatch polling loops | Already in dev extras at `>=0.21`; bump floor to `>=1.3.0` for stable `asyncio_mode = "auto"` config. Needed if polling helpers are written as `async def`. Verified: v1.3.0 released 2025-11-10. |

### Development Tools (No New Additions Needed)

The existing `terraform` binary (called via `subprocess`) covers Terraform apply/destroy. No Python wrapper library is needed — the pattern already established by `rsf deploy` is correct and sufficient.

| Tool | Purpose | Notes |
|------|---------|-------|
| `terraform` (binary) | `apply -auto-approve` and `destroy -auto-approve` in test fixtures | Invoked via `subprocess.run` in `conftest.py` session-scoped fixtures — same pattern as existing `deploy_cmd.py`. No new Python wrapper. |
| CloudWatch Logs Insights (boto3 `logs` client) | Query structured handler logs post-execution | Use `start_query` + poll `get_query_results` until `status == 'Complete'`. |
| `GetDurableExecution` boto3 API | Retrieve Lambda return value + terminal status | Returns `Result` (JSON), `Status` (SUCCEEDED/FAILED/TIMED_OUT), `Error`. Use this for primary workflow output assertion. |

---

## AWS API Patterns to Know

### Invoking a Durable Lambda (Async)

```python
import boto3, json, time

client = boto3.client("lambda", region_name="us-east-2")

# 1. Fire the invocation — returns immediately with 202
response = client.invoke(
    FunctionName="my-rsf-workflow",
    InvocationType="Event",  # async; required for durable functions > 15 min
    Payload=json.dumps({"order_id": "test-001"}).encode(),
)
# response["StatusCode"] == 202

# 2. Capture the execution ARN from response headers
#    OR use ListDurableExecutionsByFunction to find the execution by name/time
```

### Polling for Completion

```python
def wait_for_execution(
    lambda_client,
    function_name: str,
    execution_name: str,
    timeout_s: int = 120,
    poll_interval_s: float = 3.0,
) -> dict:
    """Poll GetDurableExecution until terminal status."""
    deadline = time.monotonic() + timeout_s

    # First, resolve execution ARN via list
    resp = lambda_client.list_durable_executions_by_function(
        FunctionName=function_name,
        DurableExecutionName=execution_name,
        MaxItems=1,
    )
    arn = resp["DurableExecutions"][0]["DurableExecutionArn"]

    while time.monotonic() < deadline:
        detail = lambda_client.get_durable_execution(DurableExecutionArn=arn)
        status = detail["Status"]
        if status in {"SUCCEEDED", "FAILED", "TIMED_OUT", "STOPPED"}:
            return detail
        time.sleep(poll_interval_s)

    raise TimeoutError(f"Execution {execution_name} did not complete within {timeout_s}s")
```

**Status values:** `RUNNING`, `SUCCEEDED`, `FAILED`, `TIMED_OUT`, `STOPPED`

`GetDurableExecution` returns:
- `Result` — JSON string of the workflow's return value (present when SUCCEEDED, up to 256 KB)
- `Error` — JSON error details (present when FAILED)
- `InputPayload` — original input
- `StartTimestamp`, `EndTimestamp`

### Querying CloudWatch Logs Insights

```python
import time

def query_logs(
    logs_client,
    log_group: str,
    query_string: str,
    start_time: int,  # epoch seconds
    end_time: int,
    timeout_s: int = 60,
) -> list[dict]:
    """Run a Logs Insights query and wait for results."""
    resp = logs_client.start_query(
        logGroupName=log_group,
        startTime=start_time,
        endTime=end_time,
        queryString=query_string,
        limit=100,
    )
    query_id = resp["queryId"]

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        result = logs_client.get_query_results(queryId=query_id)
        if result["status"] == "Complete":
            return result["results"]
        if result["status"] in {"Failed", "Cancelled", "Timeout"}:
            raise RuntimeError(f"Log query {query_id} ended with status {result['status']}")
        time.sleep(2)

    raise TimeoutError(f"Log query {query_id} did not complete within {timeout_s}s")
```

**Important:** CloudWatch Logs Insights has a lag. Logs written during Lambda execution are typically available within 5-30 seconds after function completion. Build this lag into test polling — wait for `GetDurableExecution` SUCCEEDED first, then add a short sleep (10s) before querying logs.

Log group for RSF workflows: `/aws/lambda/<workflow-name>` (generated by RSF's `cloudwatch.tf`).

Query example for structured logs:
```
fields @timestamp, message, state_name, level
| filter level = "INFO" and ispresent(state_name)
| sort @timestamp asc
```

### Structured Logging in Example Handlers

Use `aws-lambda-powertools` Logger in each example handler. CloudWatch Logs Insights auto-parses JSON keys.

```python
# handlers/process_order.py
from aws_lambda_powertools import Logger

logger = Logger(service="order-pipeline")

def handle(event: dict) -> dict:
    logger.info("Processing order", extra={"order_id": event["order_id"], "state_name": "ProcessOrder"})
    result = {"status": "processed", "order_id": event["order_id"]}
    logger.info("Order complete", extra={"result": result, "state_name": "ProcessOrder"})
    return result
```

This produces JSON logs queryable by `state_name`, `order_id`, `level`, `service`, etc.

---

## Test Harness Architecture

### Fixture Scope Strategy

```
conftest.py (tests/integration/)
  └── deploy_example(scope="module")     ← terraform apply once per example file
        ├── invoke_workflow()             ← function scope; one invocation per test
        └── teardown: terraform destroy  ← runs after all tests in the module
```

Use `scope="module"` (not `scope="session"`) for deploy fixtures. Each example is a separate test module; session scope would tie all examples together and make partial failures unrecoverable.

Use `pytest --timeout=600` globally for integration tests and per-test `@pytest.mark.timeout(300)` for individual assertions.

### Terraform Subprocess Pattern

Reuse the existing `subprocess.run(["terraform", "apply", "-auto-approve"], cwd=tf_dir, check=True)` pattern from `deploy_cmd.py`. No wrapper library needed.

```python
# tests/integration/conftest.py
import subprocess
import pytest
from pathlib import Path

@pytest.fixture(scope="module")
def deployed_example(tmp_path_factory, example_dir: Path):
    tf_dir = example_dir / "terraform"
    subprocess.run(["terraform", "init", "-no-color"], cwd=tf_dir, check=True)
    subprocess.run(["terraform", "apply", "-auto-approve", "-no-color"], cwd=tf_dir, check=True)
    yield  # tests run here
    subprocess.run(["terraform", "destroy", "-auto-approve", "-no-color"], cwd=tf_dir, check=True)
```

---

## Installation

```bash
# Add to pyproject.toml [project.optional-dependencies]
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=1.3.0",     # bumped from 0.21
    "pytest-timeout>=2.4.0",     # NEW
    "httpx>=0.24",
]
integration = [
    "boto3>=1.42.0",              # already core dep; explicit floor for integration extras
    "pytest>=7.0",
    "pytest-asyncio>=1.3.0",
    "pytest-timeout>=2.4.0",
    "aws-lambda-powertools>=3.24.0",  # NEW — for example handlers
]

# Install for integration testing
pip install -e ".[integration]"

# Example handlers install (in generated Lambda zip)
pip install aws-lambda-powertools>=3.24.0
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `aws-lambda-powertools` Logger | `structlog>=25.5.0` | Use structlog if the project already uses it elsewhere, or if you need custom processor pipelines. Powertools wins here because it auto-injects Lambda context (function name, request ID) without extra decorator plumbing, and its JSON format is identical to what CloudWatch Logs Insights expects. |
| `aws-lambda-powertools` Logger | `python-json-logger` | python-json-logger is lighter but requires manual field injection. No advantage over Powertools for Lambda. |
| `subprocess.run` (terraform) | `pytest-terraform` (cloud-custodian) | pytest-terraform wraps `terraform init/apply/destroy` with fixtures but adds a dependency on a lightly-maintained project (last PyPI release 0.5.1, 2023-09-18). The `subprocess.run` pattern already established in `deploy_cmd.py` is simpler and fully understood. |
| `subprocess.run` (terraform) | `python-terraform` (PyPI) | python-terraform is unmaintained (last release 2021). Avoid. |
| `GetDurableExecution` + `ListDurableExecutionsByFunction` | CloudWatch Logs only | Logs-only verification requires waiting for log propagation and parsing return values from logs. The dedicated durable execution APIs return the actual `Result` JSON directly — use them for return value assertions and logs for intermediate state checks. |
| `pytest.mark.timeout` | Custom `asyncio.wait_for` wrappers | pytest-timeout works at the process level and catches hanging subprocess calls (terraform, boto3 network). asyncio timeouts only cover async code. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `moto` for integration tests | moto mocks AWS at the HTTP level. It does not simulate Lambda Durable Functions (the SDK is too new for moto coverage). Use moto only for unit tests against S3/DynamoDB in isolation. | Real AWS via boto3 with `GetDurableExecution` polling. |
| `localstack` | Does not support Lambda Durable Functions (checkpoint/replay mechanism is proprietary). No benefit over real AWS for this feature. | Real AWS. |
| `pytest-terraform` (cloud-custodian) | Last PyPI release 2023-09-18 (v0.5.1). Lightly maintained. Adds indirection over straightforward subprocess calls. | `subprocess.run(["terraform", ...])` directly in `conftest.py`. |
| `python-terraform` | Unmaintained since 2021. | Same as above. |
| `asyncio` for the test harness polling loop | The polling helpers call `boto3` (synchronous) and `time.sleep`. No benefit to async here unless you are running parallel example deployments, which introduces complexity. Keep it sync with `time.sleep`. | Synchronous polling with `time.sleep`. |
| `pytest-asyncio` for integration tests | Only needed if the test functions themselves are `async def`. Synchronous boto3 calls do not need it. Keep it in `dev` for the existing async FastAPI tests, but do not require it for the integration harness. | Sync pytest fixtures with `time.sleep` polling. |
| Session-scope deploy fixtures | A single `scope="session"` fixture for all examples fails everything if one example teardown errors. | Module-scope fixtures: one deploy/teardown per test module (one module per example). |

---

## Stack Patterns by Variant

**If an example uses real AWS services (e.g., DynamoDB):**
- Add IAM permissions to the RSF-generated `iam.tf` via override file (Generation Gap pattern already supports this)
- Add DynamoDB table creation to the example's own `terraform/` directory as additional `.tf` files
- Do not add DynamoDB permissions to the core RSF Terraform generator — keep example infrastructure separate

**If CloudWatch Logs are not available within expected window:**
- Add a fixed `time.sleep(15)` after `GetDurableExecution` returns SUCCEEDED before querying logs
- CloudWatch log ingestion latency is typically 5-30s; 15s is a conservative safe floor
- Do not retry log queries indefinitely — set a max poll count of 10 with 3s intervals

**If Terraform state conflicts between examples:**
- Use a unique `backend.tf` per example with distinct S3 key paths, OR
- Use local state (`backend.tf` omitted) with `terraform workspace` per example (simpler for CI)
- Recommendation: local state in `examples/<name>/terraform/` — no S3 backend needed for CI teardown

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `aws-lambda-powertools>=3.24.0` | Python 3.12+ | v3.x requires Python 3.8+; no conflict with RSF's Python 3.13 requirement. Install into Lambda deployment package, not just dev deps. |
| `pytest-timeout>=2.4.0` | `pytest>=7.0` | No known conflicts. Works with both sync and async tests. Does not interfere with pytest-asyncio. |
| `pytest-asyncio>=1.3.0` | `pytest>=7.0` | Major version (1.x) changed `asyncio_mode` default to `strict`. Add `asyncio_mode = "auto"` to `[tool.pytest.ini_options]` in `pyproject.toml` to avoid marking every async test. |
| `boto3>=1.42.0` | `botocore>=1.35.0` | botocore is a boto3 transitive dep; always matches boto3 version. The `ListDurableExecutionsByFunction` and `GetDurableExecution` APIs require a boto3 build from after re:Invent 2025 (December 2025); 1.42.x confirmed current. |

---

## pyproject.toml Changes Required

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=1.3.0",    # bumped from >=0.21
    "pytest-timeout>=2.4.0",    # NEW
    "httpx>=0.24",
]
integration = [
    "pytest>=7.0",
    "pytest-timeout>=2.4.0",
    "aws-lambda-powertools>=3.24.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
asyncio_mode = "auto"           # REQUIRED for pytest-asyncio 1.x
```

---

## Sources

- [boto3 1.42.57 on PyPI](https://pypi.org/project/boto3/) — current version verified 2026-02-26 (HIGH confidence)
- [ListDurableExecutionsByFunction API Reference](https://docs.aws.amazon.com/lambda/latest/api/API_ListDurableExecutionsByFunction.html) — request params, response fields, status values (HIGH confidence)
- [GetDurableExecution API Reference](https://docs.aws.amazon.com/lambda/latest/api/API_GetDurableExecution.html) — result payload, error details, status enum (HIGH confidence)
- [boto3 start_query (CloudWatch Logs)](https://docs.aws.amazon.com/boto3/latest/reference/services/logs/client/start_query.html) — parameters and queryId return (HIGH confidence)
- [Monitoring durable functions](https://docs.aws.amazon.com/lambda/latest/dg/durable-monitoring.html) — CloudWatch metrics, execution ARN format (HIGH confidence)
- [aws-lambda-powertools 3.24.0 on PyPI](https://pypi.org/project/aws-lambda-powertools/) — version verified 2026-02-26 (HIGH confidence)
- [Lambda Powertools Logger docs](https://docs.aws.amazon.com/powertools/python/latest/core/logger/) — JSON field list, `inject_lambda_context` decorator (HIGH confidence)
- [pytest-asyncio 1.3.0 on PyPI](https://pypi.org/project/pytest-asyncio/) — version and asyncio_mode docs verified (HIGH confidence)
- [pytest-timeout 2.4.0 on PyPI](https://pypi.org/project/pytest-timeout/) — version verified (HIGH confidence)
- [structlog 25.5.0 on PyPI](https://pypi.org/project/structlog/) — considered and rejected in favor of Powertools (HIGH confidence)
- [Durable execution SDK logger docs](https://github.com/aws/aws-durable-execution-sdk-python/blob/main/docs/core/logger.md) — SDK log enrichment fields (MEDIUM confidence — official repo but docs may be incomplete)
- [Invoking durable Lambda functions](https://docs.aws.amazon.com/lambda/latest/dg/durable-invocation.html) — invocation patterns and InvocationType Event (HIGH confidence)

---

*Stack research for: RSF v1.2 Comprehensive Examples & Integration Testing*
*Researched: 2026-02-26*
