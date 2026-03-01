---
phase: 39
status: passed
verified: 2026-03-01
requirements: [INFRA-01, DSL-06]
---

# Phase 39: Infrastructure Decoupling and Workflow Timeout — Verification

## Phase Goal

> Users can generate workflow code without any Terraform output, and can set an execution timeout that terminates the entire workflow if exceeded

## Success Criteria Verification

### SC1: Infrastructure generation is optional
**Status: PASSED**

- `rsf generate --no-infra` flag exists and is accepted
- The `--no-infra` flag on `rsf generate` exits 0 and creates orchestrator.py + handler stubs with no Terraform files
- The `--no-infra` flag on `rsf deploy` skips all Terraform generation, init, and apply steps
- `--no-infra` and `--code-only` are correctly rejected as mutually exclusive

**Evidence:**
- `src/rsf/cli/generate_cmd.py` contains `no_infra` parameter
- `src/rsf/cli/deploy_cmd.py` contains `no_infra` parameter with mutual exclusion logic
- 7 tests verify all scenarios in `tests/test_cli/test_generate.py` and `tests/test_cli/test_deploy.py`

### SC2: Top-level TimeoutSeconds field works in workflow.yaml
**Status: PASSED**

- `TimeoutSeconds: 300` parses successfully with `definition.timeout_seconds == 300`
- `TimeoutSeconds: 0` is rejected by Pydantic validation (`gt=0`)
- `TimeoutSeconds: -5` is rejected by Pydantic validation
- `TimeoutSeconds` is optional (None when absent)

**Evidence:**
- `src/rsf/dsl/models.py` line: `timeout_seconds: int | None = Field(default=None, alias="TimeoutSeconds", gt=0)`
- 5 tests in `tests/test_dsl/test_models.py::TestWorkflowTimeout`

### SC3: Generated orchestrator enforces timeout
**Status: PASSED**

- When `TimeoutSeconds` is set, generated orchestrator contains:
  - `import time`
  - `_workflow_start_time = time.monotonic()` before the while loop
  - `WorkflowTimeoutError` check at the top of each while-loop iteration
  - `class WorkflowTimeoutError(Exception)` with timeout_seconds and elapsed attributes
- When `TimeoutSeconds` is not set, none of this code is emitted (backward compatible)

**Evidence:**
- `src/rsf/codegen/templates/orchestrator.py.j2` contains conditional blocks
- `src/rsf/codegen/generator.py` passes `timeout_seconds` to template
- 3 tests in `tests/test_codegen/test_generator.py::TestTimeoutCodeGeneration`

### SC4: rsf validate reports errors for invalid timeout
**Status: PASSED**

- Zero and negative timeouts are rejected at Pydantic parse level (before `rsf validate`)
- Extremely large timeouts (>30 days / 2592000s) produce a semantic warning
- Valid timeouts produce no errors or warnings

**Evidence:**
- `src/rsf/dsl/validator.py` contains `_validate_timeout` function
- 3 tests in `tests/test_dsl/test_validator.py::TestTimeoutValidation`

## Requirements Cross-Reference

| Requirement | Status | Verified By |
|-------------|--------|-------------|
| INFRA-01 | Complete | SC1: --no-infra flag on generate and deploy |
| DSL-06 | Complete | SC2, SC3, SC4: TimeoutSeconds validation and enforcement |

## Test Coverage

- **Total tests run:** 295 (full suite: dsl + codegen + cli)
- **All pass:** Yes
- **New tests added:** 18 (7 for --no-infra, 11 for timeout)
- **Regressions:** None

## Commits

1. `6bb029a` test(39-01): failing tests for --no-infra
2. `8e419b8` feat(39-01): implement --no-infra flag
3. `a3deb15` docs(39-01): plan summary
4. `a2241af` test(39-02): failing tests for timeout enforcement
5. `f60ca9f` feat(39-02): implement timeout enforcement
6. `a0e41e4` docs(39-02): plan summary

## Verdict

**PASSED** -- All 4 success criteria verified. Both requirements (INFRA-01, DSL-06) are complete. 295 tests pass with 18 new tests and zero regressions.
