# Tutorial 8: Execution Inspection with `rsf inspect`

This tutorial walks you through deploying a dedicated workflow to AWS for inspection, launching
the execution inspector, browsing execution history, using the time machine scrubber to step
through state-by-state data flow, observing structural diffs between steps, and tearing down
all resources.

## What You'll Learn

- How to deploy a multi-state workflow to AWS as an inspection target
- How to invoke the workflow with different inputs to create execution history
- How to launch the execution inspector with `rsf inspect`
- How to browse executions and view execution details
- How to use the time machine to scrub through history events step by step
- How to observe structural data diffs between consecutive states
- How to watch a live execution with SSE streaming
- How to tear down all infrastructure cleanly

---

## Prerequisites

Before starting, you need:

- Completed Tutorials 1-5 (familiar with the RSF workflow: init, validate, generate, deploy,
  invoke, teardown)
- AWS CLI installed and configured with credentials
- Terraform CLI installed (version 1.0+)
- An AWS account with us-east-2 region enabled

Verify your tools:

```bash
aws sts get-caller-identity
terraform --version
```

Both commands should succeed. If the AWS CLI returns an error, configure your credentials
first. If Terraform is not installed, download it from https://terraform.io.

---

## Step 1: Create the Inspection Workflow

Create a new project directory and initialize it:

```bash
mkdir inspect-demo && cd inspect-demo
rsf init .
```

Replace the generated `workflow.yaml` with a multi-state workflow that processes data through
several steps. This gives us an interesting execution history to inspect:

```yaml
rsf_version: "1.0"
Comment: "Inspection demo workflow"
StartAt: FetchData

States:
  FetchData:
    Type: Task
    Next: TransformData

  TransformData:
    Type: Task
    Next: CheckQuality

  CheckQuality:
    Type: Choice
    Choices:
      - Variable: "$.quality_score"
        NumericGreaterThanOrEquals: 80
        Next: PublishResults
    Default: FlagForReview

  FlagForReview:
    Type: Task
    Next: PublishResults

  PublishResults:
    Type: Task
    End: true
```

This workflow has four Task states and one Choice state. The Choice at `CheckQuality` routes
based on a quality score, so we can trigger different execution paths by varying the input
data.

---

## Step 2: Implement the Handlers

Create handler implementations for all four Task states. Each handler adds meaningful data
to the output so the inspector shows interesting state-by-state data transformations.

Replace `handlers/fetch_data.py`:

```python
"""Handler for the FetchData task state."""

from rsf.registry import state


@state("FetchData")
def fetch_data(input_data: dict) -> dict:
    """Simulate fetching data from a source."""
    record_id = input_data.get("record_id", "R-001")
    return {
        "record_id": record_id,
        "raw_data": {"temperature": 72.5, "humidity": 45},
        "source": "sensor-array-01",
        "fetched": True,
    }
```

Replace `handlers/transform_data.py`:

```python
"""Handler for the TransformData task state."""

from rsf.registry import state


@state("TransformData")
def transform_data(input_data: dict) -> dict:
    """Transform raw data and compute quality score."""
    raw = input_data.get("raw_data", {})
    temp_c = (raw.get("temperature", 0) - 32) * 5 / 9
    return {
        **input_data,
        "transformed": {
            "temperature_celsius": round(temp_c, 1),
            "humidity_pct": raw.get("humidity", 0),
        },
        "quality_score": 85 if temp_c > 15 else 60,
    }
```

Replace `handlers/flag_for_review.py`:

```python
"""Handler for the FlagForReview task state."""

from rsf.registry import state


@state("FlagForReview")
def flag_for_review(input_data: dict) -> dict:
    """Flag low-quality data for manual review."""
    return {
        **input_data,
        "flagged": True,
        "review_reason": "Quality score below threshold",
    }
```

Replace `handlers/publish_results.py`:

```python
"""Handler for the PublishResults task state."""

from rsf.registry import state


@state("PublishResults")
def publish_results(input_data: dict) -> dict:
    """Publish final results."""
    return {
        "record_id": input_data.get("record_id"),
        "status": "published",
        "quality_score": input_data.get("quality_score"),
        "flagged": input_data.get("flagged", False),
    }
```

---

## Step 3: Deploy the Inspection Workflow

Deploy the workflow to AWS:

```bash
rsf deploy --auto-approve
```

This generates the orchestrator code, creates the Terraform configuration, and deploys the
Lambda function to AWS. The workflow is now live and ready to be invoked.

> **Cost reminder:** This creates real AWS resources (Lambda function, IAM role, CloudWatch
> log group). Follow the teardown steps at the end of this tutorial to avoid ongoing charges.

---

## Step 4: Invoke the Workflow

Invoke the workflow twice with different inputs to create execution history with different
paths through the state machine.

**First invocation** -- default sensor data (warm temperature):

```bash
aws lambda invoke \
  --function-name rsf-Inspection-demo-workflow \
  --region us-east-2 \
  --payload '{"record_id": "R-001"}' \
  --cli-binary-format raw-in-base64-out \
  response1.json

cat response1.json
```

The FetchData handler returns default sensor data with temperature 72.5F. TransformData
converts this to 22.5C, which is greater than 15, so `quality_score` is set to 85. Since
85 >= 80, CheckQuality routes to PublishResults directly (skipping FlagForReview).

**Second invocation** -- cold temperature data to trigger the other Choice branch:

```bash
aws lambda invoke \
  --function-name rsf-Inspection-demo-workflow \
  --region us-east-2 \
  --payload '{"record_id": "R-002", "raw_data": {"temperature": 40, "humidity": 90}}' \
  --cli-binary-format raw-in-base64-out \
  response2.json

cat response2.json
```

This time FetchData receives cold temperature data (40F = 4.4C). Since 4.4C is less than 15,
`quality_score` is set to 60. Since 60 < 80, CheckQuality routes to FlagForReview before
reaching PublishResults.

Now we have two completed executions with different paths to inspect:
- R-001: FetchData -> TransformData -> CheckQuality -> PublishResults (quality passed)
- R-002: FetchData -> TransformData -> CheckQuality -> FlagForReview -> PublishResults (flagged)

---

## Step 5: Launch the Inspector

Start the execution inspector:

```bash
rsf inspect
```

You should see:

```
Starting RSF Inspector on port 8766...
Inspecting: arn:aws:lambda:us-east-2:123456789012:function:rsf-Inspection-demo-workflow
```

The inspector auto-discovers the Lambda function ARN from the Terraform state in `terraform/`.
Your browser opens to `http://127.0.0.1:8766`.

If the Terraform state is not available (e.g., you moved the terraform directory or are
inspecting a function deployed by another process), provide the ARN explicitly:

```bash
rsf inspect --arn arn:aws:lambda:us-east-2:123456789012:function:rsf-Inspection-demo-workflow
```

Use `--port` to change the port:

```bash
rsf inspect --port 9000
```

> **Tip:** Keep the terminal with `rsf inspect` running while you explore. Press Ctrl+C to
> stop the server when done.

---

## Step 6: Explore the Execution List

In the browser, the execution list panel shows all durable executions for this Lambda function.
Each execution displays:

- **Execution ID** -- a unique identifier for the invocation
- **Status** -- the current state of the execution
- **Start time** -- when the execution began
- **End time** -- when the execution completed (if finished)

The two invocations from Step 4 should appear as SUCCEEDED executions.

Execution statuses:

| Status | Meaning |
|--------|---------|
| RUNNING | Execution is in progress (the inspector streams live updates) |
| SUCCEEDED | Execution completed successfully |
| FAILED | Execution encountered an error |
| TIMED_OUT | Execution exceeded the configured timeout |
| STOPPED | Execution was manually stopped |

Click an execution to view its detail.

Here is what the execution inspector looks like with a completed execution:

![Execution Inspector — Order Processing](../docs/images/order-processing-inspector.png)

---

## Step 7: Inspect an Execution with the Time Machine

Select the first execution (R-001) to view its detail panel.

**Execution detail** shows the input payload (`{"record_id": "R-001"}`), the final result
(the output of PublishResults), and the total execution duration.

**History timeline** lists each event in chronological order -- state entries, state exits,
and data transformations at each step.

**Time machine scrubber** -- a slider at the bottom of the detail panel lets you scrub through
the execution history step by step:

1. Move the slider to the **first event**: see the initial input to FetchData --
   `{"record_id": "R-001"}`

2. Move to the **second event**: see the output of FetchData -- raw sensor data has been
   added: `{"record_id": "R-001", "raw_data": {"temperature": 72.5, "humidity": 45}, "source": "sensor-array-01", "fetched": true}`

3. Move to the **third event**: see the output of TransformData -- celsius conversion applied,
   quality score computed: `{"transformed": {"temperature_celsius": 22.5, "humidity_pct": 45}, "quality_score": 85, ...}`

4. Move to the **fourth event**: see the CheckQuality decision -- `quality_score` 85 >= 80,
   routing to PublishResults (not FlagForReview)

5. Move to the **final event**: see the output of PublishResults -- the summarized result:
   `{"record_id": "R-001", "status": "published", "quality_score": 85, "flagged": false}`

**Data diff view.** As you scrub between events, the inspector highlights structural
differences between consecutive states:

- Between FetchData output and TransformData output: the `transformed` field was added and
  `quality_score` was computed
- Between TransformData output and PublishResults output: the data was summarized down to
  just `record_id`, `status`, `quality_score`, and `flagged`

The time machine lets you replay the execution step by step, seeing exactly what data flowed
between states. This is invaluable for debugging -- you can pinpoint exactly where data was
transformed incorrectly or where a Choice condition evaluated unexpectedly.

---

## Step 8: Compare Execution Paths

Select the second execution (R-002) and use the time machine to see the different path.

This execution went through FlagForReview because `quality_score` was 60 (below the
threshold of 80). The history timeline has an extra event for the FlagForReview state.

Scrub through the events to observe:

- After TransformData: `quality_score` is 60 (not 85), because the cold temperature
  (40F = 4.4C) is below 15
- After CheckQuality: the Choice routed to FlagForReview (not PublishResults)
- After FlagForReview: the data diff shows `flagged: true` and
  `review_reason: "Quality score below threshold"` were added
- After PublishResults: the final output includes `flagged: true`

Comparing executions with different paths helps you understand how your Choice conditions
route data and verify that all branches produce correct output.

---

## Step 9: Live Inspection (Optional)

To see live streaming in action, keep the inspector running in your browser and open a
separate terminal to invoke the Lambda again:

```bash
aws lambda invoke \
  --function-name rsf-Inspection-demo-workflow \
  --region us-east-2 \
  --payload '{"record_id": "R-003"}' \
  --cli-binary-format raw-in-base64-out \
  response3.json
```

In the browser, a new RUNNING execution appears in the execution list. Click it to see live
updates via Server-Sent Events (SSE) -- events appear in the timeline as they happen. Once
the execution completes, the status changes to SUCCEEDED and the SSE stream closes.

The inspector polls for updates every 5 seconds. For fast-completing executions (like this
one), you may only see the final state. For long-running workflows with Wait states or
complex branching, you can watch events arrive in real time.

---

## Step 10: Tear Down

Stop the inspector by pressing Ctrl+C in the inspector terminal. Then tear down the AWS
infrastructure:

```bash
cd terraform && terraform destroy -auto-approve
```

Verify clean teardown:

```bash
aws lambda get-function --function-name rsf-Inspection-demo-workflow --region us-east-2
```

Expected output: `ResourceNotFoundException` -- confirming that the Lambda function has been
deleted and zero orphaned resources remain.

> **Important:** Always tear down inspection infrastructure when you are done. Lambda
> functions and CloudWatch log groups incur ongoing costs even when not actively invoked.

---

## What You've Learned

This completes the RSF tutorial series. Here is a summary of all eight tutorials:

| Tutorial | Command | What You Learned |
|----------|---------|------------------|
| 1 | `rsf init` | Scaffold a new RSF project |
| 2 | `rsf validate` | Validate workflow YAML with 3-stage checks |
| 3 | `rsf generate` | Generate orchestrator code and handler stubs |
| 4 | `rsf deploy` | Deploy to AWS with Terraform |
| 5 | `rsf deploy --code-only` | Iterate, invoke, and tear down |
| 6 | `rsf import` | Migrate from AWS Step Functions ASL |
| 7 | `rsf ui` | Visually edit workflows in the graph editor |
| 8 | `rsf inspect` | Inspect live executions with time machine |

The complete RSF development workflow:

1. **Define** -- write workflow YAML (or import from ASL)
2. **Validate** -- check for errors with `rsf validate`
3. **Generate** -- produce orchestrator and handler stubs with `rsf generate`
4. **Deploy** -- push to AWS with `rsf deploy`
5. **Iterate** -- update handlers and redeploy with `rsf deploy --code-only`
6. **Invoke** -- test with `aws lambda invoke`
7. **Inspect** -- debug with `rsf inspect` and the time machine
8. **Edit** -- refine visually with `rsf ui`
9. **Tear down** -- clean up with `terraform destroy`

---

*Tutorial 8 of 8 -- RSF Comprehensive Tutorial Series*
