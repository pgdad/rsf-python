# Roadmap: RSF — Replacement for Step Functions

## Milestones

- ✅ **v1.0 Core** — Phases 1-11 (shipped 2026-02-25)
- ✅ **v1.1 CLI Toolchain** — Phase 12 (shipped 2026-02-26)
- ✅ **v1.2 Comprehensive Examples & Integration Testing** — Phases 13-17 (shipped 2026-02-26)
- ✅ **v1.3 Comprehensive Tutorial** — Phases 18-20 (shipped 2026-02-26)
- 🚧 **v1.4 UI Screenshots** — Phases 21-24 (in progress)

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

### 🚧 v1.4 UI Screenshots (In Progress)

**Milestone Goal:** Automated Playwright screenshots of the graph editor and execution inspector for all 5 example workflows, embedded in example READMEs and tutorial docs.

- [x] **Phase 21: Playwright Setup** - Configure Playwright as dev dependency with browser automation support
- [x] **Phase 22: Mock Fixtures and Server Automation** - Create mock execution data and server lifecycle management for all 5 examples (completed 2026-02-27)
- [x] **Phase 23: Screenshot Capture** - Capture graph editor and inspector screenshots for all 5 examples via single npm script (completed 2026-02-27)
- [ ] **Phase 24: Documentation Integration** - Embed screenshots in example READMEs and tutorial docs

## Phase Details

### Phase 21: Playwright Setup
**Goal**: Playwright is installed and runnable as a dev dependency so the screenshot automation scripts have a working browser automation foundation
**Depends on**: Phase 20 (v1.3 complete)
**Requirements**: CAPT-01
**Success Criteria** (what must be TRUE):
  1. Running `npm install` in the ui/ directory installs Playwright and its chromium browser
  2. A developer can run a minimal Playwright script that opens a browser and navigates to a URL without errors
  3. Playwright is listed as a devDependency in ui/package.json with a pinned version
**Plans**: 1 plan

Plans:
- [x] 21-01-PLAN.md — Install Playwright devDependency and verify with smoke test script

### Phase 22: Mock Fixtures and Server Automation
**Goal**: Mock execution fixture data exists for all 5 workflows and scripts can start/stop the rsf ui and rsf inspect servers automatically so screenshots can be taken without real AWS
**Depends on**: Phase 21
**Requirements**: CAPT-02, CAPT-03
**Success Criteria** (what must be TRUE):
  1. Each of the 5 examples (order-processing, approval-workflow, data-pipeline, retry-and-recovery, intrinsic-showcase) has a mock execution fixture file that the inspector can load
  2. The inspector displays meaningful state when loaded with the mock fixture (states shown, event timeline populated)
  3. A script starts rsf ui for a given example, confirms the server is ready, and stops it cleanly after use
  4. A script starts rsf inspect with mock fixture data and stops it cleanly after use
**Plans**: 2 plans

Plans:
- [ ] 22-01-PLAN.md — Create mock execution fixtures for all 5 examples and a mock inspect server
- [ ] 22-02-PLAN.md — Create server lifecycle automation scripts for graph editor and inspector

### Phase 23: Screenshot Capture
**Goal**: All 15 screenshots (graph editor full layout, graph editor DSL view, and execution inspector for each of 5 examples) are captured as PNG files in docs/images/ via a single npm script
**Depends on**: Phase 22
**Requirements**: CAPT-04, CAPT-05, CAPT-06, CAPT-07
**Success Criteria** (what must be TRUE):
  1. Running `npm run screenshots` (or equivalent) in ui/ generates all 15 PNG files in docs/images/ without manual intervention
  2. Graph editor full-layout screenshots show the complete workflow graph with all nodes and edges visible for each of the 5 examples
  3. Graph editor DSL-editing screenshots show the YAML editor panel open alongside the graph for each of the 5 examples
  4. Execution inspector screenshots show a populated inspector view (state timeline, event data) for each of the 5 examples
  5. Re-running the script overwrites existing files and completes without error
**Plans**: 1 plan

Plans:
- [ ] 23-01-PLAN.md — Capture all 15 screenshots via Playwright and wire up npm run screenshots

### Phase 24: Documentation Integration
**Goal**: All 15 screenshots are embedded in example READMEs and the two relevant tutorial documents so users can see what the UI looks like without running the tool
**Depends on**: Phase 23
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04
**Success Criteria** (what must be TRUE):
  1. Each of the 5 example READMEs renders both graph editor screenshots (full graph + DSL view) when viewed on GitHub
  2. Each of the 5 example READMEs renders the execution inspector screenshot when viewed on GitHub
  3. Tutorial 07 (graph-editor) contains embedded graph editor screenshots that illustrate the workflow described in the text
  4. Tutorial 08 (execution-inspector) contains embedded inspector screenshots that illustrate the time machine and state views described in the text
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. DSL Core | v1.0 | 5/5 | Complete | 2026-02-25 |
| 2. Code Generation | v1.0 | 3/3 | Complete | 2026-02-25 |
| 3. Terraform Generation | v1.0 | 2/2 | Complete | 2026-02-25 |
| 4. ASL Importer | v1.0 | 2/2 | Complete | 2026-02-25 |
| 6. Graph Editor Backend | v1.0 | 2/2 | Complete | 2026-02-25 |
| 7. Graph Editor UI | v1.0 | 5/5 | Complete | 2026-02-25 |
| 8. Inspector Backend | v1.0 | 2/2 | Complete | 2026-02-25 |
| 9. Inspector UI | v1.0 | 5/5 | Complete | 2026-02-25 |
| 10. Testing | v1.0 | 9/9 | Complete | 2026-02-25 |
| 11. Documentation | v1.0 | 4/4 | Complete | 2026-02-25 |
| 12. CLI Toolchain | v1.1 | 4/4 | Complete | 2026-02-26 |
| 13. Example Foundation | v1.2 | 5/5 | Complete | 2026-02-26 |
| 14. Terraform Infrastructure | v1.2 | 1/1 | Complete | 2026-02-26 |
| 15. Integration Test Harness | v1.2 | 1/1 | Complete | 2026-02-26 |
| 16. AWS Deployment and Verification | v1.2 | 1/1 | Complete | 2026-02-26 |
| 17. Cleanup and Documentation | v1.2 | 1/1 | Complete | 2026-02-26 |
| 18. Getting Started | v1.3 | 2/2 | Complete | 2026-02-26 |
| 19. Build and Deploy | v1.3 | 3/3 | Complete | 2026-02-26 |
| 20. Advanced Tools | v1.3 | 3/3 | Complete | 2026-02-26 |
| 21. Playwright Setup | v1.4 | 1/1 | Complete | 2026-02-26 |
| 22. Mock Fixtures and Server Automation | 2/2 | Complete    | 2026-02-27 | - |
| 23. Screenshot Capture | 1/1 | Complete    | 2026-02-27 | - |
| 24. Documentation Integration | v1.4 | 0/TBD | Not started | - |
