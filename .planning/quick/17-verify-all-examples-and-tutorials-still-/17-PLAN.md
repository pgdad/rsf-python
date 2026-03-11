---
phase: quick-17
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: true
requirements: [QUICK-17]
must_haves:
  truths:
    - "All example test suites pass without failures"
    - "No regressions introduced by recent changes (CI fixes, ruff format, scroll bars, save indicator, doctor fix)"
  artifacts: []
  key_links: []
---

<objective>
Run the full example and tutorial test suite to verify nothing is broken after recent changes (quick-11 through quick-16: rsf doctor fix, save indicator, scroll bars, CI fixes, ruff format).

Purpose: Confidence that recent changes have not regressed example/tutorial functionality.
Output: Test results documented. If failures found, fix them.
</objective>

<execution_context>
@/Users/esa/.claude/get-shit-done/workflows/execute-plan.md
@/Users/esa/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Run example test suite and fix any failures</name>
  <files>tests/test_examples/</files>
  <action>
Run the full example test suite with verbose output:

```
pytest tests/test_examples/ -v
```

If ALL tests pass: record the output showing pass counts per test file.

If any tests FAIL:
1. Diagnose each failure from the traceback
2. Determine if the failure is in test code or production code
3. Fix the root cause (update imports, fix assertions, adjust for renamed APIs, etc.)
4. Re-run to confirm all tests pass

Recent changes that could cause regressions:
- rsf doctor now checks src/handlers/ instead of handlers/ (quick-11)
- Graph editor gained save indicator and scroll bars (quick-12, quick-14)
- CI conftest conflict resolved, ruff format applied, test deps added (quick-15)
- rsf generate handler generation fix (quick-8)

Do NOT modify test expectations to make tests pass unless the test expectation itself is wrong. Fix the underlying code if production behavior changed.
  </action>
  <verify>
    <automated>cd /Users/esa/git/rsf-python && pytest tests/test_examples/ -v 2>&1 | tail -30</automated>
  </verify>
  <done>All tests in tests/test_examples/ pass. Zero failures, zero errors.</done>
</task>

</tasks>

<verification>
pytest tests/test_examples/ -v exits with code 0 (all tests pass)
</verification>

<success_criteria>
- All example tests pass with no failures or errors
- Any fixes committed if changes were needed
- Test results documented in SUMMARY
</success_criteria>

<output>
After completion, create `.planning/quick/17-verify-all-examples-and-tutorials-still-/17-SUMMARY.md`
</output>
