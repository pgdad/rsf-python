# Tutorial: From Install to Deploy and Inspect

This tutorial walks you through creating, generating, deploying, and inspecting an RSF workflow from scratch. By the end, you'll have a working Lambda Durable Functions workflow running on AWS.

## Prerequisites

- Python 3.12+ installed
- AWS CLI configured with credentials
- Terraform installed (for deployment)
- An AWS account with Lambda Durable Functions enabled

## Step 1: Install RSF

```bash
pip install rsf
```

Verify the installation:

```bash
rsf --help
```

You should see the available commands: `init`, `generate`, `validate`, `deploy`, `import`, `ui`, `inspect`.

## Step 2: Initialize a project

```bash
rsf init order-processor
cd order-processor
```

This creates:

```
order-processor/
├── workflow.yaml      # Your workflow definition
├── handlers/          # Handler stubs (created by generate)
├── terraform/         # Infrastructure (created by generate --terraform)
└── rsf.yaml           # Project configuration
```

## Step 3: Define your workflow

Edit `workflow.yaml` with a simple order processing workflow:

```yaml
rsf_version: "1.0"
Comment: "Order processing with validation and error handling"
StartAt: ValidateOrder
States:
  ValidateOrder:
    Type: Task
    Next: CheckAmount

  CheckAmount:
    Type: Choice
    Choices:
      - Variable: "$.amount"
        NumericGreaterThan: 1000
        Next: RequireApproval
    Default: ProcessOrder

  RequireApproval:
    Type: Task
    TimeoutSeconds: 3600
    Retry:
      - ErrorEquals: ["States.Timeout"]
        MaxAttempts: 2
    Catch:
      - ErrorEquals: ["States.ALL"]
        Next: OrderFailed
        ResultPath: "$.approvalError"
    Next: ProcessOrder

  ProcessOrder:
    Type: Task
    Retry:
      - ErrorEquals: ["PaymentError"]
        MaxAttempts: 3
        BackoffRate: 2.0
    Catch:
      - ErrorEquals: ["States.ALL"]
        Next: OrderFailed
        ResultPath: "$.error"
    Next: SendConfirmation

  SendConfirmation:
    Type: Task
    End: true

  OrderFailed:
    Type: Fail
    Error: "OrderProcessingFailed"
    Cause: "The order could not be processed"
```

## Step 4: Validate the workflow

```bash
rsf validate
```

RSF parses the YAML, validates all state types, checks state references, and reports any errors with clear, path-specific messages.

!!! tip "Validation checks"
    RSF validates:

    - All state types and their required/optional fields
    - State name references (Next, Default, Catch.Next) point to existing states
    - StartAt points to an existing state
    - All states are reachable from StartAt via BFS traversal
    - Choice rules have exactly one comparison operator
    - Wait states have exactly one timing specification
    - Mutual exclusion constraints (e.g., TimeoutSeconds vs TimeoutSecondsPath)

## Step 5: Generate code

```bash
rsf generate
```

This produces two kinds of files:

**Orchestrator** (`orchestrator.py`) — Regenerated on every run. Maps your workflow states to Lambda Durable Functions SDK primitives using BFS traversal. Contains a first-line marker (`# RSF-GENERATED`) that tells RSF this file is safe to overwrite.

**Handler stubs** (`handlers/*.py`) — Created once, never overwritten. One file per Task state:

```
handlers/
├── validate_order.py
├── require_approval.py
├── process_order.py
└── send_confirmation.py
```

Each handler stub looks like:

```python
from rsf.registry import state

@state("ValidateOrder")
def handle(event, context):
    # TODO: Implement ValidateOrder logic
    return event
```

## Step 6: Implement business logic

Edit each handler to add your business logic. The `@state` decorator registers the function with the orchestrator — no manual wiring needed.

=== "validate_order.py"

    ```python
    from rsf.registry import state

    @state("ValidateOrder")
    def handle(event, context):
        order = event.get("order", {})
        if not order.get("id"):
            raise ValueError("Missing order ID")
        if not order.get("items"):
            raise ValueError("Order has no items")
        total = sum(item["price"] * item["qty"] for item in order["items"])
        return {**event, "amount": total, "validated": True}
    ```

=== "process_order.py"

    ```python
    from rsf.registry import state

    @state("ProcessOrder")
    def handle(event, context):
        # Call payment API, reserve inventory, etc.
        return {**event, "processed": True, "orderId": event["order"]["id"]}
    ```

=== "require_approval.py"

    ```python
    from rsf.registry import state

    @state("RequireApproval")
    def handle(event, context):
        # Submit for manual approval, poll for decision
        return {**event, "approved": True}
    ```

=== "send_confirmation.py"

    ```python
    from rsf.registry import state

    @state("SendConfirmation")
    def handle(event, context):
        # Send email/SMS confirmation
        return {**event, "confirmed": True}
    ```

!!! note "Generation Gap pattern"
    RSF uses the **Generation Gap** pattern: the orchestrator file is always regenerated (it has a `# RSF-GENERATED` first-line marker), while handler files are created once and never touched again. This means you can safely run `rsf generate` after changing your workflow — your business logic is preserved.

## Step 7: Generate Terraform

```bash
rsf generate --terraform
```

This produces a complete Terraform module:

| File | Contents |
|------|----------|
| `terraform/main.tf` | Lambda function resource, runtime config |
| `terraform/variables.tf` | Configurable inputs (region, memory, timeout) |
| `terraform/iam.tf` | IAM role + 3 policy statements (CloudWatch, self-invoke, durable execution) |
| `terraform/outputs.tf` | Function ARN, name, role ARN |
| `terraform/cloudwatch.tf` | CloudWatch Log Group |
| `terraform/backend.tf` | S3 remote state configuration |

The IAM policy is automatically derived from your workflow — no manual permission configuration needed.

## Step 8: Deploy

```bash
rsf deploy
```

Under the hood, this runs `terraform init` and `terraform apply` against your generated Terraform module.

!!! warning "First deployment"
    On first deployment, Terraform will create the Lambda function, IAM role, and CloudWatch Log Group. Subsequent deployments only update what changed.

## Step 9: Run your workflow

Invoke the workflow via the AWS CLI or SDK:

```bash
aws lambda invoke \
  --function-name order-processor \
  --payload '{"order": {"id": "ORD-001", "items": [{"name": "Widget", "price": 29.99, "qty": 2}]}}' \
  output.json
```

## Step 10: Inspect execution

```bash
rsf inspect
```

This opens the web-based execution inspector at `http://localhost:8000`. The inspector provides:

**Execution list** — All durable executions with status, start time, and duration. Filter by name or status (running, succeeded, failed).

**Graph view** — Your workflow visualized as a directed graph with status overlays:

- Green: succeeded states
- Red: failed states
- Yellow: caught errors
- Blue: currently running
- Gray: pending

**Time machine** — Scrub through execution history with a timeline slider. Each position shows the state of every variable at that point in time, with precomputed snapshots for instant (O(1)) scrubbing.

**Structural diffs** — Color-coded JSON diffs showing exactly what changed at each state transition:

- Green: added fields
- Red: removed fields
- Yellow: modified values

**Live updates** — SSE streaming for in-progress executions. Updates pause automatically when the browser tab is hidden (using the Tab Visibility API) and resume when you return.

## Step 11: Launch the graph editor

```bash
rsf ui
```

Opens the visual graph editor at `http://localhost:8000/#/editor`. Features:

- **Drag and drop** states from the palette onto the canvas
- **Monaco YAML editor** with JSON Schema validation and autocomplete
- **Bidirectional sync** — edit YAML or the graph, changes propagate both ways (300ms debounce)
- **ELK auto-layout** — Sugiyama layered algorithm for clean top-to-bottom layout
- **Minimap** and zoom/pan controls

Switch between editor and inspector with the `#/editor` and `#/inspector` hash routes.

## Step 12: Add a Lambda Function URL trigger

Your workflow is deployed and working via the AWS CLI (Step 9). Now let's add an HTTP trigger so you can invoke it with a simple POST request — no AWS CLI or SDK required.

Add a `lambda_url` block to the top level of your `workflow.yaml`:

```yaml
rsf_version: "1.0"
Comment: "Order processing with validation and error handling"
lambda_url:
  enabled: true
  auth_type: NONE
StartAt: ValidateOrder
States:
  # ... your existing states unchanged
```

The `lambda_url` configuration tells RSF to provision an AWS Lambda Function URL alongside your Lambda function. Setting `auth_type: NONE` creates a public endpoint that accepts unauthenticated requests.

Validate the updated workflow to confirm RSF accepts the new configuration:

```bash
rsf validate
```

!!! tip "Production auth"
    For production workloads, use `auth_type: AWS_IAM` instead of `NONE`. This requires callers to sign requests with AWS SigV4 credentials, preventing unauthorized access. See the [DSL Reference](reference/dsl.md) for details.

## Step 13: Re-deploy with Lambda URL

Run `rsf deploy` again to provision the Lambda Function URL:

```bash
rsf deploy
```

Terraform detects the new `lambda_url` configuration and creates an `aws_lambda_function_url` resource. After `terraform apply` completes, the output includes your new endpoint:

```
Apply complete! Resources: 1 added, 0 changed, 0 destroyed.

Outputs:

function_url = "https://abc123def456.lambda-url.us-east-2.on.aws/"
```

!!! note "Unique URL"
    The Lambda Function URL is generated by AWS and is unique to your deployment. Copy the URL from your terminal output — you'll use it in the next step.

## Step 14: Invoke via HTTP POST

Send a JSON payload to your Lambda Function URL using curl:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"order": {"id": "ORD-042", "items": [{"name": "Gadget", "price": 49.99, "qty": 1}]}}' \
  "https://<url-id>.lambda-url.<region>.on.aws/"
```

Replace the URL with the `function_url` value from your deployment output (Step 13). This triggers a durable execution with the POST body as the event payload — the same as invoking via `aws lambda invoke` (Step 9), but accessible over plain HTTP.

!!! tip "Inspect the execution"
    Run `rsf inspect` (Step 10) to see the execution triggered by your HTTP POST in the web-based inspector. The execution appears in the list like any other invocation.

See the complete [Lambda URL Trigger example](../examples/lambda-url-trigger/) for a standalone project with handlers, Terraform, and tests.

## Next steps

- Read the [DSL Reference](reference/dsl.md) for complete field documentation
- See [State Types](reference/state-types.md) for detailed examples of each state type
- Check the [Migration Guide](migration-guide.md) to import existing Step Functions workflows
