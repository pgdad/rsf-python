# Step Functions vs RSF Parity Tests

**Date:** 2026-03-20
**Status:** Draft

## Problem

RSF generates Lambda Durable Functions orchestrators that replicate AWS Step Functions behavior, but there are no tests proving that the same workflow produces the same results when executed as a Step Functions state machine vs an RSF-generated Lambda. Existing integration tests use stub handlers that don't interact with real AWS services.

## Solution

Three parity tests that implement identical workflows both as Step Functions state machines (using SDK integrations where possible, Lambda for custom logic) and as RSF workflows (with Python handlers). Each test deploys both versions to AWS, executes them with the same input, and compares:
1. Final output (S3 content)
2. Side effects (S3 objects created, SQS messages consumed)
3. Execution trace (state visit sequence)

## The Three Test Workflows

### Test 1: S3 ETL Pipeline

A file in S3 is read, each record is transformed (uppercase a field, add timestamp), and the result is written to a different S3 key.

**States:**

| State | Type | Step Functions | RSF |
|-------|------|---------------|-----|
| ReadFromS3 | Task | `arn:aws:states:::aws-sdk:s3:getObject` (AWS SDK integration) | `boto3 s3.get_object()` in @state handler |
| TransformRecords | Map | Lambda handler calling `transform_record()` | @state handler calling `transform_record()` |
| WriteToS3 | Task | `arn:aws:states:::aws-sdk:s3:putObject` (AWS SDK integration) | `boto3 s3.put_object()` in @state handler |
| Done | Succeed | — | — |

**Input:** `s3://bucket/input/data.json` — JSON array of records like `[{"name": "alice", "age": 30}, ...]`

**Output:** `s3://bucket/{sf|rsf}/etl/result.json` — transformed array with uppercased names and `processed_at` timestamps

**Expected duration:** ~20s. Timeout: 2 min.

### Test 2: SQS Message Collector (Long-Running)

A workflow polls SQS in a loop, accumulating messages. After collecting 10 messages, writes them as a JSON array to S3 and deletes them from the queue.

**States:**

| State | Type | Step Functions | RSF |
|-------|------|---------------|-----|
| Initialize | Pass | Set `$.messages = []`, `$.count = 0` | Same |
| PollSQS | Task | `arn:aws:states:::aws-sdk:sqs:receiveMessage` (AWS SDK integration) | `boto3 sqs.receive_message()` in @state handler |
| CheckMessages | Choice | If message received → AppendMessage, else → WaitBeforePoll | Same |
| AppendMessage | Pass | Add message to `$.messages`, increment `$.count` | Same |
| CheckCount | Choice | If `$.count >= 10` → WriteToS3, else → WaitBeforePoll | Same |
| WaitBeforePoll | Wait | Seconds: 10 | Same |
| WriteToS3 | Task | `arn:aws:states:::aws-sdk:s3:putObject` (AWS SDK integration) | `boto3 s3.put_object()` in @state handler |
| DeleteMessages | Task | Lambda (batch delete requires custom logic) | `boto3 sqs.delete_message_batch()` in @state handler |
| Done | Succeed | — | — |

**Input:** 10 JSON messages sent to SQS staggered over ~90 seconds.

**Output:** `s3://bucket/{sf|rsf}/sqs-collector/result.json` — JSON array of 10 messages.

**Expected duration:** ~3 min (10 polls × 10s wait + message stagger). Timeout: 5 min.

### Test 3: Choice-Based Format Routing

A workflow reads a config file from S3, inspects its `format` field, and routes processing to either a CSV or JSON processor, writing the result to a format-specific S3 prefix.

**States:**

| State | Type | Step Functions | RSF |
|-------|------|---------------|-----|
| ReadConfig | Task | `arn:aws:states:::aws-sdk:s3:getObject` (AWS SDK integration) | `boto3 s3.get_object()` in @state handler |
| RouteByFormat | Choice | `$.format == "csv"` → ProcessCSV, `$.format == "json"` → ProcessJSON, Default → HandleUnknownFormat | Same |
| ProcessCSV | Task | Lambda handler calling `process_csv()` | @state handler calling `process_csv()` |
| ProcessJSON | Task | Lambda handler calling `process_json()` | @state handler calling `process_json()` |
| WriteResult | Task | `arn:aws:states:::aws-sdk:s3:putObject` (writes to `output/{format}/result.json`) | `boto3 s3.put_object()` in @state handler |
| HandleUnknownFormat | Fail | Error: "UnsupportedFormat" | Same |
| Done | Succeed | — | — |

**Test runs twice:** once with `config_csv.json` (format=csv), once with `config_json.json` (format=json).

**Output:** `s3://bucket/{sf|rsf}/choice-routing/{format}/result.json`

**Expected duration:** ~20s per run. Timeout: 2 min.

## Infrastructure

### Shared Terraform Module

Deployed once before all tests, destroyed after all complete.

**Resources:**
- S3 bucket (`rsf-parity-test-{random_suffix}`, versioning enabled, `force_destroy = true`)
- SQS queue (`rsf-parity-test-queue`, visibility_timeout=30s, message_retention=300s)
- SQS dead letter queue (`rsf-parity-test-dlq`)
- IAM role for Lambda handlers — permissions: `s3:GetObject`, `s3:PutObject`, `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:DeleteMessageBatch`, `logs:CreateLogGroup`, `logs:PutLogEvents`
- IAM role for Step Functions — permissions: `lambda:InvokeFunction`, `s3:GetObject`, `s3:PutObject`, `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:DeleteMessageBatch`, `sqs:SendMessage`

### Per-Test Terraform Modules

Each deploys both the Step Functions and RSF versions:

- `aws_sfn_state_machine` — ASL JSON definition referencing SDK integrations and handler Lambda ARNs
- `aws_lambda_function` (SF handlers) — for Task states that need custom logic (Map transform, CSV/JSON processing, SQS batch delete)
- `aws_lambda_function` (RSF) — durable Lambda with generated orchestrator + all handlers bundled
- `aws_lambda_alias` (RSF) — "live" alias for the RSF Lambda (required for durable execution invocation)

Shared outputs (S3 bucket, SQS queue URL, IAM role ARNs) passed as Terraform variables. Per-test outputs must include `sfn_arn`, `rsf_function_name`, and `rsf_alias_arn`. RSF invocation **must** use the alias ARN, not the function name directly.

## Handler Code Strategy

Business logic lives in pure functions. RSF handlers and SF Lambda handlers both call the same pure functions.

```
handlers/common/s3_utils.py    — read_json_from_s3(), write_json_to_s3()
handlers/common/sqs_utils.py   — poll_sqs(), delete_messages()
handlers/etl/transform.py      — transform_record() (pure, no AWS calls)
handlers/choice_routing/process_csv.py   — parse CSV → records (pure)
handlers/choice_routing/process_json.py  — validate/normalize JSON (pure)
```

RSF handlers (`rsf_handlers.py`) use `@state` decorators wrapping common utils + pure logic.
SF handlers (`sf_handler.py`) are Lambda entry points calling the same pure logic.

SF uses AWS SDK integrations (`arn:aws:states:::aws-sdk:*`) for S3 and SQS operations where possible — no Lambda needed for those operations. Lambda is only used for custom logic (record transformation, CSV/JSON processing, SQS batch delete).

## Parity Verification

### 1. Final Output

Both workflows write to different S3 prefixes (`sf/` vs `rsf/`). After both complete, read and compare JSON content.

### 2. Side Effects

| Test | Verifications |
|------|--------------|
| ETL | Input file read from S3, output file written, content matches between SF and RSF |
| SQS Collector | All 10 messages consumed (queue empty after each run), S3 file contains exactly 10 messages, messages deleted from queue |
| Choice Routing | Config file read, output written to correct prefix (`output/csv/` or `output/json/`), Fail path produces no S3 output |

### 3. Execution Trace

Normalize both execution histories into a common format:

```python
@dataclass
class StateTransition:
    state_name: str
    state_type: str   # Task, Choice, Wait, Pass, etc.
    status: str       # entered, succeeded, failed
```

- Step Functions: `get_execution_history()` API
- RSF: CloudWatch Logs with step name patterns

Compare **state visit order** (the sequence of state names entered). Timing is not compared — SF has service overhead, RSF has cold start differences.

## Test Execution Flow

```
1. SHARED SETUP (session-scoped fixture)
   terraform apply tests/parity/shared/terraform/
   → S3 bucket, SQS queue, IAM roles

2. PER-TEST DEPLOY (function-scoped fixture)
   terraform apply tests/parity/test-NN/terraform/
   → SF state machine + handler Lambdas + RSF Lambda

3. SEED TEST DATA
   Upload input files to S3
   For SQS test: send 10 messages staggered over ~90s (background thread)

4. RUN STEP FUNCTIONS
   sfn.start_execution(stateMachineArn=..., input=...)
   Poll describe_execution() until terminal (timeout per test)
   Collect get_execution_history()

5. RESET SHARED STATE
   Re-upload input files to S3
   Re-send SQS messages (for SQS test)
   Purge queue between runs

6. RUN RSF
   lambda.invoke(FunctionName=rsf_alias_arn, InvocationType="Event", DurableExecutionName=...)
   Poll list_durable_executions_by_function() until terminal
   Collect CloudWatch logs

7. COMPARE
   Final output, side effects, execution trace

8. PER-TEST TEARDOWN
   terraform destroy tests/parity/test-NN/terraform/

9. SHARED TEARDOWN (session end)
   Empty S3 bucket, terraform destroy shared stack
```

The **reset between SF and RSF runs** (step 5) ensures both start from identical conditions.

## File Structure

```
tests/parity/
├── conftest.py                          # Shared fixtures: deploy/teardown, polling,
│                                        #   trace parsing, parity comparison helpers
├── handlers/
│   ├── common/
│   │   ├── __init__.py
│   │   ├── s3_utils.py                  # read_json_from_s3(), write_json_to_s3()
│   │   └── sqs_utils.py                # poll_sqs(), delete_messages()
│   ├── etl/
│   │   ├── __init__.py
│   │   ├── transform.py                 # transform_record() — pure logic
│   │   ├── rsf_handlers.py              # @state decorators wrapping utils + transform
│   │   └── sf_handler.py                # Lambda entry point for SF Map task
│   ├── sqs_collector/
│   │   ├── __init__.py
│   │   ├── rsf_handlers.py              # @state: PollSQS, WriteToS3, DeleteMessages
│   │   └── sf_handler.py                # SF Lambda for DeleteMessages
│   └── choice_routing/
│       ├── __init__.py
│       ├── process_csv.py               # Pure logic: CSV → records
│       ├── process_json.py              # Pure logic: JSON normalize
│       ├── rsf_handlers.py              # @state handlers wrapping processors
│       └── sf_handler.py                # SF Lambda entry points
├── shared/
│   └── terraform/
│       ├── main.tf                      # S3 bucket, SQS queue + DLQ, IAM roles
│       ├── variables.tf
│       └── outputs.tf
├── test-01-etl/
│   ├── terraform/
│   │   ├── main.tf                      # SF state machine + SF handler Lambda + RSF Lambda
│   │   ├── sfn_definition.json          # ASL JSON for Step Functions
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── workflow.yaml                    # RSF workflow definition
│   ├── test_data/
│   │   └── input.json                   # JSON array of records
│   └── test_etl_parity.py
├── test-02-sqs-collector/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── sfn_definition.json
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── workflow.yaml
│   ├── test_data/
│   │   └── messages.json                # 10 JSON messages
│   └── test_sqs_collector_parity.py
└── test-03-choice-routing/
    ├── terraform/
    │   ├── main.tf
    │   ├── sfn_definition.json
    │   ├── variables.tf
    │   └── outputs.tf
    ├── workflow.yaml
    ├── test_data/
    │   ├── config_csv.json
    │   ├── config_json.json
    │   ├── sample.csv
    │   └── sample.json
    └── test_choice_routing_parity.py
```

## Dependencies

- **AWS services:** S3, SQS, Step Functions, Lambda (Durable Functions), CloudWatch Logs, IAM
- **Terraform:** infrastructure deployment
- **boto3:** AWS SDK for test harness + RSF handlers
- **pytest:** test framework (with existing `@pytest.mark.integration` marker). The parity `conftest.py` should reuse helpers from `tests/test_examples/conftest.py` (`poll_execution`, `terraform_deploy`, `terraform_teardown`, `make_execution_id`, `iam_propagation_wait`) rather than re-implementing them.
- **RSF CLI:** `rsf generate` to produce orchestrator from workflow.yaml

## Out of Scope

- Performance benchmarking (SF vs RSF latency/cost)
- DynamoDB, SNS, or other service integrations beyond S3/SQS
- Distributed Map (cross-Lambda item processing)
- Error injection / chaos testing
- Automated ASL generation from RSF workflow.yaml (ASL JSON is hand-written per test)
