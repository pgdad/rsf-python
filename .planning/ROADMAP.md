# Roadmap: RSF — Replacement for Step Functions

## Milestones

- ✅ **v1.0 Core** — Phases 1-11 (shipped 2026-02-25)
- ✅ **v1.1 CLI Toolchain** — Phase 12 (shipped 2026-02-26)
- ✅ **v1.2 Comprehensive Examples & Integration Testing** — Phases 13-17 (shipped 2026-02-26)
- ✅ **v1.3 Comprehensive Tutorial** — Phases 18-20 (shipped 2026-02-26)
- ✅ **v1.4 UI Screenshots** — Phases 21-24 (shipped 2026-02-27)
- ✅ **v1.5 PyPI Packaging & Distribution** — Phases 25-27 (shipped 2026-02-28)
- ✅ **v1.6 Ruff Linting Cleanup** — Phases 28-35 (shipped 2026-03-01)
- 🚧 **v1.7 Lambda Function URL Support** — Phases 36-38 (in progress)

## Phases

<details>
<summary>✅ v1.0 Core (Phases 1-11) — SHIPPED 2026-02-25</summary>

- [x] Phase 1: DSL Core (5/5 plans) — completed 2026-02-25
- [x] Phase 2: Code Generation (3/3 plans) — completed 2026-02-25
- [x] Phase 3: Terraform Generation (2/2 plans) — completed 2026-02-25
- [x] Phase 4: ASL Importer (2/2 plans) — completed 2026-02-25
- [x] Phase 6: Graph Editor Backend (2/2 plans) — completed 2026-02-25
- [x] Phase 7: Graph Editor UI (5/5 plans) — completed 2026-02-25
- [x] Phase 8: Inspector Backend (2/2 plans) — completed 2026-02-25
- [x] Phase 9: Inspector UI (5/5 plans) — completed 2026-02-25
- [x] Phase 10: Testing (9/9 plans) — completed 2026-02-25
- [x] Phase 11: Documentation (4/4 plans) — completed 2026-02-25

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 CLI Toolchain (Phase 12) — SHIPPED 2026-02-26</summary>

- [x] Phase 12: CLI Toolchain (4/4 plans) — completed 2026-02-26

Full details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

<details>
<summary>✅ v1.2 Comprehensive Examples & Integration Testing (Phases 13-17) — SHIPPED 2026-02-26</summary>

- [x] Phase 13: Example Foundation (5/5 plans) — completed 2026-02-26
- [x] Phase 14: Terraform Infrastructure (1/1 plan) — completed 2026-02-26
- [x] Phase 15: Integration Test Harness (1/1 plan) — completed 2026-02-26
- [x] Phase 16: AWS Deployment and Verification (1/1 plan) — completed 2026-02-26
- [x] Phase 17: Cleanup and Documentation (1/1 plan) — completed 2026-02-26

Full details: `.planning/milestones/v1.2-ROADMAP.md`

</details>

<details>
<summary>✅ v1.3 Comprehensive Tutorial (Phases 18-20) — SHIPPED 2026-02-26</summary>

- [x] Phase 18: Getting Started (2/2 plans) — completed 2026-02-26
- [x] Phase 19: Build and Deploy (3/3 plans) — completed 2026-02-26
- [x] Phase 20: Advanced Tools (3/3 plans) — completed 2026-02-26

Full details: `.planning/milestones/v1.3-ROADMAP.md`

</details>

<details>
<summary>✅ v1.4 UI Screenshots (Phases 21-24) — SHIPPED 2026-02-27</summary>

- [x] Phase 21: Playwright Setup (1/1 plan) — completed 2026-02-26
- [x] Phase 22: Mock Fixtures and Server Automation (2/2 plans) — completed 2026-02-27
- [x] Phase 23: Screenshot Capture (1/1 plan) — completed 2026-02-27
- [x] Phase 24: Documentation Integration (1/1 plan) — completed 2026-02-27

Full details: `.planning/milestones/v1.4-ROADMAP.md`

</details>

<details>
<summary>✅ v1.5 PyPI Packaging & Distribution (Phases 25-27) — SHIPPED 2026-02-28</summary>

- [x] Phase 25: Package & Version (1/1 plan) — completed 2026-02-28
- [x] Phase 26: CI/CD Pipeline (1/1 plan) — completed 2026-02-28
- [x] Phase 27: README as Landing Page (1/1 plan) — completed 2026-02-28

Full details: `.planning/milestones/v1.5-ROADMAP.md`

</details>

<details>
<summary>✅ v1.6 Ruff Linting Cleanup (Phases 28-35) — SHIPPED 2026-03-01</summary>

- [x] Phase 28: F401 Unused Imports (2/2 plans) — completed 2026-02-28
- [x] Phase 29: F841 Unused Variables — completed 2026-02-28
- [x] Phase 30: F541 f-string Without Placeholders — completed 2026-02-28
- [x] Phase 31: E402 Import Not at Top of File — completed 2026-02-28
- [x] Phase 32: E741 Ambiguous Variable Names — completed 2026-02-28
- [x] Phase 33: E501 Line Too Long — completed 2026-02-28
- [x] Phase 34: Config Cleanup — completed 2026-02-28
- [x] Phase 35: Run All Tests That Do Not Require AWS Access/Resources (1/1 plan) — completed 2026-03-01

</details>

### v1.7 Lambda Function URL Support (In Progress)

**Milestone Goal:** Add optional Lambda Function URL support so users can trigger durable workflow executions via HTTP POST, with a new example and tutorial.

- [ ] **Phase 36: DSL and Terraform** - Lambda URL DSL field, validation, and Terraform resource generation
- [ ] **Phase 37: Example Workflow** - New example demonstrating Lambda URL invocation with local and integration tests
- [ ] **Phase 38: Tutorial** - New tutorial covering Lambda URL configuration, deployment, and HTTP invocation

## Phase Details

### Phase 28: F401 Unused Imports
**Goal**: The entire codebase (including examples/) is linted and all unused imports are eliminated or justified
**Depends on**: Phase 27
**Requirements**: CONF-01, F401-01, F401-02, F401-03, F401-04, F401-05, F401-06
**Success Criteria** (what must be TRUE):
  1. `exclude = ["examples"]` is removed from pyproject.toml ruff config so examples/ is linted
  2. `ruff check src/` reports zero F401 violations
  3. `ruff check tests/` reports zero F401 violations
  4. `ruff check examples/` reports zero F401 violations
  5. F401 is removed from the `ignore` list in pyproject.toml
**Plans:** 2/2 plans executed ✓
Plans:
- [x] 28-01-PLAN.md — Fix all 61 F401 violations across src/, tests/, and examples/
- [x] 28-02-PLAN.md — Update pyproject.toml ruff config (remove examples exclusion, remove F401 from ignore)

### Phase 29: F841 Unused Variables
**Goal**: All unused variable assignments are eliminated across the whole codebase
**Depends on**: Phase 28
**Requirements**: F841-01, F841-02, F841-03
**Success Criteria** (what must be TRUE):
  1. `ruff check src/ tests/` reports zero F841 violations
  2. `ruff check examples/` reports zero F841 violations
  3. F841 is removed from the `ignore` list in pyproject.toml
**Plans**: Complete ✓

### Phase 30: F541 f-string Without Placeholders
**Goal**: All f-strings that contain no interpolation expressions are converted to regular strings
**Depends on**: Phase 29
**Requirements**: F541-01, F541-02
**Success Criteria** (what must be TRUE):
  1. `ruff check .` reports zero F541 violations
  2. F541 is removed from the `ignore` list in pyproject.toml
**Plans**: Complete ✓

### Phase 31: E402 Import Not at Top of File
**Goal**: All import statements appear at the top of their files or carry justified inline suppressions; no redundant noqa comments remain
**Depends on**: Phase 30
**Requirements**: E402-01, E402-02, E402-03, E402-04
**Success Criteria** (what must be TRUE):
  1. `ruff check src/` reports zero E402 violations
  2. `ruff check examples/` reports zero E402 violations
  3. Redundant `# noqa: E402` in cli/main.py is removed
  4. E402 is removed from the `ignore` list in pyproject.toml
**Plans**: Complete ✓

### Phase 32: E741 Ambiguous Variable Names
**Goal**: All single-letter ambiguous variable names (l, O, I) are renamed to clear, descriptive names
**Depends on**: Phase 31
**Requirements**: E741-01, E741-02
**Success Criteria** (what must be TRUE):
  1. `ruff check .` reports zero E741 violations
  2. E741 is removed from the `ignore` list in pyproject.toml
**Plans**: Complete ✓

### Phase 33: E501 Line Too Long
**Goal**: All lines in examples/ that exceed 120 characters are shortened
**Depends on**: Phase 32
**Requirements**: E501-01, E501-02
**Success Criteria** (what must be TRUE):
  1. `ruff check examples/` reports zero E501 violations
  2. `ruff check .` reports zero E501 violations across the entire codebase
**Plans**: Complete ✓

### Phase 34: Config Cleanup
**Goal**: The ruff ignore list is empty and the full codebase passes strict ruff checks with zero suppressions
**Depends on**: Phase 33
**Requirements**: CONF-02
**Success Criteria** (what must be TRUE):
  1. The `ignore` list in pyproject.toml is empty (or absent)
  2. `ruff check .` exits with code 0 and zero violations reported
  3. The CI lint step passes on the final commit
**Plans**: Complete ✓

### Phase 35: Run All Tests That Do Not Require AWS Access/Resources
**Goal**: A single `pytest -m "not integration"` invocation from the project root runs ALL non-AWS tests (both tests/ and examples/*/tests/) with zero failures, and CI does the same
**Requirements**: None (standalone quality phase)
**Depends on**: Phase 34
**Success Criteria** (what must be TRUE):
  1. `pytest -m "not integration"` discovers and runs all 744 non-AWS tests (592 unit + 152 example local)
  2. All tests pass with zero failures
  3. The 13 integration tests remain excluded
  4. CI runs the same comprehensive test suite
**Plans:** 1/1 plans complete ✓

Plans:
- [x] 35-01-PLAN.md — Fix pytest config (importmode=importlib, testpaths), verify CI runs full non-AWS test suite ✓

### Phase 36: DSL and Terraform
**Goal**: Users can add a `lambda_url` block to their workflow YAML and the generated Terraform includes a complete `aws_lambda_function_url` resource with correct auth and IAM
**Depends on**: Phase 35
**Requirements**: DSL-01, DSL-02, TF-01, TF-02, TF-03
**Success Criteria** (what must be TRUE):
  1. User can add `lambda_url: {enabled: true, auth_type: NONE}` (or `AWS_IAM`) to workflow YAML and `rsf validate` accepts it
  2. `rsf validate` rejects invalid `auth_type` values with a clear error message identifying the invalid field
  3. `rsf generate` followed by `rsf deploy` produces Terraform that includes an `aws_lambda_function_url` resource when `lambda_url.enabled` is true
  4. The generated Terraform outputs include the Lambda Function URL endpoint value after `terraform apply`
  5. When `auth_type: AWS_IAM` is set, the generated IAM policy includes the `lambda:InvokeFunctionUrl` permission
**Plans**: TBD

### Phase 37: Example Workflow
**Goal**: Users can study a working example that demonstrates triggering a durable execution via HTTP POST to a Lambda Function URL, with both local tests and a real-AWS integration test
**Depends on**: Phase 36
**Requirements**: EX-01, EX-02, EX-03
**Success Criteria** (what must be TRUE):
  1. A new example directory (`examples/lambda-url-trigger/`) exists with DSL YAML, Python handlers, and Terraform that uses the `lambda_url` feature
  2. `pytest -m "not integration"` runs the example's local tests and they pass with zero failures
  3. Running the integration test against real AWS verifies that an HTTP POST to the Lambda URL triggers and completes a durable execution
**Plans**: TBD

### Phase 38: Tutorial
**Goal**: Users can follow a step-by-step tutorial that walks them from adding the `lambda_url` DSL field through deploying via Terraform to invoking the workflow with a curl POST
**Depends on**: Phase 37
**Requirements**: TUT-01, TUT-02
**Success Criteria** (what must be TRUE):
  1. A new tutorial document exists covering how to add `lambda_url` configuration to workflow YAML and how to run `rsf deploy` to provision the Lambda URL resource
  2. The tutorial includes a working curl command that users can copy-paste to POST to their Lambda URL and trigger a durable execution
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 28. F401 Unused Imports | v1.6 | 2/2 | Complete | 2026-02-28 |
| 29. F841 Unused Variables | v1.6 | 1/1 | Complete | 2026-02-28 |
| 30. F541 f-string Without Placeholders | v1.6 | 1/1 | Complete | 2026-02-28 |
| 31. E402 Import Not at Top of File | v1.6 | 1/1 | Complete | 2026-02-28 |
| 32. E741 Ambiguous Variable Names | v1.6 | 1/1 | Complete | 2026-02-28 |
| 33. E501 Line Too Long | v1.6 | 1/1 | Complete | 2026-02-28 |
| 34. Config Cleanup | v1.6 | 1/1 | Complete | 2026-02-28 |
| 35. Run All Tests (Non-AWS) | v1.6 | 1/1 | Complete | 2026-03-01 |
| 36. DSL and Terraform | v1.7 | 0/? | Not started | - |
| 37. Example Workflow | v1.7 | 0/? | Not started | - |
| 38. Tutorial | v1.7 | 0/? | Not started | - |
