---
phase: 63-complete-property-editors-and-validation-enforcement
plan: "01"
subsystem: ui-graph-editor
tags: [validation, nodes, css, zustand, tdd]
dependency_graph:
  requires: [62-02-SUMMARY]
  provides: [BaseNode-for-all-8-types, collapse-validation-guard, required-field-CSS]
  affects: [ui/src/nodes/, ui/src/store/flowStore.ts, ui/src/index.css]
tech_stack:
  added: []
  patterns: [REQUIRED_FIELDS-map, oneOf-validation-spec, collapseBlocked-transient-flag, shake-animation-onAnimationEnd]
key_files:
  created: []
  modified:
    - ui/src/store/flowStore.ts
    - ui/src/nodes/BaseNode.tsx
    - ui/src/nodes/ChoiceNode.tsx
    - ui/src/nodes/SucceedNode.tsx
    - ui/src/nodes/FailNode.tsx
    - ui/src/index.css
    - ui/src/test/flowStore.test.ts
decisions:
  - "REQUIRED_FIELDS map: only Wait has Pydantic-required inline fields (oneOf timing field); Task/Pass/Fail/Succeed/Choice/Parallel/Map have no enforced collapse validation"
  - "collapseBlocked is a transient string|null flag (nodeId) cleared on any next toggleExpand call — used by BaseNode to trigger shake animation"
  - "BaseNode uses useEffect + prevBlockedRef to detect rising edge of collapseBlocked, onAnimationEnd to clear local shake state"
  - "ChoiceNode/SucceedNode/FailNode now render via BaseNode — all 8 node types use unified expand/collapse infrastructure"
metrics:
  duration: "173 seconds"
  completed_date: "2026-03-06"
  tasks_completed: 2
  files_modified: 7
---

# Phase 63 Plan 01: BaseNode Migration, Validation Guard, and Required-Field CSS Summary

**One-liner:** All 8 node types use BaseNode with accordion expand/collapse; toggleExpand blocks Wait-node collapse when no timing field is set, triggering shake animation via collapseBlocked flag.

## What Was Built

### Task 1 (TDD): Validation guard in toggleExpand + collapseBlocked state

Added `REQUIRED_FIELDS` map and `checkRequiredFields()` helper to `flowStore.ts`. The only enforced validation is the Wait state's oneOf requirement — at least one of `Seconds`, `Timestamp`, `SecondsPath`, or `TimestampPath` must be set before collapse is allowed.

When validation fails on a collapse attempt:
- `expandedNodeId` stays set (collapse blocked)
- `toastMessage` is set with a description of the missing field
- `collapseBlocked` is set to the nodeId (transient flag for shake animation)

`collapseBlocked` is cleared at the start of every `toggleExpand` call regardless of direction.

8 new tests were added (TDD RED→GREEN) covering all cases: Task collapse always allowed, Succeed always allowed, Wait blocks on missing timing field, Wait allows with any one timing field set, and collapseBlocked clears on next call.

### Task 2: Refactor Choice/Succeed/Fail to BaseNode + CSS additions

**ChoiceNode.tsx:** Replaced custom div layout with BaseNode. Color `#e6a817`, icon `?`. Badges (rules count, Default) remain as `children` prop content.

**SucceedNode.tsx:** Replaced with minimal BaseNode wrapper. Color `#27ae60`, icon `&#10003;` (checkmark). No children needed.

**FailNode.tsx:** Replaced with BaseNode. Color `#e74c3c`, icon `&#10007;` (X). Error/Cause detail display preserved as `children` slot content.

**BaseNode.tsx:** Added `collapseBlocked` store subscription. Uses `useEffect` + `useRef` to detect rising edge (new block event). Sets local `isShaking` state which adds CSS class `shake`. `onAnimationEnd` callback clears `isShaking` so animation can re-trigger on subsequent blocked attempts.

**index.css additions:**
- `.property-field label .required-asterisk` — red asterisk after label
- `.property-field input.field-error`, `.property-field textarea.field-error` — red border for empty required fields
- `@keyframes shake` + `.flow-node.shake` — 0.3s lateral shake animation
- `.radio-group`, `.radio-option`, `.radio-option.disabled` — mutual-exclusion radio group styles
- `.readonly-summary`, `.readonly-summary .edit-hint` — read-only summary badge for complex fields
- `.io-section`, `.io-section-header`, `.io-section-chevron`, `.io-section-body` — collapsible I/O Processing section

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `npx tsc -b --noEmit` — passes (no TypeScript errors)
- `npx vitest run` — 112 tests pass across 5 test files
- All 8 node types now use BaseNode (Task, Pass, Wait from Phase 62; Choice, Succeed, Fail from this plan; Parallel, Map already used BaseNode)
- CSS classes: required-asterisk, field-error, shake, radio-group, readonly-summary, io-section all defined

## Self-Check: PASSED

Files modified:
- FOUND: /home/esa/git/rsf-python/ui/src/store/flowStore.ts
- FOUND: /home/esa/git/rsf-python/ui/src/nodes/BaseNode.tsx
- FOUND: /home/esa/git/rsf-python/ui/src/nodes/ChoiceNode.tsx
- FOUND: /home/esa/git/rsf-python/ui/src/nodes/SucceedNode.tsx
- FOUND: /home/esa/git/rsf-python/ui/src/nodes/FailNode.tsx
- FOUND: /home/esa/git/rsf-python/ui/src/index.css
- FOUND: /home/esa/git/rsf-python/ui/src/test/flowStore.test.ts

Commits:
- eb872a0: test(63-01): add failing tests for toggleExpand validation guard
- d1714be: feat(63-01): implement toggleExpand validation guard with collapseBlocked state
- 5911fb6: feat(63-01): refactor Choice/Succeed/Fail to BaseNode and add validation CSS
