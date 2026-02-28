---
phase: 27-readme-as-landing-page
plan: 01
subsystem: docs
tags: [readme, badges, pypi, shields.io, markdown]

requires:
  - phase: 26-ci-cd-pipeline
    provides: CI/CD workflows (ci.yml, release.yml) referenced by badges
  - phase: 24-documentation-integration
    provides: Screenshot images in docs/images/ used as hero shots
provides:
  - Polished README.md serving as GitHub and PyPI landing page
  - Three clickable status badges (PyPI version, CI, License)
  - Quick-start with expected terminal output for init/generate/deploy/inspect
  - Hero screenshots with absolute raw.githubusercontent.com URLs
  - All documentation links converted to absolute GitHub URLs
affects: []

tech-stack:
  added: []
  patterns:
    - "Absolute URLs for all images and links in README (PyPI compatibility)"
    - "shields.io badges linked to PyPI and GitHub Actions"

key-files:
  created: []
  modified:
    - README.md

key-decisions:
  - "Used raw.githubusercontent.com URLs for images instead of relative paths (required for PyPI rendering)"
  - "Placed screenshots in a Markdown table for side-by-side display on wide screens"
  - "Condensed quick-start from 7 subsections to 5 (install, init, generate, deploy, inspect)"

patterns-established:
  - "Badge row pattern: PyPI version + CI status + License immediately after title"
  - "Quick-start pattern: command block followed by unlabeled output block"

requirements-completed:
  - README-01
  - README-02
  - README-03
  - README-04

duration: 8min
completed: 2026-02-28
---

# Phase 27: README as Landing Page Summary

**Polished README with three status badges, condensed quick-start showing terminal output, hero screenshots, and absolute URLs for PyPI compatibility**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-28
- **Completed:** 2026-02-28
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Added PyPI version, CI status, and Apache 2.0 license badges as clickable links
- Condensed quick-start to show init/generate/deploy/inspect with realistic expected terminal output
- Added two hero screenshots (Graph Editor + Execution Inspector) using absolute raw.githubusercontent.com URLs
- Converted all documentation links from relative to absolute GitHub URLs
- Fixed clone URL placeholder from `your-org` to `pgdad`
- Validated README rendering with twine check (PASSED)

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite README.md as polished landing page** - `0132148` (docs)
2. **Task 2: Validate README renders correctly for PyPI** - (validation only, no file changes)

## Files Created/Modified
- `README.md` - Polished landing page with badges, quick-start, screenshots, and absolute URLs

## Decisions Made
- Removed verbose "Define your workflow" and "Add business logic" subsections from quick-start to keep it concise
- Used side-by-side table layout for screenshots rather than stacked images
- Kept expected terminal output blocks unlabeled (no language specifier) for clean rendering on both GitHub and PyPI

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- README is ready for GitHub and PyPI
- All v1.5 milestone phases complete (25: Package, 26: CI/CD, 27: README)

---
*Phase: 27-readme-as-landing-page*
*Completed: 2026-02-28*
