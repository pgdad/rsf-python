# RSF Examples

Five real-world workflow examples demonstrating the full RSF feature set — from basic state types to advanced retry policies, intrinsic functions, and DynamoDB integration.

## Prerequisites

- **Python 3.13+** with `pip`
- **Terraform** CLI (v1.0+)
- **AWS credentials** configured (profile or environment variables)
- **boto3 >= 1.42.0** (for Lambda Durable Functions API support)
- **AWS region** `us-east-2`

Install project dependencies:

```bash
pip install -e ".[dev]"
```

## Quick Start

### Run All Local Tests (No AWS)

```bash
for d in examples/*/; do pytest "$d/tests/test_local.py" -v; done
```

### Run Full Integration Suite (AWS)

```bash
pytest tests/test_examples/ -m integration -v
```

This single command deploys all 5 examples to AWS, invokes each workflow, verifies execution results and CloudWatch logs, then tears down all infrastructure. No AWS resources remain after the run completes.

### Run a Single Example

```bash
# Local (no AWS)
pytest examples/order-processing/tests/test_local.py -v

# Integration (AWS)
pytest tests/test_examples/test_order_processing.py -m integration -v
```

## Examples

| Example | State Types | Key Features |
|---------|------------|--------------|
| [order-processing](order-processing/) | Task, Choice, Parallel, Succeed, Fail | Retry/Catch, TimeoutSeconds, concurrent branches |
| [approval-workflow](approval-workflow/) | Task, Wait, Choice, Pass, Succeed, Fail | Context Object (`$$`), Variables/Assign, looping |
| [data-pipeline](data-pipeline/) | Task, Pass, Map | ItemProcessor, all 5 I/O pipeline stages, DynamoDB |
| [retry-and-recovery](retry-and-recovery/) | Task, Pass, Succeed, Fail | Multi-Retry, JitterStrategy, MaxDelaySeconds, multi-Catch |
| [intrinsic-showcase](intrinsic-showcase/) | Task, Pass, Choice, Succeed | 14+ intrinsic functions, full I/O pipeline |

All 8 ASL state types (Task, Choice, Parallel, Map, Pass, Wait, Succeed, Fail) are covered across the combined example set.

## Resource Cleanup

The integration test harness automatically cleans up all AWS resources after each test class:

1. **`terraform destroy`** removes Lambda functions, IAM roles, DynamoDB tables, and CloudWatch log groups
2. **Explicit `delete_log_group()`** catches any orphaned CloudWatch log groups that Terraform may miss

This runs in the test fixture teardown, so cleanup happens whether tests pass or fail. After a full integration run, no Lambda functions, CloudWatch log groups, DynamoDB tables, or IAM roles from the test suite remain in the AWS account.

## Directory Structure

Each example follows the same layout:

```
examples/<name>/
├── workflow.yaml          # RSF DSL workflow definition
├── handlers/              # Python handler functions (@state decorated)
├── src/generated/         # Auto-generated orchestrator (lambda_handler)
├── terraform/             # Terraform infrastructure (Lambda, IAM, etc.)
├── tests/
│   ├── conftest.py        # Local test fixtures (mock SDK)
│   └── test_local.py      # Unit tests (no AWS required)
└── README.md              # Feature documentation
```
