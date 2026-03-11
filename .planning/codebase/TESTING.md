# Testing Patterns

**Analysis Date:** 2026-03-11

## Test Framework

**Runner:**
- `pytest` 7.0+ (from dev dependencies in `pyproject.toml`)
- Config: `[tool.pytest.ini_options]` in `pyproject.toml`

**Async Testing:**
- `pytest-asyncio` 0.21+ for async test support
- Marker: `@pytest.mark.asyncio` for async test functions

**HTTP Testing (Inspector):**
- `httpx` 0.24+ for async HTTP client testing
- Used in `tests/test_inspect/test_replay.py` with `AsyncClient` and `ASGITransport`

**Run Commands:**
```bash
pytest                    # Run all tests
pytest -v               # Verbose output with test names
pytest tests/           # Run tests in specific directory
pytest --import-mode=importlib  # Default mode in pyproject.toml
```

**Custom pytest options:**
- `--update-snapshots` flag (custom, defined in `tests/conftest.py`) - regenerates snapshot golden files instead of comparing

## Test File Organization

**Location:**
- Co-located in parallel `tests/` directory structure
- Pattern: `tests/test_<domain>/test_<feature>.py`
- Example: `tests/test_cdk/test_generator.py`, `tests/test_inspect/test_replay.py`

**Directory structure:**
```
tests/
├── conftest.py              # Root conftest with custom pytest options
├── mock_sdk.py              # Shared mock SDK utilities
├── test_cdk/
│   ├── __init__.py
│   ├── test_engine.py
│   └── test_generator.py
├── test_context/
│   ├── __init__.py
│   └── test_context.py
├── test_inspect/
│   ├── __init__.py
│   ├── test_client.py
│   ├── test_models.py
│   ├── test_replay.py
│   └── test_server.py
├── test_mock_sdk/
│   ├── __init__.py
│   ├── test_chaos.py
│   └── test_mock_context.py
├── test_integration/
│   ├── __init__.py
│   └── test_sdk_integration.py
└── test_examples/
    ├── conftest.py          # Shared integration test harness
    ├── test_approval_workflow.py
    ├── test_data_pipeline.py
    ├── test_order_processing.py
    └── [other example tests]
```

**Naming:**
- Test files: `test_<feature>.py`
- Test classes: `class Test<Feature>:`
- Test methods: `def test_<specific_behavior>():`

## Test Structure

**Test suite organization (class-based):**

```python
class TestFeature:
    """Tests for specific feature/module."""

    def test_basic_operation(self):
        """Test description as docstring."""
        # Arrange
        input_data = {...}

        # Act
        result = function_under_test(input_data)

        # Assert
        assert result == expected
```

**Patterns:**
- Arrange-Act-Assert (AAA) pattern (implicit, not always formalized with comments)
- Single responsibility per test method
- Descriptive test names that explain the behavior being tested
- Example from `tests/test_context/test_context.py`:

```python
class TestContextObject:
    def test_create_factory(self):
        ctx = ContextObject.create(
            execution_id="exec-123",
            execution_name="MyExec",
            state_name="MyState",
            state_machine_name="MyMachine",
        )
        assert ctx.Execution.Id == "exec-123"
        assert ctx.Execution.Name == "MyExec"
```

**Fixtures:**

```python
@pytest.fixture
def minimal_config():
    """Minimal CDK configuration for testing."""
    return CDKConfig(workflow_name="MyWorkflow")

@pytest.fixture(scope="session")
def lambda_client(aws_region):
    """Shared boto3 Lambda client for integration tests."""
    return boto3.client("lambda", region_name=aws_region)
```

Scopes used:
- `function` (default): Fresh instance per test
- `session`: Shared across entire test session
- `module`: Shared across module

**Example fixture usage:**
```python
def test_creates_all_files(self, tmp_path, minimal_config):
    """Generator creates app.py, stack.py, cdk.json, requirements.txt."""
    result = generate_cdk(minimal_config, tmp_path)
    expected_files = {"app.py", "stack.py", "cdk.json", "requirements.txt"}
    generated_names = {f.name for f in result.generated_files}
    assert generated_names == expected_files
```

## Mocking & Fixtures

**Framework:** `unittest.mock` (standard library) with pytest integration

**Mocking patterns:**

```python
from unittest.mock import AsyncMock, MagicMock, patch

# Create mock object
mock_boto_client = MagicMock()
mock_boto_client.invoke.return_value = {"StatusCode": 202}

# Patch module import
with patch("rsf.inspect.client.boto3") as mock_boto:
    mock_boto.client.return_value = mock_boto_client
    # Test code using mocked boto3
    client = LambdaInspectClient(...)
```

**Async mocking:**
```python
@pytest.mark.asyncio
async def test_invoke_execution_calls_lambda_invoke() -> None:
    """invoke_execution calls boto3 lambda_client.invoke with InvocationType='Event'."""
    mock_boto_client = MagicMock()
    mock_boto_client.invoke.return_value = {
        "StatusCode": 202,
        "ResponseMetadata": {"RequestId": "req-123"},
    }

    with patch("rsf.inspect.client.boto3") as mock_boto:
        mock_boto.client.return_value = mock_boto_client
        client = LambdaInspectClient(...)
        result = await client.invoke_execution({"key": "value"})

    mock_boto_client.invoke.assert_called_once_with(...)
```

**What to mock:**
- External services (boto3, AWS Lambda, CloudWatch)
- HTTP calls (with httpx `AsyncClient` + `patch`)
- File I/O (use `tmp_path` fixture instead)
- Dependencies that are slow or stateful

**What NOT to mock:**
- Domain models (Pydantic models, dataclasses)
- Business logic functions (test real behavior)
- In-memory data structures
- Utility functions

## Fixtures & Test Data

**Fixture location:**
- Root: `tests/conftest.py` - pytest configuration and root-level fixtures
- Module-level: `tests/test_examples/conftest.py` - shared integration test harness

**Test data utilities:**
- Mock SDK: `tests/mock_sdk.py` provides `MockDurableContext`, `Duration` for durable execution testing
- Config factories: `@pytest.fixture` that returns configured objects (e.g., `minimal_config`, `full_config`)

**Example from `tests/mock_sdk.py`:**
```python
from tests.mock_sdk import BranchResult, Duration, MockDurableContext

class TestStep:
    def test_step_calls_handler(self):
        ctx = MockDurableContext()
        result = ctx.step("DoWork", lambda x: {"processed": x["val"] * 2}, {"val": 5})
        assert result == {"processed": 10}
```

**Integration test harness (`tests/test_examples/conftest.py`):**
- Provides helpers for AWS integration tests:
  - `make_execution_id(name)` - generates UUID-suffixed execution names
  - `poll_execution(lambda_client, function_name, execution_name)` - waits for durable execution completion with exponential backoff
  - `query_logs(logs_client, log_group, query)` - CloudWatch Logs Insights queries with propagation buffer
  - `terraform_deploy(example_dir)` / `terraform_teardown(example_dir)` - infrastructure management
  - `iam_propagation_wait(seconds)` - 15s buffer for IAM propagation
- Session-scoped fixtures for boto3 clients:
  - `aws_region()` - returns "us-east-2"
  - `lambda_client(aws_region)` - shared boto3 Lambda client
  - `logs_client(aws_region)` - shared boto3 CloudWatch Logs client

## Exception Testing

**Pattern:**
```python
def test_get_missing_raises(self):
    store = VariableStore()
    with pytest.raises(KeyError, match="not defined"):
        store.get("missing")
```

**Features:**
- `pytest.raises()` context manager for catching expected exceptions
- `match` parameter for regex validation of error message
- Example assertions on exception details:
  ```python
  def test_step_handler_exception_propagates(self):
      ctx = MockDurableContext()
      with pytest.raises(ValueError, match="boom"):
          ctx.step("Fail", lambda x: (_ for _ in ()).throw(ValueError("boom")), {})
  ```

## Async Testing

**Pattern:**
```python
@pytest.mark.asyncio
async def test_invoke_execution_calls_lambda_invoke() -> None:
    """Test async function."""
    mock_boto_client = MagicMock()
    mock_boto_client.invoke.return_value = {"StatusCode": 202}

    with patch("rsf.inspect.client.boto3") as mock_boto:
        mock_boto.client.return_value = mock_boto_client
        client = LambdaInspectClient(function_name="fn", ...)
        result = await client.invoke_execution({"key": "value"})

    assert result["StatusCode"] == 202
```

**Features:**
- `@pytest.mark.asyncio` marks test as async
- `async def` and `await` keywords
- Works with mocks and fixtures like sync tests

## Test Types

**Unit Tests:**
- Located in `tests/test_<domain>/`
- Scope: Single function/class in isolation
- Mocked external dependencies
- Example: `tests/test_cdk/test_generator.py` tests CDK code generation without AWS

**Integration Tests:**
- Located in `tests/test_integration/` and `tests/test_examples/`
- Scope: Multiple components working together
- Real AWS infrastructure (with terraform)
- Example: `tests/test_integration/test_sdk_integration.py` tests SDK with real workflow execution

**SDK Integration:**
- `tests/test_integration/test_sdk_integration.py`
- Tests: Workflow execution, state transitions, handler invocation
- Fixtures: `workflow`, `tmp_path` for generated code
- Example:
  ```python
  class TestSimpleTaskWorkflow:
      @pytest.fixture
      def workflow(self):
          return Workflow(...)

      def test_executes_handler_and_returns(self, workflow):
          result = workflow.execute({"key": "value"})
          assert result == expected
  ```

## Markers & Test Organization

**Custom markers (defined in `tests/conftest.py`):**
- `@pytest.mark.integration` - AWS integration tests requiring credentials and terraform

**Usage:**
```python
@pytest.mark.integration
def test_deploy_and_execute():
    """Requires AWS credentials and terraform."""
    pass
```

**Running specific markers:**
```bash
pytest -m integration          # Only integration tests
pytest -m "not integration"    # Skip integration tests
```

## Testing Strategies

**Parametrized tests:**
```python
@pytest.mark.parametrize("arg", [value1, value2, value3])
def test_handles_values(self, arg):
    result = process(arg)
    assert result is valid
```

**Snapshot testing:**
- Custom `--update-snapshots` flag in `tests/conftest.py`
- Used for comparing generated code output to golden files
- Example usage pattern (likely in generator tests):
  ```python
  def test_generates_valid_code(self, fixture, tmp_path):
      result = generate_cdk(fixture, tmp_path)
      # Compare generated files to snapshots
  ```

**Cleanup patterns:**
- Terraform infrastructure: `terraform_teardown()` in integration tests
- Log group cleanup: Explicit deletion via boto3 to prevent orphaned resources
- Fixture scope management: Session-scoped fixtures for shared clients

## Coverage

**Requirements:** Not enforced in `pyproject.toml` (no coverage section)

**Test paths included in pytest discovery:**
```
testpaths = [
    "tests",
    "examples/order-processing/tests",
    "examples/data-pipeline/tests",
    "examples/intrinsic-showcase/tests",
    "examples/approval-workflow/tests",
    "examples/retry-and-recovery/tests",
    "examples/lambda-url-trigger/tests",
    "examples/registry-modules-demo/tests",
]
```

---

*Testing analysis: 2026-03-11*
