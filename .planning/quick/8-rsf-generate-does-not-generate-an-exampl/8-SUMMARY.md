---
phase: quick-8
plan: 1
subsystem: cli/codegen
tags: [bugfix, templates, codegen, init]
dependency_graph:
  requires: []
  provides: [working-init-generate-flow]
  affects: [cli-templates, codegen-stubs]
tech_stack:
  added: []
  patterns: [task-state-handler-generation]
key_files:
  created: []
  modified:
    - src/rsf/cli/templates/workflow.yaml
    - src/rsf/cli/templates/handler_example.py
    - src/rsf/cli/templates/test_example.py
    - tests/test_cli/test_init.py
decisions:
  - Changed HelloWorld from Type: Pass to Type: Task so rsf generate produces handler stubs
  - Aligned handler_example.py with current rsf.registry API (was using deprecated rsf.functions.decorators)
metrics:
  duration: 87s
  completed: "2026-03-06T21:53:32Z"
---

# Quick Task 8: Fix rsf generate to produce handler on default scaffold

Updated default workflow template and handler example so `rsf init` followed by `rsf generate` produces a usable handler stub file in `src/handlers/`.

## What Changed

### Task 1: Update default workflow template to use Task state and align handler example (55a4551)

**Problem:** The default `workflow.yaml` created by `rsf init` used `Type: Pass` for HelloWorld, which meant `rsf generate` produced zero handler stubs (codegen only generates stubs for Task states). Additionally, `handler_example.py` used the deprecated `rsf.functions.decorators` import and the old `(event, context)` function signature.

**Fix:**
- `workflow.yaml`: Changed HelloWorld from `Type: Pass` to `Type: Task`, removed the inline `Result:` block (Task states get results from their handler)
- `handler_example.py`: Updated import from `rsf.functions.decorators` to `rsf.registry`, changed function signature from `(event: dict, context: dict)` to `(input_data: dict)` matching the current codegen stub template
- `test_example.py`: Updated test calls from `hello_world({}, {})` to `hello_world({})` to match the new single-argument signature

### Task 2: Verify rsf init + rsf generate produces handler and update tests (9eb6739)

- Added `test_init_then_generate_produces_handler` integration test that runs the full `rsf init` + `rsf generate` flow and asserts `src/handlers/hello_world.py` is created
- Updated `test_init_workflow_yaml_is_valid` to verify the scaffolded workflow contains at least one `Type: Task` state
- All 34 tests across `test_init.py`, `test_generate.py`, and `test_init_templates.py` pass

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- 34/34 tests pass across test_init.py (6), test_generate.py (10), test_init_templates.py (18)
- Integration test confirms end-to-end: `rsf init` creates project, `rsf generate` produces `hello_world.py` handler stub

## Self-Check: PASSED

All 5 files verified present. Both commits (55a4551, 9eb6739) confirmed in git log.
