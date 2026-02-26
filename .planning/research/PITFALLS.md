# Pitfalls Research

**Domain:** Automated integration testing for Lambda Durable Functions workflows
**Researched:** 2026-02-26
**Confidence:** HIGH (core pitfalls); MEDIUM (cost/billing specifics)

---

## Critical Pitfalls

### Pitfall 1: Treating Event-Invocation Like Synchronous — No Polling

**What goes wrong:**
Lambda Durable Functions must be invoked with `InvocationType=Event` (async). The invoke call returns immediately with HTTP 202 — there is no return value in the response body. Tests that call `lambda.invoke()` and immediately read the response payload get an empty result and assume the workflow completed, producing false positives.

**Why it happens:**
Developers used to synchronous Lambda testing (RequestResponse invocation type) apply the same pattern. The boto3 call succeeds with no error, so the test appears to pass.

**How to avoid:**
1. Always use `InvocationType='Event'` for durable function invocations.
2. After invoke, enter a polling loop calling `lambda.list_durable_executions_by_function()` with the function name and execution identifier.
3. Poll only for terminal states: `SUCCEEDED`, `FAILED`, `TIMED_OUT`, `STOPPED`.
4. Never assert on return value of the invoke call itself — it will always be empty.
5. Build a `poll_until_complete(function_name, execution_id, timeout_seconds, interval_seconds)` helper shared by all example tests.

**Warning signs:**
- Tests complete in under 2 seconds for workflows that should take 10+
- Test assertions always pass regardless of handler logic
- No IAM `lambda:ListDurableExecutionsByFunction` permission errors — those only surface when you actually call the polling API

**Phase to address:**
Test harness phase (before any example tests are written). The polling helper must exist and be validated before it can be used.

---

### Pitfall 2: Polling Interval Too Aggressive — Lambda Control Plane Rate Limit

**What goes wrong:**
The Lambda control plane enforces a 15 req/s rate limit. The existing inspector already uses a token bucket limited to 12 req/s. An integration test harness that polls `list_durable_executions_by_function` every second across multiple concurrent examples will hit 429 ThrottlingException, causing flaky test failures that look like network errors.

**Why it happens:**
Each "check if done" loop call counts against the same per-account rate limit that the inspector and any other Lambda API calls share. Running 5 examples in parallel, each polling once per second, equals 5 req/s from testing alone, on top of whatever the inspector adds.

**How to avoid:**
1. Set polling interval to 3-5 seconds minimum (not 1 second).
2. Run examples sequentially by default (not parallel) to stay well under limits.
3. Add exponential backoff on ThrottlingException in the polling loop.
4. Catch `botocore.exceptions.ClientError` with `ErrorCode == 'TooManyRequestsException'` and back off before retrying.
5. Document the 15 req/s account-level limit in test harness code comments.

**Warning signs:**
- `TooManyRequestsException` or HTTP 429 from the Lambda API during polling
- Tests that pass in isolation but fail when run together
- Intermittent `ThrottlingException` in CloudWatch dashboard

**Phase to address:**
Test harness phase. The polling helper must implement backoff before any examples exercise it.

---

### Pitfall 3: CloudWatch Log Propagation Delay — Asserting on Logs Too Early

**What goes wrong:**
CloudWatch Logs has a propagation delay of ~5-30 seconds between when a Lambda function emits a log line and when that log line appears in `filter_log_events`. Tests that use log content for intermediate state verification (e.g., "did handler X execute") and call `filter_log_events` immediately after the durable execution reaches `SUCCEEDED` status get empty results and either fail or return a false negative.

**Why it happens:**
The execution completion signal (SUCCEEDED state from polling API) arrives before logs are queryable. Log ingestion is eventually consistent. The median is under 9 seconds but worst-case is 30+ seconds, especially for cold-start invocations where the Lambda runtime flushes buffers late.

**How to avoid:**
1. After detecting SUCCEEDED state, always wait a fixed propagation buffer of 15 seconds before querying logs.
2. Use retry loops (not a single check) when querying logs: poll `filter_log_events` up to N times with 5-second intervals.
3. Prefer verifying workflow output (the Lambda return value retrieved via `get_durable_execution`) over log content — return values are immediately available on SUCCEEDED.
4. Use logs only for intermediate state verification where return values cannot carry the information.
5. Set `startTime` in `filter_log_events` to the invocation timestamp to avoid scanning unrelated prior log entries.

**Warning signs:**
- Tests pass when run manually (developer watches progress) but fail in CI (automated, no waiting)
- Log assertions that sometimes fail on first run but pass on retry
- Empty `events` array from `filter_log_events` immediately after execution completion

**Phase to address:**
Test harness phase (design the log verification helper with built-in delay). Also, example creation phase — structure handlers to emit verifiable log lines at specific points, and prefer output-based verification over log-based.

---

### Pitfall 4: Shared Terraform State Across Examples — State File Collisions

**What goes wrong:**
If multiple examples share a single `terraform.tfstate` file (local state or same S3 key), running `terraform apply` for one example affects another. `terraform destroy` for one example can destroy resources needed by another. Partial failures leave the state file in an inconsistent mixed state. Re-running apply after a failed destroy attempts to recreate resources that still exist, producing `ResourceConflictException`.

**Why it happens:**
The RSF Terraform generator defaults to a single state backend configuration. It is tempting to initialize one Terraform workspace and run all examples from it rather than using per-example isolation.

**How to avoid:**
1. Each example must have its own Terraform working directory with its own `terraform.tfstate` (or distinct S3 key if using remote state).
2. Name all AWS resources with an example-specific prefix (e.g., `rsf-example-order-processing-` not `rsf-`).
3. Test harness `terraform init` and `terraform apply` commands must `cd` to each example's directory in isolation — never run from a shared root.
4. For CI: generate a unique suffix per test run (e.g., UUID or git SHA) to prevent cross-run collisions if a prior run's destroy failed.

**Warning signs:**
- `terraform plan` shows changes to resources from a different example
- `ResourceConflictException: Function already exists` on `terraform apply`
- `destroy` succeeds per Terraform but resources from a different example are also deleted

**Phase to address:**
Examples creation phase (directory structure must be decided before any example is written). Each example directory must be fully self-contained.

---

### Pitfall 5: `durable_config` Cannot Be Added to Existing Lambda Functions

**What goes wrong:**
AWS does not allow enabling durable execution on an existing Lambda function. If a test deploys a function without `durable_config`, then a subsequent `terraform apply` adds `durable_config`, Terraform must destroy and recreate the function. This triggers a replacement cycle that deletes the CloudWatch log group (losing logs), resets IAM propagation, and causes a cold start on the new function. In CI, this means test runs that partially apply then fail leave behind undurable Lambda functions that block retries.

**Why it happens:**
Iterative development — developers prototype the handler first without durable config, then add it. Or a copy-paste from non-durable Terraform templates omits the block.

**How to avoid:**
1. Every example's `main.tf` must include `durable_config` from the very first `terraform apply`. No incremental enablement.
2. The RSF Terraform generator already includes `durable_config` in its `main.tf.j2` template — always use generated files, never hand-edit to remove this block.
3. Treat any Lambda function missing `durable_config` as misconfigured — add a pre-deploy validation check in the test harness.
4. If a function exists without `durable_config`, the test harness must destroy and recreate it, not attempt an in-place update.

**Warning signs:**
- `terraform plan` shows `-/+ destroy and then create replacement` for the Lambda function resource
- Durable execution invocations return `InvalidParameterValueException` indicating the function is not durable-enabled
- Function exists in console but Durable Executions tab is absent

**Phase to address:**
Examples creation phase (template structure). Test harness phase (pre-deploy validation).

---

### Pitfall 6: Lambda Cold Starts Adding Non-Deterministic Timing to Tests

**What goes wrong:**
Python 3.13 Lambda cold starts with the durable SDK bundled in the deployment package can add 3-8 seconds of initialization time. Tests with fixed polling timeouts that were measured against warm Lambda executions fail on first run (cold) but pass on subsequent runs (warm). This is the primary cause of flaky integration tests — they pass locally during active development (warm functions) but fail in CI (cold functions on fresh deployment).

**Why it happens:**
Cold starts occur on first invocation after deployment, after periods of inactivity, and after function updates. CI pipelines deploy fresh then immediately invoke, always hitting a cold start. Local development often invokes repeatedly, so the cold start only occurs once.

**How to avoid:**
1. Add an explicit warm-up invocation (a no-op or minimal invocation) before the actual test invocation. Discard this result.
2. Or design polling timeouts to accommodate cold starts: minimum 30 seconds for a simple workflow, not 10.
3. Never hard-code polling timeout based on observed warm-execution timing alone.
4. In the test harness, log whether execution was cold (check `Init Duration` in CloudWatch logs) and emit a warning if test timing was borderline.
5. For Python 3.13 durable functions specifically: the SDK adds initialization overhead beyond standard Lambda cold starts.

**Warning signs:**
- Tests pass locally but fail consistently in CI with timeout errors
- Polling detects `RUNNING` state for longer than expected on first invocation
- CloudWatch logs show `Init Duration: X ms` in the START line (indicates cold start occurred)

**Phase to address:**
Test harness phase. Timeout values must be set with cold start budget included. Warm-up strategy must be decided before running the full test suite.

---

### Pitfall 7: Terraform Destroy Leaving Orphaned CloudWatch Log Groups

**What goes wrong:**
`terraform destroy` frequently fails to delete the CloudWatch log group for a Lambda function. This happens because Lambda itself auto-creates the log group on first invocation — if Lambda created it before Terraform managed it, or if Lambda creates a new log group after Terraform deletes it during the destroy cycle, the log group is left in the account. On the next `terraform apply` for the same example, the apply succeeds but Terraform's `aws_cloudwatch_log_group` resource errors with "resource already exists."

**Why it happens:**
Lambda runtime creates `/aws/lambda/<function-name>` log groups automatically on first invocation. If Terraform did not create it first (or if the function was invoked during destroy), the log group is orphaned outside Terraform state. Additionally, the destroy ordering sometimes destroys the Lambda before destroying the log group, and Lambda's final output (late-flushed buffers) recreates the log group immediately after Terraform deletes it.

**How to avoid:**
1. Use `skip_destroy = false` and set `retention_in_days` in `aws_cloudwatch_log_group` resource to ensure Terraform always manages it.
2. Add a `depends_on` in the log group resource pointing to the Lambda function, so Terraform creates the log group before the Lambda can auto-create it.
3. In the test harness teardown: after `terraform destroy`, explicitly call `logs.delete_log_group()` via boto3 for any log groups associated with the test — treat this as a required cleanup step, not optional.
4. If `terraform apply` fails with "log group already exists", run `terraform import aws_cloudwatch_log_group.main /aws/lambda/<name>` before retrying.

**Warning signs:**
- `terraform apply` errors: `LogGroupAlreadyExistsException`
- Log groups for old example runs accumulate in the account
- `terraform destroy` reports "0 resources destroyed" for log groups that still appear in the console

**Phase to address:**
Examples creation phase (Terraform template structure). Test harness phase (teardown cleanup step).

---

### Pitfall 8: Checkpoint Storage Data Accumulating From Test Runs

**What goes wrong:**
Each durable execution creates checkpoint data in Lambda's managed backend. The default retention period is 14 days. Running the full integration test suite daily produces a minimum of (number of examples) × (executions per test run) × 14 days of checkpoint data accumulating. For long-running or large-state workflows with frequent retries, this data grows materially and incurs ongoing storage charges even after the Lambda function is destroyed.

**Why it happens:**
`terraform destroy` deletes the Lambda function but does NOT delete the checkpoint data for completed executions. AWS manages the backend separately. The retention period clock starts from when execution reaches a terminal state, not from function deletion.

**How to avoid:**
1. Set `retention_period` to the minimum useful value for test deployments — use 1 day for all test examples (not the default 14).
2. In the Terraform templates for examples, explicitly set `retention_period = 1` in the `durable_config` block.
3. Use unique execution names (e.g., include a test run UUID) so that each run's executions are distinguishable and can be audited if costs spike.
4. For cost monitoring: set up a CloudWatch alarm on `DurableExecutionStorageWrittenBytes` metric to detect unexpected accumulation.

**Warning signs:**
- AWS Cost Explorer shows DurableExecution storage costs growing linearly over time
- `list_durable_executions_by_function` returns executions from weeks ago (indicating high retention)
- DurableExecutionStorageWrittenBytes metric trending upward without corresponding increase in test runs

**Phase to address:**
Examples creation phase. Every example's `durable_config` must specify `retention_period = 1` (not default) for test purposes.

---

### Pitfall 9: Race Condition Between Terraform Apply and Lambda IAM Propagation

**What goes wrong:**
After `terraform apply` creates the Lambda function and its IAM role, the IAM policy takes up to 10-15 seconds to propagate globally. The test harness that immediately invokes the Lambda function after `terraform apply` exits gets `AccessDeniedException` because the execution role does not yet have effective permissions for `lambda:CheckpointDurableExecutions`. The Lambda executes but fails immediately in the runtime when attempting its first checkpoint.

**Why it happens:**
IAM is eventually consistent. `terraform apply` marks apply as complete when the API call returns 200, not when IAM is globally consistent. The execution role appears in the IAM console but is not yet effective for Lambda's cross-region checkpoint service.

**How to avoid:**
1. After `terraform apply`, add a 15-second sleep before the first invocation in the test harness.
2. Or: treat the first invocation's result as potentially an IAM-propagation failure and retry it once after a delay if it fails with `AccessDeniedException`.
3. Ensure the IAM role includes the managed policy `AWSLambdaBasicDurableExecutionRolePolicy` (not just manually listed actions) — the managed policy is pre-distributed and may propagate faster.
4. Log and fail loudly if IAM errors are detected, rather than silently retrying — IAM errors and actual test failures need to be distinguished.

**Warning signs:**
- Executions fail with `FAILED` state and error type `AccessDeniedException` or `UnauthorizedException` immediately after deployment
- Error occurs only on first invocation after apply, not on subsequent invocations
- Execution duration in `DurableExecutionDuration` metric is very short (function failed before doing meaningful work)

**Phase to address:**
Test harness phase. The deploy-then-invoke sequence must include an IAM propagation buffer.

---

### Pitfall 10: Execution Identifier Collision Across Test Runs

**What goes wrong:**
If the test harness uses a fixed execution name (e.g., `"test-execution-1"`) and a prior test run failed to clean up (due to a destroy failure), re-running the tests attempts to start a new execution with the same name. Lambda durable functions prevent duplicate execution names within the retention window, returning an error. The test fails with a confusing conflict error rather than a meaningful test failure.

**Why it happens:**
Test harness code that generates execution IDs deterministically (e.g., from test name) produces the same ID on every run. Retention periods default to 14 days, so the collision window is large.

**How to avoid:**
1. Always generate execution IDs dynamically with a timestamp + UUID suffix: e.g., `f"test-{example_name}-{int(time.time())}-{uuid4().hex[:8]}"`.
2. Never use a fixed or test-name-derived execution ID.
3. In the polling helper, store the execution ARN returned from the first polling call, not just the name, to precisely identify the specific run being tracked.

**Warning signs:**
- `ResourceConflictException: Execution with this name already exists` on invocation
- Errors only on second and subsequent test runs, not the first
- Errors disappear after 14+ days (retention period expires)

**Phase to address:**
Test harness phase. The invocation helper must generate IDs dynamically from the start.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using a single Terraform state file for all examples | Simpler test runner setup | State file collisions, destroy failures cascade across examples | Never |
| Hard-coding polling timeout to observed warm-execution time | Faster test loop | Flaky CI due to cold starts | Never |
| Querying CloudWatch logs without propagation delay | Simpler code | Intermittent false negatives in log assertions | Never |
| Using default `retention_period = 14` in test examples | No config needed | Checkpoint storage costs accumulate | Never in test deployments |
| Asserting on fixed execution IDs | Simpler naming | Collision errors after failed teardowns | Never |
| Skipping IAM propagation wait after apply | Faster test startup | AccessDeniedException on first invocation | Only if warm-up invocation absorbs the wait |
| Logging all intermediate state to CloudWatch for verification | Easy debugging | Log verbosity → higher CloudWatch costs | Acceptable during example development; trim before final |
| Using `$LATEST` function version for durable invocation | No version management needed | `AllowInvokeLatest = true` is required and is a non-default config | Acceptable for test examples; document clearly |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| boto3 Lambda invoke | Using `InvocationType='RequestResponse'` expecting return value | Use `InvocationType='Event'`, poll `list_durable_executions_by_function` |
| boto3 filter_log_events | Calling immediately after execution SUCCEEDED | Wait 15s propagation buffer, then retry loop with 5s intervals |
| Terraform + durable Lambda | Adding `durable_config` to existing function | Must create function with `durable_config` from the start; addition requires replacement |
| Terraform destroy + log groups | Assuming destroy removes everything | Always follow destroy with boto3 `delete_log_group()` for each example's log group |
| Lambda + IAM | Invoking immediately after terraform apply | Sleep 15s or implement retry on AccessDeniedException before first invocation |
| parallel() / map() results | Calling `.results` directly on return value | Must call `.get_results()` — returns `BatchResult`, not a list |
| DynamoDB integration example | Using default region in boto3 client | Always pass `region_name='us-east-2'` explicitly to match deployment region |
| CloudWatch log group naming | Lambda auto-creates `/aws/lambda/<name>` before Terraform | Create `aws_cloudwatch_log_group` with `depends_on` before function creation |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Polling every 1 second across multiple examples | 429 ThrottlingException; flaky failures | Minimum 3-5s polling interval; sequential (not parallel) examples | 3+ examples running simultaneously |
| Large handler return values as checkpoint state | `DurableExecutionStorageWrittenBytes` spikes; 256KB limit errors | Keep handler return values minimal; store large data in S3/DynamoDB and return a reference | Any single checkpoint result exceeding 256KB |
| Long execution timeout in test examples | Slow teardown when a test hangs; test suite times out waiting | Set `execution_timeout` to 2-3x the expected workflow duration, not the maximum | Any example that hangs — destroy blocks for the full timeout |
| Querying all log events without time bounds | Slow log queries; data from previous runs confuses assertions | Always pass `startTime` equal to invocation timestamp in `filter_log_events` | Examples with many historical runs |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Hardcoding AWS account ID in Terraform templates | Example code published to git exposes account ID | Use `data.aws_caller_identity.current.account_id` variable, never hardcode |
| Overly broad IAM role for test Lambda (`*` actions) | Unnecessary privilege in test account | Use the minimum: CloudWatch Logs, self-invoke, and the 3 durable execution actions |
| Storing sensitive test payloads in durable execution state | Checkpoint data persists for retention period; accessible via `get_durable_execution` API | Use only synthetic test data in example handlers; never real credentials or PII |
| Using production AWS credentials for integration tests | Accidental resource creation in production account | Always use the `adfs` profile targeting `us-east-2`; add account ID assertion in test harness startup |

---

## "Looks Done But Isn't" Checklist

- [ ] **Polling helper:** Often missing the terminal state check for `STOPPED` — verify it handles all four states: SUCCEEDED, FAILED, TIMED_OUT, STOPPED.
- [ ] **Log assertion helper:** Often missing the retry loop — verify that a single call to `filter_log_events` returning empty events triggers a retry, not an immediate assertion failure.
- [ ] **Teardown:** Often missing explicit log group deletion — verify `terraform destroy` is followed by boto3 `delete_log_group()` calls.
- [ ] **Example Terraform templates:** Often missing `retention_period = 1` in `durable_config` — verify every example's `main.tf` has it explicitly set.
- [ ] **Execution IDs:** Often using a fixed string — verify test harness generates UUID-suffixed IDs on every invocation.
- [ ] **IAM propagation wait:** Often absent after `terraform apply` — verify 15-second sleep or retry on AccessDeniedException before first invocation.
- [ ] **Warm-up invocation:** Often missing — verify the test harness invokes once before the measured test invocation (or that polling timeout accounts for cold start).
- [ ] **parallel() / map() result extraction:** Often missing `.get_results()` — verify any example using Parallel or Map state calls `.get_results()` before indexing results.
- [ ] **Python runtime pinned to 3.13+:** Often defaulting to 3.12 — verify every example's Terraform specifies `runtime = "python3.13"`.
- [ ] **AWS provider version pinned to >= 6.25.0:** Often missing — verify every example's `versions.tf` or `main.tf` requires `version = ">= 6.25.0"` for the hashicorp/aws provider.
- [ ] **Per-example state isolation:** Often absent — verify each example is in its own directory and terraform is initialized and applied independently.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Shared state file collision | MEDIUM | `terraform state list` to see what's in state, manually remove or import the conflicting resource, re-run apply |
| Orphaned log group blocking apply | LOW | `terraform import aws_cloudwatch_log_group.main /aws/lambda/<name>` to bring it under management, then re-apply |
| durable_config missing on existing function | MEDIUM | `terraform destroy` then `terraform apply` — function is destroyed and recreated; all prior checkpoint data is lost |
| ThrottlingException in polling loop | LOW | Increase polling interval to 5s, add exponential backoff, re-run the affected test |
| IAM propagation AccessDeniedException | LOW | Wait 30 seconds and retry the invocation; if persistent, verify IAM policy attachment in console |
| Execution ID collision | LOW | Delete the conflicting execution via `stop_durable_execution` API, then re-run; or wait for retention to expire |
| Log assertions failing due to propagation delay | LOW | Add 15-second sleep before log query; convert log assertions to output assertions where possible |
| Terraform destroy incomplete — resources remain | HIGH | Use `aws-nuke` or manual console deletion; then `terraform state rm` for affected resources; re-initialize |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| No polling for async execution | Test harness phase | Polling helper tests: verify SUCCEEDED detection, FAILED detection, timeout |
| Lambda control plane rate limit | Test harness phase | Run harness with rate-limit smoke test: verify backoff triggers on 429 |
| CloudWatch log propagation delay | Test harness phase | Log assertion helper: verify empty events triggers retry, not failure |
| Shared Terraform state | Examples creation phase | Each example dir has own `terraform.tfstate`; harness runs apply/destroy per-dir |
| durable_config not in initial deploy | Examples creation phase | Template review: all example `main.tf` files include `durable_config` from v1 |
| Lambda cold start timing | Test harness phase | CI test run on fresh deploy with cold start; verify timeouts accommodate |
| Orphaned CloudWatch log groups | Test harness phase | Teardown step: boto3 delete_log_group() after destroy; verify no residual groups |
| Checkpoint storage accumulation | Examples creation phase | All examples: `retention_period = 1` in durable_config |
| IAM propagation race | Test harness phase | Deploy-to-invoke pipeline: 15-second buffer or AccessDeniedException retry |
| Execution ID collision | Test harness phase | Invocation helper: UUID-suffixed ID generation; collision test with re-run |

---

## Sources

- [AWS Lambda Durable Functions — Official Documentation](https://docs.aws.amazon.com/lambda/latest/dg/durable-functions.html) — HIGH confidence
- [AWS Lambda Durable Functions Monitoring](https://docs.aws.amazon.com/lambda/latest/dg/durable-monitoring.html) — HIGH confidence (execution states, EventBridge events, CloudWatch metrics)
- [AWS Lambda Durable Functions Supported Runtimes](https://docs.aws.amazon.com/lambda/latest/dg/durable-supported-runtimes.html) — HIGH confidence (Python 3.13, Python 3.14)
- [Deploy Lambda Durable Functions with IaC](https://docs.aws.amazon.com/lambda/latest/dg/durable-getting-started-iac.html) — HIGH confidence (durable_config block, IAM, provider version >= 6.25.0)
- [Configure Lambda Durable Functions](https://docs.aws.amazon.com/lambda/latest/dg/durable-configuration.html) — HIGH confidence (retention 1-365 days, execution_timeout range, AllowInvokeLatest)
- [AWS Durable Execution SDK Testing Modes](https://github.com/aws/aws-durable-execution-sdk-python/blob/main/docs/advanced/testing-modes.md) — HIGH confidence (DurableFunctionCloudTestRunner, cloud vs local mode, timeout recommendations)
- [Terraform AWS Provider — Lambda Durable Functions Issue #45354](https://github.com/hashicorp/terraform-provider-aws/issues/45354) — MEDIUM confidence (released in v6.25.0, December 2025)
- [CloudWatch Log Group Destroy Issues — terraform-provider-aws #29247](https://github.com/hashicorp/terraform-provider-aws/issues/29247) — HIGH confidence (known Terraform limitation, multiple confirmed reports)
- [Lambda Durable Functions Cost and Checkpoint Storage — thecandidstartup.org](https://www.thecandidstartup.org/2026/01/12/aws-lambda-durable-functions.html) — MEDIUM confidence (cost structure analysis, DynamoDB checkpoint details)
- [boto3 filter_log_events timing issue — GitHub #1524](https://github.com/boto/boto3/issues/1524) — HIGH confidence (confirmed propagation delay causing empty results immediately after invocation)
- [RSF Project — PROJECT.md](../.planning/PROJECT.md) — HIGH confidence (Lambda control plane 15 req/s limit, token bucket at 12 req/s, Event invocation type, polling requirement, Python 3.13+, AWS provider >= 6.25.0)

---

*Pitfalls research for: Lambda Durable Functions automated integration testing (RSF v1.2 milestone)*
*Researched: 2026-02-26*
