# Tutorial 2: Branching Logic

<div class="tutorial-meta">
  <span class="badge badge-difficulty badge-beginner">Beginner</span>
  <span class="tutorial-time">15 min</span>
</div>

Add Choice states to route workflow execution based on conditions.

---

## Steps


### Step 1: The starter workflow

Starting from the default rsf init workflow before adding branching logic.


![Step 1 — The starter workflow](assets/step-01-starter-workflow.png){ .tutorial-screenshot }




### Step 2: Enter the branching workflow YAML

Paste a workflow with a Choice state that branches based on validation results.


![Step 2 — Enter the branching workflow YAML](assets/step-02-yaml-entered.png){ .tutorial-screenshot }




### Step 3: Five-state workflow with Choice branching

The graph shows ValidateInput → CheckResult (Choice) branching to ProcessItem or InvalidInput.


![Step 3 — Five-state workflow with Choice branching](assets/step-03-graph-rendered.png){ .tutorial-screenshot }




### Step 4: Choice state expanded

Expanding CheckResult reveals its branching rules: if $.valid is true, go to ProcessItem; otherwise, go to InvalidInput.


![Step 4 — Choice state expanded](assets/step-04-choice-expanded.png){ .tutorial-screenshot }




### Step 5: Complete branching logic workflow

All five states are connected with proper Choice branching. The workflow validates input and routes to success or failure.


![Step 5 — Complete branching logic workflow](assets/step-05-final-workflow.png){ .tutorial-screenshot }





---


## Full Walkthrough Video

<video controls width="100%" style="border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
  <source src="assets/video.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>


---


<div class="tutorial-nav">

  [← Tutorial 1: Hello Workflow](tutorial-01-hello-workflow.html)


  [Tutorial 3: Wait & Retry →](tutorial-03-wait-and-retry.html)

</div>

