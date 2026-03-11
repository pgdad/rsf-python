---
phase: quick-15
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
autonomous: true
requirements: []
must_haves:
  truths:
    - "pytest runs without conftest plugin registration conflict"
    - "All example tests still execute via tests/test_examples/"
    - "CI passes on both Python 3.12 and 3.13"
  artifacts:
    - path: "pyproject.toml"
      provides: "Fixed pytest testpaths without example dirs"
      contains: 'testpaths = ["tests"]'
  key_links: []
---

<objective>
Fix CI pytest failure caused by conftest.py plugin name collision between
`tests/conftest.py` and `examples/lambda-url-trigger/tests/conftest.py`.

Purpose: Both resolve to module name `tests.conftest` causing
`ValueError: Plugin already registered under a different name`. The example
test directories are redundant in testpaths because `tests/test_examples/`
already covers all example testing.

Output: Updated pyproject.toml, CI passes.
</objective>

<execution_context>
@/Users/esa/.claude/get-shit-done/workflows/execute-plan.md
@/Users/esa/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@pyproject.toml
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove example testpaths from pyproject.toml</name>
  <files>pyproject.toml</files>
  <action>
In pyproject.toml `[tool.pytest.ini_options]`, change `testpaths` from the
current list of 8 directories to just:

```toml
testpaths = ["tests"]
```

Remove these entries:
- "examples/order-processing/tests"
- "examples/data-pipeline/tests"
- "examples/intrinsic-showcase/tests"
- "examples/approval-workflow/tests"
- "examples/retry-and-recovery/tests"
- "examples/lambda-url-trigger/tests"
- "examples/registry-modules-demo/tests"

These are redundant because `tests/test_examples/` already has dedicated test
files for every example (test_order_processing.py, test_data_pipeline.py, etc.)
that import and run the example tests without conftest conflicts.

Keep all other pytest config unchanged (pythonpath, addopts, markers).
  </action>
  <verify>
    <automated>cd /Users/esa/git/rsf-python && python -m pytest -m "not integration" --co -q 2>&1 | tail -5</automated>
  </verify>
  <done>pytest collection succeeds without conftest conflict error, all tests from tests/ and tests/test_examples/ are collected</done>
</task>

<task type="auto">
  <name>Task 2: Verify tests pass and push</name>
  <files></files>
  <action>
Run the full test suite (excluding integration tests) to confirm no regressions:

```bash
python -m pytest -m "not integration" -v
```

Verify that:
1. No conftest collision error
2. Example tests still run via tests/test_examples/
3. All tests pass

Then push to master (do NOT create a version tag):

```bash
git add pyproject.toml
git commit -m "fix(ci): remove example testpaths to resolve conftest plugin collision"
git push origin master
```
  </action>
  <verify>
    <automated>cd /Users/esa/git/rsf-python && python -m pytest -m "not integration" -q 2>&1 | tail -3</automated>
  </verify>
  <done>All tests pass, changes pushed to master, no version tag created</done>
</task>

</tasks>

<verification>
- `pytest -m "not integration" --co` collects tests without error
- `pytest -m "not integration"` runs all tests to passing
- `tests/test_examples/` tests still execute (check output for test_examples filenames)
- No conftest ValueError in output
</verification>

<success_criteria>
- CI green on GitHub after push (no conftest plugin conflict)
- All existing tests still pass (no test coverage lost)
- No version tag created
</success_criteria>

<output>
After completion, create `.planning/quick/15-fix-ci-conftest-conflict-exclude-example/15-SUMMARY.md`
</output>
