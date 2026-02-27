/**
 * Start inspect server — lifecycle management for the mock inspect server.
 *
 * Spawns the mock inspect server (mock-inspect-server.ts) with fixture data
 * for a given example, health-checks until ready, then keeps the process alive
 * until SIGINT/SIGTERM.
 *
 * Usage:
 *   node --import tsx/esm scripts/start-inspect-server.ts --example order-processing --port 8766
 *
 * Output signals (consumed by downstream scripts):
 *   SERVER_READY: http://127.0.0.1:{port}
 *   SERVER_STOPPED
 */

import { spawn, type ChildProcess } from 'node:child_process';
import { existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// ---------------------------------------------------------------------------
// CLI argument parsing
// ---------------------------------------------------------------------------

function parseArgs(argv: string[]): { example: string; port: number } {
  let example = '';
  let port = 8766;

  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--example' && argv[i + 1]) {
      example = argv[i + 1];
      i++;
    }
    if (argv[i] === '--port' && argv[i + 1]) {
      port = parseInt(argv[i + 1], 10);
      i++;
    }
  }

  if (!example) {
    console.error('Error: --example <name> is required');
    console.error('Valid examples: order-processing, approval-workflow, data-pipeline, retry-and-recovery, intrinsic-showcase');
    process.exit(1);
  }

  return { example, port };
}

const { example, port } = parseArgs(process.argv.slice(2));

// ---------------------------------------------------------------------------
// Verify fixture file exists
// ---------------------------------------------------------------------------

const fixturePath = resolve(__dirname, 'fixtures', `${example}.json`);

if (!existsSync(fixturePath)) {
  console.error(`Error: Fixture file not found: ${fixturePath}`);
  console.error(`Check that fixture for "${example}" exists in scripts/fixtures/ directory`);
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Resolve mock server script path
// ---------------------------------------------------------------------------

const mockServerScript = resolve(__dirname, 'mock-inspect-server.ts');

if (!existsSync(mockServerScript)) {
  console.error(`Error: Mock inspect server script not found: ${mockServerScript}`);
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
      // Server not ready yet — expected during startup
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return false;
}

// ---------------------------------------------------------------------------
// Server lifecycle
// ---------------------------------------------------------------------------

let child: ChildProcess | null = null;
let shuttingDown = false;

// Repo root is one level up from ui/
const repoRoot = resolve(__dirname, '..', '..');

function startServer(): void {
  child = spawn('node', ['--import', 'tsx/esm', mockServerScript, '--fixture', example, '--port', String(port)], {
    stdio: ['ignore', 'pipe', 'pipe'],
    cwd: resolve(repoRoot, 'ui'),
  });

  child.stdout?.on('data', (data: Buffer) => {
    const lines = data.toString().trimEnd().split('\n');
    for (const line of lines) {
      console.log(`[mock-inspect] ${line}`);
    }
  });

  child.stderr?.on('data', (data: Buffer) => {
    const lines = data.toString().trimEnd().split('\n');
    for (const line of lines) {
      console.error(`[mock-inspect] ${line}`);
    }
  });

  child.on('error', (err) => {
    console.error(`Error: Failed to spawn mock inspect server process: ${err.message}`);
    process.exit(1);
  });

  child.on('exit', (code, signal) => {
    if (!shuttingDown) {
      console.error(`Error: Mock inspect server exited unexpectedly (code=${code}, signal=${signal})`);
      process.exit(1);
    }
  });
}

async function shutdown(): Promise<void> {
  if (shuttingDown) return;
  shuttingDown = true;

  if (child && !child.killed) {
    child.kill('SIGTERM');

    // Wait up to 2 seconds for graceful shutdown, then force kill
    await new Promise<void>((r) => {
      const timer = setTimeout(() => {
        if (child && !child.killed) {
          child.kill('SIGKILL');
        }
        r();
      }, 2000);

      child!.on('exit', () => {
        clearTimeout(timer);
        r();
      });
    });
  }

  console.log('SERVER_STOPPED');
  process.exit(0);
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  console.log(`Starting mock inspect server for example "${example}" on port ${port}...`);
  console.log(`Fixture: ${fixturePath}`);

  startServer();

  const url = `http://127.0.0.1:${port}/api/inspect/executions`;
  const ready = await waitForReady(url, 20, 500);

  if (!ready) {
    console.error(`Error: Health check timed out after 10 seconds — server not responding at ${url}`);
    if (child && !child.killed) {
      child.kill('SIGTERM');
    }
    process.exit(1);
  }

  console.log(`SERVER_READY: http://127.0.0.1:${port}`);
}

main();
