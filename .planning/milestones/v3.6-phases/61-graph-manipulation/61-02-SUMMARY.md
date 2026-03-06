---
phase: 61-graph-manipulation
plan: "02"
subsystem: ui-graph-editor
tags: [node-deletion, edge-cascade, startAt-reassignment, reference-cleanup, tdd, zustand, keyboard-shortcuts]
dependency_graph:
  requires: [61-01]
  provides: [node-deletion, last-node-guard, startAt-reassignment, dangling-ref-cleanup]
  affects: [ui/src/store/flowStore.ts, ui/src/sync/mergeGraphIntoYaml.ts, ui/src/components/GraphCanvas.tsx]
tech_stack:
  added: []
  patterns: [tdd-red-green, zustand-immer, alphabetical-sort, defensive-ast-cleanup]
key_files:
  created: []
  modified:
    - ui/src/store/flowStore.ts
    - ui/src/sync/mergeGraphIntoYaml.ts
    - ui/src/components/GraphCanvas.tsx
    - ui/src/test/flowStore.test.ts
    - ui/src/test/mergeGraphIntoYaml.test.ts
decisions:
  - "Last-node guard in removeState — set toastMessage and return early, no deletion"
  - "isStart reassignment via alphabetical sort of remaining node IDs after deletion"
  - "selectedEdgeId cleared unconditionally on any removeState call for clean slate"
  - "Defensive Next/Default reference cleanup in mergeGraphIntoYaml as independent safety net"
metrics:
  duration_seconds: 120
  completed_date: "2026-03-06"
  tasks_completed: 1
  tasks_total: 1
  files_created: 0
  files_modified: 5
---

# Phase 61 Plan 02: Node Deletion with Cascade, StartAt Reassignment, and Reference Cleanup Summary

**One-liner:** Node deletion via Delete/Backspace with edge cascade, last-node guard toast, alphabetical StartAt reassignment, and defensive dangling-reference cleanup (End:true) in mergeGraphIntoYaml.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Add failing tests for node deletion, StartAt reassignment, reference cleanup | 193b359 | flowStore.test.ts, mergeGraphIntoYaml.test.ts |
| 1 (GREEN) | Node deletion with cascade, StartAt reassignment, and reference cleanup | 6c9b5b6 | flowStore.ts, mergeGraphIntoYaml.ts, GraphCanvas.tsx |

## What Was Built

### Store Changes (flowStore.ts)

Enhanced `removeState` with three new behaviors:

**Last-node guard:**
- Before removing, checks `state.nodes.length <= 1`
- If only one node exists, sets `toastMessage = 'Cannot delete the only state'` and returns early
- Node is preserved

**StartAt reassignment:**
- Checks if the node being removed has `data.isStart === true`
- After filtering out the node from `state.nodes`, sorts remaining nodes alphabetically by `id`
- Sets `sorted[0].data.isStart = true` (first alphabetically)

**Selection cleanup:**
- Clears `selectedNodeId` if it matched the deleted node (existing)
- Unconditionally clears `selectedEdgeId` for a clean slate after any node deletion (new)

### mergeGraphIntoYaml.ts

Added defensive reference cleanup loop after the main transition-update loop:

```typescript
for (const stateName of Object.keys(states)) {
  const state = states[stateName];
  if (state.Next !== undefined && !existingNodeIds.has(state.Next as string)) {
    delete state.Next;
    state.End = true;
  }
  if (state.Default !== undefined && !existingNodeIds.has(state.Default as string)) {
    delete state.Default;
  }
}
```

This is an independent safety net — the edge cascade in `removeState` and the existing transition-update loop already handle most cases, but this explicitly handles any AST state whose `Next`/`Default` target was deleted.

### GraphCanvas.tsx

Extended the Delete/Backspace keyboard handler to handle node deletion:

```typescript
if (currentSelectedEdgeId) {
  event.preventDefault();
  removeEdge(currentSelectedEdgeId);
  onGraphChange?.();
} else if (currentSelectedNodeId) {
  event.preventDefault();
  removeState(currentSelectedNodeId);
  onGraphChange?.();
}
```

- Imported `removeState` from flowStore
- Added `removeState` to the `useEffect` dependency array
- No confirmation dialog — deletion is immediate on keypress

## Tests Written

**flowStore.test.ts** (5 new tests):
- Last-node guard: `removeState` with 1 node sets toast, keeps node
- isStart reassignment with nodes A, B, C (delete A) → B gets isStart
- isStart reassignment with nodes C, A, B (delete C) → A gets isStart (alphabetical)
- Non-start node deletion: isStart flags unchanged on remaining nodes
- `selectedEdgeId` cleared after any `removeState` call

**mergeGraphIntoYaml.test.ts** (4 new tests):
- State whose Next points to deleted node gets End:true, Next removed
- StartAt updated to match the isStart node (after start-node deletion)
- Choice state whose Default target deleted: Default key removed
- 3-state chain A->B->C, remove B: A gets End:true, C keeps End:true, B absent

**Results:** 76/76 tests pass (up from 67).

## Verification

- `npx vitest run`: 76 tests pass (5 test files)
- `npx tsc -b --noEmit`: No TypeScript errors
- `npx vite build`: Production build succeeds (1958 kB)

## Deviations from Plan

None — plan executed exactly as written.

The "does not change isStart flags when a non-start node is removed" test passed on the RED phase because the existing `removeState` already filtered nodes correctly and didn't touch isStart (no reassignment needed for non-start deletions). This confirms the behavior was already correct for that case.

## Self-Check: PASSED

All created/modified files verified on disk:
- FOUND: ui/src/store/flowStore.ts
- FOUND: ui/src/sync/mergeGraphIntoYaml.ts
- FOUND: ui/src/components/GraphCanvas.tsx
- FOUND: ui/src/test/flowStore.test.ts
- FOUND: ui/src/test/mergeGraphIntoYaml.test.ts
- FOUND: .planning/phases/61-graph-manipulation/61-02-SUMMARY.md

Commits verified:
- FOUND: 193b359 (RED phase tests)
- FOUND: 6c9b5b6 (GREEN phase implementation)
