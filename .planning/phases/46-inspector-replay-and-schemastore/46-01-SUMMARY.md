---
plan: 46-01
status: complete
completed: 2026-03-02
---

# Plan 46-01: Replay Backend API — Summary

## What was built
POST /api/inspect/execution/{id}/replay endpoint that invokes the same Lambda function with the original or modified input payload, enabling execution replay from the inspector UI.

## Key files

### Created
- tests/test_inspect/test_replay.py — 13 tests covering models, client method, and endpoint

### Modified
- src/rsf/inspect/models.py — Added ReplayRequest and ReplayResponse Pydantic models
- src/rsf/inspect/client.py — Added invoke_execution() method with async Lambda invocation and rate limiting
- src/rsf/inspect/router.py — Added POST replay endpoint with terminal status validation

## Self-Check: PASSED
- [x] ReplayRequest accepts optional input_payload
- [x] ReplayResponse includes execution_id, replay_from, function_name, status_code
- [x] invoke_execution calls Lambda with InvocationType='Event'
- [x] Rate limiter respected for replay invocations
- [x] Terminal status validation (400 for RUNNING)
- [x] Original payload used when none provided
- [x] Custom payload forwarded when provided
- [x] 404 for non-existent executions
- [x] All 13 tests pass
- [x] No regressions in existing 59 inspect tests

## Deviations
None.
