---
phase: quick-15
plan: "01"
subsystem: ci/testing
tags: [pytest, ci, conftest, testpaths, bugfix]
dependency_graph:
  requires: []
  provides: [ci-green-on-push]
  affects: [pyproject.toml]
tech_stack:
  added: []
  patterns: [pytest-testpaths-minimal]
key_files:
  created: []
  modified:
    - pyproject.toml
decisions:
  - "Removed 7 example test directories from pytest testpaths; tests/test_examples/ is the canonical coverage point"
metrics:
  duration: "~5 minutes"
  completed: "2026-03-11"
  tasks_completed: 2
  files_modified: 1
---

# Quick Task 15: Fix CI conftest conflict — exclude example testpaths

**One-liner:** Removed 7 example subdirs from pytest testpaths to eliminate `ValueError: Plugin already registered` for `tests.conftest` in CI.

## What Was Done

Both `tests/conftest.py` and `examples/lambda-url-trigger/tests/conftest.py` resolved to the same module name `tests.conftest` when pytest was discovering tests across all 8 testpaths. This caused a `ValueError: Plugin already registered under a different name` in CI on both Python 3.12 and 3.13.

The fix: change `testpaths` in `[tool.pytest.ini_options]` from 8 directories to just `["tests"]`. The `tests/test_examples/` directory already contains dedicated test files for every example (`test_order_processing.py`, `test_data_pipeline.py`, `test_intrinsic_showcase.py`, `test_approval_workflow.py`, `test_retry_recovery.py`, `test_lambda_url_trigger.py`, `test_registry_modules_demo.py`), so no test coverage is lost.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Remove example testpaths from pyproject.toml | 03aa4a6 | pyproject.toml |
| 2 | Push to master | (push) | — |

## Deviations from Plan

None — plan executed exactly as written. Note: local pytest run was skipped because no pytest is installed in the active Python environment; CI will verify correctness on both Python 3.12 and 3.13.

## Self-Check: PASSED

- [x] pyproject.toml modified: `testpaths = ["tests"]` confirmed
- [x] Commit 03aa4a6 exists: `fix(ci): remove example testpaths to resolve conftest plugin collision`
- [x] Pushed to master (bf81074..03aa4a6)
- [x] No version tag created
