# Phase 61: Graph Manipulation - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can select, delete, and manage edges and nodes directly in the graph with all changes reflected live in YAML. Requirements: GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04. No new capabilities — this phase adds manipulation to the existing read-only graph.

</domain>

<decisions>
## Implementation Decisions

### Edge Selection Visual
- Selected edge gets strokeWidth 3-4 and a distinct blue (#3b82f6) color, overriding the per-type color
- Edge label also gets blue highlight background when edge is selected
- No contextual info panel — selection is purely visual + enables deletion
- Toggle on re-click: clicking a selected edge deselects it
- Pane click and Escape key also deselect

### Deletable Edge Types
- Only **normal** and **default** transition edges are deletable
- **Choice rule edges** (gold) are protected — carry complex condition data that can't be rebuilt from graph
- **Catch edges** (red dashed) are protected — carry complex error handler data
- When user tries to delete a protected edge: show inline toast message ("Catch edges must be edited in YAML") near the edge, disappears after 2-3 seconds
- When deleting a Default edge from a Choice state: add End:true as fallback to keep YAML valid

### Node Deletion
- No confirmation dialog — immediate delete on keypress for fast workflow
- StartAt node is deletable: auto-reassign StartAt to the first remaining node alphabetically
- Reference cleanup: when a node is deleted, states whose Next pointed to it get End:true set (keeps YAML valid, no dangling arrows)
- Last remaining node cannot be deleted — show message "Cannot delete the only state"

### Keyboard & Mouse Interaction
- Delete/Backspace keys work for both edges and nodes (context-aware: deletes whatever is selected)
- Single selection only: selecting an edge deselects any selected node, and vice versa
- Escape key deselects everything
- Delete key only triggers when graph canvas is focused (prevents accidental deletion when typing in Monaco editor)

### Claude's Discretion
- Exact toast/message styling and positioning
- Animation timing for selection highlight transitions
- Implementation of focus tracking for Delete key scoping
- Edge interactionWidth (clickable area around edge path)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `flowStore.ts:removeState(nodeId)`: Already cascades node removal to connected edges + clears selection. Needs extension for YAML ref cleanup (End:true on orphaned states)
- `TransitionEdge.tsx`: Custom edge component with per-type colors. Needs `selected` prop handling for blue highlight
- `mergeGraphIntoYaml.ts`: AST-merge strategy already handles node removal (removes states not in existingNodeIds) and transition updates (Next/End). Core of YAML sync
- `GraphCanvas.tsx`: Already fires `onGraphChange` for edge removes and has `handlePaneClick` for deselection
- `BaseNode.tsx`: Already has `selected` CSS class handling — same pattern can be extended for edge selection
- `useGraphToYamlSync.ts`: Graph-to-YAML sync hook, already wired into App.tsx

### Established Patterns
- **Zustand + immer** for state management — all new state (selectedEdgeId, toast messages) goes in flowStore
- **syncSource flag** prevents infinite YAML<->Graph update loops — must set before mutation, clear after microtask
- **AST-merge strategy** preserves complex state data (Choice rules, Catch arrays, Parallel branches) — graph edits patch YAML AST
- **Per-type edge colors**: normal=#555, catch=#e74c3c, default=#95a5a6, choice=#e6a817

### Integration Points
- `ReactFlow` component in GraphCanvas.tsx: needs `onEdgeClick` handler and keyboard event listener
- `flowStore.ts`: needs `selectedEdgeId` state, `selectEdge()` action, and `removeEdge()` action
- `mergeGraphIntoYaml.ts`: needs ref cleanup logic (set End:true when Next target is deleted)
- `TransitionEdge.tsx`: needs selected state prop to switch to blue highlight style

</code_context>

<specifics>
## Specific Ideas

- Edge selection should feel like Figma/draw.io — click to select, Delete to remove, clear and immediate
- Protected edge toast should be informative, not blocking — brief inline message that auto-dismisses
- The AST-merge strategy is the key integration point — all deletion operations ultimately flow through it to update YAML

</specifics>

<deferred>
## Deferred Ideas

- Undo/redo for deletions — ADVEDIT-02 (future requirement)
- Multi-node/multi-edge selection — explicitly out of scope per requirements
- Choice rule condition editing in graph — out of scope (better in YAML per requirements)

</deferred>

---

*Phase: 61-graph-manipulation*
*Context gathered: 2026-03-06*
