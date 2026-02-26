# Phase 16: AWS Deployment and Verification

## Goal
All 5 examples deploy to real AWS, execute successfully, and pass dual-channel assertions.

## Requirements
- **VERF-01**: Each example verifies workflow correctness via Lambda return value assertion
- **VERF-02**: Each example verifies intermediate state transitions via CloudWatch log assertions
- **VERF-03**: All 8 state types verified in real AWS execution across the example set

## Success Criteria
1. Each of the 5 examples reaches SUCCEEDED terminal state
2. Each example has ≥1 CloudWatch log assertion confirming intermediate state transitions
3. All 8 state types observed in real AWS execution (Task, Choice, Parallel, Succeed, Fail, Pass, Wait, Map)

## State Type Coverage Matrix

| State Type | Example(s) | How Exercised |
|-----------|------------|---------------|
| Task | All 5 examples | Handler execution via context.step() |
| Choice | order-processing, approval-workflow, intrinsic-showcase | Branching on data values |
| Parallel | order-processing | ProcessPayment + ReserveInventory concurrent |
| Succeed | All 5 (happy path terminal) | Workflow completion |
| Fail | order-processing (error path) | Empty order → OrderRejected |
| Pass | data-pipeline, approval-workflow, retry-recovery, intrinsic-showcase | Data transformation states |
| Wait | approval-workflow | WaitForReview (5s intervals) |
| Map | data-pipeline | TransformRecords over fetched items |

## Test Structure

Each test file follows a consistent pattern:
1. Class-scoped `deployment` fixture: terraform deploy → IAM wait → invoke → poll → yield → teardown
2. `test_execution_succeeds`: Assert SUCCEEDED status (VERF-01)
3. `test_handler_log_entries`: Query CloudWatch for handler step_name entries (VERF-02)
4. Example-specific assertions (DynamoDB logs, Fail state, approval loop count)

## Test Inputs

| Example | Input | Expected Path |
|---------|-------|---------------|
| order-processing | `{orderId, total:59.98, items:[1 item]}` | ValidateOrder→CheckOrderValue→ProcessOrder(Parallel)→SendConfirmation→OrderComplete |
| data-pipeline | `{source:{bucket, prefix}}` | InitPipeline→FetchRecords→TransformRecords(Map)→StoreResults→PipelineComplete |
| approval-workflow | `{request, userId}` | SubmitRequest→SetApprovalContext→WaitForReview(×4)→EscalateRequest→RequestApproved |
| retry-recovery | `{requestId, payload}` | CallPrimaryService→VerifyResult→ServiceComplete |
| intrinsic-showcase | `{input:{userName}}` | PrepareData→StringOperations→ArrayOperations→MathAndJsonOps→CheckResults→ShowcaseComplete |

## Files Modified
- `tests/test_examples/test_order_processing.py` — Replace stub with full integration tests
- `tests/test_examples/test_data_pipeline.py` — Replace stub with full integration tests
- `tests/test_examples/test_approval_workflow.py` — Replace stub with full integration tests
- `tests/test_examples/test_retry_recovery.py` — Replace stub with full integration tests
- `tests/test_examples/test_intrinsic_showcase.py` — Replace stub with full integration tests
