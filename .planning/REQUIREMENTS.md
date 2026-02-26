# Requirements: RSF

**Defined:** 2026-02-26
**Core Value:** Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.

## v1.4 Requirements

Requirements for v1.4 UI Screenshots milestone. Each maps to roadmap phases.

### Screenshot Capture

- [ ] **CAPT-01**: Playwright configured as dev dependency with browser automation support
- [ ] **CAPT-02**: Scripts manage rsf ui/inspect server lifecycle (auto start/stop for each example)
- [ ] **CAPT-03**: Mock execution fixture data created for all 5 example workflows
- [ ] **CAPT-04**: Graph editor full-layout screenshot captured for each of 5 examples (saved to docs/images/)
- [ ] **CAPT-05**: Graph editor DSL-editing screenshot captured for each of 5 examples (saved to docs/images/)
- [ ] **CAPT-06**: Execution inspector screenshot captured for each of 5 examples (saved to docs/images/)
- [ ] **CAPT-07**: Single npm script regenerates all 15 screenshots in one command

### Documentation Integration

- [ ] **DOCS-01**: Each of 5 example READMEs embeds its graph editor screenshots (full graph + DSL)
- [ ] **DOCS-02**: Each of 5 example READMEs embeds its execution inspector screenshot
- [ ] **DOCS-03**: Tutorial 07 (graph-editor) updated with graph editor screenshots
- [ ] **DOCS-04**: Tutorial 08 (execution-inspector) updated with inspector screenshots

## Future Requirements

None — v1.4 is self-contained.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Visual regression testing | Screenshots are for documentation, not automated diff testing |
| Video recordings | Static screenshots sufficient for documentation |
| Real AWS execution data for inspector | Mock fixtures avoid AWS dependency and cost |
| Screenshot CI pipeline | Manual npm script is sufficient; CI integration deferred |
| Animated GIFs | Static PNGs preferred for documentation clarity |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CAPT-01 | — | Pending |
| CAPT-02 | — | Pending |
| CAPT-03 | — | Pending |
| CAPT-04 | — | Pending |
| CAPT-05 | — | Pending |
| CAPT-06 | — | Pending |
| CAPT-07 | — | Pending |
| DOCS-01 | — | Pending |
| DOCS-02 | — | Pending |
| DOCS-03 | — | Pending |
| DOCS-04 | — | Pending |

**Coverage:**
- v1.4 requirements: 11 total
- Mapped to phases: 0
- Unmapped: 11 ⚠️

---
*Requirements defined: 2026-02-26*
*Last updated: 2026-02-26 after initial definition*
