# Phase 59: Tests - Research

**Researched:** 2026-03-04
**Domain:** pytest — local unit tests + AWS integration tests for registry-modules-demo
**Confidence:** HIGH

## Summary

Phase 59 adds the test suite for the `examples/registry-modules-demo` example. Two scopes are needed: (1) local tests that run without AWS — workflow YAML parsing and handler registration — and (2) a real-AWS integration test that deploys via `rsf deploy` (the custom provider pipeline), invokes a durable execution, polls to SUCCEEDED, verifies CloudWatch logs, and tears down via `rsf deploy --teardown` with empty terraform state verification.

The project already has a mature integration test harness in `tests/test_examples/conftest.py` with `poll_execution()`, `query_logs()`, `make_execution_id()`, `iam_propagation_wait()`, and shared boto3 fixtures. The reference integration test pattern is `tests/test_examples/test_order_processing.py`. The key difference for this phase is that deployment goes through `rsf generate` + `rsf deploy` subprocesses (exercising the custom provider) rather than direct `terraform_deploy()`.

**Primary recommendation:** Follow the established class-based integration test pattern with a `scope="class"` deployment fixture. Route all deployment/teardown through `subprocess.run(["rsf", "generate", ...])` and `subprocess.run(["rsf", "deploy", ...])` calls from the example directory. Derive the log group name as `/aws/lambda/{function_name}` (the terraform-aws-modules/lambda module convention). Patch the rsf.toml `program` field to the real deploy.sh absolute path before invoking `rsf deploy`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Integration deployment path:**
- Deploy via `rsf deploy` subprocess call — exercises the full custom provider pipeline: rsf.toml -> CustomProvider -> FileTransport -> deploy.sh -> terraform apply
- Run `rsf generate` first (also as subprocess) to create src/generated/ that deploy.sh zips
- Full test fixture sequence: `rsf generate` -> `rsf deploy` -> [test assertions] -> `rsf deploy --teardown`
- All RSF CLI calls via subprocess (not Python API imports) — tests exactly what users run

**Lambda invocation:**
- Use boto3 `lambda_client.invoke()` with `InvocationType='Event'` and `DurableExecutionName` targeting the alias ARN
- Parse alias ARN from `rsf deploy` output or from terraform output in the terraform/ dir
- Poll with `list_durable_executions_by_function` until SUCCEEDED (matching existing integration test pattern)

**Teardown verification:**
- Dedicated test method `test_teardown_leaves_empty_state` runs `rsf deploy --teardown` and asserts `terraform state list` returns empty — visible, reportable test result matching TEST-03
- Delete orphaned CloudWatch log group `/aws/lambda/{function_name}` after teardown (established pattern from test_harness.py)
- Fallback: if `rsf deploy --teardown` fails, fall back to direct `terraform destroy` in fixture cleanup to prevent stuck AWS resources — test still FAILs the teardown assertion but cleanup happens

**Local test organization:**
- `examples/registry-modules-demo/tests/test_handlers.py` already has 16 handler business logic tests — keep as-is
- Create `examples/registry-modules-demo/tests/test_local.py` for workflow YAML parsing and handler registration tests (new scope per TEST-01)
- conftest.py already exists with path setup + registry clear pattern — reuse

### Claude's Discretion
- Integration test payload (image processing input to trigger happy path)
- Which handler names to assert in CloudWatch log queries
- Whether to test error path (InvalidImageError -> ProcessingFailed) in integration or leave that to local tests
- Exact terraform state list invocation method (subprocess in terraform/ dir)
- How to parse alias ARN from rsf deploy output vs. terraform output -raw
- Local test count and specific assertions for workflow YAML parsing and handler registration

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TEST-01 | Local unit tests verify workflow parsing, handler registration, and handler execution | `load_definition()` from `rsf.dsl.parser` parses workflow YAML into `StateMachineDefinition`; `discover_handlers()` + `registered_states()` from `rsf.registry` verify registration; existing conftest.py handles path setup and registry clearing |
| TEST-02 | Integration test deploys to AWS, invokes durable execution, polls for SUCCEEDED, verifies logs | `rsf generate` + `rsf deploy` subprocess pattern; `lambda_client.invoke(InvocationType='Event', DurableExecutionName=...)` targeting alias ARN; `poll_execution()` from conftest; `query_logs()` for CloudWatch Logs Insights verification |
| TEST-03 | Integration test performs clean teardown via custom provider teardown path | `rsf deploy --teardown` subprocess; `terraform state list` in terraform/ dir verifies empty state; fallback to direct `terraform destroy` ensures cleanup even on teardown failure |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | installed (project) | Test runner, fixtures, markers | Project-wide standard; all existing tests use it |
| boto3 | installed (project) | Lambda invocation, CloudWatch Logs queries | Used in all integration tests |
| subprocess (stdlib) | Python 3.x | Invoke `rsf generate`, `rsf deploy`, `terraform state list` | Established pattern in conftest.py and deploy.sh |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rsf.dsl.parser | project source | `load_definition()` / `load_yaml()` — parse workflow YAML | Local test: verify workflow parses without error |
| rsf.registry | project source | `discover_handlers()`, `registered_states()`, `clear()` | Local test: verify handler registration discovers all 4 |
| botocore.exceptions.ClientError | botocore | Throttle detection in polling | Already used in poll_execution() |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| subprocess `rsf deploy` | Python API imports (`rsf.cli.deploy_cmd.deploy`) | Locked decision: subprocess tests what users run; API imports would bypass CLI error handling |
| `terraform output -raw alias_arn` | Parse rsf deploy stdout | Both work; `terraform output` is simpler and reliable since Terraform state already exists |

**Installation:** No new dependencies — everything is already installed in the project.

## Architecture Patterns

### Recommended File Structure
```
examples/registry-modules-demo/tests/
├── conftest.py          # EXISTING — path setup, registry clear (reuse as-is)
├── test_handlers.py     # EXISTING — 16 handler unit tests (keep as-is)
└── test_local.py        # NEW — workflow YAML parsing + handler registration

tests/test_examples/
├── conftest.py          # EXISTING — shared harness: poll_execution, query_logs, etc.
└── test_registry_modules_demo.py  # NEW — integration test
```

### Pattern 1: Local Tests Without AWS (TEST-01)

**What:** Import RSF internals directly to verify workflow YAML is parseable and handlers register correctly. No subprocess, no AWS.

**When to use:** Fast CI gate that runs on every commit without credentials.

```python
# Source: examples/registry-modules-demo/tests/conftest.py (path setup pattern)
# Source: rsf/dsl/parser.py (load_definition API)
# Source: rsf/registry/registry.py (discover_handlers, registered_states API)

from pathlib import Path
from rsf.dsl.parser import load_definition
from rsf.registry import discover_handlers, registered_states

EXAMPLE_ROOT = Path(__file__).parent.parent

class TestWorkflowParsing:
    """Verify workflow.yaml is parseable by RSF (TEST-01)."""

    def test_workflow_yaml_parses_without_error(self):
        """load_definition() succeeds on workflow.yaml."""
        definition = load_definition(EXAMPLE_ROOT / "workflow.yaml")
        assert definition is not None

    def test_workflow_start_at(self):
        """StartAt state is ValidateImage."""
        definition = load_definition(EXAMPLE_ROOT / "workflow.yaml")
        assert definition.start_at == "ValidateImage"

    def test_workflow_has_expected_states(self):
        """Workflow defines all 6 states (4 Task + Succeed + Fail)."""
        definition = load_definition(EXAMPLE_ROOT / "workflow.yaml")
        assert "ValidateImage" in definition.states
        assert "ResizeImage" in definition.states
        assert "AnalyzeContent" in definition.states
        assert "CatalogueImage" in definition.states
        assert "ProcessingComplete" in definition.states
        assert "ProcessingFailed" in definition.states

    def test_workflow_has_dynamodb_config(self):
        """workflow.yaml declares a DynamoDB table."""
        definition = load_definition(EXAMPLE_ROOT / "workflow.yaml")
        assert definition.dynamodb_tables is not None
        assert len(definition.dynamodb_tables) >= 1

    def test_workflow_has_dlq_config(self):
        """workflow.yaml declares a DLQ."""
        definition = load_definition(EXAMPLE_ROOT / "workflow.yaml")
        assert definition.dead_letter_queue is not None
        assert definition.dead_letter_queue.enabled is True


class TestHandlerRegistration:
    """Verify discover_handlers() registers all 4 handlers (TEST-01)."""

    def test_discover_handlers_registers_all_four(self):
        """All 4 handler state names are registered after discover_handlers()."""
        discover_handlers(EXAMPLE_ROOT / "handlers")
        states = registered_states()
        assert "ValidateImage" in states
        assert "ResizeImage" in states
        assert "AnalyzeContent" in states
        assert "CatalogueImage" in states

    def test_no_spurious_registrations(self):
        """discover_handlers() registers exactly 4 handlers (no __init__ leakage)."""
        discover_handlers(EXAMPLE_ROOT / "handlers")
        states = registered_states()
        assert len(states) == 4
```

### Pattern 2: Integration Test — rsf deploy subprocess (TEST-02, TEST-03)

**What:** Class-based integration test with `scope="class"` deployment fixture. The fixture runs `rsf generate`, then `rsf deploy`, reads terraform outputs to get alias ARN and function name, invokes Lambda, polls to SUCCEEDED, yields context for test methods, then runs teardown.

**When to use:** Integration gate requiring real AWS credentials.

```python
# Source: tests/test_examples/test_order_processing.py (class-based pattern)
# Source: tests/test_examples/conftest.py (make_execution_id, poll_execution, query_logs)

import subprocess
from pathlib import Path
from tests.test_examples.conftest import (
    EXAMPLES_ROOT, iam_propagation_wait, make_execution_id,
    poll_execution, query_logs,
)

EXAMPLE_DIR = EXAMPLES_ROOT / "registry-modules-demo"
TF_DIR = EXAMPLE_DIR / "terraform"

@pytest.fixture(scope="class")
def deployment(self, lambda_client, logs_client):
    # 1. Patch rsf.toml program path (fixture setup)
    rsf_toml_path = EXAMPLE_DIR / "rsf.toml"
    original_content = rsf_toml_path.read_text()
    real_deploy_sh = str(EXAMPLE_DIR / "deploy.sh")
    patched = original_content.replace(
        "/REPLACE/WITH/YOUR/ABSOLUTE/PATH/TO/examples/registry-modules-demo/deploy.sh",
        real_deploy_sh,
    )
    rsf_toml_path.write_text(patched)

    try:
        # 2. rsf generate — creates src/generated/
        subprocess.run(
            ["rsf", "generate", "workflow.yaml"],
            cwd=EXAMPLE_DIR, check=True, capture_output=True, text=True,
        )
        # 3. rsf deploy — runs custom provider pipeline (generates tfvars, tf init+apply)
        subprocess.run(
            ["rsf", "deploy", "workflow.yaml", "--auto-approve"],
            cwd=EXAMPLE_DIR, check=True, capture_output=True, text=True,
        )
    finally:
        rsf_toml_path.write_text(original_content)  # restore placeholder

    # 4. Read alias ARN from terraform output
    result = subprocess.run(
        ["terraform", "output", "-raw", "alias_arn"],
        cwd=TF_DIR, check=True, capture_output=True, text=True,
    )
    alias_arn = result.stdout.strip()

    result = subprocess.run(
        ["terraform", "output", "-raw", "function_name"],
        cwd=TF_DIR, check=True, capture_output=True, text=True,
    )
    function_name = result.stdout.strip()
    log_group = f"/aws/lambda/{function_name}"

    iam_propagation_wait()

    exec_id = make_execution_id("registry-modules-demo")
    start_time = datetime.now(timezone.utc)
    lambda_client.invoke(
        FunctionName=alias_arn,
        InvocationType="Event",
        Payload=json.dumps(HAPPY_EVENT),
        DurableExecutionName=exec_id,
    )
    execution = poll_execution(lambda_client, alias_arn, exec_id)

    yield {
        "execution": execution,
        "alias_arn": alias_arn,
        "function_name": function_name,
        "log_group": log_group,
        "start_time": start_time,
    }

    # Teardown (after yield) — handled by test_teardown_leaves_empty_state
    # Safety fallback: direct terraform destroy if rsf deploy --teardown failed
```

### Pattern 3: Teardown Verification (TEST-03)

**What:** Dedicated test method that runs `rsf deploy --teardown`, then verifies empty state via `terraform state list`.

**Critical detail:** The teardown test method must run LAST in the class (alphabetical name ordering or `pytest.mark.last`). Since teardown is also the fixture cleanup, the test asserts the teardown path while the fixture provides the safety net.

```python
def test_teardown_leaves_empty_state(self, deployment, logs_client):
    """rsf deploy --teardown produces empty terraform state (TEST-03)."""
    function_name = deployment["function_name"]
    log_group = deployment["log_group"]

    # Patch rsf.toml program path for teardown
    rsf_toml_path = EXAMPLE_DIR / "rsf.toml"
    original = rsf_toml_path.read_text()
    rsf_toml_path.write_text(original.replace(
        "/REPLACE/WITH/YOUR/ABSOLUTE/PATH/TO/examples/registry-modules-demo/deploy.sh",
        str(EXAMPLE_DIR / "deploy.sh"),
    ))

    teardown_ok = False
    try:
        subprocess.run(
            ["rsf", "deploy", "workflow.yaml", "--teardown", "--auto-approve"],
            cwd=EXAMPLE_DIR, check=True, capture_output=True, text=True,
        )
        teardown_ok = True
    finally:
        rsf_toml_path.write_text(original)
        if not teardown_ok:
            # Fallback: direct terraform destroy to prevent stuck resources
            subprocess.run(
                ["terraform", "destroy", "-auto-approve", "-input=false",
                 f"-var-file={TF_DIR}/terraform.tfvars.json"],
                cwd=TF_DIR, capture_output=True, text=True,
            )

    assert teardown_ok, "rsf deploy --teardown exited non-zero"

    # Verify empty state
    state_result = subprocess.run(
        ["terraform", "state", "list"],
        cwd=TF_DIR, capture_output=True, text=True,
    )
    assert state_result.stdout.strip() == "", (
        f"Orphaned resources after teardown:\n{state_result.stdout}"
    )

    # Clean up orphaned log group (established pattern)
    try:
        logs_client.delete_log_group(logGroupName=log_group)
    except logs_client.exceptions.ResourceNotFoundException:
        pass
```

### Anti-Patterns to Avoid
- **Importing rsf.cli.deploy_cmd directly:** Bypasses CLI error handling and doesn't test what users run. Use subprocess only.
- **Using `function_name` as FunctionName for Lambda invocation:** Must use `alias_arn` — the live alias is mandatory (Terraform provider issue #45800, AllowInvokeLatest unresolved).
- **Omitting rsf.toml patch:** `program = "/REPLACE/..."` will cause CustomProvider to raise FileNotFoundError before deploy.sh is invoked.
- **Relying on test_handlers.py covering TEST-01:** test_handlers.py covers handler business logic only. TEST-01 requires workflow YAML parsing and handler registration — that's test_local.py's scope.
- **Running teardown test before happy path test:** Teardown must be last — once state is destroyed, all other assertions become invalid.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Execution polling with backoff | Custom poll loop | `poll_execution()` from conftest.py | Already handles ThrottlingException backoff, TimeoutError, all terminal statuses |
| CloudWatch log queries | Direct boto3 start_query loop | `query_logs()` from conftest.py | Already handles propagation wait, retry on empty results, query completion polling |
| Unique execution IDs | String formatting | `make_execution_id()` from conftest.py | UUID suffix prevents collision across reruns |
| IAM propagation delay | `time.sleep(15)` inline | `iam_propagation_wait()` from conftest.py | Self-documenting, consistent across all integration tests |
| boto3 client setup | Per-test client creation | `lambda_client`, `logs_client` session fixtures from conftest.py | Shared session scope reduces API client overhead |

**Key insight:** The `tests/test_examples/conftest.py` harness solves all the timing and retry problems that naive integration tests encounter. Re-implementing any of these would introduce bugs already fixed in the harness.

## Common Pitfalls

### Pitfall 1: rsf.toml Program Path Placeholder
**What goes wrong:** `CustomProvider.deploy()` validates the `program` field — it checks the path is absolute, exists, and is executable. `/REPLACE/WITH/YOUR/ABSOLUTE/PATH/...` fails `FileNotFoundError` before `rsf generate` even runs.
**Why it happens:** The rsf.toml is intentionally left with a placeholder for tutorial users to fill in.
**How to avoid:** Before calling `subprocess.run(["rsf", "deploy", ...])`, patch rsf.toml to replace the placeholder with `str(EXAMPLE_DIR / "deploy.sh")`. Restore the placeholder after deploy (even on failure) so the tutorial file remains correct.
**Warning signs:** `subprocess.CalledProcessError` from `rsf deploy` with stderr mentioning "File not found" or "not executable".

### Pitfall 2: Invoking Lambda via function_name instead of alias_arn
**What goes wrong:** `lambda_client.invoke(FunctionName=function_name, ...)` without `InvocationType='Event'` and `DurableExecutionName` hits $LATEST or unqualified ARN — Terraform provider issue #45800 (AllowInvokeLatest unresolved). The invocation may succeed but durable execution won't start.
**Why it happens:** The alias "live" is the only supported invocation target for durable functions in this example.
**How to avoid:** Always read `alias_arn` from `terraform output -raw alias_arn` and use it as `FunctionName`.
**Warning signs:** `poll_execution()` times out — execution never appears in `list_durable_executions_by_function`.

### Pitfall 3: pyproject.toml testpaths excludes registry-modules-demo
**What goes wrong:** Running `pytest` from project root doesn't discover `examples/registry-modules-demo/tests/` — both test_handlers.py (existing) and test_local.py (new) are missed.
**Why it happens:** `pyproject.toml [tool.pytest.ini_options].testpaths` lists only specific example directories; registry-modules-demo is not in that list.
**How to avoid:** Add `"examples/registry-modules-demo/tests"` to `testpaths` in pyproject.toml. The integration test (`tests/test_examples/test_registry_modules_demo.py`) is already covered by `"tests"` in testpaths.
**Warning signs:** `pytest --collect-only` shows 0 tests from registry-modules-demo.

### Pitfall 4: terraform state list Non-Zero Exit When State Is Empty
**What goes wrong:** `terraform state list` returns exit code 0 with empty stdout when state is empty — but `check=True` is safe. However, if the Terraform backend is not initialized (terraform/ dir has no .terraform/), the command fails.
**Why it happens:** After `rsf deploy --teardown`, the .terraform/ directory still exists (from init), so state list works. But if run in a fresh environment, init is needed first.
**How to avoid:** Only run `terraform state list` in the teardown test method after a successful `rsf deploy --teardown` — at that point, `.terraform/` was already initialized by the terraform init step inside deploy.sh.
**Warning signs:** `terraform state list` fails with "No such file or directory" for `.terraform/terraform.tfstate`.

### Pitfall 5: Log Group Name Not in Terraform Outputs
**What goes wrong:** The `registry-modules-demo` terraform has no `log_group_name` output (unlike `order-processing`). Attempting `outputs["log_group_name"]` raises KeyError.
**Why it happens:** The terraform-aws-modules/lambda module creates the log group automatically via `attach_cloudwatch_logs_policy = true`, but the example only outputs `alias_arn`, `function_name`, `role_arn`, `dynamodb_table_arns`, `sqs_dlq_url`, `sns_alarm_topic_arn`.
**How to avoid:** Derive the log group name: `log_group = f"/aws/lambda/{function_name}"`. AWS Lambda always creates CloudWatch log groups in this format.
**Warning signs:** KeyError on `outputs["log_group_name"]`.

### Pitfall 6: Teardown Test Must Run Last
**What goes wrong:** If `test_teardown_leaves_empty_state` runs before `test_execution_succeeds` or `test_handler_log_entries`, those tests fail because the Lambda function no longer exists.
**Why it happens:** The deployment fixture is `scope="class"`, so setup runs once and teardown happens after the fixture is finalized. But if the teardown test is part of the class body, it runs during the "live infrastructure" phase.
**How to avoid:** Name the teardown test method `test_z_teardown_leaves_empty_state` (alphabetical ordering) so pytest runs it last in the class. Alternatively, move teardown to the fixture's cleanup phase (after `yield`) and remove it from test methods — but TEST-03 requires it to be a reportable test result.
**Warning signs:** `test_execution_succeeds` fails with `ResourceNotFoundException` or `FunctionDoesNotExist`.

### Pitfall 7: rsf generate Output Directory
**What goes wrong:** `rsf generate workflow.yaml` by default writes to `"."` (current directory) with handlers in `./handlers/`. But `deploy.sh` zips `src/generated/` — which is where the orchestrator goes when deploy calls `codegen_generate`.
**Why it happens:** `rsf deploy` internally calls `codegen_generate` with `output_dir=workflow.parent`, which puts orchestrator in `src/generated/`. But `rsf generate` as a standalone command uses `--output .` which puts it in the example root.
**How to avoid:** Per locked decision, run `rsf generate workflow.yaml` from `EXAMPLE_DIR` first (which creates `src/generated/`), then `rsf deploy` which also runs generate internally. The standalone `rsf generate` before `rsf deploy` ensures `src/generated/` exists before deploy.sh zips it. The `rsf deploy` internal codegen creates `src/generated/orchestrator.py` at `workflow.parent / "src" / "generated"` — confirm this matches deploy.sh's zip target.
**Warning signs:** `deploy.sh` zip step fails with "No such file or directory" for `src/generated/`.

## Code Examples

Verified patterns from project source:

### Parsing workflow YAML (test_local.py)
```python
# Source: src/rsf/dsl/parser.py
from rsf.dsl.parser import load_definition

definition = load_definition(EXAMPLE_ROOT / "workflow.yaml")
assert definition.start_at == "ValidateImage"
assert len(definition.states) == 6
```

### Discovering handlers and verifying registration (test_local.py)
```python
# Source: src/rsf/registry/registry.py
from rsf.registry import discover_handlers, registered_states

discover_handlers(EXAMPLE_ROOT / "handlers")
states = registered_states()
assert states == frozenset({"ValidateImage", "ResizeImage", "AnalyzeContent", "CatalogueImage"})
```

### RSF CLI subprocess invocation (integration test fixture)
```python
# Based on: tests/test_examples/conftest.py subprocess pattern
import subprocess

subprocess.run(
    ["rsf", "generate", "workflow.yaml"],
    cwd=EXAMPLE_DIR,
    check=True,
    capture_output=True,
    text=True,
)
subprocess.run(
    ["rsf", "deploy", "workflow.yaml", "--auto-approve"],
    cwd=EXAMPLE_DIR,
    check=True,
    capture_output=True,
    text=True,
)
```

### Reading terraform outputs after rsf deploy
```python
# Standard terraform output pattern
import subprocess, json

result = subprocess.run(
    ["terraform", "output", "-json"],
    cwd=TF_DIR,
    check=True,
    capture_output=True,
    text=True,
)
outputs = {k: v["value"] for k, v in json.loads(result.stdout).items()}
alias_arn = outputs["alias_arn"]
function_name = outputs["function_name"]
log_group = f"/aws/lambda/{function_name}"
```

### Lambda invocation via alias ARN (durable execution)
```python
# Source: tests/test_examples/test_order_processing.py (adapted for alias_arn)
import json
lambda_client.invoke(
    FunctionName=alias_arn,         # alias ARN, not function_name (issue #45800)
    InvocationType="Event",
    Payload=json.dumps(HAPPY_EVENT),
    DurableExecutionName=exec_id,
)
execution = poll_execution(lambda_client, alias_arn, exec_id)
assert execution["Status"] == "SUCCEEDED"
```

### Teardown verification via terraform state list
```python
# Pattern: subprocess in terraform/ dir after rsf deploy --teardown
result = subprocess.run(
    ["terraform", "state", "list"],
    cwd=TF_DIR,
    capture_output=True,
    text=True,
)
assert result.stdout.strip() == "", f"Orphaned resources:\n{result.stdout}"
```

### CloudWatch log assertion pattern
```python
# Source: tests/test_examples/test_order_processing.py
query = "fields @message | filter @message like /step_name/ | sort @timestamp asc"
results = query_logs(logs_client, log_group, query, start_time)
messages = " ".join(
    next((f["value"] for f in row if f["field"] == "@message"), "")
    for row in results
)
for handler in ("ValidateImage", "ResizeImage", "AnalyzeContent", "CatalogueImage"):
    assert handler in messages, f"Handler '{handler}' not found in CloudWatch logs"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Direct terraform_deploy() for integration tests | rsf deploy subprocess for custom provider tests | Phase 59 (new) | Tests the full custom provider pipeline end-to-end, not just terraform |
| Unqualified function ARN for Lambda invocation | Alias ARN "live" mandatory | Phase 56 (decided) | Workaround for Terraform provider issue #45800 |
| Log group name from terraform outputs | Derived: `/aws/lambda/{function_name}` | Phase 59 (no output defined) | registry-modules-demo tf has no log_group_name output |

**Key differences from order-processing integration test:**
- Deployment: `rsf deploy` subprocess vs `terraform_deploy()` helper
- Invocation target: `alias_arn` vs `function_name`
- Teardown: `rsf deploy --teardown` subprocess + state list assertion vs `terraform_teardown()` helper
- Log group: derived from function_name vs explicit terraform output

## Open Questions

1. **rsf generate output directory vs deploy.sh zip target**
   - What we know: `rsf deploy` calls `codegen_generate(output_dir=workflow.parent)` which places orchestrator at `{example_root}/src/generated/orchestrator.py`. deploy.sh zips `src/generated/`.
   - What's unclear: Does the standalone `rsf generate workflow.yaml` (run from EXAMPLE_DIR) place the orchestrator in `src/generated/` or the example root?
   - Recommendation: The planner should verify by checking `generate_cmd.py` output_dir default — it defaults to `"."` with handlers in `./handlers/`. The `rsf deploy` internal codegen should create `src/generated/`. Running `rsf generate` first may be redundant if `rsf deploy` already generates. The locked decision says "Run `rsf generate` first" — follow it, but verify during Wave 0 that src/generated/ is created correctly.

2. **rsf.toml patch strategy — test isolation vs shared state**
   - What we know: The fixture must patch rsf.toml before `rsf deploy` and restore it after. If tests run in parallel, two concurrent patches would conflict.
   - What's unclear: Does the project run integration tests in parallel?
   - Recommendation: Given `scope="class"` fixtures and single-class integration test, no parallelism concern. Write-restore pattern is sufficient.

3. **Happy path event payload**
   - What we know: ValidateImage accepts `{image_id, format, size_bytes}` where format in {jpeg, png, webp, gif} and size_bytes <= 10MB. Happy path goes ValidateImage -> ResizeImage -> AnalyzeContent -> CatalogueImage -> ProcessingComplete.
   - What's unclear: ResizeImage requires `{image_id, width, height, target_width}` — the happy path event must include all fields needed by all handlers, or handlers must gracefully handle missing fields.
   - Recommendation: Use `{"image_id": "test-001", "format": "jpeg", "size_bytes": 1048576, "width": 1920, "height": 1080, "target_width": 960}` — covers all handler input shapes.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed, project-wide) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest examples/registry-modules-demo/tests/ -v` |
| Full suite command | `pytest examples/registry-modules-demo/tests/ tests/test_examples/test_registry_modules_demo.py -v -m "not integration"` for local; add `-m integration` for AWS |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEST-01 | Workflow YAML parsing | unit | `pytest examples/registry-modules-demo/tests/test_local.py -v` | ❌ Wave 0 |
| TEST-01 | Handler registration | unit | `pytest examples/registry-modules-demo/tests/test_local.py -v` | ❌ Wave 0 |
| TEST-01 | Handler business logic (existing) | unit | `pytest examples/registry-modules-demo/tests/test_handlers.py -v` | ✅ |
| TEST-02 | Deploy + invoke + poll SUCCEEDED | integration | `pytest tests/test_examples/test_registry_modules_demo.py -v -m integration -k "not teardown"` | ❌ Wave 0 |
| TEST-02 | CloudWatch log assertions | integration | `pytest tests/test_examples/test_registry_modules_demo.py -v -m integration -k "log"` | ❌ Wave 0 |
| TEST-03 | Teardown via custom provider + empty state | integration | `pytest tests/test_examples/test_registry_modules_demo.py -v -m integration -k "teardown"` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest examples/registry-modules-demo/tests/ -v -m "not integration"`
- **Per wave merge:** `pytest examples/registry-modules-demo/tests/ tests/test_examples/ -v -m "not integration"`
- **Phase gate:** Full suite including integration: `pytest tests/test_examples/test_registry_modules_demo.py -v -m integration`

### Wave 0 Gaps
- [ ] `examples/registry-modules-demo/tests/test_local.py` — covers TEST-01 (workflow parsing + handler registration)
- [ ] `tests/test_examples/test_registry_modules_demo.py` — covers TEST-02, TEST-03
- [ ] `pyproject.toml` testpaths must add `"examples/registry-modules-demo/tests"` — currently missing

## Sources

### Primary (HIGH confidence)
- `tests/test_examples/conftest.py` — poll_execution, query_logs, make_execution_id, iam_propagation_wait, terraform helpers (read directly)
- `tests/test_examples/test_order_processing.py` — class-based integration test reference pattern (read directly)
- `examples/registry-modules-demo/tests/conftest.py` — existing conftest with path setup + registry clear (read directly)
- `examples/registry-modules-demo/tests/test_handlers.py` — 16 existing handler tests (read directly)
- `examples/registry-modules-demo/workflow.yaml` — 6 states, 4 Task handlers, DynamoDB + DLQ config (read directly)
- `examples/registry-modules-demo/terraform/outputs.tf` — outputs available: alias_arn, function_name, no log_group_name (read directly)
- `examples/registry-modules-demo/deploy.sh` — deploy/destroy dispatch, generate_tfvars, terraform init+apply (read directly)
- `src/rsf/registry/registry.py` — discover_handlers, registered_states, clear API (read directly)
- `src/rsf/dsl/parser.py` — load_definition, load_yaml API (read directly)
- `pyproject.toml` testpaths — registry-modules-demo NOT currently in testpaths (read directly)

### Secondary (MEDIUM confidence)
- `src/rsf/cli/deploy_cmd.py` — deploy/teardown dispatch, confirms --auto-approve flag (read directly)
- `src/rsf/config.py` — confirms rsf.toml program field validation path (read directly)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are installed project dependencies, verified by reading pyproject.toml and existing test files
- Architecture: HIGH — derived directly from existing test patterns in conftest.py and test_order_processing.py
- Pitfalls: HIGH — derived from code inspection of rsf.toml placeholder, outputs.tf (no log_group_name), pyproject.toml testpaths, and project decisions (issue #45800)
- Validation architecture: HIGH — test framework and existing test infrastructure confirmed by direct file reads

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (stable domain — pytest + boto3 + rsf internals)
