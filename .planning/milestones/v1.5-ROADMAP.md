# Roadmap: RSF — Replacement for Step Functions

## Milestones

- ✅ **v1.0 Core** — Phases 1-11 (shipped 2026-02-25)
- ✅ **v1.1 CLI Toolchain** — Phase 12 (shipped 2026-02-26)
- ✅ **v1.2 Comprehensive Examples & Integration Testing** — Phases 13-17 (shipped 2026-02-26)
- ✅ **v1.3 Comprehensive Tutorial** — Phases 18-20 (shipped 2026-02-26)
- ✅ **v1.4 UI Screenshots** — Phases 21-24 (shipped 2026-02-27)
- 🚧 **v1.5 PyPI Packaging & Distribution** — Phases 25-27 (in progress)

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

### v1.5 PyPI Packaging & Distribution (In Progress)

**Milestone Goal:** Make RSF installable via `pip install rsf` with bundled UIs, git-tag versioning, and CI/CD publishing to PyPI.

- [x] **Phase 25: Package & Version** - Installable Python package with bundled React UIs and git-tag-derived versioning
- [x] **Phase 26: CI/CD Pipeline** - GitHub Actions automated testing on PRs and publishing to PyPI on tag push (completed 2026-02-28)
- [x] **Phase 27: README as Landing Page** - README updated as polished PyPI and GitHub landing page with badges and quick start (completed 2026-02-28)

## Phase Details

### Phase 25: Package & Version
**Goal**: RSF is installable via `pip install rsf` from source with bundled React UI static assets and git-tag-derived version numbers
**Depends on**: Phase 24 (v1.4 complete)
**Requirements**: PKG-01, PKG-02, PKG-03, PKG-04, PKG-05, VER-01, VER-02, VER-03
**Success Criteria** (what must be TRUE):
  1. Running `pip install .` in the repo installs the `rsf` CLI command with all subcommands functional
  2. `rsf ui` and `rsf inspect` serve their React UIs from bundled static assets without npm or node installed
  3. Running `rsf --version` displays the version string derived from the current git tag (e.g., `1.5.0`)
  4. On a repo with no release tag, `rsf --version` displays a dev version (e.g., `1.5.0.dev3+gabcdef`)
  5. The built wheel contains correct package metadata: authors, description, classifiers, project URLs, and Apache-2.0 license
**Plans**: 1/1 (direct implementation)

### Phase 26: CI/CD Pipeline
**Goal**: GitHub Actions automatically runs tests on every pull request and publishes a new wheel to PyPI on every git tag push, with React UIs compiled as part of the build
**Depends on**: Phase 25
**Requirements**: CICD-01, CICD-02, CICD-03, CICD-04
**Success Criteria** (what must be TRUE):
  1. Opening a pull request triggers a GitHub Actions workflow that runs lint and the full test suite; the PR shows a pass/fail status check
  2. Pushing a `v*` git tag triggers a separate GitHub Actions workflow that builds the wheel (including React UI compilation) and publishes it to PyPI
  3. The published package on PyPI is installable immediately after the tag workflow completes (`pip install rsf==<version>` works)
  4. PyPI publishing uses OIDC trusted publisher authentication — no API tokens stored in repository secrets
**Plans**: 1 plan
Plans:
- [x] 26-01-PLAN.md -- CI/CD workflows (ci.yml for PR checks + release.yml for tag-triggered PyPI publishing)

### Phase 27: README as Landing Page
**Goal**: The README serves as a polished landing page on both GitHub and PyPI, with accurate install instructions, a working quick-start example, and status badges
**Depends on**: Phase 26
**Requirements**: README-01, README-02, README-03, README-04
**Success Criteria** (what must be TRUE):
  1. The README contains a `pip install rsf` install command that users can copy and run to get a working CLI
  2. The README contains a quick-start sequence (init -> generate -> deploy) showing the end-to-end workflow with commands and expected output
  3. The README displays a PyPI version badge, a CI status badge, and a license badge that all link to their respective targets
  4. The README renders without broken images, missing sections, or formatting errors on both the GitHub repository page and the PyPI project page
**Plans**: 1 plan
Plans:
- [x] 27-01-PLAN.md -- Polish README with badges, tightened quick-start, hero screenshots, and absolute URLs

## Progress

**Execution Order:** 25 -> 26 -> 27

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 25. Package & Version | v1.5 | 1/1 | Complete | 2026-02-28 |
| 26. CI/CD Pipeline | v1.5 | 1/1 | Complete | 2026-02-28 |
| 27. README as Landing Page | v1.5 | 1/1 | Complete | 2026-02-28 |
