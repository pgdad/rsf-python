---
phase: 35
status: passed
verified: 2026-02-28
---

# Phase 35 Verification: Run All Tests That Do Not Require AWS Access/Resources

## Goal
A single `pytest -m "not integration"` invocation from the project root runs ALL non-AWS tests (both tests/ and examples/*/tests/) with zero failures, and CI does the same.

## Success Criteria Results

### 1. pytest discovers and runs all 744 non-AWS tests
**Status: PASSED**

```
$ pytest -m "not integration" -q
744 passed, 13 deselected in 1.43s
```

Test breakdown:
- 592 unit tests from tests/
- 36 from examples/approval-workflow/tests/
- 39 from examples/data-pipeline/tests/
- 13 from examples/intrinsic-showcase/tests/
- 26 from examples/order-processing/tests/
- 38 from examples/retry-and-recovery/tests/
- Total: 744 non-AWS tests

### 2. All tests pass with zero failures
**Status: PASSED**

744 passed, 0 failed, 0 errors.

### 3. The 13 integration tests remain excluded
**Status: PASSED**

```
$ pytest -m "integration" --collect-only -q
13/757 tests collected (744 deselected)
```

### 4. CI runs the same comprehensive test suite
**Status: PASSED**

CI workflow at `.github/workflows/ci.yml` runs:
```yaml
run: pytest -m "not integration" -v
```

pytest reads `testpaths` from `pyproject.toml`, which now includes all 5 example test directories. No CI workflow changes needed.

## Must-Haves Verification

| Must-Have | Status |
|-----------|--------|
| Single pytest invocation runs all 592 unit + 152 example local tests | PASSED |
| pytest -m "not integration" runs with zero failures | PASSED |
| CI runs all non-AWS tests and fails on any test failure | PASSED |
| 13 integration-marked tests excluded from default run | PASSED |

## Artifacts Verified

| Artifact | Expected | Actual |
|----------|----------|--------|
| pyproject.toml testpaths | includes examples/*/tests | 6 testpaths configured |
| pyproject.toml addopts | --import-mode=importlib | Present |
| .github/workflows/ci.yml | pytest -m "not integration" | Unchanged, reads config from pyproject.toml |

## Overall Result

**PASSED** - All success criteria met. Phase 35 goal fully achieved.
