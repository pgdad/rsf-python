# Requirements: RSF — Ruff Linting Cleanup

**Defined:** 2026-02-28
**Core Value:** Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.

## v1.6 Requirements

Requirements for ruff linting cleanup. Each maps to roadmap phases.

### Config

- [ ] **CONF-01**: Ruff `exclude = ["examples"]` is removed — all Python code is linted
- [ ] **CONF-02**: Ruff `ignore` list is empty — no rules suppressed globally

### F401 — Unused Imports

- [x] **F401-01**: All unused imports in `src/` are removed or justified with inline `# noqa: F401`
- [x] **F401-02**: All unused imports in `tests/` are removed
- [x] **F401-03**: All unused imports in `examples/` are removed
- [x] **F401-04**: Side-effect imports in `functions/__init__.py` use `__all__` or inline `# noqa: F401`
- [x] **F401-05**: Generated `handlers/__init__.py` code uses appropriate `# noqa: F401` for side-effect imports
- [ ] **F401-06**: F401 is removed from the global `ignore` list

### F841 — Unused Variables

- [ ] **F841-01**: All unused variables in `src/` and `tests/` are removed or used
- [ ] **F841-02**: All unused variables in `examples/` are removed or used
- [ ] **F841-03**: F841 is removed from the global `ignore` list

### F541 — f-string Without Placeholders

- [ ] **F541-01**: All f-strings without placeholders are converted to regular strings
- [ ] **F541-02**: F541 is removed from the global `ignore` list

### E402 — Import Not at Top of File

- [ ] **E402-01**: All E402 violations in `src/` are fixed or justified with inline `# noqa: E402`
- [ ] **E402-02**: All E402 violations in `examples/` conftest files are fixed or justified
- [ ] **E402-03**: Redundant `# noqa: E402` in `cli/main.py` is cleaned up
- [ ] **E402-04**: E402 is removed from the global `ignore` list

### E741 — Ambiguous Variable Name

- [ ] **E741-01**: All ambiguous variable names (`l`, `O`, `I`) are renamed to clear names
- [ ] **E741-02**: E741 is removed from the global `ignore` list

### E501 — Line Too Long

- [ ] **E501-01**: All lines exceeding 120 characters in `examples/` are shortened
- [ ] **E501-02**: `ruff check .` passes with zero violations across the entire codebase

## Future Requirements

None — this is a self-contained code quality milestone.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Enabling additional ruff rule categories (ANN, PLR, UP, I, etc.) | Would be a separate milestone; current scope is removing existing ignores only |
| ruff format changes | Formatting is already passing; this milestone covers linting only |
| Type annotation improvements | Separate concern from linting cleanup |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONF-01 | Phase 28 | Complete |
| CONF-02 | Phase 34 | Complete |
| F401-01 | Phase 28 | Complete |
| F401-02 | Phase 28 | Complete |
| F401-03 | Phase 28 | Complete |
| F401-04 | Phase 28 | Complete |
| F401-05 | Phase 28 | Complete |
| F401-06 | Phase 28 | Complete |
| F841-01 | Phase 29 | Complete |
| F841-02 | Phase 29 | Complete |
| F841-03 | Phase 29 | Complete |
| F541-01 | Phase 30 | Complete |
| F541-02 | Phase 30 | Complete |
| E402-01 | Phase 31 | Complete |
| E402-02 | Phase 31 | Complete |
| E402-03 | Phase 31 | Complete |
| E402-04 | Phase 31 | Complete |
| E741-01 | Phase 32 | Complete |
| E741-02 | Phase 32 | Complete |
| E501-01 | Phase 33 | Complete |
| E501-02 | Phase 33 | Complete |

**Coverage:**
- v1.6 requirements: 21 total
- Mapped to phases: 21
- Complete: 21 ✓

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-02-28 after milestone completion*
