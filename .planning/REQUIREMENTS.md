# Requirements: RSF Interactive Graph Editor

**Defined:** 2026-03-06
**Core Value:** Users can define, visualize, generate, deploy, and debug state machine workflows on Lambda Durable Functions with full AWS Step Functions feature parity — without writing state management or orchestration code by hand.

## v3.6 Requirements

Requirements for milestone v3.6. Each maps to roadmap phases.

### Inline Property Editing

- [ ] **EDIT-01**: User can click a state node to expand it and reveal editable property fields
- [ ] **EDIT-02**: User can edit property values with type-appropriate inputs (text, number, boolean toggle)
- [ ] **EDIT-03**: Property changes instantly sync to the YAML editor and trigger backend validation
- [ ] **EDIT-04**: Required fields are visually marked and enforce non-empty values before collapsing
- [ ] **EDIT-05**: "Must have one of" fields (e.g., Wait duration) display as radio group + input, enforcing exactly one selection
- [ ] **EDIT-06**: All 8 state types have correct property editors matching their Pydantic model fields

### Graph Manipulation

- [ ] **GRAPH-01**: User can select an edge by clicking it, with visual highlight feedback
- [ ] **GRAPH-02**: User can delete a selected edge by pressing Delete/Backspace key, preserving both connected nodes
- [ ] **GRAPH-03**: User can delete a state node, which cascades to remove all connected edges
- [ ] **GRAPH-04**: Edge deletion updates the YAML (removes Next/Default references) with live sync

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Editing

- **ADVEDIT-01**: User can rename a state node (updating all references)
- **ADVEDIT-02**: User can undo/redo property changes
- **ADVEDIT-03**: User can duplicate a state node with all properties

## Out of Scope

| Feature | Reason |
|---------|--------|
| Drag-to-reorder states | Visual ordering doesn't affect execution semantics |
| Multi-node selection/bulk edit | Adds significant complexity for rare use case |
| Choice rule condition editor | Complex nested conditions better edited in YAML |
| Parallel/Map branch sub-workflow editor | Nested state machine editing is a separate milestone |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| EDIT-01 | — | Pending |
| EDIT-02 | — | Pending |
| EDIT-03 | — | Pending |
| EDIT-04 | — | Pending |
| EDIT-05 | — | Pending |
| EDIT-06 | — | Pending |
| GRAPH-01 | — | Pending |
| GRAPH-02 | — | Pending |
| GRAPH-03 | — | Pending |
| GRAPH-04 | — | Pending |

**Coverage:**
- v3.6 requirements: 10 total
- Mapped to phases: 0
- Unmapped: 10 ⚠️

---
*Requirements defined: 2026-03-06*
*Last updated: 2026-03-06 after initial definition*
