# Test-First UI Tutorial Documentation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Playwright-based tutorial tests that regression-test end-to-end workflow creation through the RSF graph editor UI while producing screenshots and video for GitHub Pages documentation.

**Architecture:** Each tutorial is a Playwright spec that drives the UI through building a real workflow from `rsf init`. A custom `capture` fixture records screenshots/video at each step, producing a `manifest.json`. A post-processing pipeline (ImageMagick + FFmpeg) annotates raw captures and a Python script assembles them into markdown pages for GitHub Pages.

**Tech Stack:** Playwright, TypeScript, ImageMagick, FFmpeg, Python/Jinja2, GitHub Actions, GitHub Pages

**Spec:** `docs/superpowers/specs/2026-03-18-ui-tutorial-testing-design.md`

**Reference:** The existing `ui/scripts/capture-screenshots.ts` provides a working pattern for starting `rsf ui`, polling readiness, and capturing Playwright screenshots. Reuse its patterns (process lifecycle, health checks, rsf CLI discovery) rather than reinventing.

---

## File Structure

### New Files

```
tests/ui-tutorials/
├── package.json                                    # Playwright + tsx dev dependencies
├── tsconfig.json                                   # TypeScript config
├── playwright.config.ts                            # 1280×800 viewport, video on, chromium only
├── fixtures/
│   ├── rsf-server.ts                               # rsf init + rsf ui lifecycle per spec
│   └── capture.ts                                  # Screenshot/video step tracker + manifest writer
├── tutorial-01-hello-workflow.spec.ts              # Tutorial 1: Task → Task → Succeed
├── tutorial-02-branching-logic.spec.ts             # Tutorial 2: Choice branching
├── tutorial-03-wait-and-retry.spec.ts              # Tutorial 3: Retry/Catch + Wait
├── tutorial-04-parallel-processing.spec.ts         # Tutorial 4: Parallel branches
├── tutorial-05-order-processing.spec.ts            # Tutorial 5: Full order-processing example
├── .gitignore                                      # Ignore .captures/, test-results/
scripts/docs-pipeline/
├── annotate.sh                                     # ImageMagick annotation
├── video-process.sh                                # FFmpeg video/GIF processing
├── assemble.py                                     # Manifest → markdown assembly
├── config.yaml                                     # Annotation styles
├── templates/
│   ├── tutorial.md.j2                              # Tutorial page template
│   └── index.md.j2                                 # Tutorial index template
docs/tutorials/
├── _config.yml                                     # GitHub Pages Jekyll config
.github/workflows/tutorials.yml                     # CI: test → capture → process → deploy
```

### Modified Files

```
ui/src/components/Palette.tsx                       # Add data-testid to palette items
ui/src/nodes/BaseNode.tsx                           # Add data-testid to node wrapper
ui/src/components/GraphCanvas.tsx                   # Add data-testid to graph container + edge handles
ui/src/App.tsx                                      # Add data-testid to app header
ui/src/components/MonacoEditor.tsx                  # Add data-testid to editor pane
.gitignore                                          # Add .captures/ and tests/ui-tutorials/test-results/
```

---

## Task 1: Add `data-testid` Attributes to UI Components

**Files:**
- Modify: `ui/src/components/Palette.tsx:26-29` (palette items)
- Modify: `ui/src/nodes/BaseNode.tsx:45-82` (node wrapper)
- Modify: `ui/src/components/GraphCanvas.tsx:444-482` (graph container)
- Modify: `ui/src/App.tsx:125` (app header)
- Modify: `ui/src/components/MonacoEditor.tsx:56` (editor pane)
- Test: run existing `ui/` vitest suite to verify no regressions

- [ ] **Step 1: Add data-testid to Palette items**

In `ui/src/components/Palette.tsx`, each `.palette-item` div needs a testid based on its state type. Find the map that renders palette items and add the attribute:

```tsx
// In the palette items map/render:
<div
  className="palette-item"
  draggable
  data-testid={`palette-${item.type.toLowerCase()}`}
  onDragStart={(e) => {
    e.dataTransfer.setData('application/rsf-state-type', item.type);
    e.dataTransfer.effectAllowed = 'move';
  }}
>
```

This produces: `data-testid="palette-task"`, `data-testid="palette-choice"`, etc.

- [ ] **Step 2: Add data-testid to BaseNode wrapper**

In `ui/src/nodes/BaseNode.tsx`, the root `.flow-node` div wraps all node types. Add a testid using the node's label (state name):

```tsx
<div
  className={`flow-node ${selected ? 'selected' : ''} ...`}
  data-testid={`state-${data.label}`}
  onClick={() => selectNode(id)}
>
```

This produces: `data-testid="state-HelloWorld"`, `data-testid="state-Done"`, etc.

- [ ] **Step 3: Add data-testid to GraphCanvas container**

In `ui/src/components/GraphCanvas.tsx`, the `.graph-container` div is the drop target:

```tsx
<div
  className="graph-container"
  data-testid="graph-canvas"
  ref={containerRef}
  tabIndex={0}
  onDrop={handleDrop}
  onDragOver={handleDragOver}
>
```

- [ ] **Step 4: Add data-testid to App header and MonacoEditor pane**

In `ui/src/App.tsx`, add testid to the header:

```tsx
<header className="app-header" data-testid="app-header">
```

In `ui/src/components/MonacoEditor.tsx`, add testid to the `.editor-pane` div (line 56):

```tsx
<div className="editor-pane" data-testid="yaml-editor">
```

- [ ] **Step 5: Run existing vitest suite to verify no regressions**

Run: `cd ui && npm test`
Expected: All 112 tests pass. The `data-testid` attributes don't affect logic.

- [ ] **Step 6: Commit**

```bash
git add ui/src/components/Palette.tsx ui/src/nodes/BaseNode.tsx ui/src/components/GraphCanvas.tsx ui/src/App.tsx ui/src/components/MonacoEditor.tsx
git commit -m "feat(ui): add data-testid attributes for Playwright test automation"
```

---

## Task 2: Scaffold Playwright Test Project

**Files:**
- Create: `tests/ui-tutorials/package.json`
- Create: `tests/ui-tutorials/tsconfig.json`
- Create: `tests/ui-tutorials/playwright.config.ts`
- Create: `tests/ui-tutorials/.gitignore`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "rsf-ui-tutorials",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "playwright test",
    "test:headed": "playwright test --headed",
    "test:one": "playwright test --grep"
  },
  "devDependencies": {
    "@playwright/test": "1.58.2",
    "tsx": "^4.19.0"
  }
}
```

Pin Playwright to same version as `ui/package.json` to avoid drift.

- [ ] **Step 2: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "dist",
    "rootDir": ".",
    "declaration": false,
    "sourceMap": true
  },
  "include": ["**/*.ts"],
  "exclude": ["dist", "node_modules"]
}
```

- [ ] **Step 3: Create playwright.config.ts**

```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: 'tutorial-*.spec.ts',
  timeout: 120_000, // 2 min per test — tutorials involve server startup
  retries: 0,
  workers: 1, // Sequential — each test starts its own rsf ui server
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    viewport: { width: 1280, height: 800 },
    video: 'on',
    screenshot: 'off', // We control screenshots via capture fixture
    trace: 'on-first-retry',
    browserName: 'chromium',
  },
  projects: [
    {
      name: 'tutorials',
      use: { browserName: 'chromium' },
    },
  ],
});
```

- [ ] **Step 4: Create .gitignore**

```
node_modules/
dist/
test-results/
playwright-report/
.captures/
```

- [ ] **Step 5: Install dependencies**

Run: `cd tests/ui-tutorials && npm install && npx playwright install chromium`
Expected: `node_modules/` created, chromium browser downloaded.

- [ ] **Step 6: Commit**

```bash
git add tests/ui-tutorials/package.json tests/ui-tutorials/tsconfig.json tests/ui-tutorials/playwright.config.ts tests/ui-tutorials/.gitignore
git commit -m "feat: scaffold Playwright test project for UI tutorials"
```

---

## Task 3: Build the `rsf-server` Fixture

**Files:**
- Create: `tests/ui-tutorials/fixtures/rsf-server.ts`
- Test: write a minimal smoke test that uses the fixture

This fixture manages the lifecycle of an `rsf init` project + `rsf ui` server for each test. Reuse patterns from the existing `ui/scripts/capture-screenshots.ts` (process management, health polling, rsf CLI discovery).

- [ ] **Step 1: Write a failing smoke test**

Create `tests/ui-tutorials/tutorial-00-smoke.spec.ts`:

```typescript
import { test, expect } from './fixtures/rsf-server';

test('smoke: rsf ui starts and graph renders', async ({ page }) => {
  // The fixture navigates to the editor and waits for readiness
  await expect(page.locator('.react-flow__node')).toHaveCount(2); // HelloWorld + Done
  await expect(page.locator('[data-testid="state-HelloWorld"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-Done"]')).toBeVisible();
});
```

- [ ] **Step 2: Run the smoke test to verify it fails**

Run: `cd tests/ui-tutorials && npx playwright test tutorial-00-smoke`
Expected: FAIL — fixture file doesn't exist yet.

- [ ] **Step 3: Implement the rsf-server fixture**

Create `tests/ui-tutorials/fixtures/rsf-server.ts`:

```typescript
import { test as base, expect, type Page } from '@playwright/test';
import { spawn, execFileSync, type ChildProcess } from 'node:child_process';
import { existsSync, mkdirSync, rmSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { tmpdir } from 'node:os';

const REPO_ROOT = resolve(__dirname, '..', '..', '..');

// ---------------------------------------------------------------------------
// Find rsf CLI (reused from ui/scripts/capture-screenshots.ts pattern)
// ---------------------------------------------------------------------------

function findRsfCommand(): string {
  const venvRsf = resolve(REPO_ROOT, '.venv', 'bin', 'rsf');
  if (existsSync(venvRsf)) return venvRsf;

  try {
    execFileSync('rsf', ['--version'], { stdio: 'ignore' });
    return 'rsf';
  } catch {
    // not in PATH
  }

  throw new Error('rsf CLI not found. Ensure the project venv exists with rsf installed.');
}

// ---------------------------------------------------------------------------
// Health check polling
// ---------------------------------------------------------------------------

async function waitForReady(url: string, maxRetries = 30, intervalMs = 500): Promise<void> {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // not ready
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`Server at ${url} did not become ready after ${maxRetries} attempts`);
}

// ---------------------------------------------------------------------------
// Port allocation
// ---------------------------------------------------------------------------

let nextPort = 18765;
function allocatePort(): number {
  return nextPort++;
}

// ---------------------------------------------------------------------------
// Fixture
// ---------------------------------------------------------------------------

interface RsfServerFixtures {
  rsfProjectDir: string;
  rsfPort: number;
}

export const test = base.extend<RsfServerFixtures>({
  rsfProjectDir: async ({}, use, testInfo) => {
    // Create a temp directory and run rsf init
    const projectName = testInfo.titlePath[0]
      ?.replace(/[^a-zA-Z0-9]/g, '-')
      .replace(/-+/g, '-')
      .toLowerCase()
      .slice(0, 30) || 'tutorial-test';

    const tmpDir = join(tmpdir(), `rsf-tutorial-${Date.now()}`);
    mkdirSync(tmpDir, { recursive: true });

    const rsf = findRsfCommand();
    execFileSync(rsf, ['init', projectName], { cwd: tmpDir, stdio: 'pipe' });

    const projectDir = join(tmpDir, projectName);

    await use(projectDir);

    // Cleanup
    rmSync(tmpDir, { recursive: true, force: true });
  },

  rsfPort: async ({}, use) => {
    const port = allocatePort();
    await use(port);
  },

  page: async ({ page, rsfProjectDir, rsfPort }, use) => {
    // Start rsf ui server
    const rsf = findRsfCommand();
    const child: ChildProcess = spawn(
      rsf,
      ['ui', 'workflow.yaml', '--port', String(rsfPort), '--no-browser'],
      {
        cwd: rsfProjectDir,
        stdio: ['ignore', 'pipe', 'pipe'],
        detached: true,
      },
    );

    // Collect stderr for diagnostics
    let stderr = '';
    child.stderr?.on('data', (d: Buffer) => { stderr += d.toString(); });

    try {
      // Wait for server readiness by polling /api/schema (HTTP GET endpoint)
      await waitForReady(`http://127.0.0.1:${rsfPort}/api/schema`);

      // Navigate to the editor
      await page.goto(`http://127.0.0.1:${rsfPort}/`, { waitUntil: 'networkidle' });

      // Wait for graph to render
      await page.waitForSelector('.react-flow', { state: 'visible', timeout: 15_000 });
      await page.waitForSelector('.react-flow__node', { state: 'visible', timeout: 15_000 });

      // Wait for ELK layout to stabilize
      await page.waitForTimeout(1500);

      await use(page);
    } finally {
      // Kill server
      if (child.pid) {
        try { process.kill(-child.pid, 'SIGTERM'); } catch { /* already dead */ }
      }
      // Grace period then force kill
      await new Promise<void>((resolve) => {
        const timer = setTimeout(() => {
          if (child.pid) {
            try { process.kill(-child.pid, 'SIGKILL'); } catch { /* ok */ }
          }
          resolve();
        }, 3000);
        child.on('exit', () => { clearTimeout(timer); resolve(); });
      });
    }
  },
});

export { expect };
```

Key design decisions:
- Uses `/api/schema` for health check (HTTP GET, not WebSocket)
- Allocates incrementing ports to avoid collisions when tests run sequentially
- Creates temp directory per test, cleans up after
- Navigates page and waits for graph render before yielding to the test
- Process group kill (`-child.pid`) to handle child processes of rsf

- [ ] **Step 4: Run the smoke test to verify it passes**

Run: `cd tests/ui-tutorials && npx playwright test tutorial-00-smoke`
Expected: PASS — graph renders with 2 nodes (HelloWorld, Done).

- [ ] **Step 5: Commit**

```bash
git add tests/ui-tutorials/fixtures/rsf-server.ts tests/ui-tutorials/tutorial-00-smoke.spec.ts
git commit -m "feat: add rsf-server Playwright fixture with smoke test"
```

---

## Task 4: Build the `capture` Fixture

**Files:**
- Create: `tests/ui-tutorials/fixtures/capture.ts`
- Test: extend the smoke test to use capture

- [ ] **Step 1: Write a failing test that uses capture**

Update `tests/ui-tutorials/tutorial-00-smoke.spec.ts`:

```typescript
import { test, expect } from './fixtures/capture';

test('smoke: capture fixture records steps', async ({ page, capture }) => {
  await capture.step('initial-graph', {
    title: 'Starter workflow',
    description: 'The default two-state workflow from rsf init',
  });

  await expect(page.locator('[data-testid="state-HelloWorld"]')).toBeVisible();

  await capture.step('verify-nodes', {
    title: 'Verify starter states',
    description: 'HelloWorld and Done states are visible',
    highlight: { selector: '[data-testid="state-HelloWorld"]', label: 'Start state' },
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tests/ui-tutorials && npx playwright test tutorial-00-smoke`
Expected: FAIL — capture fixture doesn't exist yet.

- [ ] **Step 3: Implement the capture fixture**

Create `tests/ui-tutorials/fixtures/capture.ts`:

```typescript
import { test as rsfTest, expect } from './rsf-server';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import type { Page, Locator } from '@playwright/test';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface HighlightSpec {
  selector: string;
  label: string;
}

interface HighlightCoords {
  x: number;
  y: number;
  width: number;
  height: number;
  label: string;
}

interface StepOptions {
  title: string;
  description: string;
  highlight?: HighlightSpec;
  format?: 'screenshot' | 'gif-start' | 'gif-end';
}

interface ManifestStep {
  step: number;
  name: string;
  title: string;
  description: string;
  screenshot: string;
  timestamp_ms: number;
  highlight?: HighlightCoords;
  format: 'screenshot' | 'gif-start' | 'gif-end';
}

interface Manifest {
  tutorial: string;
  steps: ManifestStep[];
}

// ---------------------------------------------------------------------------
// Capture helper class
// ---------------------------------------------------------------------------

class CaptureHelper {
  private page: Page;
  private outputDir: string;
  private tutorialName: string;
  private steps: ManifestStep[] = [];
  private startTime: number;

  constructor(page: Page, outputDir: string, tutorialName: string) {
    this.page = page;
    this.outputDir = outputDir;
    this.tutorialName = tutorialName;
    this.startTime = Date.now();
    mkdirSync(outputDir, { recursive: true });
  }

  async step(name: string, options: StepOptions): Promise<void> {
    const stepNum = this.steps.length + 1;
    const paddedNum = String(stepNum).padStart(2, '0');
    const screenshotFile = `step-${paddedNum}-${name}.png`;
    const screenshotPath = join(this.outputDir, screenshotFile);
    const format = options.format ?? 'screenshot';

    // Resolve highlight selector to pixel coordinates
    let highlightCoords: HighlightCoords | undefined;
    if (options.highlight) {
      try {
        const locator: Locator = this.page.locator(options.highlight.selector);
        const box = await locator.boundingBox();
        if (box) {
          highlightCoords = {
            x: Math.round(box.x),
            y: Math.round(box.y),
            width: Math.round(box.width),
            height: Math.round(box.height),
            label: options.highlight.label,
          };
        }
      } catch {
        // Selector not found — skip highlight, still capture screenshot
      }
    }

    // Take screenshot
    await this.page.screenshot({ path: screenshotPath, fullPage: false });

    // Record manifest entry
    const entry: ManifestStep = {
      step: stepNum,
      name,
      title: options.title,
      description: options.description,
      screenshot: screenshotFile,
      timestamp_ms: Date.now() - this.startTime,
      format,
    };
    if (highlightCoords) {
      entry.highlight = highlightCoords;
    }
    this.steps.push(entry);
  }

  writeManifest(): void {
    const manifest: Manifest = {
      tutorial: this.tutorialName,
      steps: this.steps,
    };
    writeFileSync(
      join(this.outputDir, 'manifest.json'),
      JSON.stringify(manifest, null, 2),
    );
  }
}

// ---------------------------------------------------------------------------
// Fixture extension
// ---------------------------------------------------------------------------

interface CaptureFixtures {
  capture: CaptureHelper;
}

export const test = rsfTest.extend<CaptureFixtures>({
  capture: async ({ page }, use, testInfo) => {
    // Derive tutorial name from the test file: "tutorial-01-hello-workflow.spec.ts" → "tutorial-01"
    const fileName = testInfo.titlePath[0] ?? 'unknown';
    const tutorialMatch = fileName.match(/tutorial-(\d+)/);
    const tutorialName = tutorialMatch
      ? `tutorial-${tutorialMatch[1]}`
      : fileName.replace(/[^a-zA-Z0-9-]/g, '-');

    // Output directory for raw captures
    const capturesRoot = join(__dirname, '..', '.captures');
    const outputDir = join(capturesRoot, tutorialName);

    const helper = new CaptureHelper(page, outputDir, tutorialName);

    await use(helper);

    // Write manifest on teardown
    helper.writeManifest();
  },
});

export { expect };
```

- [ ] **Step 4: Run test to verify capture works**

Run: `cd tests/ui-tutorials && npx playwright test tutorial-00-smoke`
Expected: PASS. Check that `.captures/tutorial-00/manifest.json` exists and contains 2 steps with screenshot files.

Run: `cat tests/ui-tutorials/.captures/tutorial-00/manifest.json`
Expected: JSON with `tutorial: "tutorial-00"`, `steps` array of 2 entries, each with `screenshot`, `title`, `timestamp_ms`.

Run: `ls tests/ui-tutorials/.captures/tutorial-00/`
Expected: `step-01-initial-graph.png`, `step-02-verify-nodes.png`, `manifest.json`

- [ ] **Step 5: Commit**

```bash
git add tests/ui-tutorials/fixtures/capture.ts tests/ui-tutorials/tutorial-00-smoke.spec.ts
git commit -m "feat: add capture Playwright fixture with manifest generation"
```

---

## Task 5: Write Tutorial 1 — Hello Workflow

**Files:**
- Create: `tests/ui-tutorials/tutorial-01-hello-workflow.spec.ts`

This tutorial starts from `rsf init` (HelloWorld → Done) and builds: HelloWorld → ProcessData → Done (Succeed). It teaches: adding a state via drag-and-drop, connecting edges, renaming states, editing properties.

- [ ] **Step 1: Write the tutorial spec**

Create `tests/ui-tutorials/tutorial-01-hello-workflow.spec.ts`:

```typescript
import { test, expect } from './fixtures/capture';

test('Tutorial 1: Hello Workflow', async ({ page, capture }) => {
  // Step 1: Observe the starter workflow
  await capture.step('starter-workflow', {
    title: 'The starter workflow',
    description: 'After rsf init, you have a two-state workflow: HelloWorld (Task) → Done (Succeed)',
  });

  // Verify starter states exist
  await expect(page.locator('[data-testid="state-HelloWorld"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-Done"]')).toBeVisible();

  // Step 2: Drag a new Task state from the palette onto the canvas
  await capture.step('drag-task-start', {
    title: 'Drag a Task state from the palette',
    description: 'Drag the Task item from the palette onto the canvas to add a new state',
    highlight: { selector: '[data-testid="palette-task"]', label: 'Drag from here' },
    format: 'gif-start',
  });

  const paletteTask = page.locator('[data-testid="palette-task"]');
  const canvas = page.locator('[data-testid="graph-canvas"]');

  // Perform drag-and-drop: palette → canvas center
  const canvasBox = await canvas.boundingBox();
  expect(canvasBox).toBeTruthy();
  await paletteTask.dragTo(canvas, {
    targetPosition: { x: canvasBox!.width / 2, y: canvasBox!.height / 2 },
  });

  // Wait for the new node to appear and layout to settle
  await page.waitForTimeout(1500);

  // The new node has a generated name like "TaskState<timestamp>"
  // Find it — there should now be 3 nodes total
  const allNodes = page.locator('.react-flow__node');
  await expect(allNodes).toHaveCount(3);

  await capture.step('task-added', {
    title: 'New Task state appears on the canvas',
    description: 'A new Task state has been added. It has an auto-generated name that we will rename.',
    format: 'gif-end',
  });

  // Step 3: Rename the new state by expanding it and editing in YAML
  // The new state needs to be renamed to "ProcessData"
  // This is done by editing the YAML in the Monaco editor
  // Find the YAML editor and update the state name
  await capture.step('yaml-editor', {
    title: 'Rename the state in the YAML editor',
    description: 'Edit the YAML to rename the auto-generated state to "ProcessData" and set its Next to "Done"',
    highlight: { selector: '[data-testid="yaml-editor"]', label: 'Edit YAML here' },
  });

  // Replace YAML content via Monaco keyboard input
  // Click into the editor pane, select all, and type the new YAML
  await page.locator('[data-testid="yaml-editor"]').click();
  await page.keyboard.press('Control+a');
  await page.keyboard.type(`rsf_version: "1.0"
Comment: "Hello Workflow tutorial"
StartAt: HelloWorld

States:
  HelloWorld:
    Type: Task
    Next: ProcessData

  ProcessData:
    Type: Task
    Next: Done

  Done:
    Type: Succeed
`, { delay: 5 }); // Small delay for realistic typing speed in video

  // Wait for YAML → graph sync
  await page.waitForTimeout(2000);

  // Verify the renamed state appears
  await expect(page.locator('[data-testid="state-ProcessData"]')).toBeVisible();

  await capture.step('workflow-complete', {
    title: 'Complete three-state workflow',
    description: 'The workflow now has three states: HelloWorld → ProcessData → Done',
    highlight: { selector: '[data-testid="state-ProcessData"]', label: 'New state' },
  });

  // Step 4: Verify the graph structure
  await expect(page.locator('[data-testid="state-HelloWorld"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-ProcessData"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-Done"]')).toBeVisible();

  // Verify edges: should have 2 edges (HelloWorld→ProcessData, ProcessData→Done)
  const edges = page.locator('.react-flow__edge');
  await expect(edges).toHaveCount(2);

  await capture.step('final-verification', {
    title: 'Verify the completed workflow',
    description: 'All three states are connected: HelloWorld → ProcessData → Done. The workflow is valid.',
  });
});
```

- [ ] **Step 2: Run the tutorial test**

Run: `cd tests/ui-tutorials && npx playwright test tutorial-01`
Expected: PASS. Screenshots and manifest written to `.captures/tutorial-01/`.

- [ ] **Step 3: Verify captures**

Run: `ls tests/ui-tutorials/.captures/tutorial-01/`
Expected: 5 screenshot PNGs + `manifest.json`

Run: `cat tests/ui-tutorials/.captures/tutorial-01/manifest.json | python3 -m json.tool`
Expected: Valid JSON with 5 steps, each with title, description, screenshot filename, timestamp.

- [ ] **Step 4: Commit**

```bash
git add tests/ui-tutorials/tutorial-01-hello-workflow.spec.ts
git commit -m "feat: add Tutorial 1 — Hello Workflow (Task → Task → Succeed)"
```

---

## Task 6: Write Tutorial 2 — Branching Logic

**Files:**
- Create: `tests/ui-tutorials/tutorial-02-branching-logic.spec.ts`

Builds a workflow with Choice state: ValidateInput (Task) → CheckResult (Choice) → [Success (Task) | InvalidInput (Fail)]. Teaches: adding Choice states, configuring choice rules, default branches, multiple outbound edges.

- [ ] **Step 1: Write the tutorial spec**

Create `tests/ui-tutorials/tutorial-02-branching-logic.spec.ts`:

```typescript
import { test, expect } from './fixtures/capture';

test('Tutorial 2: Branching Logic', async ({ page, capture }) => {
  await capture.step('starter-workflow', {
    title: 'Start from the default workflow',
    description: 'We begin with the rsf init starter: HelloWorld → Done',
  });

  // Replace YAML with the branching workflow
  await page.locator('[data-testid="yaml-editor"]').click();
  await page.keyboard.press('Control+a');

  // Build in stages to show progression

  // Stage 1: Add a Task state with a Choice state
  await page.keyboard.type(`rsf_version: "1.0"
Comment: "Branching logic tutorial"
StartAt: ValidateInput

States:
  ValidateInput:
    Type: Task
    Next: CheckResult

  CheckResult:
    Type: Choice
    Choices:
      - Variable: "$.valid"
        BooleanEquals: true
        Next: ProcessItem
    Default: InvalidInput

  ProcessItem:
    Type: Task
    Next: Success

  Success:
    Type: Succeed

  InvalidInput:
    Type: Fail
    Error: "ValidationError"
    Cause: "Input validation failed"
`, { delay: 5 });

  await page.waitForTimeout(2000);

  await capture.step('yaml-entered', {
    title: 'Define the branching workflow in YAML',
    description: 'A workflow with ValidateInput → CheckResult (Choice) that branches to ProcessItem or InvalidInput',
    highlight: { selector: '[data-testid="yaml-editor"]', label: 'YAML definition' },
  });

  // Verify all states rendered
  await expect(page.locator('[data-testid="state-ValidateInput"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-CheckResult"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-ProcessItem"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-Success"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-InvalidInput"]')).toBeVisible();

  await capture.step('graph-rendered', {
    title: 'Graph shows the branching structure',
    description: 'The graph renders all 5 states with the Choice state branching to ProcessItem and InvalidInput',
    highlight: { selector: '[data-testid="state-CheckResult"]', label: 'Choice state branches here' },
  });

  // Verify edges: ValidateInput→CheckResult, CheckResult→ProcessItem, CheckResult→InvalidInput, ProcessItem→Success
  const edges = page.locator('.react-flow__edge');
  await expect(edges).toHaveCount(4);

  // Click on the Choice node to expand its property editor
  await page.locator('[data-testid="state-CheckResult"]').click();
  await page.waitForTimeout(500);

  // Expand the node to see choice rules
  const expandBtn = page.locator('[data-testid="state-CheckResult"] .node-expand-chevron');
  if (await expandBtn.isVisible()) {
    await expandBtn.click();
    await page.waitForTimeout(500);
  }

  await capture.step('choice-expanded', {
    title: 'Inspect the Choice state properties',
    description: 'Expanding the CheckResult state shows the choice rule: $.valid equals true → ProcessItem, default → InvalidInput',
    highlight: { selector: '[data-testid="state-CheckResult"]', label: 'Choice rules' },
  });

  await capture.step('final-workflow', {
    title: 'Complete branching workflow',
    description: 'The workflow validates input, branches on the result, and either processes the item or fails with a validation error',
  });
});
```

- [ ] **Step 2: Run the test**

Run: `cd tests/ui-tutorials && npx playwright test tutorial-02`
Expected: PASS with 5 screenshots in `.captures/tutorial-02/`.

- [ ] **Step 3: Commit**

```bash
git add tests/ui-tutorials/tutorial-02-branching-logic.spec.ts
git commit -m "feat: add Tutorial 2 — Branching Logic (Choice state)"
```

---

## Task 7: Write Tutorial 3 — Wait & Retry

**Files:**
- Create: `tests/ui-tutorials/tutorial-03-wait-and-retry.spec.ts`

Builds: SubmitRequest (Task with Retry+Catch) → WaitForProcessing (Wait) → CheckStatus (Task) → Complete (Succeed) / HandleError (Fail). Teaches: Retry configuration, Catch blocks, Wait state timing.

- [ ] **Step 1: Write the tutorial spec**

Create `tests/ui-tutorials/tutorial-03-wait-and-retry.spec.ts`:

```typescript
import { test, expect } from './fixtures/capture';

test('Tutorial 3: Wait and Retry', async ({ page, capture }) => {
  await capture.step('starter-workflow', {
    title: 'Start from the default workflow',
    description: 'Begin with rsf init starter and build a workflow with retry logic and wait states',
  });

  await page.locator('[data-testid="yaml-editor"]').click();
  await page.keyboard.press('Control+a');

  await page.keyboard.type(`rsf_version: "1.0"
Comment: "Wait and retry tutorial"
StartAt: SubmitRequest

States:
  SubmitRequest:
    Type: Task
    Retry:
      - ErrorEquals: ["ServiceUnavailable"]
        IntervalSeconds: 2
        MaxAttempts: 3
        BackoffRate: 2.0
    Catch:
      - ErrorEquals: ["States.ALL"]
        Next: HandleError
        ResultPath: "$.error"
    Next: WaitForProcessing

  WaitForProcessing:
    Type: Wait
    Seconds: 10
    Next: CheckStatus

  CheckStatus:
    Type: Task
    Next: Complete

  Complete:
    Type: Succeed

  HandleError:
    Type: Fail
    Error: "ProcessingFailed"
    Cause: "Request processing failed after retries"
`, { delay: 5 });

  await page.waitForTimeout(2000);

  await capture.step('yaml-entered', {
    title: 'Define retry and wait workflow',
    description: 'SubmitRequest has a Retry policy (3 attempts with exponential backoff) and a Catch that routes errors to HandleError',
    highlight: { selector: '[data-testid="yaml-editor"]', label: 'Retry + Catch config' },
  });

  // Verify states
  await expect(page.locator('[data-testid="state-SubmitRequest"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-WaitForProcessing"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-CheckStatus"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-Complete"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-HandleError"]')).toBeVisible();

  await capture.step('graph-rendered', {
    title: 'Graph shows the workflow with error handling',
    description: 'The graph shows the main path (Submit → Wait → Check → Complete) with a catch edge to HandleError',
  });

  // Click SubmitRequest to show Retry/Catch badges
  await page.locator('[data-testid="state-SubmitRequest"]').click();
  await page.waitForTimeout(500);

  const expandBtn = page.locator('[data-testid="state-SubmitRequest"] .node-expand-chevron');
  if (await expandBtn.isVisible()) {
    await expandBtn.click();
    await page.waitForTimeout(500);
  }

  await capture.step('retry-config', {
    title: 'Inspect the Retry configuration',
    description: 'SubmitRequest shows Retry (3 attempts, 2s interval, 2x backoff) and Catch (all errors → HandleError)',
    highlight: { selector: '[data-testid="state-SubmitRequest"]', label: 'Retry + Catch' },
  });

  // Click Wait state to show timing
  await page.locator('[data-testid="state-WaitForProcessing"]').click();
  await page.waitForTimeout(500);

  const waitExpand = page.locator('[data-testid="state-WaitForProcessing"] .node-expand-chevron');
  if (await waitExpand.isVisible()) {
    await waitExpand.click();
    await page.waitForTimeout(500);
  }

  await capture.step('wait-config', {
    title: 'Inspect the Wait state',
    description: 'WaitForProcessing pauses execution for 10 seconds before checking the status',
    highlight: { selector: '[data-testid="state-WaitForProcessing"]', label: 'Wait: 10 seconds' },
  });

  await capture.step('final-workflow', {
    title: 'Complete workflow with error handling',
    description: 'A resilient workflow: submit with retries, wait, check status, with full error handling',
  });
});
```

- [ ] **Step 2: Run the test**

Run: `cd tests/ui-tutorials && npx playwright test tutorial-03`
Expected: PASS with 7 screenshots.

- [ ] **Step 3: Commit**

```bash
git add tests/ui-tutorials/tutorial-03-wait-and-retry.spec.ts
git commit -m "feat: add Tutorial 3 — Wait & Retry (Retry/Catch + Wait states)"
```

---

## Task 8: Write Tutorial 4 — Parallel Processing

**Files:**
- Create: `tests/ui-tutorials/tutorial-04-parallel-processing.spec.ts`

Builds: PrepareData (Task) → ProcessBranches (Parallel with 2 branches) → MergeResults (Task) → Done (Succeed). Teaches: Parallel state, branch definitions, result merging.

- [ ] **Step 1: Write the tutorial spec**

Create `tests/ui-tutorials/tutorial-04-parallel-processing.spec.ts`:

```typescript
import { test, expect } from './fixtures/capture';

test('Tutorial 4: Parallel Processing', async ({ page, capture }) => {
  await capture.step('starter-workflow', {
    title: 'Start from the default workflow',
    description: 'Build a workflow with parallel branches for concurrent processing',
  });

  await page.locator('[data-testid="yaml-editor"]').click();
  await page.keyboard.press('Control+a');

  await page.keyboard.type(`rsf_version: "1.0"
Comment: "Parallel processing tutorial"
StartAt: PrepareData

States:
  PrepareData:
    Type: Task
    Next: ProcessBranches

  ProcessBranches:
    Type: Parallel
    Branches:
      - StartAt: EnrichData
        States:
          EnrichData:
            Type: Task
            End: true
      - StartAt: ValidateData
        States:
          ValidateData:
            Type: Task
            End: true
    Next: MergeResults

  MergeResults:
    Type: Task
    Next: Done

  Done:
    Type: Succeed
`, { delay: 5 });

  await page.waitForTimeout(2000);

  await capture.step('yaml-entered', {
    title: 'Define a parallel workflow',
    description: 'ProcessBranches runs EnrichData and ValidateData concurrently, then merges results',
    highlight: { selector: '[data-testid="yaml-editor"]', label: 'Parallel branches' },
  });

  // Verify main states
  await expect(page.locator('[data-testid="state-PrepareData"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-ProcessBranches"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-MergeResults"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-Done"]')).toBeVisible();

  await capture.step('graph-rendered', {
    title: 'Graph shows parallel structure',
    description: 'The Parallel state shows its two branches: EnrichData and ValidateData execute concurrently',
    highlight: { selector: '[data-testid="state-ProcessBranches"]', label: 'Parallel state' },
  });

  // Expand Parallel node to see branches
  await page.locator('[data-testid="state-ProcessBranches"]').click();
  await page.waitForTimeout(500);

  const expandBtn = page.locator('[data-testid="state-ProcessBranches"] .node-expand-chevron');
  if (await expandBtn.isVisible()) {
    await expandBtn.click();
    await page.waitForTimeout(500);
  }

  await capture.step('parallel-expanded', {
    title: 'Inspect Parallel state branches',
    description: 'The Parallel state contains two branches, each with their own sub-workflow',
    highlight: { selector: '[data-testid="state-ProcessBranches"]', label: 'Branch details' },
  });

  await capture.step('final-workflow', {
    title: 'Complete parallel processing workflow',
    description: 'PrepareData → ProcessBranches (EnrichData || ValidateData) → MergeResults → Done',
  });
});
```

- [ ] **Step 2: Run the test**

Run: `cd tests/ui-tutorials && npx playwright test tutorial-04`
Expected: PASS with 5 screenshots.

- [ ] **Step 3: Commit**

```bash
git add tests/ui-tutorials/tutorial-04-parallel-processing.spec.ts
git commit -m "feat: add Tutorial 4 — Parallel Processing"
```

---

## Task 9: Write Tutorial 5 — Order Processing (Full Example)

**Files:**
- Create: `tests/ui-tutorials/tutorial-05-order-processing.spec.ts`

Builds the complete `examples/order-processing/workflow.yaml` from scratch through the UI. This is the capstone tutorial covering all state types, Retry/Catch, Choice, Parallel, Succeed, and Fail.

- [ ] **Step 1: Write the tutorial spec**

Create `tests/ui-tutorials/tutorial-05-order-processing.spec.ts`. This tutorial builds the workflow in stages, capturing screenshots at each stage to show progression:

```typescript
import { test, expect } from './fixtures/capture';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const REPO_ROOT = resolve(__dirname, '..', '..');

test('Tutorial 5: Order Processing', async ({ page, capture }) => {
  await capture.step('starter-workflow', {
    title: 'Start from the default workflow',
    description: 'We will build the complete order-processing example — the most complex workflow in RSF',
  });

  // Stage 1: Basic structure — ValidateOrder + CheckOrderValue
  await page.locator('[data-testid="yaml-editor"]').click();
  await page.keyboard.press('Control+a');
  await page.keyboard.type(`rsf_version: "1.0"
Comment: "Order processing workflow"
StartAt: ValidateOrder

States:
  ValidateOrder:
    Type: Task
    Next: CheckOrderValue

  CheckOrderValue:
    Type: Choice
    Choices:
      - Variable: "$.validation.total"
        NumericGreaterThan: 1000
        Next: RequireApproval
      - Variable: "$.validation.itemCount"
        NumericEquals: 0
        Next: OrderRejected
    Default: ProcessOrder

  RequireApproval:
    Type: Task
    Next: ProcessOrder

  ProcessOrder:
    Type: Task
    Next: SendConfirmation

  SendConfirmation:
    Type: Task
    Next: OrderComplete

  OrderComplete:
    Type: Succeed

  OrderRejected:
    Type: Fail
    Error: "OrderRejected"
    Cause: "Order could not be processed"
`, { delay: 3 });

  await page.waitForTimeout(2000);

  await capture.step('basic-structure', {
    title: 'Stage 1: Basic workflow structure',
    description: 'Define the core states: validate, branch on value, approval path, process, confirm',
  });

  // Verify core states
  await expect(page.locator('[data-testid="state-ValidateOrder"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-CheckOrderValue"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-OrderComplete"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-OrderRejected"]')).toBeVisible();

  await capture.step('core-states-visible', {
    title: 'Core states rendered in the graph',
    description: 'The graph shows the branching structure: high-value orders require approval, empty orders are rejected',
    highlight: { selector: '[data-testid="state-CheckOrderValue"]', label: 'Choice branches' },
  });

  // Stage 2: Add Retry/Catch to ValidateOrder and full Parallel for ProcessOrder
  await page.locator('[data-testid="yaml-editor"]').click();
  await page.keyboard.press('Control+a');

  // Now enter the complete workflow (matching examples/order-processing/workflow.yaml)
  const fullWorkflow = readFileSync(
    resolve(REPO_ROOT, 'examples', 'order-processing', 'workflow.yaml'),
    'utf-8',
  );
  await page.keyboard.type(fullWorkflow, { delay: 2 });

  await page.waitForTimeout(2500);

  await capture.step('full-workflow-yaml', {
    title: 'Stage 2: Complete workflow with error handling and parallelism',
    description: 'Added Retry/Catch to ValidateOrder, timeout to RequireApproval, and Parallel branches for ProcessOrder',
    highlight: { selector: '[data-testid="yaml-editor"]', label: 'Full YAML definition' },
  });

  // Verify all states
  const expectedStates = [
    'ValidateOrder', 'CheckOrderValue', 'RequireApproval',
    'ProcessOrder', 'SendConfirmation', 'OrderComplete', 'OrderRejected',
  ];
  for (const state of expectedStates) {
    await expect(page.locator(`[data-testid="state-${state}"]`)).toBeVisible();
  }

  await capture.step('full-graph', {
    title: 'Complete order-processing graph',
    description: 'All 7 states with Retry/Catch, Choice branching, Parallel processing, and terminal states',
  });

  // Inspect key nodes
  // ValidateOrder — Retry + Catch
  await page.locator('[data-testid="state-ValidateOrder"]').click();
  await page.waitForTimeout(300);
  const validateExpand = page.locator('[data-testid="state-ValidateOrder"] .node-expand-chevron');
  if (await validateExpand.isVisible()) {
    await validateExpand.click();
    await page.waitForTimeout(500);
  }

  await capture.step('validate-retry-catch', {
    title: 'ValidateOrder: Retry and Catch configuration',
    description: 'Retries on ValidationTimeout (3 attempts, exponential backoff). Catches InvalidOrderError → OrderRejected',
    highlight: { selector: '[data-testid="state-ValidateOrder"]', label: 'Retry + Catch' },
  });

  // Collapse and inspect ProcessOrder — Parallel
  await page.locator('[data-testid="state-ProcessOrder"]').click();
  await page.waitForTimeout(300);
  const processExpand = page.locator('[data-testid="state-ProcessOrder"] .node-expand-chevron');
  if (await processExpand.isVisible()) {
    await processExpand.click();
    await page.waitForTimeout(500);
  }

  await capture.step('process-parallel', {
    title: 'ProcessOrder: Parallel branches',
    description: 'ProcessPayment and ReserveInventory run concurrently, each with their own Retry policies',
    highlight: { selector: '[data-testid="state-ProcessOrder"]', label: 'Parallel branches' },
  });

  await capture.step('final-complete', {
    title: 'Complete order-processing workflow',
    description: 'A production-ready workflow with validation, branching, approval, parallel processing, error handling, and terminal states',
  });
});
```

- [ ] **Step 2: Run the test**

Run: `cd tests/ui-tutorials && npx playwright test tutorial-05`
Expected: PASS with 9 screenshots.

- [ ] **Step 3: Commit**

```bash
git add tests/ui-tutorials/tutorial-05-order-processing.spec.ts
git commit -m "feat: add Tutorial 5 — Order Processing (full example)"
```

---

## Task 10: Build the Post-Processing Pipeline — Annotate

**Files:**
- Create: `scripts/docs-pipeline/annotate.sh`
- Create: `scripts/docs-pipeline/config.yaml`

- [ ] **Step 1: Create config.yaml with annotation styles**

Create `scripts/docs-pipeline/config.yaml`:

```yaml
# Annotation styles for ImageMagick post-processing
badge:
  size: 36
  font_size: 18
  background: "#3b82f6"
  text_color: "white"
  offset_x: 12
  offset_y: 12

highlight:
  border_color: "#f59e0b"
  border_width: 3
  corner_radius: 6
  label_font_size: 14
  label_background: "#f59e0b"
  label_text_color: "#1e293b"
  label_padding: 4

output:
  captures_dir: "tests/ui-tutorials/.captures"
  annotated_subdir: "annotated"
```

- [ ] **Step 2: Create annotate.sh**

Create `scripts/docs-pipeline/annotate.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Annotate raw screenshots with step numbers, highlights, and labels
# Reads manifest.json from each tutorial's .captures/ directory
# Outputs annotated PNGs to .captures/<tutorial>/annotated/

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CAPTURES_DIR="${REPO_ROOT}/tests/ui-tutorials/.captures"

# Config values (could parse from config.yaml, but shell keeps it simple)
BADGE_SIZE=36
BADGE_FONT_SIZE=18
BADGE_BG="#3b82f6"
BADGE_TEXT="white"
BADGE_OFFSET=12
HIGHLIGHT_COLOR="#f59e0b"
HIGHLIGHT_WIDTH=3
LABEL_FONT_SIZE=14
LABEL_BG="#f59e0b"
LABEL_TEXT="#1e293b"

if [ ! -d "$CAPTURES_DIR" ]; then
  echo "No captures directory found at $CAPTURES_DIR"
  exit 1
fi

for tutorial_dir in "$CAPTURES_DIR"/tutorial-*/; do
  [ -d "$tutorial_dir" ] || continue

  manifest="$tutorial_dir/manifest.json"
  if [ ! -f "$manifest" ]; then
    echo "Warning: No manifest.json in $tutorial_dir, skipping"
    continue
  fi

  tutorial_name=$(basename "$tutorial_dir")
  annotated_dir="$tutorial_dir/annotated"
  mkdir -p "$annotated_dir"

  echo "Annotating $tutorial_name..."

  # Parse manifest with python (jq alternative that's always available)
  python3 -c "
import json, sys

with open('$manifest') as f:
    manifest = json.load(f)

for step in manifest['steps']:
    print(json.dumps(step))
" | while IFS= read -r step_json; do
    step_num=$(echo "$step_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['step'])")
    screenshot=$(echo "$step_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['screenshot'])")
    src="$tutorial_dir/$screenshot"
    dst="$annotated_dir/$screenshot"

    if [ ! -f "$src" ]; then
      echo "  Warning: $screenshot not found, skipping"
      continue
    fi

    # Start with a copy
    cp "$src" "$dst"

    # Add step number badge (top-left circle with number)
    convert "$dst" \
      -fill "$BADGE_BG" -draw "circle $((BADGE_OFFSET + BADGE_SIZE/2)),$((BADGE_OFFSET + BADGE_SIZE/2)) $((BADGE_OFFSET + BADGE_SIZE)),$((BADGE_OFFSET + BADGE_SIZE/2))" \
      -fill "$BADGE_TEXT" -pointsize "$BADGE_FONT_SIZE" -gravity NorthWest \
      -annotate "+$((BADGE_OFFSET + BADGE_SIZE/2 - BADGE_FONT_SIZE/3))+$((BADGE_OFFSET + BADGE_SIZE/2 - BADGE_FONT_SIZE/2))" "$step_num" \
      "$dst"

    # Add highlight rectangle if present
    has_highlight=$(echo "$step_json" | python3 -c "
import json, sys
step = json.load(sys.stdin)
print('yes' if 'highlight' in step and step['highlight'] else 'no')
")

    if [ "$has_highlight" = "yes" ]; then
      eval "$(echo "$step_json" | python3 -c "
import json, sys
h = json.load(sys.stdin)['highlight']
print(f\"H_X={h['x']} H_Y={h['y']} H_W={h['width']} H_H={h['height']} H_LABEL='{h['label']}'\")"
)"

      # Draw highlight rectangle
      convert "$dst" \
        -stroke "$HIGHLIGHT_COLOR" -strokewidth "$HIGHLIGHT_WIDTH" -fill none \
        -draw "roundrectangle $H_X,$H_Y $((H_X+H_W)),$((H_Y+H_H)) 6,6" \
        "$dst"

      # Add label above the highlight
      convert "$dst" \
        -fill "$LABEL_BG" -draw "roundrectangle $H_X,$((H_Y-24)) $((H_X+${#H_LABEL}*9+8)),$((H_Y-2)) 3,3" \
        -fill "$LABEL_TEXT" -pointsize "$LABEL_FONT_SIZE" \
        -annotate "+$((H_X+4))+$((H_Y-7))" "$H_LABEL" \
        "$dst"
    fi

    echo "  Annotated: $screenshot (step $step_num)"
  done
done

echo "Annotation complete."
```

- [ ] **Step 3: Make executable and test**

Run: `chmod +x scripts/docs-pipeline/annotate.sh`

Run the tutorial tests first to generate captures, then run annotation:
Run: `cd tests/ui-tutorials && npx playwright test tutorial-01 && cd ../.. && bash scripts/docs-pipeline/annotate.sh`
Expected: Annotated PNGs in `tests/ui-tutorials/.captures/tutorial-01/annotated/`

Run: `ls tests/ui-tutorials/.captures/tutorial-01/annotated/`
Expected: Same filenames as raw screenshots, now with badges and highlights.

- [ ] **Step 4: Commit**

```bash
git add scripts/docs-pipeline/annotate.sh scripts/docs-pipeline/config.yaml
git commit -m "feat: add ImageMagick annotation pipeline for tutorial screenshots"
```

---

## Task 11: Build the Post-Processing Pipeline — Video

**Files:**
- Create: `scripts/docs-pipeline/video-process.sh`

- [ ] **Step 1: Create video-process.sh**

Create `scripts/docs-pipeline/video-process.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Process raw Playwright video recordings:
# 1. Convert .webm to .mp4
# 2. Add step title overlays using manifest timestamps
# 3. Extract short GIF clips for gif-start/gif-end ranges

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CAPTURES_DIR="${REPO_ROOT}/tests/ui-tutorials/.captures"

if [ ! -d "$CAPTURES_DIR" ]; then
  echo "No captures directory found at $CAPTURES_DIR"
  exit 1
fi

for tutorial_dir in "$CAPTURES_DIR"/tutorial-*/; do
  [ -d "$tutorial_dir" ] || continue

  manifest="$tutorial_dir/manifest.json"
  if [ ! -f "$manifest" ]; then
    continue
  fi

  tutorial_name=$(basename "$tutorial_dir")
  echo "Processing video for $tutorial_name..."

  # Find the Playwright video recording
  # Playwright stores videos in test-results/ or as configured
  # The video path depends on Playwright config; look for .webm files
  video_file=""
  for webm in "$tutorial_dir"/*.webm "${REPO_ROOT}/tests/ui-tutorials/test-results/"*"${tutorial_name}"*/*.webm; do
    if [ -f "$webm" ]; then
      video_file="$webm"
      break
    fi
  done

  if [ -z "$video_file" ]; then
    echo "  No video recording found for $tutorial_name, skipping video processing"
    continue
  fi

  # 1. Convert .webm → .mp4
  mp4_file="$tutorial_dir/full-walkthrough.mp4"
  ffmpeg -y -i "$video_file" \
    -c:v libx264 -preset fast -crf 23 \
    -movflags +faststart \
    "$mp4_file" 2>/dev/null

  echo "  Converted: full-walkthrough.mp4"

  # 2. Add step title overlays
  overlay_file="$tutorial_dir/full-walkthrough-titled.mp4"
  # Build drawtext filter from manifest timestamps
  drawtext_filter=$(python3 -c "
import json, sys

with open('$manifest') as f:
    manifest = json.load(f)

filters = []
steps = manifest['steps']
for i, step in enumerate(steps):
    start_s = step['timestamp_ms'] / 1000.0
    # End at next step's start, or +5s for last step
    if i + 1 < len(steps):
        end_s = steps[i+1]['timestamp_ms'] / 1000.0
    else:
        end_s = start_s + 5.0

    title = step['title'].replace(\"'\", \"\\\\'\").replace(':', '\\\\:')
    step_num = step['step']
    text = f'Step {step_num}: {title}'

    filters.append(
        f\"drawtext=text='{text}':fontsize=20:fontcolor=white:\"
        f\"box=1:boxcolor=black@0.7:boxborderw=8:\"
        f\"x=20:y=h-60:enable='between(t,{start_s:.2f},{end_s:.2f})'\"
    )

print(','.join(filters))
")

  if [ -n "$drawtext_filter" ]; then
    ffmpeg -y -i "$mp4_file" \
      -vf "$drawtext_filter" \
      -c:v libx264 -preset fast -crf 23 \
      "$overlay_file" 2>/dev/null
    # Replace original with titled version
    mv "$overlay_file" "$mp4_file"
    echo "  Added step title overlays"
  fi

  # 3. Extract GIF clips for gif-start/gif-end ranges
  python3 -c "
import json
with open('$manifest') as f:
    manifest = json.load(f)

steps = manifest['steps']
gif_start = None
for step in steps:
    if step.get('format') == 'gif-start':
        gif_start = step
    elif step.get('format') == 'gif-end' and gif_start:
        start_ms = gif_start['timestamp_ms']
        end_ms = step['timestamp_ms']
        name = gif_start['name']
        print(f'{start_ms} {end_ms} {name}')
        gif_start = None
" | while IFS=' ' read -r start_ms end_ms gif_name; do
    start_s=$(python3 -c "print(f'{$start_ms / 1000.0:.2f}')")
    duration_s=$(python3 -c "print(f'{($end_ms - $start_ms) / 1000.0:.2f}')")
    gif_file="$tutorial_dir/${gif_name}.gif"

    # Extract clip and convert to GIF with palette for quality
    ffmpeg -y -ss "$start_s" -t "$duration_s" -i "$mp4_file" \
      -vf "fps=10,scale=640:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" \
      "$gif_file" 2>/dev/null

    echo "  Extracted GIF: ${gif_name}.gif (${duration_s}s)"
  done

done

echo "Video processing complete."
```

- [ ] **Step 2: Make executable and test**

Run: `chmod +x scripts/docs-pipeline/video-process.sh`

Run: `bash scripts/docs-pipeline/video-process.sh`
Expected: For tutorials with video recordings, produces `.mp4` with overlays and `.gif` clips.

Note: Playwright video output location depends on config. The script searches both the `.captures/` dir and `test-results/`. If videos aren't found, that's OK — the pipeline is idempotent and skips missing videos.

- [ ] **Step 3: Commit**

```bash
git add scripts/docs-pipeline/video-process.sh
git commit -m "feat: add FFmpeg video processing pipeline (MP4 + GIF extraction)"
```

---

## Task 12: Build the Post-Processing Pipeline — Assemble

**Files:**
- Create: `scripts/docs-pipeline/assemble.py`
- Create: `scripts/docs-pipeline/templates/tutorial.md.j2`
- Create: `scripts/docs-pipeline/templates/index.md.j2`

- [ ] **Step 1: Create the tutorial page Jinja2 template**

Create `scripts/docs-pipeline/templates/tutorial.md.j2`:

```jinja2
---
layout: default
title: "Tutorial {{ tutorial.number }}: {{ tutorial.title }}"
---

# Tutorial {{ tutorial.number }}: {{ tutorial.title }}

{{ tutorial.description }}

| Difficulty | Time | States |
|-----------|------|--------|
| {{ tutorial.difficulty }} | ~{{ tutorial.time_estimate }} | {{ tutorial.state_count }} |

---

{% for step in steps %}
## Step {{ step.step }}: {{ step.title }}

{{ step.description }}

{% if step.gif %}
![{{ step.title }}](assets/{{ tutorial.dir }}/{{ step.gif }})
{% elif step.screenshot %}
![{{ step.title }}](assets/{{ tutorial.dir }}/{{ step.screenshot }})
{% endif %}

{% endfor %}

---

{% if video_file %}
## Full Walkthrough Video

Prefer to watch? Here's the complete tutorial as a video:

<video controls width="100%">
  <source src="assets/{{ tutorial.dir }}/full-walkthrough.mp4" type="video/mp4">
</video>
{% endif %}

---

<div style="display: flex; justify-content: space-between;">
{% if prev_tutorial %}
  <a href="{{ prev_tutorial.filename }}">&larr; Tutorial {{ prev_tutorial.number }}: {{ prev_tutorial.title }}</a>
{% else %}
  <span></span>
{% endif %}
{% if next_tutorial %}
  <a href="{{ next_tutorial.filename }}">Tutorial {{ next_tutorial.number }}: {{ next_tutorial.title }} &rarr;</a>
{% else %}
  <span></span>
{% endif %}
</div>
```

- [ ] **Step 2: Create the index page template**

Create `scripts/docs-pipeline/templates/index.md.j2`:

```jinja2
---
layout: default
title: RSF Tutorials
---

# RSF Tutorials

Learn to build AWS Lambda Durable Function workflows using the RSF graph editor. Each tutorial builds a complete workflow from scratch.

| # | Tutorial | Difficulty | Time | What You'll Learn |
|---|----------|-----------|------|-------------------|
{% for t in tutorials %}
| {{ t.number }} | [{{ t.title }}]({{ t.filename }}) | {{ t.difficulty }} | ~{{ t.time_estimate }} | {{ t.summary }} |
{% endfor %}

---

Start with [Tutorial 1: Hello Workflow](01-hello-workflow.md) to learn the basics, then work your way through increasingly complex workflows.
```

- [ ] **Step 3: Create assemble.py**

Create `scripts/docs-pipeline/assemble.py`:

```python
#!/usr/bin/env python3
"""Assemble tutorial markdown pages from capture manifests and annotated assets."""

import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CAPTURES_DIR = REPO_ROOT / "tests" / "ui-tutorials" / ".captures"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
OUTPUT_DIR = REPO_ROOT / "docs" / "tutorials"

# Tutorial metadata (not derivable from manifests alone)
TUTORIALS = [
    {
        "number": 1,
        "dir": "tutorial-01",
        "title": "Hello Workflow",
        "description": "Build a simple three-state workflow from scratch using the graph editor.",
        "summary": "Add states, connect edges, edit properties",
        "difficulty": "Beginner",
        "time_estimate": "5 min",
        "state_count": 3,
        "filename": "01-hello-workflow.md",
    },
    {
        "number": 2,
        "dir": "tutorial-02",
        "title": "Branching Logic",
        "description": "Build a workflow with conditional branching using a Choice state.",
        "summary": "Choice rules, multiple branches, default paths",
        "difficulty": "Beginner",
        "time_estimate": "8 min",
        "state_count": 5,
        "filename": "02-branching-logic.md",
    },
    {
        "number": 3,
        "dir": "tutorial-03",
        "title": "Wait & Retry",
        "description": "Build a resilient workflow with retry policies, catch blocks, and wait states.",
        "summary": "Retry/Catch, Wait states, error handling",
        "difficulty": "Intermediate",
        "time_estimate": "10 min",
        "state_count": 5,
        "filename": "03-wait-and-retry.md",
    },
    {
        "number": 4,
        "dir": "tutorial-04",
        "title": "Parallel Processing",
        "description": "Build a workflow with concurrent execution branches using a Parallel state.",
        "summary": "Parallel branches, concurrent execution",
        "difficulty": "Intermediate",
        "time_estimate": "10 min",
        "state_count": 4,
        "filename": "04-parallel-processing.md",
    },
    {
        "number": 5,
        "dir": "tutorial-05",
        "title": "Order Processing",
        "description": "Build the complete order-processing example — a production-ready workflow with all state types.",
        "summary": "All state types, full production workflow",
        "difficulty": "Advanced",
        "time_estimate": "15 min",
        "state_count": 7,
        "filename": "05-order-processing.md",
    },
]


def main() -> None:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    tutorial_tmpl = env.get_template("tutorial.md.j2")
    index_tmpl = env.get_template("index.md.j2")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    assets_dir = OUTPUT_DIR / "assets"
    assets_dir.mkdir(exist_ok=True)

    for i, tutorial in enumerate(TUTORIALS):
        tutorial_captures = CAPTURES_DIR / tutorial["dir"]
        manifest_path = tutorial_captures / "manifest.json"

        if not manifest_path.exists():
            print(f"Warning: No manifest for {tutorial['dir']}, skipping")
            continue

        with open(manifest_path) as f:
            manifest = json.load(f)

        # Copy annotated assets (prefer annotated/ over raw)
        tutorial_assets_dir = assets_dir / tutorial["dir"]
        tutorial_assets_dir.mkdir(exist_ok=True)

        annotated_dir = tutorial_captures / "annotated"
        source_dir = annotated_dir if annotated_dir.exists() else tutorial_captures

        for step in manifest["steps"]:
            src = source_dir / step["screenshot"]
            if src.exists():
                shutil.copy2(src, tutorial_assets_dir / step["screenshot"])

        # Copy GIF files if they exist
        for gif in tutorial_captures.glob("*.gif"):
            shutil.copy2(gif, tutorial_assets_dir / gif.name)

        # Copy video if it exists
        video_file = tutorial_captures / "full-walkthrough.mp4"
        has_video = video_file.exists()
        if has_video:
            shutil.copy2(video_file, tutorial_assets_dir / "full-walkthrough.mp4")

        # Map gif-start steps to their GIF filenames
        steps_with_gifs = []
        for step in manifest["steps"]:
            step_data = dict(step)
            if step.get("format") == "gif-start":
                gif_path = tutorial_captures / f"{step['name']}.gif"
                if gif_path.exists():
                    step_data["gif"] = f"{step['name']}.gif"
            # Use annotated screenshot
            step_data["screenshot"] = step["screenshot"]
            steps_with_gifs.append(step_data)

        # Render tutorial page
        prev_tutorial = TUTORIALS[i - 1] if i > 0 else None
        next_tutorial = TUTORIALS[i + 1] if i + 1 < len(TUTORIALS) else None

        rendered = tutorial_tmpl.render(
            tutorial=tutorial,
            steps=steps_with_gifs,
            video_file="full-walkthrough.mp4" if has_video else None,
            prev_tutorial=prev_tutorial,
            next_tutorial=next_tutorial,
        )

        output_path = OUTPUT_DIR / tutorial["filename"]
        output_path.write_text(rendered)
        print(f"Generated: {tutorial['filename']}")

    # Render index page
    index_rendered = index_tmpl.render(tutorials=TUTORIALS)
    (OUTPUT_DIR / "index.md").write_text(index_rendered)
    print("Generated: index.md")

    print(f"\nAll tutorials assembled in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Test the assembly pipeline end-to-end**

Run the full pipeline on Tutorial 1 captures:

```bash
cd tests/ui-tutorials && npx playwright test tutorial-01
cd ../..
bash scripts/docs-pipeline/annotate.sh
bash scripts/docs-pipeline/video-process.sh
python3 scripts/docs-pipeline/assemble.py
```

Expected: `docs/tutorials/01-hello-workflow.md` generated with step sections and image references. `docs/tutorials/assets/tutorial-01/` contains annotated PNGs.

Run: `cat docs/tutorials/01-hello-workflow.md`
Expected: Markdown with step headings, image links, navigation links.

- [ ] **Step 5: Commit**

```bash
git add scripts/docs-pipeline/assemble.py scripts/docs-pipeline/templates/tutorial.md.j2 scripts/docs-pipeline/templates/index.md.j2
git commit -m "feat: add markdown assembly pipeline for tutorial documentation"
```

---

## Task 13: GitHub Pages Configuration

**Files:**
- Create: `docs/tutorials/_config.yml`
- Modify: `.gitignore`

- [ ] **Step 1: Create Jekyll config for GitHub Pages**

Create `docs/tutorials/_config.yml`:

```yaml
title: RSF Tutorials
description: Learn to build AWS Lambda Durable Function workflows with RSF
baseurl: /rsf-python/tutorials
theme: minima
```

- [ ] **Step 2: Update .gitignore**

Add to the project root `.gitignore`:

```
# Tutorial test captures (raw + annotated, regenerated by CI)
tests/ui-tutorials/.captures/
tests/ui-tutorials/test-results/
tests/ui-tutorials/playwright-report/
tests/ui-tutorials/node_modules/

# Generated tutorial assets (regenerated by CI)
docs/tutorials/assets/
```

- [ ] **Step 3: Commit**

```bash
git add docs/tutorials/_config.yml .gitignore
git commit -m "feat: add GitHub Pages config and update .gitignore for tutorial pipeline"
```

---

## Task 14: GitHub Actions CI Workflow

**Files:**
- Create: `.github/workflows/tutorials.yml`

- [ ] **Step 1: Create the CI workflow**

Create `.github/workflows/tutorials.yml`:

```yaml
name: Tutorial Tests & Docs

on:
  push:
    paths:
      - 'ui/src/**'
      - 'tests/ui-tutorials/**'
      - 'scripts/docs-pipeline/**'
      - '.github/workflows/tutorials.yml'
  workflow_dispatch:

permissions:
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '22'

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install Python package
        run: pip install -e .

      - name: Install Playwright dependencies
        working-directory: tests/ui-tutorials
        run: |
          npm ci
          npx playwright install --with-deps chromium

      - name: Build UI
        working-directory: ui
        run: |
          npm ci
          npm run build

      - name: Run tutorial tests
        working-directory: tests/ui-tutorials
        run: npx playwright test

      - name: Install ImageMagick and FFmpeg
        run: sudo apt-get install -y imagemagick ffmpeg

      - name: Annotate screenshots
        run: bash scripts/docs-pipeline/annotate.sh

      - name: Process videos
        run: bash scripts/docs-pipeline/video-process.sh

      - name: Assemble tutorial pages
        run: python3 scripts/docs-pipeline/assemble.py

      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: docs/tutorials

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/tutorials.yml
git commit -m "feat: add GitHub Actions workflow for tutorial tests and Pages deployment"
```

---

## Task 15: Run Full Pipeline End-to-End

**Files:** None (validation only)

This task validates the complete pipeline works locally before merging.

- [ ] **Step 1: Run all tutorial tests**

Run: `cd tests/ui-tutorials && npx playwright test`
Expected: All 6 specs pass (smoke + 5 tutorials). Video recordings in `test-results/`.

- [ ] **Step 2: Run full post-processing pipeline**

```bash
bash scripts/docs-pipeline/annotate.sh
bash scripts/docs-pipeline/video-process.sh
python3 scripts/docs-pipeline/assemble.py
```

Expected: `docs/tutorials/` populated with 6 markdown files + `assets/` directory with annotated PNGs, GIFs, and MP4s.

- [ ] **Step 3: Verify generated markdown**

Run: `ls docs/tutorials/`
Expected: `_config.yml`, `index.md`, `01-hello-workflow.md` through `05-order-processing.md`, `assets/`

Run: `ls docs/tutorials/assets/tutorial-01/`
Expected: Annotated PNGs matching manifest steps.

- [ ] **Step 4: Preview locally (optional)**

Run: `cd docs/tutorials && python3 -m http.server 8080`
Open `http://localhost:8080` to verify the tutorial pages render correctly.

- [ ] **Step 5: Clean up smoke test**

Delete `tests/ui-tutorials/tutorial-00-smoke.spec.ts` — it was scaffolding for fixture development and isn't a real tutorial.

```bash
rm tests/ui-tutorials/tutorial-00-smoke.spec.ts
git add -A tests/ui-tutorials/tutorial-00-smoke.spec.ts
git commit -m "chore: remove smoke test scaffold"
```
