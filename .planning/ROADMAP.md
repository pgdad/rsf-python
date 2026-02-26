# Roadmap: RSF — Replacement for Step Functions

## Milestones

- ✅ **v1.0 Core** — Phases 1-11 (shipped 2026-02-25)
- ✅ **v1.1 CLI Toolchain** — Phase 12 (shipped 2026-02-26)
- ✅ **v1.2 Comprehensive Examples & Integration Testing** — Phases 13-17 (shipped 2026-02-26)
- 🔄 **v1.3 Comprehensive Tutorial** — Phases 18-20 (in progress)

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

### v1.3 Comprehensive Tutorial (Phases 18-20)

- [x] **Phase 18: Getting Started** — Tutorials for project init and workflow validation (completed 2026-02-26)
- [x] **Phase 19: Build and Deploy** — Tutorials for code generation, Terraform deployment, and live AWS verification (completed 2026-02-26)
- [x] **Phase 20: Advanced Tools** — Tutorials for ASL migration, visual graph editing, and execution inspection (completed 2026-02-26)

## Phase Details

### Phase 18: Getting Started
**Goal**: Users can scaffold a new RSF project and validate their workflow YAML with confidence
**Depends on**: Nothing (first v1.3 phase)
**Requirements**: SETUP-01, SETUP-02
**Success Criteria** (what must be TRUE):
  1. User can follow the `rsf init` tutorial step-by-step, run the command, and understand what each generated file (workflow.yaml, handlers.py, pyproject.toml, .gitignore) is for
  2. User can follow the `rsf validate` tutorial, intentionally introduce an error into workflow.yaml, run validation, and interpret the 3-stage error message to locate and fix the problem
  3. User can complete both tutorials in sequence and have a working, validated RSF project ready for code generation
**Plans**: TBD

### Phase 19: Build and Deploy
**Goal**: Users can generate orchestrator code, deploy a workflow to real AWS, iterate on handler logic, invoke the Lambda, and cleanly tear down all infrastructure
**Depends on**: Phase 18
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04
**Success Criteria** (what must be TRUE):
  1. User can follow the `rsf generate` tutorial and get a working orchestrator file + handler stubs, then connect their own business logic via `@state` decorators
  2. User can follow the `rsf deploy` tutorial, run the provided Terraform scripts end-to-end, and have a live Lambda Durable Function deployed in their AWS account
  3. User can follow the `--code-only` fast path tutorial, update a handler, redeploy in seconds (no Terraform re-apply), and verify the change on AWS
  4. User can run the provided invoke script, see the Lambda return value, and run the teardown script to remove all AWS resources with zero orphaned infrastructure
**Plans**: 3 plans
- [ ] 19-01-PLAN.md — rsf generate tutorial (Wave 1)
- [ ] 19-02-PLAN.md — rsf deploy tutorial (Wave 2)
- [ ] 19-03-PLAN.md — code-only, invoke, and teardown tutorial (Wave 3)

### Phase 20: Advanced Tools
**Goal**: Users can migrate existing ASL workflows to RSF, visually edit workflows in the graph editor, and inspect live executions with time machine debugging
**Depends on**: Phase 19
**Requirements**: MIGR-01, VIS-01, VIS-02, VIS-03
**Success Criteria** (what must be TRUE):
  1. User can follow the `rsf import` tutorial, provide a real ASL JSON file, and receive RSF YAML + handler stubs they can immediately validate and generate from
  2. User can follow the `rsf ui` tutorial, launch the graph editor, make a visual change to a workflow, and see the YAML update in the Monaco editor in real time
  3. User can follow the inspection workflow tutorial, deploy the dedicated inspection workflow to AWS using the provided Terraform, and have a running target for the inspector
  4. User can follow the `rsf inspect` tutorial, attach to a live execution, scrub through historical execution states with the time machine, and observe structural data diffs between steps
**Plans**: 3 plans
- [ ] 20-01-PLAN.md — rsf import tutorial (Wave 1)
- [ ] 20-02-PLAN.md — rsf ui graph editor tutorial (Wave 1)
- [ ] 20-03-PLAN.md — inspection deployment + rsf inspect tutorial (Wave 1)

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
| 18. Getting Started | 2/2 | Complete    | 2026-02-26 | - |
| 19. Build and Deploy | 3/3 | Complete    | 2026-02-26 | - |
| 20. Advanced Tools | 3/3 | Complete   | 2026-02-26 | - |
