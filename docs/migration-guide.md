# Migration Guide: Step Functions to RSF

This guide walks you through importing an existing AWS Step Functions workflow (ASL JSON) into RSF. The process takes under 30 minutes for most workflows.

## Overview

RSF includes a built-in ASL importer that:

1. Parses your Step Functions ASL JSON definition
2. Converts it to RSF YAML format
3. Generates handler stubs for every Task state
4. Reports warnings for unsupported features

## Step 1: Export your Step Functions definition

Get your workflow's ASL JSON from the AWS console or CLI:

```bash
aws stepfunctions describe-state-machine \
  --state-machine-arn arn:aws:states:us-east-1:123456789:stateMachine:MyWorkflow \
  --query 'definition' \
  --output text > my-workflow.json
```

Or download from the Step Functions console: open your state machine, click **Definition**, and copy the JSON.

## Step 2: Import into RSF

```bash
rsf import my-workflow.json
```

This produces:
- `workflow.yaml` — Your workflow in RSF format
- `handlers/*.py` — One handler stub per Task state

### Example

Given this ASL JSON:

```json
{
  "Comment": "A simple Step Functions workflow",
  "StartAt": "ValidateOrder",
  "States": {
    "ValidateOrder": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789:function:validate",
      "Next": "CheckAmount",
      "Retry": [
        {
          "ErrorEquals": ["TransientError"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2.0
        }
      ]
    },
    "CheckAmount": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.amount",
          "NumericGreaterThan": 1000,
          "Next": "HighValueApproval"
        }
      ],
      "Default": "ProcessOrder"
    },
    "HighValueApproval": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789:function:approve",
      "Next": "ProcessOrder"
    },
    "ProcessOrder": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789:function:process",
      "End": true
    }
  }
}
```

The importer produces this `workflow.yaml`:

```yaml
rsf_version: "1.0"
Comment: A simple Step Functions workflow
StartAt: ValidateOrder
States:
  ValidateOrder:
    Type: Task
    Next: CheckAmount
    Retry:
      - ErrorEquals:
          - TransientError
        IntervalSeconds: 2
        MaxAttempts: 3
        BackoffRate: 2.0
  CheckAmount:
    Type: Choice
    Choices:
      - Variable: $.amount
        NumericGreaterThan: 1000
        Next: HighValueApproval
    Default: ProcessOrder
  HighValueApproval:
    Type: Task
    Next: ProcessOrder
  ProcessOrder:
    Type: Task
    End: true
```

And these handler stubs:

```
handlers/
├── validate_order.py
├── high_value_approval.py
└── process_order.py
```

## What the importer does

The importer applies these conversion rules automatically:

### 1. Injects RSF version

Adds `rsf_version: "1.0"` at the root.

### 2. Removes Resource fields

ASL Task states reference Lambda ARNs via `Resource`. RSF uses `@state` decorators instead — the `Resource` field is removed and a warning is emitted:

```
WARNING: State 'ValidateOrder' has a Resource field
('arn:aws:lambda:...').  RSF does not use Resource — use @state
decorators to register handlers instead.
```

### 3. Strips Fail state I/O fields

ASL allows I/O processing fields on Fail states, but RSF follows a strict interpretation where Fail states do not process I/O. These fields are silently removed: `InputPath`, `OutputPath`, `Parameters`, `ResultSelector`, `ResultPath`, `Assign`, `Output`.

### 4. Renames legacy Iterator to ItemProcessor

Older ASL definitions use `Iterator` on Map states. The importer renames it to `ItemProcessor`:

```
WARNING: Renamed legacy 'Iterator' to 'ItemProcessor' in state 'ProcessItems'.
```

### 5. Warns on distributed Map fields

Distributed Map features (`ItemReader`, `ItemBatcher`, `ResultWriter`) are not supported by RSF and are removed with warnings:

```
WARNING: Distributed Map field 'ItemReader' in state 'ProcessBatch'
is not supported by RSF and has been removed.
```

### 6. Handles nested structures

Parallel branches and Map ItemProcessors are recursively converted. All conversion rules apply at every nesting level.

## Step 3: Implement handlers

Each generated handler stub returns the event unchanged:

```python
from rsf.registry import state

@state("ValidateOrder")
def handle(event, context):
    # TODO: Implement ValidateOrder logic
    return event
```

Move your business logic from the existing Lambda functions into the handler stubs. The key difference: in Step Functions, each Task is a separate Lambda function. In RSF, all tasks run in a single Lambda with the orchestrator dispatching to the right handler via `@state` decorators.

### Mapping your existing code

| Step Functions | RSF |
|---------------|-----|
| Separate Lambda function per Task | Single Lambda, `@state` decorator per Task |
| `Resource` ARN references | `@state("StateName")` decorator |
| Event input from Step Functions | Same event input from orchestrator |
| Return value → next state | Same — return value passes to next state |

### Example migration

**Before (separate Lambda):**

```python
# validate_order_lambda/handler.py
def lambda_handler(event, context):
    order = event["order"]
    if order["total"] <= 0:
        raise ValueError("Invalid total")
    return {"validated": True, "orderId": order["id"]}
```

**After (RSF handler):**

```python
# handlers/validate_order.py
from rsf.registry import state

@state("ValidateOrder")
def handle(event, context):
    order = event["order"]
    if order["total"] <= 0:
        raise ValueError("Invalid total")
    return {"validated": True, "orderId": order["id"]}
```

The logic is identical — just wrapped with `@state` instead of the raw `lambda_handler` entry point.

## Step 4: Validate and generate

```bash
# Validate the imported workflow
rsf validate

# Generate the orchestrator
rsf generate

# Generate Terraform
rsf generate --terraform
```

## Step 5: Deploy and verify

```bash
rsf deploy
```

Test the migrated workflow with the same inputs you used with Step Functions. The behavior should be identical since RSF implements full ASL feature parity.

## Programmatic import

You can also use the importer as a Python library:

```python
from pathlib import Path
from rsf.importer import import_asl

result = import_asl(
    source="my-workflow.json",
    output_path=Path("workflow.yaml"),
    handlers_dir=Path("handlers"),
)

# Check warnings
for warning in result.warnings:
    print(f"{warning.severity}: {warning.path} — {warning.message}")

# List generated handler stubs
print(f"Task states: {result.task_state_names}")
```

## Known limitations

| ASL Feature | RSF Support |
|------------|-------------|
| `Resource` (Lambda ARN) | Removed — use `@state` decorators |
| Distributed Map (`ItemReader`, `ItemBatcher`, `ResultWriter`) | Not supported — removed with warning |
| Fail state I/O fields | Not supported — silently removed |
| Legacy `Iterator` on Map | Auto-renamed to `ItemProcessor` |
| Service integrations (SQS, SNS, DynamoDB, etc.) | Not supported — implement in handler code |
| `ResultWriter` for Map | Not supported |

## Troubleshooting

### "Malformed JSON" error

Ensure your ASL file is valid JSON. Common issues:
- Trailing commas (not allowed in JSON)
- Single quotes instead of double quotes
- Comments in JSON (not allowed)

### Missing states after import

If your workflow uses service integrations (`Resource: arn:aws:states:::sqs:sendMessage`), those Task states will have their `Resource` removed. You'll need to implement the equivalent logic in the handler stub.

### Validation errors after import

Run `rsf validate` to check for any issues. Common post-import validation errors:
- Unreachable states (states not reachable from `StartAt` via BFS)
- Missing state references (a `Next` or `Default` pointing to a non-existent state)
- These usually indicate the original ASL had issues, or distributed Map features created orphaned states
