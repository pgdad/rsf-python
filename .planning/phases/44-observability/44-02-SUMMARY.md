# Plan 44-02 Summary: rsf cost CLI Command

## Status: COMPLETE

## What was built
Cost estimation CLI command (`rsf cost`) that analyzes a workflow definition and produces an estimated monthly AWS cost breakdown. Covers Lambda invocations (with recursive counting through Parallel branches, Map iterations, and Choice paths), DynamoDB read/write operations, data transfer, and trigger costs (SQS, EventBridge). Supports regional pricing multipliers and both Rich table and JSON output formats.

## Key files
- `src/rsf/cli/cost_cmd.py` -- Full cost estimation engine with pricing tables, recursive state counting, and Rich/JSON output
- `src/rsf/cli/main.py` -- CLI registration (cost command added)
- `tests/test_cli/test_cost.py` -- 27 tests covering pricing, counting, calculation, and CLI integration

## Test results
27/27 tests passed

## Self-Check: PASSED
- [x] All tasks executed
- [x] Tests pass
- [x] Command registered in main.py
- [x] Recursive state counting (Parallel, Map, Choice)
- [x] Regional pricing multipliers
- [x] JSON output format
