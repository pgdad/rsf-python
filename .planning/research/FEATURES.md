# Feature Research

**Domain:** Integration test harness and use-case based examples for RSF (Lambda Durable Functions state machine framework)
**Researched:** 2026-02-26
**Confidence:** HIGH (boto3 APIs verified against official docs; SDK patterns verified against AWS GitHub repos; existing RSF code inspected directly)

---

## Context: This Is a Subsequent Milestone

RSF v1.1 is complete. The full DSL, code generator, Terraform generator, and CLI toolchain exist and work. This milestone (v1.2) adds:

1. Real-world use-case based example workflows (full artifacts: DSL YAML + handlers + Terraform files)
2. An automated test harness that deploys, invokes, verifies, and tears down each example in AWS

The feature map below distinguishes table stakes (what a credible v1.2 requires), differentiators (what makes the examples useful beyond coverage), and anti-features (scope traps to avoid).

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that make the v1.2 milestone credible. Missing any of these means the milestone is incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Complete example artifacts (DSL YAML + handlers.py + Terraform) | Without all three, the example cannot be deployed; RSF's core promise is end-to-end | MEDIUM | Each example uses `rsf generate` output as the scaffold; handler code must be real (not stubs) |
| Coverage of all 8 state types across example set | The DSL supports 8 types; examples must prove all work end-to-end | LOW | Can be spread across multiple examples; one example per type not required |
| Coverage of error handling (Retry + Catch) | Error handling is the most-used production feature; absent = incomplete | MEDIUM | Needs a handler that actually raises exceptions so retries/catches fire |
| Coverage of I/O processing pipeline (InputPath, Parameters, ResultSelector, ResultPath, OutputPath) | I/O pipeline is non-trivial generated code; must be verified via real execution | MEDIUM | Verify that the final Lambda return value reflects correct I/O transformation |
| Automated deploy-invoke-verify-teardown cycle | Core value proposition of v1.2; manual steps = not an integration test | HIGH | Uses boto3 `lambda.invoke(InvocationType='Event')`, then polls `ListDurableExecutionsByFunction` |
| Dual verification: Lambda return value + CloudWatch logs | Return value verifies workflow output; CW logs verify intermediate state transitions | MEDIUM | CloudWatch verification uses `filter_log_events` with structured JSON log patterns |
| Single-command test runner | Developers must be able to run all integration tests with one command | MEDIUM | pytest with session-scoped fixture for Terraform deploy/destroy |
| Real AWS execution (not mocked) | v1.2 is about end-to-end, not local mocks; local mock tests already exist in v1.0 | LOW | Requires AWS credentials; Terraform apply before tests, destroy after |
| Teardown on failure | Leaked AWS resources = cost and confusion | LOW | pytest fixture with `yield` + `terraform destroy -auto-approve` in the teardown block |

### Differentiators (Competitive Advantage)

Features that make the examples genuinely useful as documentation and reference material, not just test coverage.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Real-world scenario framing (order processing, data pipeline, etc.) | Readers understand why each state type exists; abstract "TestWorkflow1" teaches nothing | LOW | Naming matters; "OrderValidation" beats "ChoiceExample" |
| One example with DynamoDB integration | Proves RSF works with real AWS service calls inside handlers; establishes the pattern for service-integrated workflows | MEDIUM | DynamoDB is the simplest stateful service; PutItem + GetItem in handlers suffices |
| Intrinsic function coverage inside real execution | 18 intrinsic functions are tested locally; real execution under checkpoint/replay exposes bugs that mocks miss | MEDIUM | Use States.Format, States.Array, States.JsonMerge, States.MathAdd in Pass state Parameters |
| Variables/Assign/Output coverage in a deployed workflow | Assign is generated as Python dict mutation; real execution verifies the generated code path is correct | LOW | One workflow using Assign and Output is sufficient |
| Context Object (`$$`) coverage | `$$` references `$$.Execution.Id` etc.; real execution provides real values, exposing bugs mocks cannot | LOW | Include one Choice rule that uses `$$.Execution.StartTime` or similar |
| Parallel and Map state coverage with verifiable output | Parallel and Map use `BatchResult.get_results()`; the test must assert the list shape and values | MEDIUM | Map handler can multiply each item by a constant; output is a deterministic list |
| Structured logging in handlers (`import logging; logging.info(json.dumps({...}))`) | Makes CloudWatch log verification reliable; grep for JSON keys instead of text parsing | LOW | Handlers emit structured JSON logs; test uses `filter_log_events` with filterPattern |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem useful for v1.2 but create disproportionate cost or risk.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| LocalStack-based testing | Avoids real AWS cost; faster | LocalStack's durable execution support is unverified for this SDK; durable functions are a brand-new feature (re:Invent 2025) — emulation fidelity is unknown | Use real AWS with per-example teardown to bound cost; durable execution steps are cheap |
| One example per feature (39 examples for 39 operators) | Maximum granularity | Combinatorial explosion; most comparison operators differ only in type (StringGreaterThan vs NumericGreaterThan); testing all 39 in isolation has diminishing returns | Cover all 6 operator families (String, Numeric, Boolean, Timestamp, Type-check, Path-suffix) via one Choice-heavy example; that's 6 branches, not 39 tests |
| Shared Terraform state across all examples | Simplifies apply/destroy | If one example's deploy fails, it blocks all others; destroy is harder to target; state file conflicts in parallel CI | Per-example Terraform directory with independent state; more files, zero coupling |
| Parallel CI execution of integration tests | Faster CI | Multiple concurrent Terraform applies against same account hit IAM and Lambda rate limits (15 req/s Lambda control plane); deploy conflicts likely | Run integration tests sequentially; deploy time per example is small (< 60s) |
| Ephemeral Lambda function names per test run | Avoids name collision between runs | Adds complexity; requires dynamic name injection into Terraform; names become unguessable in the console | Use stable, well-known function names per example (e.g., `rsf-example-order-processing`); protect with `rsf-example-` prefix convention |
| Integration test coverage of the CLI commands (rsf deploy, rsf validate) | CLI tests already exist | CLI integration is a separate concern from workflow behavior; mixing them makes tests slower and harder to diagnose | CLI commands are covered by v1.1 test suite; v1.2 tests focus on workflow execution behavior |
| Wait state with real time delays | Proves Wait works end-to-end | A Wait of even 30 seconds makes CI impractical; 1-year waits are the feature, not the test target | Use Pass state to represent the "what happens after a wait" path; document that Wait produces correct checkpoint behavior but skip real-time delay in integration tests |
| Failure-injection testing (chaos testing) | Validates retry behavior | Requires handler code that deterministically fails N times then succeeds; this is complex to wire reliably in real Lambda | Cover retry/catch by raising a custom exception in a handler and verifying the Catch branch fires; simpler and deterministic |

---

## Feature Dependencies

```
[Terraform deploy automation]
    └──requires──> [Per-example Terraform directory structure]
                       └──requires──> [rsf generate output as scaffold]
                                          └──requires──> [DSL YAML authoring (existing)]

[CloudWatch log verification]
    └──requires──> [Structured JSON logging in handlers]
    └──requires──> [Known execution ID from ListDurableExecutionsByFunction]

[Lambda return value verification]
    └──requires──> [Async invoke (InvocationType=Event)]
    └──requires──> [Poll ListDurableExecutionsByFunction until SUCCEEDED/FAILED]
    └──requires──> [GetDurableExecutionState to retrieve EXECUTION operation result]

[DynamoDB integration example]
    └──requires──> [IAM role with DynamoDB permissions in Terraform]
    └──requires──> [DynamoDB table Terraform resource in example's tf directory]

[Context Object coverage]
    └──enhances──> [Choice state example]
    (Choice rule using $$.Execution.Id verifies context is populated in real execution)

[Variables/Assign coverage]
    └──enhances──> [Task or Pass state in any example]
    (Assign sets workflow-level variables; Output controls what flows to next state)

[Parallel coverage]
    └──requires──> [BatchResult.get_results() call in orchestrator]
    └──enhances──> [Order processing example]
    (Pay + reserve + notify in parallel is the canonical use case)
```

### Dependency Notes

- **CloudWatch log verification requires structured logging:** Unstructured log lines are fragile to parse in tests. Handlers must emit `logging.info(json.dumps({"state": "...", "step": "...", "value": ...}))` so tests can use `filterPattern='{ $.state = "X" }'` in `filter_log_events`.

- **Async poll loop requires ListDurableExecutionsByFunction:** The durable invoke is `InvocationType='Event'` (fire-and-forget). The test must call `lambda_client.list_durable_executions_by_function(FunctionName=..., Statuses=['RUNNING', 'SUCCEEDED', 'FAILED'])` in a polling loop with a timeout (suggested: 120s poll interval 2s). Terminal statuses are `SUCCEEDED`, `FAILED`, `TIMED_OUT`, `STOPPED`.

- **GetDurableExecutionState requires CheckpointToken + ARN:** This API is used by the SDK internally for replay. For testing, use the `DurableExecutionArn` from `ListDurableExecutionsByFunction` response and inspect the `Operations` list for the `EXECUTION` type to get the final result.

- **Per-example terraform directories prevent teardown coupling:** Each example lives in `examples/<name>/terraform/`; each test fixture `cd`s to that directory for `terraform apply` and `terraform destroy`.

---

## Example Coverage Matrix

This matrix shows how 5-6 examples can cover all 8 state types, all 6 operator families, 18 intrinsic functions, error handling, I/O processing, variables, and context objects without testing every permutation individually.

| Example | Primary Use Case | State Types | Operator Families | Intrinsic Functions | Error Handling | I/O Pipeline | Variables/Assign | Context Object | AWS Services |
|---------|-----------------|-------------|-------------------|---------------------|----------------|--------------|------------------|----------------|--------------|
| `order-processing` | E-commerce order flow | Task, Choice, Parallel, Succeed, Fail | NumericGreaterThan, StringEquals, BooleanEquals | States.Format, States.MathAdd | Retry on payment, Catch to Fail | InputPath, ResultPath | Assign order ID | No | None (compute-only) |
| `data-pipeline` | ETL-style batch processing | Task, Pass, Map, Succeed | IsPresent, IsNumeric, StringMatches | States.Array, States.ArrayPartition, States.ArrayLength | Catch on map item failure | Parameters, ResultSelector, OutputPath | Assign batch metadata | No | DynamoDB (PutItem + GetItem) |
| `approval-workflow` | Human-in-the-loop (simulated) | Task, Wait, Choice, Pass, Succeed, Fail | TimestampGreaterThan, BooleanEquals | States.JsonMerge, States.StringToJson | Retry on Task, Catch to Fail | InputPath, OutputPath | Assign approval state | `$$.Execution.Id` in Choice | None |
| `retry-and-recovery` | Fault-tolerant service call | Task, Choice, Pass, Succeed, Fail | StringEqualsPath, NumericLessThanEquals | States.Format, States.MathRandom | Retry with BackoffRate + JitterStrategy, multi-Catch | ResultPath for error, OutputPath | No | No | None |
| `intrinsic-showcase` | Function coverage | Pass, Task, Succeed | StringGreaterThanEquals, IsString, IsBoolean | States.ArrayContains, States.ArrayGetItem, States.ArrayRange, States.ArrayUnique, States.StringSplit, States.JsonToString, States.MathRandom, States.MathAdd | No | Parameters (all 5 I/O fields in one state) | Output field | No | None |

**Coverage summary across all 5 examples:**

- State types: Task (all), Pass (all), Choice (all), Wait (approval), Parallel (order), Map (data-pipeline), Succeed (all), Fail (all) = **8/8**
- Operator families: String, Numeric, Boolean, Timestamp, Type-check, Path-suffix variants = **all 6 families represented** (subset of 39 operators; representative, not exhaustive)
- Intrinsic functions: ~14 of 18 explicitly exercised; remaining 4 (States.Base64Encode, States.Base64Decode, States.Hash, States.UUID) covered by local unit tests in v1.0 = **14 in integration + 4 in unit**
- Error handling: Retry with BackoffRate + MaxDelaySeconds + JitterStrategy = **covered**; multi-Catch = **covered**
- I/O pipeline: All 5 fields (InputPath, Parameters, ResultSelector, ResultPath, OutputPath) = **covered**
- Variables/Assign/Output: **covered** in order-processing and approval-workflow
- Context Object ($$): **covered** in approval-workflow via `$$.Execution.Id`
- AWS service integration: DynamoDB in data-pipeline = **1 example**

---

## MVP Definition

### Launch With (v1.2)

Minimum needed to call v1.2 complete and credible.

- [ ] 5 example workflows, each with complete DSL YAML + handlers.py + Terraform files — covers all 8 state types and major feature surface
- [ ] 1 of the 5 examples uses DynamoDB to demonstrate real AWS service integration
- [ ] Automated pytest-based test harness with session-scoped Terraform fixture (apply before, destroy after)
- [ ] Async invoke + poll loop using `ListDurableExecutionsByFunction` until terminal status
- [ ] Dual verification per example: assert on Lambda return value AND assert on CloudWatch log content
- [ ] Structured JSON logging in all handler files so CW log assertions are reliable
- [ ] Single command: `pytest tests/integration_aws/ -v` runs all examples

### Add After Validation (v1.2.x)

- [ ] CI workflow (GitHub Actions) that runs integration tests on merge to main — add when examples are stable and cost is understood
- [ ] Coverage report mapping examples to DSL features — add if users report difficulty understanding what each example tests
- [ ] Second AWS service example (e.g., SQS or S3) — add when DynamoDB example is validated and demand exists

### Future Consideration (v2+)

- [ ] LocalStack support — defer until LocalStack confirms durable execution compatibility
- [ ] Parallel CI execution of integration tests — defer until per-example cost and timing is understood
- [ ] Example for Callback pattern (waitForTaskToken equivalent) — defer; not yet in RSF DSL scope

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| 5 use-case examples (DSL + handlers + Terraform) | HIGH | MEDIUM | P1 |
| Automated deploy-verify-teardown harness | HIGH | HIGH | P1 |
| Dual verification (return value + CW logs) | HIGH | MEDIUM | P1 |
| Structured JSON logging in handlers | HIGH | LOW | P1 |
| DynamoDB integration example | MEDIUM | MEDIUM | P1 |
| Context Object (`$$`) in real execution | MEDIUM | LOW | P1 |
| Single-command test runner | HIGH | LOW | P1 |
| Per-example independent Terraform state | HIGH | LOW | P1 |
| CI/CD workflow for integration tests | MEDIUM | MEDIUM | P2 |
| Coverage report / feature-to-example map | LOW | LOW | P2 |
| Second AWS service example (SQS/S3) | LOW | MEDIUM | P3 |
| LocalStack support | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for v1.2 launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Integration Test Harness: Technical Decisions

These decisions are informed by the API research above and directly affect implementation.

### Invocation Pattern (MEDIUM confidence — confirmed via official docs)

```python
# 1. Invoke asynchronously (returns immediately, 202 accepted)
lambda_client.invoke(
    FunctionName="rsf-example-order-processing:$LATEST",
    InvocationType="Event",
    Payload=json.dumps({"orderId": "test-001", "amount": 250}),
)

# 2. Poll for terminal status (SUCCEEDED | FAILED | TIMED_OUT | STOPPED)
def poll_for_completion(lambda_client, function_name, started_after, timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = lambda_client.list_durable_executions_by_function(
            FunctionName=function_name,
            StartedAfter=started_after,
            Statuses=["SUCCEEDED", "FAILED", "TIMED_OUT", "STOPPED"],
            MaxItems=1,
        )
        executions = resp.get("DurableExecutions", [])
        if executions:
            return executions[0]  # Has DurableExecutionArn, Status, StartTimestamp
        time.sleep(2)
    raise TimeoutError(f"Execution did not complete within {timeout}s")
```

**Note:** `ListDurableExecutionsByFunction` returns `DurableExecutionArn`, `Status`, `StartTimestamp`, `EndTimestamp`. Filtering by `StartedAfter` (timestamp from before the invoke call) isolates the specific test run's execution.

### Result Retrieval (LOW confidence — `GetDurableExecutionState` is an internal SDK API)

The `GetDurableExecutionState` API (boto3: `get_durable_execution_state`) is used by the SDK internally for checkpoint replay. Using it for test result extraction is technically possible but undocumented for external use. **Recommended alternative:** Emit the final result as a structured CloudWatch log entry in the orchestrator's last step, then verify via `filter_log_events`. The `DurableFunctionCloudTestRunner` from `aws-durable-execution-sdk-python-testing` wraps this pattern; consider using it instead of reinventing the poll loop.

### CloudWatch Log Verification (HIGH confidence — boto3 `filter_log_events` is stable)

```python
def assert_log_contains(logs_client, log_group, filter_pattern, start_time_ms):
    resp = logs_client.filter_log_events(
        logGroupName=f"/aws/lambda/rsf-example-order-processing",
        filterPattern=filter_pattern,  # e.g., '{ $.step = "ValidateOrder" }'
        startTime=start_time_ms,
    )
    assert len(resp["events"]) > 0, f"No log events matched {filter_pattern!r}"
```

Handlers must emit structured JSON: `logging.info(json.dumps({"step": "ValidateOrder", "result": "ok"}))`. CloudWatch structured log filtering (`{ $.key = "value" }` syntax) is stable and well-documented.

### Terraform Lifecycle (HIGH confidence — established pattern)

```python
@pytest.fixture(scope="session")
def deployed_order_processing(tmp_path_factory):
    tf_dir = Path("examples/order-processing/terraform")
    subprocess.run(["terraform", "init"], cwd=tf_dir, check=True)
    subprocess.run(["terraform", "apply", "-auto-approve"], cwd=tf_dir, check=True)
    yield  # tests run here
    subprocess.run(["terraform", "destroy", "-auto-approve"], cwd=tf_dir, check=True)
```

Session scope ensures one deploy per test session. Each example gets its own fixture so failures are isolated.

---

## Competitor Feature Analysis

This is not a competitive product; the "competitors" are AWS Step Functions and the existing RSF v1.0 local test suite.

| Feature | AWS Step Functions | RSF v1.0 local tests | RSF v1.2 integration tests (this milestone) |
|---------|-------------------|---------------------|----------------------------------------------|
| Real AWS execution | Yes | No (MockDurableContext) | Yes |
| CloudWatch log verification | Manual | Not applicable | Automated via filter_log_events |
| Terraform deploy/teardown automation | No (console-based) | No | Yes (pytest session fixture) |
| Use-case based example library | Limited (Serverless Patterns) | No | Yes (5 real-world examples) |
| DynamoDB integration | Yes | No | Yes (1 example) |

---

## Sources

- [ListDurableExecutionsByFunction API](https://docs.aws.amazon.com/lambda/latest/api/API_ListDurableExecutionsByFunction.html) — confirmed status values (RUNNING, SUCCEEDED, FAILED, TIMED_OUT, STOPPED) and response structure — HIGH confidence
- [GetDurableExecutionState API (boto3)](https://docs.aws.amazon.com/boto3/latest/reference/services/lambda/client/get_durable_execution_state.html) — operation status values (STARTED, PENDING, READY, SUCCEEDED, FAILED, CANCELLED, TIMED_OUT, STOPPED) — MEDIUM confidence (internal SDK use)
- [Invoking durable Lambda functions (AWS docs)](https://docs.aws.amazon.com/lambda/latest/dg/durable-invoking.html) — InvocationType=Event invocation pattern — HIGH confidence
- [Testing Lambda durable functions (AWS docs)](https://docs.aws.amazon.com/lambda/latest/dg/durable-testing.html) — local vs cloud testing modes, DurableFunctionCloudTestRunner — MEDIUM confidence
- [aws-durable-execution-sdk-python-testing (GitHub)](https://github.com/aws/aws-durable-execution-sdk-python-testing) — cloud runner polls until completion, result verification — MEDIUM confidence
- [aws-durable-execution-sdk-python testing-modes.md](https://github.com/aws/aws-durable-execution-sdk-python/blob/main/docs/advanced/testing-modes.md) — local vs cloud runner pattern, InvocationStatus enum — MEDIUM confidence
- [Monitoring durable functions (AWS docs)](https://docs.aws.amazon.com/lambda/latest/dg/durable-monitoring.html) — CloudWatch metrics (DurableExecutionSucceeded etc), EventBridge status change events — HIGH confidence
- [aws-samples/sample-ai-workflows-in-aws-lambda-durable-functions (GitHub)](https://github.com/aws-samples/sample-ai-workflows-in-aws-lambda-durable-functions) — real-world workflow pattern examples (prompt chaining, parallel, human review, map) — MEDIUM confidence
- [pytest-terraform plugin](https://github.com/cloud-custodian/pytest-terraform) — session-scoped fixture pattern, terraform apply/destroy teardown — HIGH confidence
- RSF source code (direct inspection): `/home/esa/git/rsf-python/src/rsf/`, `/home/esa/git/rsf-python/fixtures/`, `/home/esa/git/rsf-python/tests/` — HIGH confidence

---

*Feature research for: RSF v1.2 — Examples and Integration Testing*
*Researched: 2026-02-26*
