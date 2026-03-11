---
phase: quick-11
plan: 01
subsystem: cli
tags: [bug-fix, doctor, handlers, path]
dependency_graph:
  requires: []
  provides: [correct-handlers-path-in-doctor]
  affects: [rsf-doctor-command]
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - src/rsf/cli/doctor_cmd.py
    - tests/test_cli/test_doctor.py
decisions:
  - "Use workflow.parent / 'src' / 'handlers' to match rsf init, rsf generate, and rsf deploy canonical path"
metrics:
  duration: "5 minutes"
  completed: "2026-03-11"
---

# Quick Task 11: Fix rsf doctor to check src/handlers/ Summary

**One-liner:** Fixed rsf doctor handlers directory path from `handlers/` to `src/handlers/` to match all other CLI commands.

## What Was Done

`rsf doctor` was checking for handlers in `workflow.parent / "handlers"` (project root), but all other commands use `src/handlers/`:

- `rsf init` scaffolds to `src_dir / "handlers"` (init_cmd.py line 188)
- `rsf generate` outputs to `src/generated/../handlers` (generate_cmd.py)
- `rsf deploy` references `workflow.parent / "src" / "handlers"` (deploy_cmd.py line 89)

This caused `rsf doctor` to incorrectly report handlers as missing even when they existed at `src/handlers/`.

## Tasks Completed

| Task | Description | Commit | Files Modified |
|------|-------------|--------|----------------|
| 1 | Fix handlers directory path in doctor command and update tests | 8c1ea30 | src/rsf/cli/doctor_cmd.py, tests/test_cli/test_doctor.py |

## Changes Made

**src/rsf/cli/doctor_cmd.py (line 487):**
- Before: `handlers_dir = workflow.parent / "handlers" if workflow else None`
- After: `handlers_dir = workflow.parent / "src" / "handlers" if workflow else None`

**tests/test_cli/test_doctor.py (line 222):**
- Before: `handlers_dir = tmp_path / "handlers"`
- After: `handlers_dir = tmp_path / "src" / "handlers"`

## Verification

- `python -m pytest tests/test_cli/test_doctor.py -x -q` — 28 passed
- `grep -n "src.*handlers" src/rsf/cli/doctor_cmd.py` — confirms fix on line 487

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- [x] src/rsf/cli/doctor_cmd.py modified with correct path
- [x] tests/test_cli/test_doctor.py updated with matching path
- [x] All 28 doctor tests pass
- [x] Commit 8c1ea30 exists
