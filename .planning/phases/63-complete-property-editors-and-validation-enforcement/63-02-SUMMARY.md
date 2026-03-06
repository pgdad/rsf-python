---
phase: 63-complete-property-editors-and-validation-enforcement
plan: "02"
subsystem: ui-graph-editor
tags: [radio-groups, io-processing, property-editors, zustand, react]
dependency_graph:
  requires: [63-01-SUMMARY]
  provides: [WaitNode-radio-group, TaskNode-radio-pairs, PassNode-io-section, all-3-nodes-complete-editors]
  affects: [ui/src/nodes/WaitNode.tsx, ui/src/nodes/TaskNode.tsx, ui/src/nodes/PassNode.tsx]
tech_stack:
  added: []
  patterns: [4-option-radio-group, radio-pair-mutual-exclusion, collapsible-io-section, readonly-summary-badges]
key_files:
  created: []
  modified:
    - ui/src/nodes/WaitNode.tsx
    - ui/src/nodes/TaskNode.tsx
    - ui/src/nodes/PassNode.tsx
decisions:
  - "WaitNode radio group: activeWaitType local state initialized from stateData, synced back via useEffect when stateData changes from YAML edit"
  - "TaskNode radio pairs: activeTimeoutType and activeHeartbeatType each initialized from stateData, null when neither field is set (optional pairs)"
  - "Radio switching clears the partner field via updateStateProperty(id, field, undefined) before setting new active type"
  - "I/O Processing section is collapsible (ioOpen local state) and consistent across all 3 nodes"
  - "Read-only complex fields (Parameters, ResultSelector, Assign, Output, Retry, Catch) use readonly-summary div with object key count or array length"
metrics:
  duration: "171 seconds"
  completed_date: "2026-03-06"
  tasks_completed: 3
  files_modified: 3
---

# Phase 63 Plan 02: Radio Groups, I/O Processing Sections, and Complete Property Editors Summary

**One-liner:** Wait node upgraded to 4-option radio group with mutual exclusion; Task node upgraded with 2 optional radio pairs for Timeout/Heartbeat; all three nodes (Task, Wait, Pass) now have collapsible I/O Processing sections matching their full Pydantic model fields.

## What Was Built

### Task 1: WaitNode — 4-option radio group + I/O section

Rewrote `WaitNode`'s `expandedContent` to replace 4 separate flat inputs with a single `radio-group` containing 4 `radio-option` divs.

**Radio group behavior:**
- `activeWaitType` local state initialized from `getActiveWaitType()` — inspects `stateData` to determine which field (if any) has a value
- `handleRadioChange(type)` clears all other 3 duration fields via `updateStateProperty(id, field, undefined)` before setting the new active type
- Non-active radio options receive the `.disabled` CSS class and their inputs get `disabled` attribute
- The active radio's label shows `<span className="required-asterisk">*</span>` since exactly one timing field is required per Pydantic validator
- A `useEffect` syncs `activeWaitType` back when stateData changes externally (YAML edit direction)

**Debounce+focus-guard preserved:** Timestamp, SecondsPath, TimestampPath use 300ms debounce with ref-based focus guards. Seconds uses immediate sync (number field).

**I/O Processing section:** Collapsible (`ioOpen` local state). Contains InputPath, OutputPath, ResultPath as text inputs with debounce+focus-guard, and Parameters/ResultSelector/Assign/Output as read-only summaries showing `{N keys}` or `Not set` + `(edit in YAML)` hint. QueryLanguage text input also inside the section.

### Task 2: TaskNode — 2 radio pairs + I/O section

Updated `TaskNode`'s `expandedContent` with two radio pairs and additional fields.

**Timeout radio pair (optional):** `activeTimeoutType: 'static' | 'path' | null`
- `'static'` → TimeoutSeconds (number, immediate sync)
- `'path'` → TimeoutSecondsPath (text, debounce+focus-guard)
- `null` → neither selected (valid — both optional)
- Switching clears the partner field

**Heartbeat radio pair (optional):** `activeHeartbeatType: 'static' | 'path' | null` — same pattern as timeout.

**New fields added:**
- Retry: read-only summary `"N polic(y/ies)"` or `"Not set"` + edit hint
- Catch: read-only summary `"N catcher(s)"` or `"Not set"` + edit hint
- SubWorkflow: text input with debounce+focus-guard

**Field order:** Resource, Comment, Timeout pair, Heartbeat pair, Retry, Catch, SubWorkflow, End, I/O Processing.

**I/O Processing section:** Same pattern as WaitNode — InputPath, OutputPath, ResultPath, Parameters, ResultSelector, Assign, Output, QueryLanguage.

### Task 3: PassNode — I/O section

Added `ioOpen` state and I/O Processing collapsible section after the existing Result/Comment/End fields.

**No radio groups needed** — PassState has no mutually exclusive fields.
**No required-asterisk indicators** — PassState has no Pydantic-required inline fields.

I/O section contains: InputPath, OutputPath, ResultPath (debounce+focus-guard), Parameters, ResultSelector, Assign, Output (read-only summaries), QueryLanguage (debounce+focus-guard).

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `npx tsc -b --noEmit` — passes (no TypeScript errors) after each task
- `npx vitest run` — 112 tests pass across 5 test files after each task
- WaitNode: 4-option radio group with mutual exclusion and required-asterisk on active option
- TaskNode: 2 optional radio pairs (Timeout, Heartbeat) with null/static/path states
- PassNode: I/O Processing collapsible section with path inputs and read-only summaries
- All 3 nodes have consistent I/O Processing sections

## Self-Check: PASSED

Files modified:
- FOUND: /home/esa/git/rsf-python/ui/src/nodes/WaitNode.tsx
- FOUND: /home/esa/git/rsf-python/ui/src/nodes/TaskNode.tsx
- FOUND: /home/esa/git/rsf-python/ui/src/nodes/PassNode.tsx

Commits:
- f73078a: feat(63-02): WaitNode radio group for 4-option duration + I/O Processing section
- f35129e: feat(63-02): TaskNode radio pairs for Timeout/Heartbeat + I/O Processing section
- e35ee01: feat(63-02): PassNode I/O Processing section with path inputs and read-only summaries
