---
phase: quick-14
plan: "01"
subsystem: ui
tags: [ui, react-flow, scroll-bars, graph-editor, ux]
dependency_graph:
  requires: []
  provides: [graph-scroll-bars]
  affects: [ui/src/components/GraphCanvas.tsx, ui/src/index.css]
tech_stack:
  added: []
  patterns: [react-flow-viewport-api, custom-scroll-bars, resize-observer]
key_files:
  created: []
  modified:
    - ui/src/components/GraphCanvas.tsx
    - ui/src/index.css
decisions:
  - Custom HTML scroll bars via setViewport() rather than native CSS overflow scroll (avoids conflict with React Flow transform)
  - GraphScrollBars as inner component to co-locate viewport hooks with scroll logic
  - Auto-hide after 2s with opacity transition keeps UI uncluttered for small graphs
metrics:
  duration_seconds: 95
  completed_date: "2026-03-11"
  tasks_completed: 2
  files_modified: 2
---

# Phase quick-14 Plan 01: Add Scroll Bars to Workflow Editor Summary

**One-liner:** Custom overlay scroll bars synced to React Flow's setViewport() API with auto-hide, drag-to-pan, and click-to-jump for large workflow graph navigation.

## What Was Built

Added a `GraphScrollBars` inner component to `GraphCanvas.tsx` that renders two thin overlay scroll bars (horizontal at bottom, vertical at right) inside `.graph-container`. The bars read viewport state via `useViewport()` and write it via `setViewport()` — keeping them fully in sync with React Flow's pan/zoom without conflicting with its internal transform system.

## Implementation Details

**Bounding box computation:** On each render, all node positions and dimensions are iterated to produce a min/max bounding box in flow-space, padded by 200px. This determines the scrollable extent.

**Thumb sizing:** Thumb width/height = `(containerSize / extentScreenPx)` ratio, clamped between 5% and 99% of the track length. The track accounts for the 10px corner gap.

**Drag interaction:** `mousedown` on a thumb attaches `mousemove`/`mouseup` to `window`. Each move event converts pixel delta to a fraction of the scroll range and calls `setViewport()` wrapped in `requestAnimationFrame` for smooth updates.

**Click-on-track:** Calculates the click position relative to the track, maps it to a scroll fraction, and jumps the viewport immediately.

**Auto-hide:** A `useEffect` watching `{x, y, zoom}` resets a 2-second `setTimeout` each time the viewport changes. Opacity transitions from 1→0 over 0.3s. Hovering the track resets the timer.

**Container sizing:** A `ResizeObserver` tracks the container element's dimensions so thumb sizes stay accurate after layout changes.

**z-index:** Scroll bars use `z-index: 4` — below React Flow's controls/minimap (z-index 5) but above the canvas background.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Add custom scroll bars to graph editor using React Flow viewport API | 62064bf |
| 2 | Verify scroll bars work correctly (auto-approved in auto mode) | — |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- GraphCanvas.tsx: FOUND
- index.css: FOUND
- Commit 62064bf: FOUND
