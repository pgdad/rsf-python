# Roadmap: RSF — Replacement for Step Functions

## Milestones

- ✅ **v1.0 Core** — Phases 1-11 (shipped 2026-02-25)
- ✅ **v1.1 CLI Toolchain** — Phase 12 (shipped 2026-02-26)
- ✅ **v1.2 Comprehensive Examples & Integration Testing** — Phases 13-17 (shipped 2026-02-26)
- ✅ **v1.3 Comprehensive Tutorial** — Phases 18-20 (shipped 2026-02-26)
- ✅ **v1.4 UI Screenshots** — Phases 21-24 (shipped 2026-02-27)
- ✅ **v1.5 PyPI Packaging & Distribution** — Phases 25-27 (shipped 2026-02-28)
- ✅ **v1.6 Ruff Linting Cleanup** — Phases 28-34 (shipped 2026-02-28)

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

### v1.6 Ruff Linting Cleanup (In Progress)

**Milestone Goal:** Fix all ruff linting violations and remove all ignored rules and exclusions so the entire codebase passes strict ruff checks with zero suppressions.

- [x] **Phase 28: F401 Unused Imports** — Remove examples/ exclusion from ruff config; fix all unused imports across src/, tests/, examples/, and generated code (~61 violations) ✓
- [x] **Phase 29: F841 Unused Variables** — Fix all unused variable assignments across src/, tests/, and examples/ (6 violations) ✓
- [x] **Phase 30: F541 f-string Without Placeholders** — Convert all bare f-strings to regular strings (1 violation) ✓
- [x] **Phase 31: E402 Import Not at Top of File** — Fix or justify all out-of-order imports; clean up redundant noqa comments (6 violations) ✓
- [x] **Phase 32: E741 Ambiguous Variable Names** — Rename all ambiguous single-letter variables (2 violations) ✓
- [x] **Phase 33: E501 Line Too Long** — Shorten all lines exceeding 120 characters in examples/ (2 violations) ✓
- [x] **Phase 34: Config Cleanup** — Remove all ignore entries, verify zero violations across the whole codebase ✓

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
**Plans**: TBD

### Phase 30: F541 f-string Without Placeholders
**Goal**: All f-strings that contain no interpolation expressions are converted to regular strings
**Depends on**: Phase 29
**Requirements**: F541-01, F541-02
**Success Criteria** (what must be TRUE):
  1. `ruff check .` reports zero F541 violations
  2. F541 is removed from the `ignore` list in pyproject.toml
**Plans**: TBD

### Phase 31: E402 Import Not at Top of File
**Goal**: All import statements appear at the top of their files or carry justified inline suppressions; no redundant noqa comments remain
**Depends on**: Phase 30
**Requirements**: E402-01, E402-02, E402-03, E402-04
**Success Criteria** (what must be TRUE):
  1. `ruff check src/` reports zero E402 violations
  2. `ruff check examples/` reports zero E402 violations
  3. Redundant `# noqa: E402` in cli/main.py is removed
  4. E402 is removed from the `ignore` list in pyproject.toml
**Plans**: TBD

### Phase 32: E741 Ambiguous Variable Names
**Goal**: All single-letter ambiguous variable names (l, O, I) are renamed to clear, descriptive names
**Depends on**: Phase 31
**Requirements**: E741-01, E741-02
**Success Criteria** (what must be TRUE):
  1. `ruff check .` reports zero E741 violations
  2. E741 is removed from the `ignore` list in pyproject.toml
**Plans**: TBD

### Phase 33: E501 Line Too Long
**Goal**: All lines in examples/ that exceed 120 characters are shortened
**Depends on**: Phase 32
**Requirements**: E501-01, E501-02
**Success Criteria** (what must be TRUE):
  1. `ruff check examples/` reports zero E501 violations
  2. `ruff check .` reports zero E501 violations across the entire codebase
**Plans**: TBD

### Phase 34: Config Cleanup
**Goal**: The ruff ignore list is empty and the full codebase passes strict ruff checks with zero suppressions
**Depends on**: Phase 33
**Requirements**: CONF-02
**Success Criteria** (what must be TRUE):
  1. The `ignore` list in pyproject.toml is empty (or absent)
  2. `ruff check .` exits with code 0 and zero violations reported
  3. The CI lint step passes on the final commit
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 28. F401 Unused Imports | 1/2 | In Progress|  | - |
| 29. F841 Unused Variables | v1.6 | 0/? | Not started | - |
| 30. F541 f-string Without Placeholders | v1.6 | 0/? | Not started | - |
| 31. E402 Import Not at Top of File | v1.6 | 0/? | Not started | - |
| 32. E741 Ambiguous Variable Names | v1.6 | 0/? | Not started | - |
| 33. E501 Line Too Long | v1.6 | 0/? | Not started | - |
| 34. Config Cleanup | v1.6 | 0/? | Not started | - |

### Phase 35: Run All Tests That Do Not Require AWS Access/Resources

**Goal:** A single `pytest -m "not integration"` invocation from the project root runs ALL non-AWS tests (both tests/ and examples/*/tests/) with zero failures, and CI does the same
**Requirements**: None (standalone quality phase)
**Depends on:** Phase 34
**Success Criteria** (what must be TRUE):
  1. `pytest -m "not integration"` discovers and runs all 744 non-AWS tests (592 unit + 152 example local)
  2. All tests pass with zero failures
  3. The 13 integration tests remain excluded
  4. CI runs the same comprehensive test suite
**Plans:** 1/1 plans executed ✓

Plans:
- [x] 35-01-PLAN.md — Fix pytest config (importmode=importlib, testpaths), verify CI runs full non-AWS test suite ✓
