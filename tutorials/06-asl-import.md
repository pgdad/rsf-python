# Tutorial 6: Importing ASL Workflows with `rsf import`

This tutorial walks you through converting an existing AWS Step Functions ASL JSON definition
to RSF YAML format, reviewing the generated output and handler stubs, and validating the
imported workflow.

## What You'll Learn

- How to import an existing ASL (Amazon States Language) JSON file into RSF
- What conversion rules are applied and why
- How to interpret conversion warnings
- How to review the generated RSF YAML and handler stubs
- How to validate and generate from the imported workflow immediately
- How to customize output paths

---

## Prerequisites

Before starting, you need:

- RSF installed (`pip install rsf`)
- Familiarity with AWS Step Functions ASL (Amazon States Language) JSON format
- No AWS account needed -- this tutorial works entirely offline

---

## Step 1: Create a Sample ASL Definition

Create a file called `order-processing.asl.json` with the following ASL definition:

```json
{
  "Comment": "Order processing workflow",
  "StartAt": "ValidateOrder",
  "States": {
    "ValidateOrder": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-2:123456789012:function:validate-order",
      "Next": "CheckAmount"
    },
    "CheckAmount": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.amount",
          "NumericGreaterThan": 100,
          "Next": "RequireApproval"
        }
      ],
      "Default": "ProcessOrder"
    },
    "RequireApproval": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-2:123456789012:function:require-approval",
      "Next": "ProcessOrder"
    },
    "ProcessOrder": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-2:123456789012:function:process-order",
      "Next": "NotifyComplete"
    },
    "NotifyComplete": {
      "Type": "Succeed"
    }
  }
}
```

This is a standard ASL definition with three Task states that reference Lambda ARNs via the
`Resource` field, a Choice state for conditional routing, and a Succeed terminal state. In AWS
Step Functions, the `Resource` field tells the service which Lambda function to invoke. In RSF,
handler routing uses `@state` decorators instead.

---

## Step 2: Run the Import

Run `rsf import` with the ASL file as the argument:

```bash
rsf import order-processing.asl.json
```

You should see the following output:

```
Warning: State 'ValidateOrder' has a Resource field ('arn:aws:lambda:us-east-2:123456789012:function:validate-order'). RSF does not use Resource — use @state decorators to register handlers instead. The Resource field has been removed.
Warning: State 'RequireApproval' has a Resource field ('arn:aws:lambda:us-east-2:123456789012:function:require-approval'). RSF does not use Resource — use @state decorators to register handlers instead. The Resource field has been removed.
Warning: State 'ProcessOrder' has a Resource field ('arn:aws:lambda:us-east-2:123456789012:function:process-order'). RSF does not use Resource — use @state decorators to register handlers instead. The Resource field has been removed.
Success: Converted ASL to workflow.yaml
  Handler stubs: 3 created in handlers/
    - ValidateOrder
    - RequireApproval
    - ProcessOrder
```

The warnings are expected. RSF removes the `Resource` field from each Task state because RSF
uses `@state` decorators instead of Lambda ARNs for handler routing. Three handler stubs were
created, one per Task state. The Choice and Succeed states do not get handler stubs because
they have no user-defined logic.

---

## Step 3: Review the Generated YAML

Open the generated `workflow.yaml`:

```bash
cat workflow.yaml
```

You should see:

```yaml
rsf_version: '1.0'
Comment: Order processing workflow
StartAt: ValidateOrder
States:
  ValidateOrder:
    Type: Task
    Next: CheckAmount
  CheckAmount:
    Type: Choice
    Choices:
    - Variable: $.amount
      NumericGreaterThan: 100
      Next: RequireApproval
    Default: ProcessOrder
  RequireApproval:
    Type: Task
    Next: ProcessOrder
  ProcessOrder:
    Type: Task
    Next: NotifyComplete
  NotifyComplete:
    Type: Succeed
```

Notice the differences from the original ASL JSON:

- `rsf_version: "1.0"` has been injected at the top of the file
- All `Resource` fields have been removed from Task states
- Everything else is preserved as-is: structure, field names, values, and state ordering

The generated YAML is valid RSF and ready to use.

---

## Step 4: Review the Handler Stubs

List the generated handler stubs:

```bash
ls handlers/
```

You should see three files:

```
validate_order.py
require_approval.py
process_order.py
```

Each file corresponds to one Task state. Open `handlers/validate_order.py`:

```bash
cat handlers/validate_order.py
```

```python
"""Handler for the ValidateOrder task state."""

from rsf.registry import state


@state("ValidateOrder")
def validate_order(input_data: dict) -> dict:
    """Handler for the ValidateOrder task state.

    Implement your business logic here.
    """
    raise NotImplementedError("Implement ValidateOrder handler")
```

Key points about the handler stubs:

- One stub per Task state: `validate_order.py`, `require_approval.py`, `process_order.py`
- The function name is the snake_case version of the state name
- The `@state("ValidateOrder")` decorator replaces the ASL `Resource` field -- this is how RSF knows which function handles which state
- The stub body raises `NotImplementedError` -- replace it with your business logic (port the logic from your original Lambda functions)

---

## Step 5: Validate the Imported Workflow

Run `rsf validate` on the generated YAML to confirm it passes all three validation stages:

```bash
rsf validate workflow.yaml
```

The import pipeline produces valid RSF YAML. No manual fixups are needed after import.

---

## Step 6: Generate and Continue

Run `rsf generate` to produce the orchestrator module from the imported workflow:

```bash
rsf generate
```

The imported workflow is now fully integrated into the RSF pipeline. From here, follow the same
workflow as Tutorials 3-5: customize the handler stubs with your business logic, deploy to AWS,
iterate, and invoke.

---

## Understanding Conversion Rules

The `rsf import` converter applies the following rules when translating ASL JSON to RSF YAML:

**Resource removal.** ASL Task states reference Lambda functions via the `Resource` field
(a Lambda ARN). RSF does not use `Resource` -- instead, it generates `@state` handler stubs
that map functions to states via decorators. The `Resource` field is removed and a warning
is printed for each affected state.

**Fail state I/O stripping.** ASL allows I/O processing fields (`InputPath`, `OutputPath`,
`Parameters`, `ResultSelector`, `ResultPath`, `Assign`, `Output`) on Fail states. RSF's strict
validation rejects these fields on Fail states, so they are silently stripped during import.

**Iterator to ItemProcessor.** Legacy Map states use the `Iterator` field instead of the
current `ItemProcessor` field. RSF renames `Iterator` to `ItemProcessor` automatically and
prints a warning.

**Distributed Map fields.** `ItemReader`, `ItemBatcher`, and `ResultWriter` are AWS-specific
distributed Map features. RSF does not support these fields and removes them with a warning.

**Recursive conversion.** Parallel branches and Map `ItemProcessor` sub-workflows are
converted recursively. Nested Task states within branches also get handler stubs generated.

> **Note:** If your ASL uses features not supported by RSF (such as distributed Map),
> review the warnings carefully. The unsupported fields are removed, and you may need to
> restructure that part of your workflow.

---

## Importing with Custom Output Paths

By default, `rsf import` writes to `workflow.yaml` and generates handler stubs in `handlers/`.
Use the `--output` and `--handlers` options to customize these paths:

```bash
rsf import order-processing.asl.json --output my-workflow.yaml --handlers my-handlers
```

This writes the RSF YAML to `my-workflow.yaml` and creates handler stubs in `my-handlers/`
instead of the default locations.

If the output file already exists, `rsf import` prints a warning before overwriting it.

---

## What's Next

In Tutorial 7, you will use `rsf ui` to launch the visual graph editor and edit your workflow
interactively. The graph editor renders your workflow as a directed graph with live YAML
synchronization.

The imported workflow can also be deployed to AWS following Tutorials 4 and 5.

---

*Tutorial 6 of 8 -- RSF Comprehensive Tutorial Series*
