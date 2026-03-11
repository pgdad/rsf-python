---
phase: quick-11
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/rsf/cli/doctor_cmd.py
  - tests/test_cli/test_doctor.py
autonomous: true
requirements: [QUICK-11]
must_haves:
  truths:
    - "rsf doctor checks src/handlers/ directory instead of handlers/"
    - "rsf doctor still works when no handlers directory exists"
  artifacts:
    - path: "src/rsf/cli/doctor_cmd.py"
      provides: "Fixed handlers directory path"
      contains: "src.*handlers"
    - path: "tests/test_cli/test_doctor.py"
      provides: "Updated test for src/handlers path"
  key_links:
    - from: "src/rsf/cli/doctor_cmd.py"
      to: "src/rsf/cli/init_cmd.py"
      via: "Both reference src/handlers as the canonical handlers location"
      pattern: "src.*handlers"
---

<objective>
Fix `rsf doctor` to look for handlers in `src/handlers/` instead of `handlers/` in the project root.

Purpose: The `rsf init` command scaffolds handlers at `src/handlers/`, `rsf generate` outputs to `src/handlers/`, and `rsf deploy` references `src/handlers/`. But `rsf doctor` incorrectly checks `workflow.parent / "handlers"` which is the wrong path, causing it to report handlers as missing even when they exist.

Output: Fixed doctor_cmd.py and updated tests.
</objective>

<execution_context>
@/Users/esa/.claude/get-shit-done/workflows/execute-plan.md
@/Users/esa/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/rsf/cli/doctor_cmd.py
@tests/test_cli/test_doctor.py
@src/rsf/cli/init_cmd.py (reference: line 188 shows `src/handlers` is canonical path)
@src/rsf/cli/deploy_cmd.py (reference: line 89 shows `workflow.parent / "src" / "handlers"`)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix handlers directory path in doctor command and update tests</name>
  <files>src/rsf/cli/doctor_cmd.py, tests/test_cli/test_doctor.py</files>
  <action>
In `src/rsf/cli/doctor_cmd.py`, line 487, change:
```python
handlers_dir = workflow.parent / "handlers" if workflow else None
```
to:
```python
handlers_dir = workflow.parent / "src" / "handlers" if workflow else None
```

This aligns with `rsf init` (init_cmd.py line 188: `src_dir / "handlers"`), `rsf generate` (generate_cmd.py line 87-88: `output_dir.parent / "handlers"` where output_dir defaults to `src/generated`), and `rsf deploy` (deploy_cmd.py line 89: `workflow.parent / "src" / "handlers"`).

In `tests/test_cli/test_doctor.py`, update `TestRunAllChecks.test_includes_project_checks_when_path_exists` (line 208). The test currently creates `tmp_path / "handlers"` as the handlers_dir. Change to create `tmp_path / "src" / "handlers"` instead, since the doctor command now constructs the path internally from the workflow path. Actually, looking more carefully: the test passes `handlers_dir` directly to `run_all_checks()`, so the test path should match what the doctor command would compute. Update the test to pass `handlers_dir=tmp_path / "src" / "handlers"` to match the new expected path structure.
  </action>
  <verify>
    <automated>cd /Users/esa/git/rsf-python && python -m pytest tests/test_cli/test_doctor.py -x -q</automated>
  </verify>
  <done>
    - doctor_cmd.py line 487 references `workflow.parent / "src" / "handlers"` instead of `workflow.parent / "handlers"`
    - All existing doctor tests pass
    - Test for project checks uses `src/handlers` path
  </done>
</task>

</tasks>

<verification>
- `python -m pytest tests/test_cli/test_doctor.py -x -q` -- all tests pass
- `grep -n "src.*handlers" src/rsf/cli/doctor_cmd.py` -- shows the fix on the relevant line
</verification>

<success_criteria>
- `rsf doctor` checks `src/handlers/` directory (matching `rsf init`, `rsf generate`, and `rsf deploy`)
- All existing tests pass with updated paths
</success_criteria>

<output>
After completion, create `.planning/quick/11-fix-rsf-doctor-to-look-for-handlers-in-s/11-SUMMARY.md`
</output>
