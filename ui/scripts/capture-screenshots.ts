/**
 * Capture screenshots — Playwright-based screenshot orchestration for all
 * example workflows.
 *
 * Captures 15 screenshots (3 per example x 5 examples):
 *   - {example}-graph.png  — Graph editor full-layout (graph only, no editor pane)
 *   - {example}-dsl.png    — Graph editor with YAML editor + graph side by side
 *   - {example}-inspector.png — Execution inspector with timeline and state data
 *
 * Usage:
 *   node --import tsx/esm scripts/capture-screenshots.ts
 *   npm run screenshots  (from ui/)
 *
 * Requires:
 *   - rsf CLI (venv or PATH) with websockets pip package installed
 *   - Playwright browsers installed (npx playwright install chromium)
 *   - Example workflows in examples/
 *   - Mock fixture data in scripts/fixtures/
 */

import { chromium } from '@playwright/test';
import { spawn, execSync, execFileSync, type ChildProcess } from 'node:child_process';
import { existsSync, mkdirSync, statSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const EXAMPLES = [
  'order-processing',
  'approval-workflow',
  'data-pipeline',
  'retry-and-recovery',
  'intrinsic-showcase',
];

const UI_PORT = 8765;
const INSPECT_PORT = 8766;
const VITE_PORT = 5199;
const VIEWPORT = { width: 1440, height: 900 };

const repoRoot = resolve(__dirname, '..', '..');
const uiDir = resolve(repoRoot, 'ui');
const docsImagesDir = resolve(repoRoot, 'docs', 'images');
const mockServerScript = resolve(__dirname, 'mock-inspect-server.ts');

// ---------------------------------------------------------------------------
// Active process tracking for cleanup
// ---------------------------------------------------------------------------

const activeChildren = new Set<ChildProcess>();

function registerChild(child: ChildProcess): void {
  activeChildren.add(child);
  child.on('exit', () => activeChildren.delete(child));
}

function killAll(): void {
  for (const child of activeChildren) {
    if (child.pid) {
      // Kill entire process group to handle npx wrapper processes
      try {
        process.kill(-child.pid, 'SIGKILL');
      } catch {
        try { child.kill('SIGKILL'); } catch { /* Already dead */ }
      }
    }
  }
  activeChildren.clear();
}

process.on('SIGINT', () => {
  killAll();
  process.exit(1);
});
process.on('SIGTERM', () => {
  killAll();
  process.exit(1);
});
process.on('exit', () => {
  killAll();
});

// ---------------------------------------------------------------------------
// Find rsf CLI executable
// ---------------------------------------------------------------------------

function findRsfCommand(workflowPath: string, port: number): { command: string; args: string[] } {
  // Check for venv rsf binary (most reliable)
  const venvRsf = resolve(repoRoot, '.venv', 'bin', 'rsf');
  if (existsSync(venvRsf)) {
    return { command: venvRsf, args: ['ui', workflowPath, '--port', String(port), '--no-browser'] };
  }

  // Try rsf from PATH
  try {
    execFileSync('rsf', ['--version'], { stdio: 'ignore' });
    return { command: 'rsf', args: ['ui', workflowPath, '--port', String(port), '--no-browser'] };
  } catch {
    // Not available
  }

  // Fall back to python -c (direct module path)
  const venvPython = resolve(repoRoot, '.venv', 'bin', 'python');
  if (existsSync(venvPython)) {
    return {
      command: venvPython,
      args: ['-c', 'from rsf.cli.main import app; app()', 'ui', workflowPath, '--port', String(port), '--no-browser'],
    };
  }

  console.error('Error: No rsf CLI found. Ensure the project venv exists with rsf installed.');
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Health check polling
// ---------------------------------------------------------------------------

async function waitForReady(url: string, maxRetries: number, intervalMs: number): Promise<boolean> {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return true;
      }
    } catch {
      // Server not ready yet
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return false;
}

/**
 * Wait until a port is free (no process listening).
 */
async function waitForPortFree(port: number, maxRetries = 10, intervalMs = 300): Promise<void> {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const result = execSync(`lsof -i :${port} -t 2>/dev/null || true`, { encoding: 'utf8' }).trim();
      if (!result) return; // Port is free
    } catch {
      return; // lsof failed = port is free
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

// ---------------------------------------------------------------------------
// Process lifecycle helpers
// ---------------------------------------------------------------------------

function startProcess(command: string, args: string[], cwd: string, label: string): ChildProcess {
  const child = spawn(command, args, {
    stdio: ['ignore', 'pipe', 'pipe'],
    cwd,
    detached: true, // Create process group for clean tree kill
  });

  child.stdout?.on('data', (data: Buffer) => {
    const lines = data.toString().trimEnd().split('\n');
    for (const line of lines) {
      console.log(`  [${label}] ${line}`);
    }
  });

  child.stderr?.on('data', (data: Buffer) => {
    const lines = data.toString().trimEnd().split('\n');
    for (const line of lines) {
      console.error(`  [${label}] ${line}`);
    }
  });

  child.on('error', (err) => {
    console.error(`  [${label}] Spawn error: ${err.message}`);
  });

  // Unref so the child doesn't prevent node from exiting
  child.unref();
  registerChild(child);
  return child;
}

async function stopProcess(child: ChildProcess, label: string): Promise<void> {
  if (child.exitCode !== null) return;

  return new Promise<void>((resolvePromise) => {
    const timer = setTimeout(() => {
      // Force kill the entire process group
      if (child.pid) {
        try {
          process.kill(-child.pid, 'SIGKILL');
        } catch {
          try { child.kill('SIGKILL'); } catch { /* Already dead */ }
        }
      }
      console.log(`  [${label}] Force killed (SIGKILL)`);
      resolvePromise();
    }, 3000);

    child.on('exit', () => {
      clearTimeout(timer);
      resolvePromise();
    });

    // Send SIGTERM to the process group
    if (child.pid) {
      try {
        process.kill(-child.pid, 'SIGTERM');
      } catch {
        try { child.kill('SIGTERM'); } catch {
          clearTimeout(timer);
          resolvePromise();
        }
      }
    }
  });
}

// ---------------------------------------------------------------------------
// Main capture logic
// ---------------------------------------------------------------------------

async function captureGraphScreenshots(
  example: string,
  page: import('@playwright/test').Page,
): Promise<{ graph: boolean; dsl: boolean }> {
  const workflowPath = resolve(repoRoot, 'examples', example, 'workflow.yaml');
  if (!existsSync(workflowPath)) {
    console.error(`  Workflow not found: ${workflowPath}`);
    return { graph: false, dsl: false };
  }

  // Ensure port is free before starting
  await waitForPortFree(UI_PORT);

  const rsfCmd = findRsfCommand(workflowPath, UI_PORT);
  const rsfChild = startProcess(rsfCmd.command, rsfCmd.args, repoRoot, 'rsf-ui');

  try {
    // Wait for rsf ui server to be ready
    const ready = await waitForReady(`http://127.0.0.1:${UI_PORT}/`, 30, 500);
    if (!ready) {
      console.error(`  rsf ui server did not become ready for ${example}`);
      return { graph: false, dsl: false };
    }

    // Navigate to graph editor
    await page.goto(`http://127.0.0.1:${UI_PORT}/`, { waitUntil: 'networkidle' });

    // Wait for graph to render — the WebSocket sends file_loaded which triggers
    // YAML parsing and graph rendering via ReactFlow
    await page.waitForSelector('.react-flow', { state: 'visible', timeout: 15000 });
    await page.waitForSelector('.react-flow__node', { state: 'visible', timeout: 15000 });

    // Wait for ELK layout to stabilize
    await page.waitForTimeout(2000);

    // --- DSL screenshot (full layout: palette + editor + graph) ---
    const dslPath = resolve(docsImagesDir, `${example}-dsl.png`);
    await page.screenshot({ path: dslPath, fullPage: false });
    console.log(`  Saved: ${example}-dsl.png`);

    // --- Graph-focused screenshot (hide editor pane and palette) ---
    await page.evaluate(() => {
      // Hide the editor pane
      const editorPane = document.querySelector('.editor-pane') as HTMLElement;
      if (editorPane) editorPane.style.display = 'none';
      // Hide the palette
      const palette = document.querySelector('.palette') as HTMLElement;
      if (palette) palette.style.display = 'none';
      // Hide the inspector/details panel
      const inspector = document.querySelector('.inspector-panel') as HTMLElement;
      if (inspector) inspector.style.display = 'none';
    });

    // Wait for layout reflow and ReactFlow to resize
    await page.waitForTimeout(1000);

    const graphPath = resolve(docsImagesDir, `${example}-graph.png`);
    await page.screenshot({ path: graphPath, fullPage: false });
    console.log(`  Saved: ${example}-graph.png`);

    return { graph: true, dsl: true };
  } finally {
    await stopProcess(rsfChild, 'rsf-ui');
    // Wait for port to be released
    await waitForPortFree(UI_PORT);
  }
}

async function captureInspectorScreenshot(
  example: string,
  page: import('@playwright/test').Page,
): Promise<boolean> {
  // Ensure ports are free
  await waitForPortFree(INSPECT_PORT);
  await waitForPortFree(VITE_PORT);

  // Start mock inspect server
  const inspectChild = startProcess(
    'node',
    ['--import', 'tsx/esm', mockServerScript, '--fixture', example, '--port', String(INSPECT_PORT)],
    uiDir,
    'mock-inspect',
  );

  let viteChild: ChildProcess | null = null;

  try {
    // Wait for mock inspect server
    const inspectReady = await waitForReady(
      `http://127.0.0.1:${INSPECT_PORT}/api/inspect/executions`,
      20,
      500,
    );
    if (!inspectReady) {
      console.error(`  Mock inspect server did not become ready for ${example}`);
      return false;
    }

    // Start Vite dev server
    viteChild = startProcess(
      'npx',
      ['vite', '--port', String(VITE_PORT), '--strictPort'],
      uiDir,
      'vite',
    );

    // Wait for Vite to be ready
    const viteReady = await waitForReady(`http://127.0.0.1:${VITE_PORT}/`, 40, 500);
    if (!viteReady) {
      console.error(`  Vite dev server did not become ready for ${example}`);
      return false;
    }

    // Navigate to inspector
    await page.goto(`http://127.0.0.1:${VITE_PORT}/#/inspector`, { waitUntil: 'networkidle' });

    // Wait for execution list to load
    await page.waitForSelector('.execution-list-item', { state: 'visible', timeout: 15000 });

    // Click the first execution to trigger SSE streaming
    await page.click('.execution-list-item');

    // Wait for inspector graph to populate
    // The InspectorGraph renders inside .inspector-center
    try {
      await page.waitForSelector('.inspector-center .react-flow__node', { state: 'visible', timeout: 15000 });
    } catch {
      // The inspector graph may not have nodes in all cases — fall back to just waiting for the react-flow container
      console.log(`  Warning: Inspector graph nodes not visible for ${example}, checking for react-flow container...`);
      await page.waitForSelector('.inspector-center .react-flow', { state: 'visible', timeout: 5000 });
    }

    // Wait for timeline events
    try {
      await page.waitForSelector('.timeline-event', { state: 'visible', timeout: 10000 });
    } catch {
      // Timeline events may not always render — continue anyway
      console.log(`  Warning: Timeline events not visible for ${example}, capturing anyway`);
    }

    // Wait for graph layout and SSE to complete
    await page.waitForTimeout(2000);

    // Capture inspector screenshot
    const inspectorPath = resolve(docsImagesDir, `${example}-inspector.png`);
    await page.screenshot({ path: inspectorPath, fullPage: false });
    console.log(`  Saved: ${example}-inspector.png`);

    return true;
  } finally {
    if (viteChild) {
      await stopProcess(viteChild, 'vite');
      await waitForPortFree(VITE_PORT);
    }
    await stopProcess(inspectChild, 'mock-inspect');
    await waitForPortFree(INSPECT_PORT);
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  console.log('Screenshot capture starting...');
  console.log(`Output directory: ${docsImagesDir}`);
  console.log(`Examples: ${EXAMPLES.join(', ')}`);
  console.log('');

  // Ensure output directory exists
  mkdirSync(docsImagesDir, { recursive: true });

  // Launch browser once
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: VIEWPORT });
  const page = await context.newPage();

  let successCount = 0;
  let failCount = 0;
  const totalScreenshots = EXAMPLES.length * 3;

  for (let i = 0; i < EXAMPLES.length; i++) {
    const example = EXAMPLES[i];
    console.log(`Capturing screenshots for ${example} (${i + 1}/${EXAMPLES.length})...`);

    // Graph editor screenshots (graph + DSL)
    try {
      const graphResult = await captureGraphScreenshots(example, page);
      if (graphResult.graph) successCount++;
      else failCount++;
      if (graphResult.dsl) successCount++;
      else failCount++;
    } catch (err) {
      console.error(`  Error capturing graph screenshots for ${example}: ${err}`);
      failCount += 2;
    }

    // Inspector screenshot
    try {
      const inspectorResult = await captureInspectorScreenshot(example, page);
      if (inspectorResult) successCount++;
      else failCount++;
    } catch (err) {
      console.error(`  Error capturing inspector screenshot for ${example}: ${err}`);
      failCount++;
    }

    console.log('');
  }

  await browser.close();

  // Summary
  console.log('---');
  console.log(`Captured ${successCount}/${totalScreenshots} screenshots. Output: docs/images/`);

  if (failCount > 0) {
    console.error(`${failCount} screenshot(s) failed.`);
    process.exit(1);
  }

  // Verify all files are non-trivial (> 10KB)
  let allValid = true;
  for (const example of EXAMPLES) {
    for (const suffix of ['graph', 'dsl', 'inspector']) {
      const filePath = resolve(docsImagesDir, `${example}-${suffix}.png`);
      if (!existsSync(filePath)) {
        console.error(`Missing: ${example}-${suffix}.png`);
        allValid = false;
        continue;
      }
      const size = statSync(filePath).size;
      if (size < 10240) {
        console.error(`Too small (${size} bytes): ${example}-${suffix}.png — may be blank`);
        allValid = false;
      }
    }
  }

  if (!allValid) {
    console.error('Some screenshots are missing or too small.');
    process.exit(1);
  }

  console.log('All screenshots validated successfully.');
}

main().catch((err) => {
  console.error('Screenshot capture FAILED:', err);
  killAll();
  process.exit(1);
});
