# Tutorial 5: Order Processing

<div class="tutorial-meta">
  <span class="badge badge-difficulty badge-advanced">Advanced</span>
  <span class="tutorial-time">30 min</span>
</div>

Build a complete order processing pipeline as a full example.

---

## Steps


### Step 1: The starter workflow

Starting from the default rsf init workflow. We will build a full order processing workflow.


![Step 1 — The starter workflow](assets/step-01-starter-workflow.png){ .tutorial-screenshot }




### Step 2: Basic order processing structure

The simplified workflow shows the core flow: ValidateOrder → CheckOrderValue (Choice) → ProcessOrder → SendConfirmation → OrderComplete, with an OrderRejected fail state.


![Step 2 — Basic order processing structure](assets/step-02-basic-structure.png){ .tutorial-screenshot }




### Step 3: CheckOrderValue — the routing decision

The Choice state routes high-value orders (> $1000) to RequireApproval, and all others directly to ProcessOrder.


![Step 3 — CheckOrderValue — the routing decision](assets/step-03-core-states-visible.png){ .tutorial-screenshot }




### Step 4: Full order processing workflow loaded

Replaced the simplified YAML with the complete workflow from examples/order-processing/workflow.yaml, including Retry/Catch and Parallel states.


![Step 4 — Full order processing workflow loaded](assets/step-04-full-workflow-yaml.png){ .tutorial-screenshot }




### Step 5: Complete graph with all 7 states

The full workflow graph shows all seven states with Choice branching, Parallel processing, Retry/Catch error handling, and terminal states.


![Step 5 — Complete graph with all 7 states](assets/step-05-full-graph.png){ .tutorial-screenshot }




### Step 6: ValidateOrder — Retry and Catch

Expanding ValidateOrder reveals retry config (3 attempts, exponential backoff for ValidationTimeout) and a Catch clause routing InvalidOrderError to OrderRejected.


![Step 6 — ValidateOrder — Retry and Catch](assets/step-06-validate-retry-catch.png){ .tutorial-screenshot }




### Step 7: ProcessOrder — Parallel branches

Expanding ProcessOrder reveals two parallel branches: ProcessPayment and ReserveInventory, each with their own retry configurations.


![Step 7 — ProcessOrder — Parallel branches](assets/step-07-process-parallel.png){ .tutorial-screenshot }




### Step 8: Order processing workflow — complete

The full order processing workflow demonstrates Task, Choice, Parallel, Succeed, and Fail states with Retry/Catch error handling. This is a production-ready pattern.


![Step 8 — Order processing workflow — complete](assets/step-08-final-complete.png){ .tutorial-screenshot }





---


## Full Walkthrough Video

<video controls width="100%" style="border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
  <source src="assets/video.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>


---


<div class="tutorial-nav">

  [← Tutorial 4: Parallel Processing](tutorial-04-parallel-processing.md)


</div>

