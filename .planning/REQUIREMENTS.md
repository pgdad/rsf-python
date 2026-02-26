# Requirements: RSF Comprehensive Tutorial

**Defined:** 2026-02-26
**Core Value:** Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.

## v1.3 Requirements

Requirements for the Comprehensive Tutorial milestone. Each maps to roadmap phases.

### Project Setup

- [x] **SETUP-01**: User can follow a tutorial to scaffold a new RSF project with `rsf init` and understand each generated file
- [x] **SETUP-02**: User can follow a tutorial to validate workflow YAML with `rsf validate` and interpret 3-stage validation errors

### Code Generation & Deployment

- [x] **DEPLOY-01**: User can follow a tutorial to generate orchestrator code and handler stubs with `rsf generate`
- [ ] **DEPLOY-02**: User can follow a tutorial to deploy a workflow to AWS with `rsf deploy` using complete Terraform
- [ ] **DEPLOY-03**: User can follow a tutorial to use `rsf deploy --code-only` fast path for iterating on handler logic
- [ ] **DEPLOY-04**: User can invoke the deployed Lambda, verify output, and tear down infrastructure with provided scripts

### ASL Migration

- [ ] **MIGR-01**: User can follow a tutorial to import an existing ASL JSON file with `rsf import` and get RSF YAML + handler stubs

### Visual Tools

- [ ] **VIS-01**: User can follow a tutorial to launch the graph editor with `rsf ui` and visually edit a workflow
- [ ] **VIS-02**: User can follow a tutorial to deploy a dedicated inspection workflow to AWS with complete Terraform
- [ ] **VIS-03**: User can follow a tutorial to inspect a running execution with `rsf inspect` using time machine scrubbing and live updates

## Future Requirements

None — this is a documentation milestone.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Video tutorials | Text-based tutorials only — video production out of scope |
| Interactive web-based tutorials | Tutorials are Markdown documents with code, not hosted apps |
| Tutorials for programmatic API usage | CLI is the user interface, not Python imports |
| Non-English translations | English only for v1.3 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SETUP-01 | Phase 18 | Complete |
| SETUP-02 | Phase 18 | Complete |
| DEPLOY-01 | Phase 19 | Complete |
| DEPLOY-02 | Phase 19 | Pending |
| DEPLOY-03 | Phase 19 | Pending |
| DEPLOY-04 | Phase 19 | Pending |
| MIGR-01 | Phase 20 | Pending |
| VIS-01 | Phase 20 | Pending |
| VIS-02 | Phase 20 | Pending |
| VIS-03 | Phase 20 | Pending |

**Coverage:**
- v1.3 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-26*
*Last updated: 2026-02-26 after roadmap creation (phases 18-20 assigned)*
