# Test-First UI Tutorial Documentation

**Date:** 2026-03-18
**Status:** Draft

## Problem

RSF has a powerful graph editor UI for building Lambda Durable Function workflows, but no systematic way to:

1. Regression-test end-to-end workflow creation through the UI
2. Produce visual documentation (screenshots, GIFs, videos) that stays in sync with the actual UI

## Solution

Playwright test specs that serve dual duty — each tutorial is a test that drives the UI through building a real workflow, captures screenshots and video at each step, then a post-processing pipeline annotates the raw captures and assembles them into GitHub Pages tutorial docs.

## Tutorial Progression

Five tutorials, graduated complexity. Each starts from `rsf init` and builds a complete workflow through the UI.

| # | Tutorial | States Used | Key UI Skills Taught |
|---|----------|-------------|----------------------|
| 1 | Hello Workflow | Task → Task → Succeed | Add states, connect edges, edit properties, rename |
| 2 | Branching Logic | Task → Choice → Task/Fail | Choice rules, multiple outbound edges, default branch |
| 3 | Wait & Retry | Task (with Retry/Catch) → Wait → Task | Error handling config, wait configuration |
| 4 | Parallel Processing | Task → Parallel (2 branches) → Task | Parallel branch editor, nested state machines |
| 5 | Order Processing (existing example) | All types | Full end-to-end, builds the real order-processing example |

**Audience:** Mix of developers — assumes basic AWS familiarity but explains state machine concepts briefly when they first appear.

## Architecture

```
┌─────────────────────┐     ┌──────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│   Tutorial Specs    │     │   Raw Captures   │     │   Post-Processing    │     │  GitHub Pages   │
│ tests/ui-tutorials/ │ ──→ │  .captures/<t>/  │ ──→ │ scripts/docs-pipeline│ ──→ │ docs/tutorials/ │
│  *.spec.ts          │     │  PNGs + WebM     │     │  annotate + assemble │     │  MD + assets    │
└─────────────────────┘     └──────────────────┘     └──────────────────────┘     └─────────────────┘
                                                                                          │
                                                                CI/CD: GitHub Actions ─────┘
```

## File Structure

### Playwright Tests

```
tests/ui-tutorials/
├── playwright.config.ts          # Shared config: 1280×800 viewport, video on, base URL
├── fixtures/
│   ├── rsf-server.ts             # Fixture: rsf init + rsf ui launch per spec
│   └── capture.ts                # Fixture: screenshot/video helpers with step metadata
├── tutorial-01-hello-workflow.spec.ts
├── tutorial-02-branching-logic.spec.ts
├── tutorial-03-wait-and-retry.spec.ts
├── tutorial-04-parallel-processing.spec.ts
├── tutorial-05-order-processing.spec.ts
└── .captures/                    # Raw output (gitignored)
    ├── tutorial-01/
    │   ├── step-01-init-project.png
    │   ├── step-02-open-editor.png
    │   ├── ...
    │   ├── full-recording.webm
    │   └── manifest.json
    └── ...
```

### Post-Processing Pipeline

```
scripts/docs-pipeline/
├── annotate.sh          # ImageMagick: add step numbers, callouts, highlights
├── video-process.sh     # FFmpeg: trim, add text overlays, produce GIFs
├── assemble.py          # Read manifests, generate markdown pages
├── templates/
│   ├── tutorial.md.j2   # Jinja2 template for a tutorial page
│   └── index.md.j2      # Tutorials index page
└── config.yaml          # Annotation styles, colors, font sizes
```

### Output

```
docs/
├── tutorials/
│   ├── index.md
│   ├── 01-hello-workflow.md
│   ├── 02-branching-logic.md
│   ├── 03-wait-and-retry.md
│   ├── 04-parallel-processing.md
│   ├── 05-order-processing.md
│   └── assets/
│       ├── 01/
│       │   ├── step-01-init-project.png    # Annotated screenshots
│       │   ├── step-03-add-task.gif        # Short interaction clips
│       │   └── full-walkthrough.mp4        # Complete video
│       ├── 02/
│       └── ...
└── _config.yml
```

## Fixture Design

### `rsf-server` Fixture

Per-spec lifecycle:

1. `rsf init <tutorial-name>` in a temp directory
2. `rsf ui --port <free-port>` launched as a child process
3. Waits for WebSocket readiness (polls `/ws` endpoint)
4. Provides `page` already navigated to the editor URL
5. On teardown: kills editor process, cleans temp directory

### `capture` Fixture

Wraps the Playwright `page` with step-tracking and screenshot/highlight helpers.

**Prerequisite:** Add `data-testid` attributes to key UI components (palette items, state nodes, edge handles, property editors, toolbar buttons) before writing tests. The current UI uses class-based selectors (`.palette-item`, React Flow internal classes) which are fragile for test automation. Adding `data-testid` attributes is a prerequisite task.

**Interaction model:** The UI uses drag-and-drop from a palette to create states (not click-based). Tests must use Playwright's drag-and-drop APIs (`page.dragAndDrop()` or manual mouse event sequences: `hover` → `mousedown` → `mousemove` → `mouseup`). Tutorial narratives should describe "drag from the palette" rather than "click to add."

```typescript
capture.step("add-task", {
  title: "Add a Task state",
  description: "Drag a Task state from the palette onto the canvas",
  highlight: { selector: "[data-testid='palette-task']", label: "Drag from here" },
  format: "gif-start"
});

// ... Playwright drag-and-drop actions ...

capture.step("add-task-result", {
  title: "Task state appears",
  description: "The new ProcessData state appears in the graph",
  highlight: { selector: "[data-testid='state-ProcessData']", label: "New state" },
  format: "gif-end"
});
```

**`capture.step()` method:**

1. Records step metadata to the in-memory manifest
2. If `highlight` specified, resolves the `data-testid` selector to bounding box pixel coordinates
3. Takes a screenshot via `page.screenshot()`
4. For `gif-start`/`gif-end`, marks timestamp ranges in the manifest for FFmpeg clip extraction from the full video
5. On fixture teardown, writes `manifest.json` to `.captures/<tutorial>/`

### Manifest Format

```json
{
  "tutorial": "01-hello-workflow",
  "steps": [
    {
      "step": 1,
      "name": "init-project",
      "title": "Initialize the project",
      "description": "Run rsf init to create a starter workflow",
      "screenshot": "step-01-init-project.png",
      "timestamp_ms": 4200,
      "highlight": {
        "x": 120, "y": 340, "width": 200, "height": 40,
        "label": "Graph updates here"
      },
      "format": "screenshot"
    }
  ]
}
```

## Post-Processing Pipeline

Three stages, each idempotent:

### 1. `annotate.sh` (ImageMagick)

For each screenshot in the manifest:
- Adds a step number badge (top-left corner)
- Draws highlight rectangles using coordinates from the manifest
- Adds label text near the highlight
- Crops to relevant area if the manifest specifies a crop region
- Outputs to `.captures/<tutorial>/annotated/`

### 2. `video-process.sh` (FFmpeg)

For each tutorial's `.webm`:
- Trims dead time between steps using manifest timestamps
- Adds text overlay at each step transition
- Produces a full-length `.mp4` for the complete walkthrough
- Extracts short `.gif` clips for `gif-start`/`gif-end` timestamp ranges

### 3. `assemble.py` (Jinja2)

- Reads all manifests and annotated assets
- Renders `tutorial.md.j2` per tutorial — each step becomes a section with annotated screenshot, title, description, and inline GIF where applicable
- Renders `index.md.j2` — tutorial cards with difficulty, time estimate, preview thumbnail
- Copies assets into `docs/tutorials/assets/`

## Tutorial Page Structure

Each generated tutorial page includes:
- Difficulty badge, estimated time, state count
- Numbered steps with annotated screenshot or inline GIF
- "Prefer to watch?" section with full video at the bottom
- Previous/next navigation between tutorials

**Format selection per step:**
- **Static screenshot** — for results (the graph after a change, the YAML output)
- **Animated GIF** — for interactions (dragging an edge, expanding a property editor)
- **Full video** — one per tutorial, linked at bottom as alternative to step-by-step

## CI/CD Integration

```yaml
# .github/workflows/tutorials.yml
# Triggers: push to ui/ or tests/ui-tutorials/, or manual dispatch
jobs:
  tutorials:
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - uses: actions/setup-python@v5
      - run: npm ci --prefix tests/ui-tutorials
      - run: npx --prefix tests/ui-tutorials playwright install --with-deps chromium
      - run: pip install -e .
      - run: npx --prefix tests/ui-tutorials playwright test
      - run: sudo apt-get install -y imagemagick ffmpeg
      - run: bash scripts/docs-pipeline/annotate.sh
      - run: bash scripts/docs-pipeline/video-process.sh
      - run: python scripts/docs-pipeline/assemble.py
      - uses: actions/configure-pages@v4
      - uses: actions/upload-pages-artifact@v3
        with:
          path: docs/
      - id: deployment
        uses: actions/deploy-pages@v4
```

**Playwright location:** Tutorial tests have their own `package.json` in `tests/ui-tutorials/` with Playwright as a dev dependency, separate from the UI's `ui/package.json`. This keeps test tooling independent from the application.

**Trigger scope:** Only runs when UI code or tutorial specs change, not on every push.

## Viewport and Visual Consistency

- Fixed viewport: 1280×800 for all specs
- Consistent browser: Chromium only (Playwright default)
- Deterministic layout: ELK.js auto-layout produces same positions for same graph structures (pin ELK version in package.json)
- Wait for animations: specs wait for layout transitions to complete before capture

## Dependencies

- **Playwright** — browser automation, screenshot, video recording
- **ImageMagick** — screenshot annotation (step badges, highlights, labels, cropping)
- **FFmpeg** — video trimming, text overlays, GIF extraction
- **Jinja2** — markdown template rendering (already an RSF dependency)
- **Jekyll / GitHub Pages** — static site hosting

## Out of Scope

- Audio narration for videos (text overlays only)
- Localization / multi-language tutorials
- Interactive tutorials (embedded sandboxes)
- Mobile viewport variants
