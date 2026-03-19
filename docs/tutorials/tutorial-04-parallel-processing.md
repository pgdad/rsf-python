# Tutorial 4: Parallel Processing

<div class="tutorial-meta">
  <span class="badge badge-difficulty badge-intermediate">Intermediate</span>
  <span class="tutorial-time">20 min</span>
</div>

Run multiple workflow branches concurrently with Parallel states.

---

## Steps


### Step 1: The starter workflow

Starting from the default rsf init workflow before adding parallel processing.


![Step 1 — The starter workflow](assets/step-01-starter-workflow.png){ .tutorial-screenshot }




### Step 2: Enter the parallel processing workflow YAML

Paste a workflow with a Parallel state that runs two branches concurrently.


![Step 2 — Enter the parallel processing workflow YAML](assets/step-02-yaml-entered.png){ .tutorial-screenshot }




### Step 3: Four-state workflow with Parallel processing

The graph shows PrepareData → ProcessBranches (Parallel) → MergeResults → Done.


![Step 3 — Four-state workflow with Parallel processing](assets/step-03-graph-rendered.png){ .tutorial-screenshot }




### Step 4: Parallel state expanded

Expanding ProcessBranches reveals two concurrent branches: EnrichData and ValidateData, both running as Task states.


![Step 4 — Parallel state expanded](assets/step-04-parallel-expanded.png){ .tutorial-screenshot }




### Step 5: Complete parallel processing workflow

All four main states are connected. The workflow demonstrates parallel execution with two concurrent branches that merge results.


![Step 5 — Complete parallel processing workflow](assets/step-05-final-workflow.png){ .tutorial-screenshot }





---


## Full Walkthrough Video

<video controls width="100%" style="border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
  <source src="assets/video.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>


---


<div class="tutorial-nav">

  [← Tutorial 3: Wait & Retry](tutorial-03-wait-and-retry.html)


  [Tutorial 5: Order Processing →](tutorial-05-order-processing.html)

</div>

