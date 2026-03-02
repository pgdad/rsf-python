---
plan: 45-02
status: complete
started: 2026-03-02
completed: 2026-03-02
requirements_completed: [TEST-02]
---

# Plan 45-02: Chaos Injection Testing Utilities

## What Was Built
ChaosFixture class in rsf.testing.chaos that injects failures (timeout, exception, throttle, custom callable) into specific workflow states during local mock SDK test runs.

## Key Files

### Created
- `src/rsf/testing/__init__.py` -- Public API: `from rsf.testing import ChaosFixture`
- `src/rsf/testing/chaos.py` -- ChaosFixture class, ChaosTimeoutError, ChaosThrottleError
- `tests/test_mock_sdk/test_chaos.py` -- 11 tests covering all failure types and edge cases

## Test Results
- 11/11 chaos injection tests pass
- 21/21 existing mock SDK tests still pass
- Total: 32/32 tests in tests/test_mock_sdk/

## Self-Check: PASSED
- [x] inject_failure(state_name, "timeout") raises ChaosTimeoutError
- [x] inject_failure(state_name, "exception") raises RuntimeError
- [x] inject_failure(state_name, "throttle") raises ChaosThrottleError
- [x] inject_failure(state_name, callable) -- return value or exception propagates
- [x] Multiple failures per test supported (independent states)
- [x] count=1 for one-shot, None for persistent
- [x] reset() clears all failures
- [x] Non-injected states call handlers normally
- [x] Public API accessible from rsf.testing and rsf.testing.chaos
