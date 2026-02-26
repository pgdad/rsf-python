# Tutorial 7: Visual Editing with `rsf ui`

This tutorial walks you through launching the RSF graph editor, viewing your workflow as a
visual graph, editing it from both the graph and YAML sides, and saving your changes back
to disk.

## What You'll Learn

- How to launch the RSF graph editor with `rsf ui`
- How the two-panel layout works: graph view and YAML editor
- How to edit the YAML and watch the graph update in real time
- How to edit the graph and watch the YAML update in real time
- How validation errors appear in the editor
- How to save your changes back to disk

---

## Prerequisites

Before starting, you need:

- RSF installed (`pip install rsf`)
- A workflow YAML file (from Tutorial 1 or Tutorial 6)
- A modern web browser (the editor runs as a local web application)
- No AWS account needed -- the graph editor is fully local

If you do not have a workflow file, create one. Save the following as `workflow.yaml`:

```yaml
rsf_version: "1.0"
Comment: "Order processing workflow"
StartAt: ValidateOrder

States:
  ValidateOrder:
    Type: Task
    Next: CheckAmount

  CheckAmount:
    Type: Choice
    Choices:
      - Variable: "$.amount"
        NumericGreaterThan: 100
        Next: RequireApproval
    Default: ProcessOrder

  RequireApproval:
    Type: Task
    Next: ProcessOrder

  ProcessOrder:
    Type: Task
    End: true
```

---

## Step 1: Launch the Graph Editor

Run `rsf ui` from the directory containing your workflow file:

```bash
rsf ui
```

You should see:

```
Starting RSF Graph Editor on port 8765...
```

The command starts a local web server and opens your browser to `http://127.0.0.1:8765`. The
server loads `workflow.yaml` from the current directory automatically.

To load a different file, pass the path as an argument:

```bash
rsf ui my-workflow.yaml
```

To use a different port:

```bash
rsf ui --port 9000
```

To prevent the browser from opening automatically:

```bash
rsf ui --no-browser
```

> **Tip:** The server runs in the foreground. Keep this terminal open while you use the
> editor. Press Ctrl+C to stop the server when you are done.

---

## Step 2: Navigate the Editor Interface

The editor has a two-panel layout:

**Left panel: Graph view.** Your workflow is rendered as a directed graph. Each state appears
as a node labeled with its name and type (Task, Choice, Succeed, etc.). Transitions are drawn
as directed edges between nodes: `Next` transitions, `Default` branches, and Choice condition
branches all appear as edges. The graph auto-layouts based on the workflow structure.

**Right panel: YAML editor.** A Monaco code editor displays the full YAML source of your
workflow. It provides syntax highlighting, line numbers, and inline validation error markers.

**Toolbar.** At the top of the editor you will find a Save button and a validation status
indicator that shows whether the current YAML is valid.

For the order processing workflow, you should see:

- Four nodes: ValidateOrder (Task), CheckAmount (Choice), RequireApproval (Task),
  ProcessOrder (Task)
- Edges showing the flow: ValidateOrder leads to CheckAmount. CheckAmount branches to
  RequireApproval (when amount > 100) and ProcessOrder (Default). RequireApproval leads
  to ProcessOrder.
- The Choice node has two outgoing edges: one for the numeric condition and one for the
  Default path.

---

## Step 3: Edit YAML and Watch the Graph Update

In the right panel (YAML editor), make a change to add a new state after ProcessOrder.

First, change ProcessOrder to point to a new state. Find this section:

```yaml
  ProcessOrder:
    Type: Task
    End: true
```

Replace it with:

```yaml
  ProcessOrder:
    Type: Task
    Next: SendConfirmation
```

Then add the new state below ProcessOrder:

```yaml
  SendConfirmation:
    Type: Task
    End: true
```

As soon as the YAML is valid, the graph re-renders. You should see a new `SendConfirmation`
node appear in the graph with an edge from `ProcessOrder` to it.

The editor validates YAML on every keystroke and updates the graph when the YAML is
structurally valid. If you introduce a syntax error mid-edit, the graph freezes at the last
valid state and the editor highlights the error inline. Once you fix the syntax, the graph
updates immediately.

---

## Step 4: Edit the Graph and Watch the YAML Update

The graph panel also supports direct editing. Click on a node to select it. The selected
node shows its properties, which you can modify: rename the state, change its type, or
update transition targets.

For example, click the `SendConfirmation` node. Use the property panel or inline editing
to rename it to `NotifyCustomer`. The YAML editor updates immediately to reflect the
new name -- both the state key and any transitions pointing to it.

The bidirectional sync means you can use whichever editing mode is more comfortable for
the change you are making. Complex structural changes (adding Choice branches, Parallel
states, nested Map configurations) are often easier to type directly in YAML. Understanding
the overall flow and catching disconnected states is easier in the graph view.

---

## Step 5: Check Validation Errors

The editor runs the same 3-stage validation as `rsf validate` -- YAML syntax, structural,
and semantic checks -- and shows errors instantly as you type.

To see validation in action, intentionally break the YAML. In the YAML editor, delete the
`StartAt` line. The editor immediately shows a validation error:

- The toolbar validation indicator turns red
- An inline error marker appears in the YAML editor at the location of the issue
- The graph may freeze at the last valid state or show an error overlay

Fix the error by adding the `StartAt` line back:

```yaml
StartAt: ValidateOrder
```

The validation indicator returns to green and the graph re-renders.

> **Tip:** The real-time validation catches errors before you save. This is especially
> useful when restructuring workflows -- you can see immediately if you left a dangling
> transition or misspelled a state name.

---

## Step 6: Save Your Changes

To save your edits back to disk, click the Save button in the toolbar. The editor sends the
current YAML content to the server, which writes it to the workflow file on disk.

Verify the save by opening a new terminal and checking the file:

```bash
cat workflow.yaml
```

The file now contains the updated workflow with the new state you added in Step 3. All
changes made in both the YAML editor and the graph panel are included.

> **Note:** The editor saves the current state of the YAML editor. Any unsaved changes
> are lost if you close the browser tab or stop the server without saving first.

---

## Stopping the Server

In the terminal where `rsf ui` is running, press Ctrl+C:

```
Server stopped
```

The browser tab remains open but loses its connection to the server. Close it manually.

---

## Command Reference

| Option | Default | Description |
|--------|---------|-------------|
| `workflow` (argument) | `workflow.yaml` | Path to the workflow YAML file |
| `--port` / `-p` | `8765` | Port the server listens on |
| `--no-browser` | `false` | Suppress automatic browser launch |

Examples:

```bash
rsf ui                          # Default: workflow.yaml on port 8765
rsf ui my-workflow.yaml         # Load a specific file
rsf ui --port 9000              # Use a different port
rsf ui --no-browser             # Start server without opening browser
```

---

## What's Next

In Tutorial 8, you will use `rsf inspect` to attach to live executions of deployed workflows
and inspect execution history with the time machine scrubber.

Workflows edited in the graph editor can be validated (`rsf validate`), generated
(`rsf generate`), and deployed (`rsf deploy`) using the same pipeline from Tutorials 2-5.

---

*Tutorial 7 of 8 -- RSF Comprehensive Tutorial Series*
