# Tutorial 2: Workflow Validation with `rsf validate`

## What You'll Learn

In this tutorial you will:

- Run `rsf validate` on a workflow and interpret the success output
- Understand the three-stage validation pipeline that `rsf validate` runs
- Intentionally introduce each of the three error types (YAML syntax, Pydantic structural, semantic)
- Read field-path-specific error messages to locate and fix problems in `workflow.yaml`

This tutorial uses a "learn by breaking" approach: you will deliberately introduce errors, observe the output, understand what it means, and restore the correct version. By the end you will be able to author and debug workflow YAML confidently.

---

## Prerequisites

- Completed Tutorial 1: you have run `rsf init my-workflow` and have a `my-workflow/` directory
- The directory contains `workflow.yaml` (the starter template created by `rsf init`)
- RSF is installed and the `rsf` command is available

If you have not completed Tutorial 1, run:

```bash
rsf init my-workflow
cd my-workflow
```

---

## The 3-Stage Validation Pipeline

When you run `rsf validate`, it checks your workflow in three stages, in order:

```
Stage 1: YAML Syntax
   Is the file valid YAML? Can it be parsed?
   If no  → print error, stop
   If yes → continue

Stage 2: Structural Validation (Pydantic)
   Does the parsed YAML match the RSF schema?
   Are required fields present? Are values the right types?
   If no  → print field-path errors, stop
   If yes → continue

Stage 3: Semantic Validation (BFS traversal)
   Are cross-state references consistent?
   Do all Next/Default/Catch.Next values point to real states?
   Are all states reachable from StartAt?
   Is there at least one terminal state?
   If no  → print semantic errors, stop
   If yes → print "Valid: workflow.yaml"
```

**Important:** Validation stops at the first failing stage. If you have a YAML syntax error (Stage 1), you will not see structural or semantic errors until you fix it. Fix errors stage by stage.

---

## Step 1: Validate the Starter Workflow

Change into your project directory and run `rsf validate`:

```bash
cd my-workflow
rsf validate
```

Expected output:

```
Valid: workflow.yaml
```

This means all three stages passed. The starter `workflow.yaml` created by `rsf init` is intentionally valid so you have a working baseline to start from.

> You can also validate a file at any path: `rsf validate path/to/workflow.yaml`

---

## Step 2: Break It — YAML Syntax Error (Stage 1)

A **Stage 1** error means the file cannot be parsed as YAML at all. The most common causes are missing colons, wrong indentation, and unclosed quotes.

### Introduce the error

Open `workflow.yaml` in your editor and replace the entire file with this broken version:

```yaml
rsf_version: "1.0"
Comment: "A minimal RSF workflow — edit to define your state machine"
StartAt HelloWorld

States:
  HelloWorld:
    Type: Pass
    Result:
      message: "Hello from RSF!"
    Next: Done

  Done:
    Type: Succeed
```

The change is on line 3: `StartAt HelloWorld` — the colon after `StartAt` is missing.

### Run the validator

```bash
rsf validate
```

Expected output:

```
Error: Invalid YAML in workflow.yaml: while scanning a simple key
  in "<unicode string>", line 3, column 1:
    StartAt HelloWorld
    ^
could not find expected ':'
  in "<unicode string>", line 5, column 1:
    States:
    ^
```

### How to read this error

**Stage 1** errors always start with `Error: Invalid YAML in workflow.yaml:`. The lines that follow come from the YAML parser itself and point to the exact location in the file.

In this case:
- "while scanning a simple key" — the parser was reading a key-value pair
- `line 3, column 1: StartAt HelloWorld` — the problem is on line 3
- "could not find expected ':'" — a colon is required between the key and value

The YAML parser reports the position where it gave up, which is usually very close to the actual mistake. Look at the line and column numbers it provides.

**Stage 1 errors are always YAML syntax issues.** The fix is always: correct the indentation, add the missing colon, close the open quote, or fix the invalid character.

### Fix it

Restore line 3 to:

```yaml
StartAt: HelloWorld
```

Re-run `rsf validate` and confirm you get `Valid: workflow.yaml`.

---

## Step 3: Break It — Structural Error (Stage 2)

A **Stage 2** error means the YAML is syntactically valid, but its contents do not match the RSF schema. The Pydantic models enforce the allowed field names, required fields, allowed values, and types.

### Introduce the error

Replace the entire contents of `workflow.yaml` with this broken version:

```yaml
rsf_version: "1.0"
Comment: "A minimal RSF workflow — edit to define your state machine"
StartAt: HelloWorld

States:
  HelloWorld:
    Type: Invalid
    Result:
      message: "Hello from RSF!"
    Next: Done

  Done:
    Type: Succeed
```

The change is on line 7: `Type: Invalid` — `Invalid` is not a recognized state type.

### Run the validator

```bash
rsf validate
```

Expected output:

```
Validation errors in workflow.yaml:
  : Input tag 'Invalid' found using 'type' | 'Type' does not match any of the expected tags: 'Task', 'Pass', 'Choice', 'Wait', 'Succeed', 'Fail', 'Parallel', 'Map'
```

### How to read this error

**Stage 2** errors always start with `Validation errors in workflow.yaml:`. Each line below it is one field-level error.

The format is:

```
  {field-path}: {message}
```

In this case the `field-path` is empty (the error arose during union type resolution before a specific field could be identified), but the message is clear: `Type` must be one of the eight recognized state types. `Invalid` is not in that list.

The eight valid state types are: `Task`, `Pass`, `Choice`, `Wait`, `Succeed`, `Fail`, `Parallel`, `Map`.

Here is another example of a **Stage 2** error with a clear field-path — trying to set a negative timeout:

```yaml
HelloWorld:
  Type: Task
  TimeoutSeconds: -5
  Next: Done
```

That would produce:

```
Validation errors in workflow.yaml:
  Task.TimeoutSeconds: Input should be greater than or equal to 0
```

Here `Task.TimeoutSeconds` is the field-path: the state type (`Task`) followed by the field name (`TimeoutSeconds`). The dot-separated path maps directly to the YAML nesting. Use it to find the exact field that failed validation.

**Stage 2 errors mean a field violates the RSF schema.** The fix is: use an allowed value, add a missing required field, or remove a field that doesn't belong on that state type.

### Fix it

Restore line 7 to:

```yaml
    Type: Pass
```

Re-run `rsf validate` and confirm you get `Valid: workflow.yaml`.

---

## Step 4: Break It — Semantic Error (Stage 3)

A **Stage 3** error means the YAML is valid and the schema is correct, but the state machine's logic is inconsistent. Semantic validation catches cross-state reference problems that Pydantic cannot detect: dangling references, unreachable states, and missing terminal states.

### Introduce the error

Replace the entire contents of `workflow.yaml` with this broken version:

```yaml
rsf_version: "1.0"
Comment: "A minimal RSF workflow — edit to define your state machine"
StartAt: HelloWorld

States:
  HelloWorld:
    Type: Pass
    Result:
      message: "Hello from RSF!"
    Next: NonExistent

  Done:
    Type: Succeed
```

Two changes were made:
1. Line 10: `Next: NonExistent` — references a state that does not exist
2. The `Done` state is now unreachable (nothing points to it)

### Run the validator

```bash
rsf validate
```

Expected output:

```
Semantic errors in workflow.yaml:
  States.HelloWorld.Next: Next 'NonExistent' does not reference an existing state
  States.Done: State 'Done' is not reachable from StartAt
```

### How to read this error

**Stage 3** errors always start with `Semantic errors in workflow.yaml:`. Each line is one semantic constraint violation.

The field-path for semantic errors uses uppercase state names as they appear in `workflow.yaml`:

```
  States.HelloWorld.Next: Next 'NonExistent' does not reference an existing state
```

Breaking this down:
- `States.HelloWorld.Next` — look at the `States` block, the `HelloWorld` state, the `Next` field
- The message tells you the exact value (`NonExistent`) and what is wrong (no state with that name exists)

The second error:

```
  States.Done: State 'Done' is not reachable from StartAt
```

This is a reachability error. The validator does a breadth-first traversal from `StartAt` and finds that `Done` is never reached. It became unreachable because `HelloWorld` no longer points to it — it points to `NonExistent` instead.

> Reachability errors often appear as a consequence of a dangling reference error. Fix the reference first, then re-validate. The reachability error will likely disappear on its own.

**Stage 3 errors mean the state machine's logic is inconsistent.** The fix is: correct the state name in the `Next`, `Default`, or `Catch.Next` field to match an existing state exactly (state names are case-sensitive).

### Fix it

Restore line 10 to:

```yaml
    Next: Done
```

Re-run `rsf validate` and confirm you get `Valid: workflow.yaml`.

---

## Step 5: Validate a Custom Workflow

Now validate a slightly more complex workflow to see that `rsf validate` works on real-world patterns. This workflow models a simple order processing scenario with a Task state, a Choice state, and error handling.

Replace the entire contents of `workflow.yaml` with:

```yaml
rsf_version: "1.0"
Comment: "Order processing workflow"
StartAt: ValidateOrder

States:
  ValidateOrder:
    Type: Task
    Next: CheckStock

  CheckStock:
    Type: Choice
    Choices:
      - Variable: "$.in_stock"
        BooleanEquals: true
        Next: ProcessOrder
    Default: OutOfStock

  ProcessOrder:
    Type: Task
    End: true

  OutOfStock:
    Type: Fail
    Error: "OutOfStockError"
    Cause: "Item is not available"
```

Run the validator:

```bash
rsf validate
```

Expected output:

```
Valid: workflow.yaml
```

This workflow has four states:

- `ValidateOrder` — a Task state that transitions to `CheckStock`
- `CheckStock` — a Choice state that routes based on `$.in_stock`; if true goes to `ProcessOrder`, otherwise falls through to `OutOfStock` (the Default)
- `ProcessOrder` — a Task state with `End: true` (a terminal state)
- `OutOfStock` — a Fail state (also a terminal state)

All three validation stages pass:
- **Stage 1:** the file is valid YAML
- **Stage 2:** all fields match the RSF schema (Task, Choice, Fail states with correct field names and types)
- **Stage 3:** all `Next` and `Default` references resolve, all states are reachable from `StartAt`, and at least one terminal state exists

> Choice states use `Choices` (an array of rules) and an optional `Default` field. They do not use `Next`. Choices terminate by pointing each rule's `Next` to the next state. This is a common source of Stage 2 and Stage 3 errors for new users.

---

## Error Reference

Quick reference for the most common validation errors:

| Error Stage | Example Message | What It Means | How to Fix |
|---|---|---|---|
| **Stage 1** (YAML) | `Error: Invalid YAML in workflow.yaml: could not find expected ':'` | The file is not valid YAML — the parser could not parse it | Check the reported line for missing colons, wrong indentation, or unclosed quotes |
| **Stage 2** (Structural) | `Task.TimeoutSeconds: Input should be greater than or equal to 0` | A field value does not satisfy the RSF schema constraint | Check the field-path to locate the field; fix the value or type |
| **Stage 2** (Structural) | `: Input tag 'Invalid' found ... does not match any of the expected tags` | The state `Type` is not a recognized RSF state type | Use one of: `Task`, `Pass`, `Choice`, `Wait`, `Succeed`, `Fail`, `Parallel`, `Map` |
| **Stage 3** (Semantic) | `States.X.Next: Next 'Y' does not reference an existing state` | A `Next` (or `Default` or `Catch.Next`) points to a state name that does not exist | Check state names for typos; names are case-sensitive |
| **Stage 3** (Semantic) | `States.X: State 'X' is not reachable from StartAt` | No transition leads to state `X` — it is orphaned | Add a `Next` or `Default` pointing to this state, or remove the state if it is unused |
| **Stage 3** (Semantic) | `States: State machine must have at least one terminal state (Succeed, Fail, or End: true)` | No state terminates the workflow | Add a `Succeed` or `Fail` state, or add `End: true` to a Task or Pass state |

---

## What's Next

Continue to Tutorial 3: Code Generation with `rsf generate`.

`rsf generate` reads your validated `workflow.yaml` and produces the Python orchestrator code and Terraform infrastructure needed to deploy your workflow as a Lambda Durable Functions state machine. **Always validate before you generate** — `rsf generate` assumes the workflow is valid and will produce incorrect code if the definition has semantic errors.

```bash
rsf generate
```

See Tutorial 3 for the full walkthrough.
