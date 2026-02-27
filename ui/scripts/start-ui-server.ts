/**
 * Start UI server — lifecycle management for the RSF graph editor (rsf ui).
 *
 * Spawns the Python-based graph editor server for a given example workflow,
 * health-checks until ready, then keeps the process alive until SIGINT/SIGTERM.
 *
 * Usage:
 *   node --import tsx/esm scripts/start-ui-server.ts --example order-processing --port 8765
 *
 * Output signals (consumed by downstream scripts):
 *   SERVER_READY: http://127.0.0.1:{port}
 *   SERVER_STOPPED
 */

import { spawn, execFileSync, type ChildProcess } from 'node:child_process';
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
  let port = 8765;

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
// Resolve and verify workflow path
// ---------------------------------------------------------------------------

// Repo root is one level up from ui/
const repoRoot = resolve(__dirname, '..', '..');
const workflowPath = resolve(repoRoot, 'examples', example, 'workflow.yaml');

if (!existsSync(workflowPath)) {
  console.error(`Error: Workflow file not found: ${workflowPath}`);
  console.error(`Check that example "${example}" exists in examples/ directory`);
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Resolve rsf CLI executable
// ---------------------------------------------------------------------------

/**
 * Find a working way to run `rsf ui`.
 * Priority: .venv/bin/rsf (project venv entry point), then rsf from PATH.
 * Returns { command, args } for spawn().
 */
function findRsfCommand(): { command: string; args: string[] } {
  // Check for venv rsf binary (most reliable — includes correct Python + module)
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

  // Fall back to python -m rsf.cli.main (direct module path)
  const venvPython = resolve(repoRoot, '.venv', 'bin', 'python');
  if (existsSync(venvPython)) {
    return { command: venvPython, args: ['-c', 'from rsf.cli.main import app; app()', 'ui', workflowPath, '--port', String(port), '--no-browser'] };
  }

  console.error('Error: No rsf CLI found. Ensure the project venv exists with rsf installed.');
  process.exit(1);
}

const rsfCmd = findRsfCommand();

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

function startServer(): void {
  child = spawn(rsfCmd.command, rsfCmd.args, {
    stdio: ['ignore', 'pipe', 'pipe'],
    cwd: repoRoot,
  });

  child.stdout?.on('data', (data: Buffer) => {
    const lines = data.toString().trimEnd().split('\n');
    for (const line of lines) {
      console.log(`[rsf-ui] ${line}`);
    }
  });

  child.stderr?.on('data', (data: Buffer) => {
    const lines = data.toString().trimEnd().split('\n');
    for (const line of lines) {
      console.error(`[rsf-ui] ${line}`);
    }
  });

  child.on('error', (err) => {
    console.error(`Error: Failed to spawn rsf ui process: ${err.message}`);
    process.exit(1);
  });

  child.on('exit', (code, signal) => {
    if (!shuttingDown) {
      console.error(`Error: rsf ui process exited unexpectedly (code=${code}, signal=${signal})`);
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
  console.log(`Starting rsf ui for example "${example}" on port ${port}...`);
  console.log(`Workflow: ${workflowPath}`);

  startServer();

  const url = `http://127.0.0.1:${port}/`;
  const ready = await waitForReady(url, 30, 500);

  if (!ready) {
    console.error(`Error: Health check timed out after 15 seconds — server not responding at ${url}`);
    if (child && !child.killed) {
      child.kill('SIGTERM');
    }
    process.exit(1);
  }

  console.log(`SERVER_READY: http://127.0.0.1:${port}`);
}

main();
