---
phase: 62-expandable-node-infrastructure-and-basic-property-editors
plan: "01"
subsystem: ui
tags: [react, zustand, immer, vitest, vite, flow-nodes, expand-collapse]

# Dependency graph
requires:
  - phase: 61-graph-manipulation
    provides: BaseNode, flowStore with selectedNodeId/selectedEdgeId, removeState
provides:
  - "expandedNodeId state in flowStore (accordion: one expanded node at a time)"
  - "toggleExpand action for expand/collapse with auto-collapse of previous node"
  - "updateStateProperty action for patching node stateData fields"
  - "Chevron button in BaseNode header with stopPropagation (no interference with selection)"
  - "node-expanded-panel slot below badges in BaseNode body"
  - "expandedContent prop on BaseNode for per-type property editors (Plan 02)"
  - "CSS classes: node-expand-chevron, flow-node.expanded, node-expanded-panel, node-expanded-placeholder"
affects: [62-02-property-editors, plan-02, property-editors]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Accordion expand pattern: store holds single expandedNodeId, toggleExpand sets/clears it"
    - "stopPropagation on chevron click to prevent interfering with node selection onClick"
    - "TDD: RED (failing tests) committed before GREEN (implementation)"

key-files:
  created: []
  modified:
    - ui/src/store/flowStore.ts
    - ui/src/nodes/BaseNode.tsx
    - ui/src/index.css
    - ui/src/test/flowStore.test.ts

key-decisions:
  - "Accordion pattern: expandedNodeId (single string | null) rather than a Set — enforces one expanded node at a time"
  - "Chevron uses e.stopPropagation() to prevent click bubbling to node's selectNode handler"
  - "expandedContent prop on BaseNode for per-type editors — empty slot renders 'Properties' placeholder until Plan 02"
  - "updateStateProperty handles null/undefined as delete (clearing optional fields cleanly)"
  - "removeState clears expandedNodeId when expanded node is deleted (no stale expand state)"

patterns-established:
  - "Store pattern: single ID state (not Set) for accordion exclusivity"
  - "Component pattern: read expandedNodeId from store, compute isExpanded = expandedNodeId === id locally"

requirements-completed: [EDIT-01]

# Metrics
duration: 2min
completed: 2026-03-06
---

# Phase 62 Plan 01: Expandable Node Infrastructure Summary

**Accordion expand/collapse infrastructure: expandedNodeId + toggleExpand in Zustand store, chevron button in BaseNode header with stopPropagation, expanded panel slot below badges ready for Plan 02 property editors**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-06T16:33:36Z
- **Completed:** 2026-03-06T16:35:36Z
- **Tasks:** 2 (TDD: 3 commits)
- **Files modified:** 4

## Accomplishments

- Store: `expandedNodeId`, `toggleExpand` (accordion), `updateStateProperty` (stateData patcher) added to flowStore with full immer support
- `removeState` updated to clear `expandedNodeId` when expanded node is deleted
- TDD: 11 failing tests committed as RED, then GREEN implementation made all 40 flowStore tests pass (87 total)
- BaseNode: chevron button added to header, `expandedContent` prop added, expanded panel renders below badges, `expanded` CSS class on root div
- All 87 tests pass, TypeScript clean, Vite production build succeeds

## Task Commits

1. **Task 1 RED - Failing tests** - `a332935` (test)
2. **Task 1 GREEN - Store implementation** - `6a6c8bb` (feat)
3. **Task 2 - BaseNode + CSS** - `3ef5afa` (feat)

## Files Created/Modified

- `ui/src/store/flowStore.ts` - Added expandedNodeId, toggleExpand, updateStateProperty; removeState clears expandedNodeId
- `ui/src/nodes/BaseNode.tsx` - Added chevron button, expandedContent prop, node-expanded-panel, expanded CSS class
- `ui/src/index.css` - Added CSS for .node-expand-chevron, .flow-node.expanded, .node-expanded-panel, .node-expanded-placeholder
- `ui/src/test/flowStore.test.ts` - Added resetStore expandedNodeId field, 11 new tests for toggleExpand/updateStateProperty/removeState

## Decisions Made

- Accordion uses a single `expandedNodeId: string | null` rather than a Set — simpler, enforces one-at-a-time by construction
- `e.stopPropagation()` on chevron prevents chevron click from triggering the node's `onClick` (selectNode), keeping expand and select independent
- `expandedContent` prop on BaseNode is the extension point for Plan 02 — empty slot shows "Properties" placeholder
- `updateStateProperty` treats `null`/`undefined` values as `delete` calls to clean up optional fields

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Expand/collapse infrastructure complete and tested. Plan 02 can now pass `expandedContent` to BaseNode for per-type property editors.
- `updateStateProperty(nodeId, key, value)` available in store for property editors to call on each keystroke.
- CSS placeholder visible when expanded with no content — ready to replace with real editors.

## Self-Check: PASSED

All files verified present. All commits verified in git log.

---
*Phase: 62-expandable-node-infrastructure-and-basic-property-editors*
*Completed: 2026-03-06*
