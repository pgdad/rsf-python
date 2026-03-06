---
phase: quick-8
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - src/rsf/cli/templates/workflow.yaml
  - src/rsf/cli/templates/handler_example.py
  - src/rsf/cli/templates/test_example.py
  - src/rsf/cli/init_cmd.py
  - tests/test_cli/test_init.py
autonomous: true
requirements: [QUICK-8]
must_haves:
  truths:
    - "rsf init creates a workflow.yaml with a Task state named HelloWorld"
    - "rsf generate on the default scaffolded project produces a handler stub in src/handlers/"
    - "The example_handler.py from rsf init matches what rsf generate would produce for HelloWorld Task"
  artifacts:
    - path: "src/rsf/cli/templates/workflow.yaml"
      provides: "Default workflow template with HelloWorld as Task state"
      contains: "Type: Task"
    - path: "src/rsf/cli/templates/handler_example.py"
      provides: "Example handler matching the HelloWorld Task state"
  key_links:
    - from: "src/rsf/cli/templates/workflow.yaml"
      to: "src/rsf/codegen/generator.py"
      via: "Task state type triggers handler stub generation"
      pattern: "Type: Task"
---

<objective>
Fix `rsf generate` to produce an example handler file when run on a default scaffolded project.

Purpose: The default `workflow.yaml` template created by `rsf init` uses `Type: Pass` for the HelloWorld state, which means `rsf generate` produces zero handler stubs (the codegen only creates stubs for Task states). Users expect `rsf generate` to produce handler files they can edit. Changing HelloWorld to `Type: Task` makes the init-then-generate workflow produce a useful handler stub in `src/handlers/`.

Output: Updated workflow template, handler example, and passing tests.
</objective>

<execution_context>
@/home/esa/.claude/get-shit-done/workflows/execute-plan.md
@/home/esa/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/rsf/cli/templates/workflow.yaml
@src/rsf/cli/templates/handler_example.py
@src/rsf/cli/templates/test_example.py
@src/rsf/cli/init_cmd.py
@src/rsf/codegen/generator.py
@src/rsf/codegen/templates/handler_stub.py.j2
@tests/test_cli/test_init.py
@tests/test_cli/test_generate.py

<interfaces>
<!-- The codegen only creates handler stubs for Task states (not Pass/Succeed/etc.) -->
<!-- From src/rsf/codegen/generator.py line 82: -->
```python
task_mappings = [m for m in mappings if m.state_type == "Task" and not m.sub_workflow]
```

<!-- Handler stub template (src/rsf/codegen/templates/handler_stub.py.j2): -->
```python
"""Handler for the {{ state_name }} task state."""

from rsf.registry import state

@state("{{ state_name }}")
def {{ function_name }}(input_data: dict) -> dict:
    """Handler for the {{ state_name }} task state.

    Implement your business logic here.
    """
    raise NotImplementedError("Implement {{ state_name }} handler")
```

<!-- The static handler_example.py currently uses the old decorator API: -->
```python
from rsf.functions.decorators import state  # OLD import
def hello_world(event: dict, context: dict) -> dict:  # OLD signature (event, context)
```

<!-- The codegen handler stub uses the current API: -->
```python
from rsf.registry import state  # CURRENT import
def hello_world(input_data: dict) -> dict:  # CURRENT signature (input_data)
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update default workflow template to use Task state and align handler example</name>
  <files>
    src/rsf/cli/templates/workflow.yaml
    src/rsf/cli/templates/handler_example.py
    src/rsf/cli/templates/test_example.py
  </files>
  <action>
  1. Update `src/rsf/cli/templates/workflow.yaml` — change HelloWorld from `Type: Pass` to `Type: Task`. Remove the `Result:` block (Task states get their result from the handler, not inline). Keep `Next: Done` and the Done Succeed state. The file should be:

  ```yaml
  rsf_version: "1.0"
  Comment: "A minimal RSF workflow — edit to define your state machine"
  StartAt: HelloWorld

  States:
    HelloWorld:
      Type: Task
      Next: Done

    Done:
      Type: Succeed
  ```

  2. Update `src/rsf/cli/templates/handler_example.py` — align with the current codegen handler stub API. The handler_example.py is what `rsf init` places at `src/handlers/example_handler.py` as a pre-made handler that matches the HelloWorld Task state. It must use `from rsf.registry import state` (not the old `rsf.functions.decorators`), and `input_data: dict` signature (not `event, context`). But unlike the bare codegen stub which raises NotImplementedError, this example should contain working logic. Update to:

  ```python
  """Example RSF handler for the HelloWorld task state."""

  from rsf.registry import state


  @state("HelloWorld")
  def hello_world(input_data: dict) -> dict:
      """Handle the HelloWorld state.

      Args:
          input_data: The input data for this state.

      Returns:
          The output to pass to the next state.
      """
      name = input_data.get("name", "World")
      return {"message": f"Hello, {name}!"}
  ```

  3. Update `src/rsf/cli/templates/test_example.py` — fix the function call signature to match the new handler. The handler now takes `input_data` as a single dict argument (no `context` parameter):

  ```python
  """Example tests for RSF handlers."""

  from handlers.example_handler import hello_world


  def test_hello_world_default() -> None:
      """Handler returns default greeting when no name is provided."""
      result = hello_world({})
      assert result == {"message": "Hello, World!"}


  def test_hello_world_with_name() -> None:
      """Handler returns personalized greeting when name is provided."""
      result = hello_world({"name": "RSF"})
      assert result == {"message": "Hello, RSF!"}
  ```
  </action>
  <verify>
    <automated>cd /home/esa/git/rsf-python && .venv/bin/python -m pytest tests/test_cli/test_init.py tests/test_cli/test_generate.py -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>Default workflow.yaml uses Type: Task for HelloWorld. handler_example.py uses current rsf.registry API with input_data signature. test_example.py calls handler with single dict arg.</done>
</task>

<task type="auto">
  <name>Task 2: Verify rsf init + rsf generate produces handler in src/handlers and update tests</name>
  <files>
    tests/test_cli/test_init.py
  </files>
  <action>
  1. Add a new test to `tests/test_cli/test_init.py` that verifies the end-to-end flow: `rsf init` followed by `rsf generate` on the scaffolded project produces a handler stub file. The test should:

     - Run `rsf init my-project` (already creates `src/handlers/example_handler.py`)
     - Run `rsf generate workflow.yaml --output src/generated --handlers-dir src/handlers` from the project dir
     - Assert exit code 0
     - Assert that `src/handlers/hello_world.py` exists (the generated handler stub for the HelloWorld Task)
     - Assert that the output mentions "1 handler" created OR "Skipped" (since example_handler.py pre-exists but hello_world.py should be newly created by generate)

  2. Update the existing `test_init_workflow_yaml_is_valid` test to also verify that the workflow contains a Task state:
     - After loading the YAML, assert that at least one state has `Type: Task`

  3. Run the full test suite for test_init.py and test_generate.py to confirm nothing is broken.
  </action>
  <verify>
    <automated>cd /home/esa/git/rsf-python && .venv/bin/python -m pytest tests/test_cli/test_init.py tests/test_cli/test_generate.py tests/test_cli/test_init_templates.py -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>New integration test confirms rsf init + rsf generate produces handler stubs. All existing init and generate tests pass.</done>
</task>

</tasks>

<verification>
End-to-end validation:
1. `rsf init test-project` creates project with workflow.yaml containing `Type: Task` for HelloWorld
2. `cd test-project && rsf generate` produces `src/handlers/hello_world.py` handler stub
3. All tests pass: `pytest tests/test_cli/test_init.py tests/test_cli/test_generate.py tests/test_cli/test_init_templates.py -x`
</verification>

<success_criteria>
- Default workflow.yaml template has HelloWorld as Type: Task (not Pass)
- `rsf generate` on a freshly-scaffolded project creates at least 1 handler file in src/handlers/
- handler_example.py uses current API (rsf.registry, input_data signature)
- All existing tests in test_init.py, test_generate.py, and test_init_templates.py pass
- New integration test validates the init-then-generate flow
</success_criteria>

<output>
After completion, create `.planning/quick/8-rsf-generate-does-not-generate-an-exampl/8-SUMMARY.md`
</output>
