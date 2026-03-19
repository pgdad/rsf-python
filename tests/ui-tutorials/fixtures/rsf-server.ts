/**
 * rsf-server fixture — Playwright fixture that manages a fresh rsf project
 * and running rsf ui server for each test.
 *
 * For each test:
 *   1. Creates a temp directory with `rsf init <project>`
 *   2. Starts `rsf ui workflow.yaml --port <port> --no-browser`
 *   3. Waits for server readiness via GET /api/schema
 *   4. Navigates the page to the editor and waits for ReactFlow to render
 *   5. Teardown: kills server process group, removes temp directory
 *
 * Exports `test` and `expect` for use by spec files.
 */

import { test as base, expect } from '@playwright/test';
import { spawn, execFileSync, type ChildProcess } from 'node:child_process';
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { tmpdir } from 'node:os';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const REPO_ROOT = resolve(import.meta.dirname, '..', '..', '..');
const BASE_PORT = 18765;
let portCounter = 0;

function nextPort(): number {
  return BASE_PORT + portCounter++;
}

// ---------------------------------------------------------------------------
// Find rsf CLI executable (adapted from ui/scripts/capture-screenshots.ts)
// ---------------------------------------------------------------------------

function findRsfCommand(): string {
  // Check for venv rsf binary (most reliable)
  const venvRsf = resolve(REPO_ROOT, '.venv', 'bin', 'rsf');
  if (existsSync(venvRsf)) {
    return venvRsf;
  }

  // Try rsf from PATH
  try {
    execFileSync('rsf', ['--version'], { stdio: 'ignore' });
    return 'rsf';
  } catch {
    // Not available
  }

  throw new Error(
    'No rsf CLI found. Ensure the project venv exists with rsf installed, ' +
      `or rsf is on PATH. Checked: ${venvRsf}`,
  );
}

// ---------------------------------------------------------------------------
// Health check polling (adapted from ui/scripts/capture-screenshots.ts)
// ---------------------------------------------------------------------------

async function waitForReady(
  url: string,
  maxRetries: number,
  intervalMs: number,
): Promise<boolean> {
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

// ---------------------------------------------------------------------------
// Fixture type
// ---------------------------------------------------------------------------

type RsfServerFixtures = {
  rsfPort: number;
  rsfProjectDir: string;
};

// ---------------------------------------------------------------------------
// Fixture implementation
// ---------------------------------------------------------------------------

export const test = base.extend<RsfServerFixtures>({
  // Provide the port allocated for this test
  rsfPort: async ({}, use) => {
    const port = nextPort();
    await use(port);
  },

  // Provide the temp project directory
  rsfProjectDir: async ({}, use) => {
    const dir = mkdtempSync(join(tmpdir(), 'rsf-test-'));
    await use(dir);
    // Cleanup
    rmSync(dir, { recursive: true, force: true });
  },

  // Override page to set up the rsf server and navigate before the test runs
  page: async ({ page, rsfPort, rsfProjectDir }, use) => {
    const rsfBin = findRsfCommand();
    const projectName = 'smoke-project';

    // 1. rsf init in the temp directory
    execFileSync(rsfBin, ['init', projectName], {
      cwd: rsfProjectDir,
      stdio: 'pipe',
      timeout: 30_000,
    });

    const projectDir = resolve(rsfProjectDir, projectName);
    const workflowPath = resolve(projectDir, 'workflow.yaml');

    if (!existsSync(workflowPath)) {
      throw new Error(`rsf init did not create workflow.yaml at ${workflowPath}`);
    }

    // 2. Start rsf ui server
    const child: ChildProcess = spawn(
      rsfBin,
      ['ui', workflowPath, '--port', String(rsfPort), '--no-browser'],
      {
        stdio: ['ignore', 'pipe', 'pipe'],
        cwd: projectDir,
        detached: true, // Create process group for clean tree kill
      },
    );

    // Log server output for debugging
    child.stdout?.on('data', (data: Buffer) => {
      const lines = data.toString().trimEnd().split('\n');
      for (const line of lines) {
        // eslint-disable-next-line no-console
        console.log(`  [rsf-ui:${rsfPort}] ${line}`);
      }
    });

    child.stderr?.on('data', (data: Buffer) => {
      const lines = data.toString().trimEnd().split('\n');
      for (const line of lines) {
        // eslint-disable-next-line no-console
        console.error(`  [rsf-ui:${rsfPort}] ${line}`);
      }
    });

    child.unref();

    try {
      // 3. Wait for server readiness via /api/schema
      const ready = await waitForReady(
        `http://127.0.0.1:${rsfPort}/api/schema`,
        40, // up to 20 seconds
        500,
      );
      if (!ready) {
        throw new Error(
          `rsf ui server did not become ready on port ${rsfPort} within 20s`,
        );
      }

      // 4. Navigate to the editor
      await page.goto(`http://127.0.0.1:${rsfPort}/`, { waitUntil: 'networkidle' });

      // Wait for ReactFlow to render
      await page.waitForSelector('.react-flow', { state: 'visible', timeout: 15_000 });
      await page.waitForSelector('.react-flow__node', { state: 'visible', timeout: 15_000 });

      // 5. Wait for ELK layout to stabilize
      await page.waitForTimeout(1500);

      // Hand the page to the test
      await use(page);
    } finally {
      // 6. Teardown: kill server process group
      if (child.pid) {
        try {
          process.kill(-child.pid, 'SIGTERM');
        } catch {
          // Process may already be dead
          try {
            child.kill('SIGTERM');
          } catch {
            /* Already dead */
          }
        }

        // Give it a moment, then force kill if needed
        await new Promise((r) => setTimeout(r, 1000));

        if (child.exitCode === null) {
          try {
            process.kill(-child.pid, 'SIGKILL');
          } catch {
            try {
              child.kill('SIGKILL');
            } catch {
              /* Already dead */
            }
          }
        }
      }
    }
  },
});

export { expect };
