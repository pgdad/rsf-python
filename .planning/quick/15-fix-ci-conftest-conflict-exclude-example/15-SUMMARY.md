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

# Quick Task 15: Fix CI Builds

**One-liner:** Fixed 3 CI failures: conftest plugin collision, ruff formatting violations, and missing test dependencies.

## What Was Done

### 1. Conftest Plugin Collision (pytest)
Both `tests/conftest.py` and `examples/lambda-url-trigger/tests/conftest.py` resolved to the same module name `tests.conftest`. Fixed by removing 7 example testpaths from `pyproject.toml`, keeping only `["tests"]`.

### 2. Ruff Lint Violations
12+ violations (F841, F541, E501, E741, F401) across src/ and tests/. All resolved.

### 3. Ruff Format Violations
49 files had formatting that didn't match `ruff format` expectations. Ran `ruff format .` across entire codebase.

### 4. Missing Test Dependencies
`requests` and `hypothesis` not in dev dependencies. Added to `[project.optional-dependencies] dev`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Remove example testpaths | 03aa4a6 | pyproject.toml |
| 2 | Fix ruff lint violations | a04c7de | 8 files |
| 3 | Ruff format + add missing deps | 9318d6e | 49 files + pyproject.toml |

## Verification

CI run 22958390431: all 3 jobs green (lint, test 3.12, test 3.13)

## Self-Check: PASSED

- [x] CI fully green on all 3 jobs
- [x] No version tag created
