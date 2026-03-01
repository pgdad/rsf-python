---
phase: 37-example-workflow
status: passed
verified: 2026-03-01
score: 3/3
---

# Phase 37: Example Workflow — Verification

## Phase Goal
Users can study a working example that demonstrates triggering a durable execution via HTTP POST to a Lambda Function URL, with both local tests and a real-AWS integration test

## Requirements Verified

| Requirement | Description | Status |
|-------------|-------------|--------|
| EX-01 | New example workflow demonstrates triggering durable execution via Lambda Function URL POST | PASSED |
| EX-02 | Example includes local tests verifying handler logic without AWS | PASSED |
| EX-03 | Example includes integration test for Lambda URL invocation on real AWS | PASSED |

## Success Criteria

### SC1: Example directory exists with DSL YAML, handlers, and Terraform
**Status:** PASSED

- `examples/lambda-url-trigger/workflow.yaml` exists with `lambda_url: {enabled: true, auth_type: NONE}`
- `examples/lambda-url-trigger/handlers/validate_order.py` and `process_order.py` exist with `@state` decorators
- `examples/lambda-url-trigger/terraform/lambda_url.tf` exists with `aws_lambda_function_url` resource
- `examples/lambda-url-trigger/terraform/outputs.tf` includes `function_url` output
- `examples/lambda-url-trigger/README.md` documents the example

### SC2: Local tests pass with zero failures
**Status:** PASSED

- 19 tests in `examples/lambda-url-trigger/tests/test_local.py`
- All 19 pass via `pytest -m "not integration"`
- Tests cover: workflow parsing (6), lambda_url feature (3), handler unit tests (8), simulation (2)
- Full suite: 779 non-integration tests pass (19 new + 760 existing)

### SC3: Integration test for Lambda URL invocation
**Status:** PASSED

- `tests/test_examples/test_lambda_url_trigger.py` exists
- Marked with `@pytest.mark.integration` (excluded from non-integration runs)
- Uses `requests.post()` to invoke via Lambda Function URL
- Polls for durable execution completion and asserts SUCCEEDED status

## Must-Haves Verification

### Truths
- [x] `examples/lambda-url-trigger/` directory exists with workflow.yaml, handlers, and README
- [x] workflow.yaml includes `lambda_url: {enabled: true, auth_type: NONE}` and parses without errors
- [x] Handlers are simple functions taking a dict and returning a dict, registered via `@state` decorator
- [x] `pytest -m "not integration"` discovers and runs the example's 19 local tests
- [x] All local tests pass with zero failures
- [x] Terraform directory exists with lambda_url.tf for the Function URL resource
- [x] Generated Terraform outputs include the function_url endpoint
- [x] Integration test POSTs to the Lambda URL and verifies execution completes
- [x] Integration test is marked with `@pytest.mark.integration`

### Artifacts
- [x] `examples/lambda-url-trigger/workflow.yaml` — DSL with lambda_url
- [x] `examples/lambda-url-trigger/handlers/validate_order.py` — ValidateOrder handler
- [x] `examples/lambda-url-trigger/handlers/process_order.py` — ProcessOrder handler
- [x] `examples/lambda-url-trigger/README.md` — Example documentation
- [x] `examples/lambda-url-trigger/tests/conftest.py` — Test fixtures
- [x] `examples/lambda-url-trigger/tests/test_local.py` — 19 local tests
- [x] `examples/lambda-url-trigger/terraform/lambda_url.tf` — Lambda URL resource
- [x] `examples/lambda-url-trigger/terraform/outputs.tf` — function_url output
- [x] `tests/test_examples/test_lambda_url_trigger.py` — Integration test

## Conclusion

All 3 success criteria met. All 3 requirements (EX-01, EX-02, EX-03) verified. Phase 37 goal achieved.
