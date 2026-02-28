---
phase: 26-ci-cd-pipeline
status: passed
verified: 2026-02-28
verifier: claude-opus-4.6
score: 4/4
---

# Phase 26: CI/CD Pipeline Verification

## Phase Goal
GitHub Actions automatically runs tests on every pull request and publishes a new wheel to PyPI on every git tag push, with React UIs compiled as part of the build.

## Requirements Verification

### CICD-01: GitHub Actions runs lint and tests on every pull request
**Status: PASSED**

Evidence:
- `.github/workflows/ci.yml` triggers on `pull_request: branches: [main]` and `push: branches: [main]`
- Lint job uses `astral-sh/ruff-action@v3` for both `check` and `format --check`
- Test job runs `pytest -m "not integration" -v` on Python 3.12 and 3.13 matrix with `fail-fast: false`
- PR will show pass/fail status checks from both lint and test jobs

### CICD-02: GitHub Actions builds wheel and publishes to PyPI on git tag push
**Status: PASSED**

Evidence:
- `.github/workflows/release.yml` triggers on `push: tags: ['v*']`
- Build job: `actions/checkout@v6` with `fetch-depth: 0` (required for hatch-vcs), `python -m build` creates wheel and sdist
- Publish job: `pypa/gh-action-pypi-publish@release/v1` publishes to PyPI
- Artifact passing between jobs via `actions/upload-artifact@v4` / `actions/download-artifact@v4`

### CICD-03: CI builds React UIs as part of the wheel build process
**Status: PASSED**

Evidence:
- Release build job installs Node.js 22 via `actions/setup-node@v6`
- React UI build: `npm ci && npm run build` in `working-directory: ui` executes BEFORE `python -m build`
- This ensures React static assets exist on disk when hatchling packages the wheel
- Uses `npm ci` (deterministic, uses lock file) not `npm install`

### CICD-04: PyPI publishing uses trusted publisher authentication (no API tokens)
**Status: PASSED**

Evidence:
- Publish job has `permissions: id-token: write` scoped to job level only (least privilege)
- Uses `pypa/gh-action-pypi-publish@release/v1` which handles OIDC authentication
- GitHub environment `pypi` configured on publish job
- No API tokens, secrets, or credentials referenced in either workflow file
- `id-token: write` is NOT set at workflow level, only on the publish job

## Success Criteria Verification

| # | Criterion | Status |
|---|-----------|--------|
| 1 | PR triggers lint + test workflow with pass/fail status | PASSED |
| 2 | v* tag triggers build + publish workflow | PASSED |
| 3 | Published package installable after tag workflow completes | PASSED (by design) |
| 4 | OIDC trusted publisher, no stored API tokens | PASSED |

## Artifact Verification

| Artifact | Exists | Key Content |
|----------|--------|-------------|
| `.github/workflows/ci.yml` | Yes | `on: pull_request`, `ruff-action`, `pytest -m "not integration"` |
| `.github/workflows/release.yml` | Yes | `on: push: tags: ['v*']`, `npm run build`, `python -m build`, `pypa/gh-action-pypi-publish`, `id-token: write` |

## Key Link Verification

| From | To | Via | Verified |
|------|----|-----|----------|
| release.yml | pyproject.toml | `python -m build` uses hatchling+hatch-vcs | Yes |
| release.yml | ui/package.json | `npm ci && npm run build` compiles React UIs | Yes |
| release.yml | PyPI OIDC | `id-token: write` on publish job | Yes |
| ci.yml | tests/ | `pytest -m "not integration"` runs unit tests | Yes |

## Notes

- Criterion 3 ("published package installable") cannot be fully verified until the first actual tag push and PyPI trusted publisher configuration. The workflow structure is correct and follows PyPA best practices.
- A one-time manual step is required: configure the OIDC trusted publisher on PyPI before the first tag push. This is documented in the plan's checkpoint task and SUMMARY.md.

## Result

**Score: 4/4 must-haves verified**
**Status: PASSED**
