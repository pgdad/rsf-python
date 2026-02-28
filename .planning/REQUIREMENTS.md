# Requirements: RSF

**Defined:** 2026-02-28
**Core Value:** Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.

## v1.5 Requirements

Requirements for PyPI Packaging & Distribution milestone. Each maps to roadmap phases.

### Package Structure

- [ ] **PKG-01**: User can install RSF via `pip install rsf` and get the `rsf` CLI command
- [ ] **PKG-02**: Package includes pre-built React UI static assets (graph editor + execution inspector)
- [ ] **PKG-03**: `rsf ui` and `rsf inspect` serve bundled static assets without requiring npm/node
- [ ] **PKG-04**: Package metadata includes authors, description, classifiers, project URLs, and license
- [ ] **PKG-05**: Build process compiles React UIs and bundles output into the Python wheel

### Version Management

- [ ] **VER-01**: Package version is derived from git tags (e.g., `v1.5.0` tag → `1.5.0` version)
- [ ] **VER-02**: `rsf --version` displays the correct version from the installed package
- [ ] **VER-03**: Development installs show dev version (e.g., `1.5.0.dev3+gabcdef`)

### CI/CD Pipeline

- [ ] **CICD-01**: GitHub Actions runs lint and tests on every pull request
- [ ] **CICD-02**: GitHub Actions builds wheel and publishes to PyPI on git tag push
- [ ] **CICD-03**: CI builds React UIs as part of the wheel build process
- [ ] **CICD-04**: PyPI publishing uses trusted publisher authentication (no API tokens)

### README

- [ ] **README-01**: README includes install instructions (`pip install rsf`)
- [ ] **README-02**: README includes quick start showing init → generate → deploy workflow
- [ ] **README-03**: README includes PyPI badge, CI status badge, and license badge
- [ ] **README-04**: README renders correctly on both GitHub and PyPI

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### Distribution

- **DIST-01**: Publish to conda-forge for Anaconda users
- **DIST-02**: Docker image with RSF pre-installed
- **DIST-03**: Homebrew formula for macOS users

### Quality

- **QUAL-01**: PEP 561 py.typed marker for downstream type checking
- **QUAL-02**: Pre-commit hooks configuration
- **QUAL-03**: Code coverage reporting in CI

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Monorepo split (rsf-core, rsf-cli, rsf-ui) | Single package is simpler for users; split if needed later |
| TestPyPI staging | Trusted publisher to real PyPI is sufficient for v1.5 |
| Automated changelog generation | Manual release notes are fine at this scale |
| npm package for UI components | UI is bundled into Python package, not distributed separately |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PKG-01 | Phase 25 | Pending |
| PKG-02 | Phase 25 | Pending |
| PKG-03 | Phase 25 | Pending |
| PKG-04 | Phase 25 | Pending |
| PKG-05 | Phase 25 | Pending |
| VER-01 | Phase 25 | Pending |
| VER-02 | Phase 25 | Pending |
| VER-03 | Phase 25 | Pending |
| CICD-01 | Phase 26 | Pending |
| CICD-02 | Phase 26 | Pending |
| CICD-03 | Phase 26 | Pending |
| CICD-04 | Phase 26 | Pending |
| README-01 | Phase 27 | Pending |
| README-02 | Phase 27 | Pending |
| README-03 | Phase 27 | Pending |
| README-04 | Phase 27 | Pending |

**Coverage:**
- v1.5 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-02-28 after roadmap creation (v1.5 traceability complete)*
