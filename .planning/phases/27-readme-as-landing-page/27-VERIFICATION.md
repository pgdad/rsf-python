---
phase: 27-readme-as-landing-page
status: passed
verified: 2026-02-28
verifier: automated
---

# Phase 27: README as Landing Page - Verification

## Phase Goal
The README serves as a polished landing page on both GitHub and PyPI, with accurate install instructions, a working quick-start example, and status badges.

## Requirements Verification

### README-01: Install instructions
**Status: PASSED**
- `pip install rsf` command present at line 46 in a bash code block
- Copy-pasteable by users

### README-02: Quick-start showing init -> generate -> deploy
**Status: PASSED**
- `rsf init my-workflow` at line 52 with expected terminal output block showing created files
- `rsf generate` at line 73 with expected terminal output showing orchestrator and handlers
- `rsf deploy` at line 88 with expected terminal output showing code gen + terraform + completion
- `rsf inspect` at line 99 with one-line output description
- Each command followed by realistic expected terminal output

### README-03: Badges (PyPI, CI, License)
**Status: PASSED**
- PyPI version badge: `[![PyPI version](https://img.shields.io/pypi/v/rsf)](https://pypi.org/project/rsf/)` at line 3
- CI status badge: `[![CI](https://github.com/pgdad/rsf-python/actions/workflows/ci.yml/badge.svg)](https://github.com/pgdad/rsf-python/actions/workflows/ci.yml)` at line 4
- License badge: `[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)` at line 5
- All three are clickable links to their respective targets

### README-04: Renders correctly on GitHub and PyPI
**Status: PASSED**
- All images use absolute `raw.githubusercontent.com` URLs (2 screenshot images)
- All documentation links use absolute `github.com/pgdad/rsf-python/blob/main/` URLs (4 doc links)
- No relative `docs/` paths remain
- Clone URL uses `pgdad/rsf-python.git` (not placeholder)
- `twine check` on built wheel returned PASSED

## Must-Have Verification

| # | Must-Have | Status |
|---|-----------|--------|
| 1 | README shows PyPI version badge, CI status badge, and license badge as clickable links | PASSED |
| 2 | README contains a pip install rsf command that users can copy-paste | PASSED |
| 3 | README quick-start shows init, generate, and deploy commands each with expected terminal output | PASSED |
| 4 | README renders without broken images, missing sections, or dead links on both GitHub and PyPI | PASSED |
| 5 | All documentation links use absolute GitHub URLs (not relative paths) | PASSED |

## Artifact Verification

| Artifact | Expected | Actual | Status |
|----------|----------|--------|--------|
| README.md | Contains `img.shields.io/pypi/v/rsf` | Present at line 3 | PASSED |
| README.md badge links | PyPI, CI, License badges linked | All 3 present and linked | PASSED |

## Key Link Verification

| From | To | Via | Status |
|------|----|----|--------|
| README.md badge row | https://pypi.org/project/rsf/ | shields.io PyPI version badge | PASSED |
| README.md badge row | GitHub Actions CI workflow | ci.yml badge.svg | PASSED |
| README.md doc links | github.com/pgdad/rsf-python/blob/main/docs/ | Absolute GitHub URLs | PASSED |

## Score

**5/5 must-haves verified**

## Result

**PASSED** - All requirements (README-01 through README-04) verified. The README serves as a polished landing page with badges, quick-start, screenshots, and absolute URLs compatible with both GitHub and PyPI rendering.
