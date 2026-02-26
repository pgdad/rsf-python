# Tutorial 5: Iterate, Invoke, and Tear Down

## What You'll Learn

In this tutorial you will:

- Edit a handler and use `rsf deploy --code-only` to update the Lambda in seconds
- Understand the difference between a full deploy and a code-only deploy
- Invoke the deployed Lambda with test payloads using the AWS CLI
- Test both branches of a Choice state by varying the input
- Tear down all AWS infrastructure cleanly with `terraform destroy`
- Verify that zero orphaned resources remain after teardown

---

## Prerequisites

- Completed Tutorial 4: you have a deployed RSF workflow running in AWS
- The `my-workflow/` directory contains `workflow.yaml`, generated code, and a `terraform/` directory with Terraform state
- AWS CLI configured and Terraform installed

If you have not deployed yet, go back to Tutorial 4 and run `rsf deploy --auto-approve` first.

---

## Step 1: Edit a Handler

Open `handlers/validate_order.py` and add a timestamp to the return value. Replace the entire file with:

```python
"""Handler for the ValidateOrder task state."""

import time

from rsf.registry import state


@state("ValidateOrder")
def validate_order(input_data: dict) -> dict:
    """Validate the incoming order and add a timestamp."""
    order_id = input_data.get("order_id")
    amount = input_data.get("amount", 0)
    if not order_id:
        raise ValueError("Missing order_id")
    return {
        "order_id": order_id,
        "amount": amount,
        "validated": True,
        "validated_at": int(time.time()),
    }
```

The change is small: you added `import time` and a `validated_at` field to the return value. Now you need to deploy this change to AWS without re-creating all the infrastructure.

---

## Step 2: Deploy Code Only

Run `rsf deploy` with the `--code-only` flag:

```bash
rsf deploy --code-only
```

Expected output:

```
Code generated: orchestrator.py + 3 handler(s) (3 skipped)

Running targeted terraform apply (Lambda code update)...
...
Apply complete! Resources: 0 added, 1 changed, 0 destroyed.

Code update complete
```

The key differences from a full deploy:

- **No `terraform init`** — the Terraform working directory was already initialized in Tutorial 4
- **Targeted apply** — only `aws_lambda_function.*` resources are updated. The IAM role, CloudWatch log group, and other infrastructure are untouched.
- **Always auto-approves** — no interactive prompt. Code-only deploys are safe because they only update Lambda code.
- **Completes in seconds** — a full deploy takes minutes because Terraform evaluates all resources. A code-only deploy targets only the Lambda function.

The code generation step still runs (to regenerate `orchestrator.py`), but your handlers are preserved by the Generation Gap pattern from Tutorial 3.

> **When to use `--code-only` vs a full deploy:**
> Use `--code-only` when you only changed handler logic (Python code). Use a full `rsf deploy` when you changed `workflow.yaml` (added, removed, or renamed states) because the Terraform configuration may need updating to reflect the new state machine structure.

---

## Step 3: Invoke the Lambda

Use the AWS CLI to invoke the deployed Lambda function with a test payload:

```bash
aws lambda invoke \
  --function-name rsf-Order-processing-workflow \
  --region us-east-2 \
  --payload '{"order_id": "ORD-001", "amount": 50}' \
  --cli-binary-format raw-in-base64-out \
  response.json
```

Expected CLI output:

```json
{
    "StatusCode": 200,
    "ExecutedVersion": "$LATEST"
}
```

A `StatusCode` of 200 means the Lambda executed successfully. View the response:

```bash
cat response.json
```

The response contains the output of the workflow execution. The exact format depends on the durable execution runtime, but it should contain the result of the final state (`ProcessOrder`).

Here is what happened during this invocation:

1. **ValidateOrder** received `{"order_id": "ORD-001", "amount": 50}`, validated the order, and returned `{"order_id": "ORD-001", "amount": 50, "validated": true, "validated_at": 1740600000}`
2. **CheckAmount** evaluated the Choice rule: is `$.amount` (50) greater than 100? No — so it routed to the `Default` target: `ProcessOrder`
3. **ProcessOrder** received the validated order data and produced the final output

The `RequireApproval` state was skipped because the amount (50) did not exceed 100.

### Test the Other Branch

Now invoke with a high amount to trigger the `RequireApproval` path:

```bash
aws lambda invoke \
  --function-name rsf-Order-processing-workflow \
  --region us-east-2 \
  --payload '{"order_id": "ORD-002", "amount": 200}' \
  --cli-binary-format raw-in-base64-out \
  response-high.json
```

View the response:

```bash
cat response-high.json
```

This time the workflow took a different path:

1. **ValidateOrder** validated the order (amount: 200)
2. **CheckAmount** evaluated the Choice rule: is `$.amount` (200) greater than 100? Yes — routed to `RequireApproval`
3. **RequireApproval** processed the approval step
4. **ProcessOrder** produced the final output

The `--function-name` follows the pattern `rsf-{workflow_name}` where `workflow_name` comes from the `Comment` field in `workflow.yaml`. The `--payload` provides the initial input to the first state (`ValidateOrder`). The `--cli-binary-format raw-in-base64-out` flag tells the AWS CLI to send the payload as raw JSON rather than base64-encoding it.

---

## Step 4: Tear Down All Infrastructure

When you are done experimenting, remove all AWS resources:

```bash
cd terraform && terraform destroy -auto-approve
```

Expected output:

```
...
Destroy complete! Resources: 4 destroyed.
```

The 4 resources destroyed are the same 4 that were created in Tutorial 4:

- **Lambda function** — the deployed workflow
- **IAM role** — the execution role
- **IAM role policy** — the permissions policy
- **CloudWatch log group** — the Lambda logs

After this command, zero AWS resources remain from the tutorial. No orphaned infrastructure.

The `-auto-approve` flag skips the interactive confirmation. The local files (`terraform/`, `orchestrator.py`, `handlers/`) remain on disk for reference.

> **Important:** Always run `terraform destroy` when you are done experimenting. Lambda Durable Functions and CloudWatch log groups incur costs while they exist. The teardown removes all resources cleanly.

Change back to the project root:

```bash
cd ..
```

---

## Step 5: Verify Clean Teardown

Confirm that the Lambda function no longer exists:

```bash
aws lambda get-function \
  --function-name rsf-Order-processing-workflow \
  --region us-east-2
```

Expected output:

```
An error occurred (ResourceNotFoundException) when calling the GetFunction
operation: Function not found: arn:aws:lambda:us-east-2:123456789012:function:rsf-Order-processing-workflow
```

The `ResourceNotFoundException` confirms the function was deleted. The teardown was complete.

---

## The Development Loop

You have now completed the full RSF development lifecycle. Here is the complete cycle:

```
1. rsf init              — scaffold project
2. rsf validate          — check workflow YAML
3. rsf generate          — create orchestrator + handler stubs
4. rsf deploy            — deploy to AWS (first time, full Terraform)
5. Edit handlers         — write business logic
6. rsf deploy --code-only — update Lambda code (seconds, no Terraform re-apply)
7. aws lambda invoke     — test the workflow
8. Repeat steps 5-7      — iterate on handler logic
9. terraform destroy     — tear down when done
```

Steps 5-7 are the fast inner loop. Each iteration takes seconds, not minutes. You edit a handler, deploy the code, invoke the Lambda, and check the result. When you are satisfied, step 9 tears down the infrastructure.

---

## What's Next

Continue to **Tutorial 6: Importing ASL Workflows with `rsf import`** (Phase 20: Advanced Tools).

If you have existing AWS Step Functions workflows defined in Amazon States Language (ASL), `rsf import` converts them to RSF YAML and generates handler stubs. This lets you migrate to RSF without rewriting your workflow definitions from scratch.

Phase 20 also covers:

- **`rsf ui`** — launch the visual graph editor to design workflows graphically
- **`rsf inspect`** — attach to a live execution and scrub through historical states with time machine debugging
