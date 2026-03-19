# Tutorial 1: Hello Workflow

<div class="tutorial-meta">
  <span class="badge badge-difficulty badge-beginner">Beginner</span>
  <span class="tutorial-time">10 min</span>
</div>

Build your first RSF workflow with Task and Succeed states.

---

## Steps


### Step 1: The starter workflow

After rsf init, you have a two-state workflow: HelloWorld (Task) → Done (Succeed)


![Step 1 — The starter workflow](assets/step-01-starter-workflow.png){ .tutorial-screenshot }




### Step 2: Drag a Task state from the palette

Drag the Task item from the palette onto the canvas to add a new state


![Step 2 — Drag a Task state from the palette](assets/demo.gif){ .tutorial-gif }





### Step 3: Rename the state in the YAML editor

Edit the YAML to add a "ProcessData" state and connect it between HelloWorld and Done


![Step 3 — Rename the state in the YAML editor](assets/step-03-yaml-editor.png){ .tutorial-screenshot }




### Step 4: New Task state appears on the canvas

A new Task state "ProcessData" has been added by editing the YAML.


![Step 4 — New Task state appears on the canvas](assets/step-04-task-added.png){ .tutorial-screenshot }





### Step 5: Complete three-state workflow

The workflow now has three states: HelloWorld → ProcessData → Done


![Step 5 — Complete three-state workflow](assets/step-05-workflow-complete.png){ .tutorial-screenshot }




### Step 6: Verify the completed workflow

All three states are connected: HelloWorld → ProcessData → Done. The workflow is valid.


![Step 6 — Verify the completed workflow](assets/step-06-final-verification.png){ .tutorial-screenshot }





---


## Full Walkthrough Video

<video controls width="100%" style="border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
  <source src="assets/video.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>


---


<div class="tutorial-nav">

  [← Smoke Test — Capture Fixture](tutorial-00-smoke.md)


  [Tutorial 2: Branching Logic →](tutorial-02-branching-logic.md)

</div>

