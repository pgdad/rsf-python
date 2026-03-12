---
phase: quick-19
plan: 01
subsystem: integration-testing
tags: [integration, aws, lambda, terraform, examples]

dependency_graph:
  requires: []
  provides: [verified-integration-tests, verified-examples]
  affects: [examples/*/src/, src/rsf/codegen/emitter.py, tests/mock_sdk.py]

tech_stack:
  added: []
  patterns:
    - "Duration(seconds=n) constructor for SDK wait calls"
    - "src/handlers/ for Lambda-deployed handler implementations"
    - "src/generated/orchestrator.py for RSF-generated orchestrators"

key_files:
  modified:
    - src/rsf/codegen/emitter.py
    - src/rsf/codegen/generator.py
    - tests/mock_sdk.py
    - tests/test_mock_sdk/test_mock_context.py
    - tests/test_integration/test_sdk_integration.py
    - examples/approval-workflow/src/generated/orchestrator.py
    - examples/lambda-url-trigger/src/generated/orchestrator.py
    - examples/lambda-url-trigger/terraform/terraform.tfvars
    - examples/registry-modules-demo/deploy.sh
    - examples/registry-modules-demo/.gitignore
    - fixtures/snapshots/approval-workflow.py.snapshot
  created:
    - examples/registry-modules-demo/src/handlers/validate_image.py
    - examples/registry-modules-demo/src/handlers/resize_image.py
    - examples/registry-modules-demo/src/handlers/analyze_content.py
    - examples/registry-modules-demo/src/handlers/catalogue_image.py
    - examples/registry-modules-demo/src/handlers/__init__.py

decisions:
  - "Use Duration(seconds=n) constructor (not Duration.seconds(n)) for real SDK compatibility"
  - "Package src/generated/orchestrator.py in Lambda zip, not root orchestrator.py"
  - "Remove src/handlers/ from registry-modules-demo gitignore to track real implementations"
  - "Force-update Lambda function code directly when terraform lifecycle ignore_changes blocks redeploy"

metrics:
  duration: "~8 hours (across 2 sessions)"
  completed: "2026-03-12"
  tasks_completed: 3
  files_changed: 25
---

# Quick Task 19 Plan 01: Run All Integration Tests and Examples Summary

All 20 integration tests pass across all 7 examples with real AWS infrastructure deployment. Multiple SDK API issues and packaging bugs were discovered and fixed during this run.

## Results

| Example | Tests | Result | Infrastructure |
|---------|-------|--------|---------------|
| order-processing | 3/3 | PASSED | Torn down |
| data-pipeline | 3/3 | PASSED | Torn down |
| intrinsic-showcase | 2/2 | PASSED | Torn down |
| approval-workflow | 3/3 | PASSED | Torn down |
| retry-and-recovery | 2/2 | PASSED | Torn down |
| lambda-url-trigger | 4/4 | PASSED | Torn down |
| registry-modules-demo | 3/3 | PASSED | Torn down |
| **Total** | **20/20** | **ALL PASSED** | **No orphans** |

## Commits

| Hash | Description |
|------|-------------|
| dc8526f | Update to real AWS Lambda Durable Functions SDK API |
| 7b93126 | Implement result_path support in code generator |
| 2f5be88 | Switch query_logs from Logs Insights to filter_log_events |
| aad7a9b | Fix handler deployment for all 6 standard examples |
| bf9cf8a | Fix lambda-url-trigger region and HTTP timeout |
| 9e5bb03 | Use Duration(seconds=n) for Wait states in codegen and mock SDK |
| a27abd9 | Fix registry-modules-demo packaging and handler deployment |

## Deviations from Plan

Multiple critical bugs were found and fixed during execution. All were Rule 1 (auto-fix bugs) or Rule 2 (auto-add missing critical functionality).

### Auto-fixed Issues

**1. [Rule 1 - Bug] Real SDK uses different step() signature**
- **Found during:** Task 1 (first test run attempt)
- **Issue:** Generated orchestrators called `context.step('name', handler, data)` but real SDK is `context.step(lambda ctx: handler(data), 'name')`
- **Fix:** Updated `emitter.py` `_emit_task()` to use lambda wrapper pattern
- **Files modified:** `src/rsf/codegen/emitter.py`, all example orchestrators
- **Commit:** dc8526f

**2. [Rule 2 - Missing] ResultPath not applied to step results**
- **Found during:** Task 1 (data-pipeline and approval-workflow failures)
- **Issue:** Task states with ResultPath were replacing entire input_data instead of merging at the path
- **Fix:** Added `_apply_result_path()` calls in Task state emission and Pass/Map/Parallel states
- **Files modified:** `src/rsf/codegen/generator.py`, `src/rsf/codegen/emitter.py`
- **Commit:** 7b93126

**3. [Rule 1 - Bug] CloudWatch query_logs used Logs Insights (indexing delay)**
- **Found during:** Task 1 (log verification tests failing despite logs existing)
- **Issue:** Logs Insights queries have an indexing delay; `filter_log_events` is immediate
- **Fix:** Switched conftest.py `query_logs()` to use `filter_log_events` paginator
- **Files modified:** `tests/test_examples/conftest.py`
- **Commit:** 2f5be88

**4. [Rule 1 - Bug] Handler stubs in src/handlers/ instead of real implementations**
- **Found during:** Task 1 (data-pipeline FAILED — handlers raised NotImplementedError)
- **Issue:** `src/handlers/` had stub files; real implementations were in `handlers/` (local dev only)
- **Fix:** Synced all real handler implementations from `handlers/` to `src/handlers/` for all 6 standard examples
- **Files modified:** All `examples/*/src/handlers/*.py`
- **Commit:** aad7a9b

**5. [Rule 2 - Missing] Map item processor and Parallel branch handlers not imported**
- **Found during:** Task 1 (data-pipeline Map handlers not registered)
- **Issue:** Code generator only collected top-level Task handlers; nested handlers in Map.ItemProcessor and Parallel branches were missing from orchestrator imports
- **Fix:** Updated generator.py to traverse Map and Parallel nested states for handler collection
- **Files modified:** `src/rsf/codegen/generator.py`
- **Commit:** aad7a9b

**6. [Rule 1 - Bug] lambda-url-trigger deployed to us-east-1 (wrong region)**
- **Found during:** Task 1 (lambda-url-trigger POST timeout)
- **Issue:** terraform.tfvars missing `aws_region = "us-east-2"`; terraform defaulted to us-east-1
- **Fix:** Added `aws_region = "us-east-2"` to terraform.tfvars; destroyed us-east-1 deployment
- **Files modified:** `examples/lambda-url-trigger/terraform/terraform.tfvars`
- **Commit:** bf9cf8a

**7. [Rule 1 - Bug] lambda-url-trigger HTTP body not parsed**
- **Found during:** Task 1 (lambda-url-trigger execution failed)
- **Issue:** Lambda Function URL events send `body` as a JSON string; orchestrator was receiving the raw HTTP event structure instead of the parsed payload
- **Fix:** Added HTTP body parsing at start of orchestrator's lambda_handler
- **Files modified:** `examples/lambda-url-trigger/src/generated/orchestrator.py`
- **Commit:** bf9cf8a

**8. [Rule 1 - Bug] Duration.seconds(n) TypeError - wrong Duration API**
- **Found during:** Task 1 (approval-workflow FAILED after Wait state)
- **Issue:** Real SDK's `Duration` is a dataclass; `Duration.seconds` is an int field (= 0), not a classmethod. `Duration.seconds(5)` raised `TypeError: 'int' object is not callable`. Also, the initial fix `context.wait(5, name)` was wrong — real SDK needs `context.wait(Duration(...), name)`
- **Fix:** Changed emitter to generate `context.wait(Duration(seconds=n), name)`. Updated mock SDK to match real SDK `Duration(seconds=n)` constructor API
- **Files modified:** `src/rsf/codegen/emitter.py`, `tests/mock_sdk.py`, `tests/test_mock_sdk/test_mock_context.py`
- **Commit:** 9e5bb03

**9. [Rule 1 - Bug] registry-modules-demo root orchestrator uses old SDK API**
- **Found during:** Task 2 (registry-modules-demo FAILED)
- **Issue:** Root `orchestrator.py` used `context.step(name, handler, data)` (old 3-arg API); real SDK is `context.step(func, name)`. The deploy.sh packaged root `orchestrator.py` not `src/generated/orchestrator.py`
- **Fix:** Updated deploy.sh to package `src/generated/orchestrator.py` (created by `rsf generate`) instead of root `orchestrator.py`
- **Files modified:** `examples/registry-modules-demo/deploy.sh`
- **Commit:** a27abd9

**10. [Rule 1 - Bug] registry-modules-demo src/handlers/ had stubs not real implementations**
- **Found during:** Task 2 (registry-modules-demo handlers would raise NotImplementedError)
- **Issue:** `src/handlers/` was gitignored and contained stubs; real implementations were in root `handlers/` but deploy.sh now packages from `src/handlers/`
- **Fix:** Removed `src/handlers/` from .gitignore, copied real implementations to `src/handlers/`
- **Files modified:** `examples/registry-modules-demo/.gitignore`, `examples/registry-modules-demo/src/handlers/*.py`
- **Commit:** a27abd9

## Infrastructure Cleanup

All AWS resources torn down after testing:
- 7 Lambda functions deployed and destroyed
- 7 IAM roles created and destroyed
- 1 DynamoDB table (data-pipeline) created and destroyed
- 1 DynamoDB table (registry-modules-demo: image-catalogue) created and destroyed
- 1 SQS DLQ (registry-modules-demo) created and destroyed
- 3 CloudWatch alarms (registry-modules-demo) created and destroyed
- 1 SNS topic (registry-modules-demo) created and destroyed
- Debug function `rsf-duration-probe` deleted manually
- All CloudWatch log groups deleted

No orphaned resources remain.

## Self-Check: PASSED

- All 7 example test files exist at `tests/test_examples/test_*.py`
- All 20 integration tests passed in final run
- Summary file exists at `.planning/quick/19-run-all-integration-tests-and-examples-w/19-SUMMARY.md`
- Commits exist: dc8526f, 7b93126, 2f5be88, aad7a9b, bf9cf8a, 9e5bb03, a27abd9
