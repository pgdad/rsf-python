# Tutorial 3: Wait & Retry

<div class="tutorial-meta">
  <span class="badge badge-difficulty badge-intermediate">Intermediate</span>
  <span class="tutorial-time">20 min</span>
</div>

Use Wait states and retry policies for resilient workflows.

---

## Steps


### Step 1: The starter workflow

Starting from the default rsf init workflow before adding wait and retry logic.


![Step 1 — The starter workflow](assets/step-01-starter-workflow.png){ .tutorial-screenshot }




### Step 2: Enter the wait and retry workflow YAML

Paste a workflow with Retry/Catch on a Task state and a Wait state for polling.


![Step 2 — Enter the wait and retry workflow YAML](assets/step-02-yaml-entered.png){ .tutorial-screenshot }




### Step 3: Five-state workflow with retry and wait

The graph shows SubmitRequest (with Retry/Catch) → WaitForProcessing → CheckStatus → Complete, with a Catch edge to HandleError.


![Step 3 — Five-state workflow with retry and wait](assets/step-03-graph-rendered.png){ .tutorial-screenshot }




### Step 4: SubmitRequest with Retry and Catch

Expanding SubmitRequest reveals retry configuration: 3 attempts with exponential backoff, and a Catch clause routing errors to HandleError.


![Step 4 — SubmitRequest with Retry and Catch](assets/step-04-retry-config.png){ .tutorial-screenshot }




### Step 5: WaitForProcessing — Wait state

The Wait state pauses execution for 10 seconds before checking the status. This is useful for polling patterns.


![Step 5 — WaitForProcessing — Wait state](assets/step-05-wait-config.png){ .tutorial-screenshot }




### Step 6: Complete wait and retry workflow

All five states are connected. The workflow demonstrates retry with backoff, error catching, and timed waits.


![Step 6 — Complete wait and retry workflow](assets/step-06-final-workflow.png){ .tutorial-screenshot }





---


## Full Walkthrough Video

<video controls width="100%" style="border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
  <source src="assets/video.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>


---


<div class="tutorial-nav">

  [← Tutorial 2: Branching Logic](tutorial-02-branching-logic.md)


  [Tutorial 4: Parallel Processing →](tutorial-04-parallel-processing.md)

</div>

