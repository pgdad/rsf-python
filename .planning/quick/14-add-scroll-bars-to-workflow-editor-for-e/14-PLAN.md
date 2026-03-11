---
phase: quick-14
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - ui/src/components/GraphCanvas.tsx
  - ui/src/index.css
autonomous: false
requirements: [QUICK-14]
must_haves:
  truths:
    - "Visible scroll bars appear on the graph editor pane for horizontal and vertical navigation"
    - "User can drag scroll bars to pan the React Flow viewport"
    - "Existing pan/zoom, minimap, and controls continue to work"
  artifacts:
    - path: "ui/src/components/GraphCanvas.tsx"
      provides: "Scroll bar wrapper around React Flow canvas"
    - path: "ui/src/index.css"
      provides: "Scroll bar styling for graph container"
  key_links:
    - from: "ui/src/components/GraphCanvas.tsx"
      to: "@xyflow/react"
      via: "useReactFlow viewport API for scroll-to-viewport sync"
---

<objective>
Add visible scroll bars to the RSF workflow graph editor so users can navigate large graphs
by scrolling, in addition to the existing pan/zoom and minimap controls.

Purpose: Large workflow graphs are hard to navigate with only pan/zoom. Scroll bars provide
a familiar, visible affordance for moving around the canvas, especially when editing nodes.

Output: Modified GraphCanvas component with synced scroll bars overlaying the React Flow canvas.
</objective>

<execution_context>
@/Users/esa/.claude/get-shit-done/workflows/execute-plan.md
@/Users/esa/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@ui/src/components/GraphCanvas.tsx
@ui/src/index.css
@ui/src/App.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add custom scroll bars to the graph editor using React Flow viewport API</name>
  <files>ui/src/components/GraphCanvas.tsx, ui/src/index.css</files>
  <action>
Add custom scroll bar overlays to the GraphCanvas component that sync with the React Flow
viewport position. React Flow does not natively support scroll bars, so we implement them
as custom HTML elements that read/write the viewport transform.

Implementation approach in GraphCanvas.tsx:

1. Import `useViewport` (or `useStore` with viewport selector) from `@xyflow/react` to track
   the current viewport {x, y, zoom}. Also use `useReactFlow().setViewport()` to update position
   when the user drags a scroll bar.

2. Compute a bounding box of all nodes to determine the "scrollable extent" of the graph.
   Use `useReactFlow().getNodes()` to get node positions and dimensions. Add padding (200px)
   around the bounding box. When there are no nodes, hide the scroll bars.

3. Create two thin scroll bar track elements (one horizontal at the bottom of .graph-container,
   one vertical on the right side) rendered as absolutely-positioned divs INSIDE the graph-container,
   positioned above the React Flow canvas via z-index.

4. Each scroll bar has a "thumb" div whose size is proportional to (viewport-visible-area / total-extent)
   and whose position maps to the current viewport offset within that extent.

5. On mousedown on a thumb, attach mousemove/mouseup listeners (on window) to drag the thumb
   and call `setViewport({ x: newX, y: newY, zoom: currentZoom })` on each frame. Use
   requestAnimationFrame for smooth updates.

6. Also handle click-on-track to jump the viewport to that position.

7. Wrap the scroll bar logic in a separate inner component `GraphScrollBars` to keep concerns
   clean. It receives no props -- it reads everything from React Flow hooks.

8. The scroll bars should auto-hide after 2 seconds of inactivity and reappear on viewport
   change (pan/zoom) or on hover over the scroll bar track area. Use a CSS class toggle with
   opacity transition (0.3s).

CSS changes in index.css:

Add styles for `.graph-scrollbar-track`, `.graph-scrollbar-thumb`, both horizontal and vertical
variants. Use dark semi-transparent styling consistent with the existing dark theme:
- Track: transparent by default, subtle on hover
- Thumb: rgba(255,255,255,0.25) normally, rgba(255,255,255,0.45) on hover
- Track width: 10px for vertical, 10px height for horizontal
- Thumb border-radius: 5px
- Position: absolute, bottom-right corner of .graph-container
- z-index: 10 (above canvas, below controls/minimap which are z-index 5 in React Flow)
  Actually React Flow controls are z-index 5, so use z-index 4 to stay below them.
- Leave 10px gap in the corner where tracks would overlap

Do NOT use overflow:scroll on the container -- React Flow manages its own transform and adding
native scroll would conflict. These are purely custom visual scroll bars that call setViewport().
  </action>
  <verify>
    <automated>cd /Users/esa/git/rsf-python/ui && npx tsc --noEmit 2>&1 | head -30</automated>
  </verify>
  <done>
    - Horizontal and vertical scroll bar overlays render inside the graph editor pane
    - Scroll bar thumb sizes reflect the ratio of visible area to total graph extent
    - Dragging a scroll bar thumb pans the React Flow viewport smoothly
    - Clicking on the track jumps the viewport to that position
    - Scroll bars auto-hide after inactivity and reappear on interaction
    - Existing pan/zoom, minimap, drag-drop, keyboard shortcuts all still work
    - TypeScript compiles without errors
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Verify scroll bars work correctly in the graph editor</name>
  <files>ui/src/components/GraphCanvas.tsx</files>
  <action>Human verifies the scroll bar implementation works correctly in the browser.</action>
  <what-built>Custom scroll bars overlaying the React Flow graph editor canvas for navigating large workflows</what-built>
  <how-to-verify>
    1. Run `cd ui && npm run dev` to start the dev server
    2. Open the RSF Graph Editor in a browser
    3. Load or create a workflow with several nodes spread across the canvas
    4. Verify scroll bars appear along the right and bottom edges of the graph pane
    5. Drag the vertical scroll bar thumb -- the graph should pan up/down
    6. Drag the horizontal scroll bar thumb -- the graph should pan left/right
    7. Click on an empty part of a scroll track -- the viewport should jump
    8. Wait 2 seconds without interacting -- scroll bars should fade out
    9. Pan the canvas (mouse drag) -- scroll bars should reappear and reflect the new position
    10. Verify minimap, zoom controls, drag-drop from palette, and node editing still work
  </how-to-verify>
  <verify>Human visual verification</verify>
  <done>User confirms scroll bars are visible, functional, and do not interfere with existing features</done>
  <resume-signal>Type "approved" or describe issues</resume-signal>
</task>

</tasks>

<verification>
- TypeScript compiles: `cd ui && npx tsc --noEmit`
- Build succeeds: `cd ui && npm run build`
- Scroll bars visible and functional in browser
</verification>

<success_criteria>
- Visible scroll bars in the graph editor pane for both axes
- Scroll bar interaction pans the React Flow viewport correctly
- No regression in existing graph editor functionality
</success_criteria>

<output>
After completion, create `.planning/quick/14-add-scroll-bars-to-workflow-editor-for-e/14-SUMMARY.md`
</output>
