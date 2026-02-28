---
phase: 26-ci-cd-pipeline
plan: 01
subsystem: infra
tags: [github-actions, ci-cd, pypi, oidc, ruff, pytest]

# Dependency graph
requires:
  - phase: 25-package-version
    provides: pyproject.toml with hatchling+hatch-vcs build system and ui/ React app
provides:
  - CI workflow running lint and tests on PRs and pushes to main
  - Release workflow building React UIs + Python wheel and publishing to PyPI on v* tags
  - OIDC trusted publisher authentication for zero-secret PyPI publishing
affects: [27-readme-landing-page]

# Tech tracking
tech-stack:
  added: [github-actions, astral-sh/ruff-action, pypa/gh-action-pypi-publish]
  patterns: [oidc-trusted-publishing, artifact-passing-between-jobs, matrix-testing]

key-files:
  created:
    - .github/workflows/ci.yml
    - .github/workflows/release.yml
  modified: []

key-decisions:
  - "Used astral-sh/ruff-action@v3 for lint instead of pip-installing ruff — cleaner, maintained by ruff team"
  - "id-token: write permission scoped to publish job only — principle of least privilege"
  - "React UI build runs in same job as Python build — ensures static assets exist on disk when hatchling packages the wheel"

patterns-established:
  - "CI pattern: lint + test jobs as separate concerns, test matrix for Python versions"
  - "Release pattern: build job produces artifact, publish job consumes it via OIDC"

requirements-completed: [CICD-01, CICD-02, CICD-03, CICD-04]

# Metrics
duration: 5min
completed: 2026-02-28
---

# Phase 26: CI/CD Pipeline Summary

**GitHub Actions CI (ruff lint + pytest on PRs) and release workflow (React UI compile + wheel build + OIDC PyPI publish on v* tags)**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-28
- **Completed:** 2026-02-28
- **Tasks:** 2 auto tasks completed, 1 checkpoint (PyPI trusted publisher config)
- **Files created:** 2

## Accomplishments
- CI workflow with ruff lint (check + format) and pytest on Python 3.12/3.13 matrix, triggered on PRs and pushes to main
- Release workflow with full git checkout for hatch-vcs versioning, React UI compilation, Python wheel build, and OIDC-based PyPI publishing
- Zero secrets stored in repository — publishing uses GitHub OIDC trusted publisher

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CI workflow for PR lint and test checks** - `bd3d774` (feat)
2. **Task 2: Create release workflow for tag-triggered PyPI publishing** - `356d889` (feat)

## Files Created/Modified
- `.github/workflows/ci.yml` - PR and main-branch lint (ruff) + test (pytest) workflow
- `.github/workflows/release.yml` - Tag-triggered React UI build, Python wheel build, and OIDC PyPI publish workflow

## Decisions Made
- Used astral-sh/ruff-action@v3 for linting instead of pip-installing ruff — cleaner CI setup and maintained by the ruff team
- Scoped id-token: write to publish job only, not workflow level — principle of least privilege
- React UI build and Python wheel build in same job to ensure static assets are available when hatchling packages the wheel

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
None

## User Setup Required
**External service requires manual configuration.** Before the first v* tag push:
- Configure PyPI OIDC trusted publisher at https://pypi.org/manage/account/publishing/
- Fields: Project Name: rsf, Owner: pgdad, Repository: rsf-python, Workflow: release.yml, Environment: pypi

## Next Phase Readiness
- CI/CD workflows committed and ready for use
- Phase 27 (README as Landing Page) can reference CI badge URL and PyPI badge URL
- PyPI trusted publisher must be configured before first release tag

---
*Phase: 26-ci-cd-pipeline*
*Completed: 2026-02-28*
