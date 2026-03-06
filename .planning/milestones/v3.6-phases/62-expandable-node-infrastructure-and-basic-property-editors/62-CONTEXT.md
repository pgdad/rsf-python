# Phase 62: Expandable Node Infrastructure and Basic Property Editors - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can expand any state node to reveal and edit its core properties, with changes immediately reflected in YAML. Covers Task, Pass, and Wait states with type-appropriate inputs (text, number, boolean toggle). Requirements: EDIT-01, EDIT-02, EDIT-03. Required field validation, radio group selectors, and remaining state types (Choice, Parallel, Map, Succeed, Fail) are Phase 63.

</domain>

<decisions>
## Implementation Decisions

### Expand/Collapse Visual
- Inline growth: node div grows taller to reveal property fields below the badges area
- Chevron icon on node header toggles expand/collapse — single click on node body still just selects
- No graph reflow on expand — node grows in place, neighboring nodes may overlap, user adjusts manually
- One node expanded at a time (accordion behavior) — expanding a node auto-collapses any previously expanded node

### Field Scope Per State Type
- **Task:** Resource (text), Comment (text), TimeoutSeconds (number), HeartbeatSeconds (number), End (boolean toggle)
- **Wait:** Seconds (number), Timestamp (text), SecondsPath (text), TimestampPath (text), Comment (text) — plain inputs, no radio group mutual exclusivity yet (Phase 63)
- **Pass:** Result (JSON — text area or mini editor), Comment (text), End (boolean toggle)
- I/O processing fields (InputPath, OutputPath, ResultPath, Parameters, ResultSelector) deferred to Phase 63

### Property Sync Pipeline
- Extend mergeGraphIntoYaml to write property data alongside transitions — property edits update stateData on FlowNodeData, merge function writes changed fields to the YAML AST
- Debounce 300ms for text inputs; boolean toggles and number changes sync immediately
- Full round-trip validation: property edit → update stateData → merge to YAML → WebSocket parse → backend validation errors returned
- syncSource='graph' flag set before property mutation, cleared after microtask — same loop prevention pattern as Phase 61

### Bidirectional Field Updates
- YAML changes in Monaco flow through existing useYamlToGraphSync → updateFromAst → stateData updates → expanded fields re-render with new values
- Focus guard: if a property input has focus, skip overwriting its value from YAML updates — reconcile on blur
- If a state's YAML block is deleted in Monaco while expanded, the node disappears naturally (existing YAML→graph removal behavior)
- Same syncSource flag pattern prevents infinite loops between property fields and YAML editor

### Claude's Discretion
- Result field input implementation (plain text area vs embedded mini Monaco editor)
- Chevron icon design and positioning within node header
- Expand/collapse animation timing and CSS transitions
- Exact field ordering within expanded property panels
- How stateData fields map to form inputs (field name casing, grouping)

</decisions>

<specifics>
## Specific Ideas

- The existing BaseNode `children` prop is the natural insertion point for expanded property content
- stateData on FlowNodeData already carries the raw AST definition — property editors read from and write to this
- Per-node components (TaskNode, WaitNode, PassNode) already render badges from stateData — expansion extends this pattern
- Accordion behavior (one-at-a-time) needs expandedNodeId state in flowStore

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BaseNode.tsx`: Has `children` prop — expanded property fields render here. Already handles `selected` CSS class.
- `flowStore.ts`: Zustand + immer store. Needs `expandedNodeId` state and `toggleExpand(nodeId)` action.
- `FlowNodeData.stateData`: Already carries raw state definition from AST — property editors read/write this field.
- `mergeGraphIntoYaml.ts`: AST-merge strategy. Currently handles transitions only — needs extension to write property fields from stateData back to YAML AST.
- `useGraphToYamlSync.ts`: Calls mergeGraphIntoYaml and sends parse to backend. Property edits hook into this via `onGraphChange`.
- `useYamlToGraphSync.ts`: YAML→graph direction. Already updates stateData from parsed AST — expanded fields will reactively re-render.

### Established Patterns
- **Zustand + immer** for all state management — new expandedNodeId and property update actions follow this pattern
- **syncSource flag** prevents infinite YAML↔graph loops — property edits set 'graph', Monaco edits set 'editor'
- **AST-merge strategy** preserves complex state data — property fields patch specific keys without clobbering Choice rules, Catch arrays, etc.
- **Per-type node components** (TaskNode, WaitNode, PassNode) each render state-specific content in BaseNode's children slot

### Integration Points
- `GraphCanvas.tsx` `handleNodeClick`: Currently selects. Chevron needs separate click handler that doesn't interfere.
- `flowStore.ts`: New actions: `toggleExpand(nodeId)`, `updateStateProperty(nodeId, key, value)`
- `mergeGraphIntoYaml.ts`: Extend state loop to write stateData properties (Resource, Comment, TimeoutSeconds, etc.) to AST
- `App.tsx / EditorApp`: No changes expected — property edits flow through existing `syncGraphToYaml` callback

</code_context>

<deferred>
## Deferred Ideas

- Required field validation with visual markers — Phase 63 (EDIT-04)
- Radio group selectors for mutually exclusive fields (Wait duration types) — Phase 63 (EDIT-05)
- Remaining state type editors (Choice, Parallel, Map, Succeed, Fail) — Phase 63 (EDIT-06)
- I/O processing fields (InputPath, OutputPath, ResultPath, Parameters, ResultSelector) — Phase 63
- Undo/redo for property changes — ADVEDIT-02 (future requirement)

</deferred>

---

*Phase: 62-expandable-node-infrastructure-and-basic-property-editors*
*Context gathered: 2026-03-06*
