/**
 * Mock inspect server — serves fixture JSON files via the same REST and SSE
 * endpoints as the real RSF inspect server.
 *
 * Usage:
 *   node --import tsx/esm scripts/mock-inspect-server.ts --fixture order-processing --port 8766
 *
 * Endpoints:
 *   GET /api/inspect/executions             — execution list
 *   GET /api/inspect/execution/:id          — execution detail with history
 *   GET /api/inspect/execution/:id/history  — history events only
 *   GET /api/inspect/execution/:id/stream   — SSE stream (execution_info + history)
 */

import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// ---------------------------------------------------------------------------
// CLI argument parsing
// ---------------------------------------------------------------------------

function parseArgs(argv: string[]): { fixture: string; port: number } {
  let fixture = 'order-processing';
  let port = 8766;

  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--fixture' && argv[i + 1]) {
      fixture = argv[i + 1];
      i++;
    }
    if (argv[i] === '--port' && argv[i + 1]) {
      port = parseInt(argv[i + 1], 10);
      i++;
    }
  }

  return { fixture, port };
}

const { fixture, port } = parseArgs(process.argv.slice(2));

// ---------------------------------------------------------------------------
// Load fixture data
// ---------------------------------------------------------------------------

const fixturePath = resolve(__dirname, 'fixtures', `${fixture}.json`);
let fixtureData: {
  executions: Record<string, unknown>[];
  execution_detail: Record<string, unknown> & { history: Record<string, unknown>[] };
};

try {
  fixtureData = JSON.parse(readFileSync(fixturePath, 'utf8'));
} catch (err) {
  console.error(`Failed to load fixture: ${fixturePath}`);
  console.error(err);
  process.exit(1);
}

// ---------------------------------------------------------------------------
// CORS + JSON helpers
// ---------------------------------------------------------------------------

function setCors(res: ServerResponse): void {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

function sendJson(res: ServerResponse, data: unknown, statusCode = 200): void {
  setCors(res);
  res.writeHead(statusCode, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(data));
}

function send404(res: ServerResponse): void {
  sendJson(res, { error: 'Not found' }, 404);
}

// ---------------------------------------------------------------------------
// Route matching
// ---------------------------------------------------------------------------

function matchRoute(pathname: string): { route: string; id?: string } | null {
  // GET /api/inspect/executions
  if (pathname === '/api/inspect/executions') {
    return { route: 'list' };
  }

  // GET /api/inspect/execution/:id/stream
  const streamMatch = pathname.match(/^\/api\/inspect\/execution\/([^/]+)\/stream$/);
  if (streamMatch) {
    return { route: 'stream', id: decodeURIComponent(streamMatch[1]) };
  }

  // GET /api/inspect/execution/:id/history
  const historyMatch = pathname.match(/^\/api\/inspect\/execution\/([^/]+)\/history$/);
  if (historyMatch) {
    return { route: 'history', id: decodeURIComponent(historyMatch[1]) };
  }

  // GET /api/inspect/execution/:id
  const detailMatch = pathname.match(/^\/api\/inspect\/execution\/([^/]+)$/);
  if (detailMatch) {
    return { route: 'detail', id: decodeURIComponent(detailMatch[1]) };
  }

  return null;
}

// ---------------------------------------------------------------------------
// Request handler
// ---------------------------------------------------------------------------

function handleRequest(req: IncomingMessage, res: ServerResponse): void {
  const method = req.method || 'GET';
  const urlObj = new URL(req.url || '/', `http://localhost:${port}`);
  const pathname = urlObj.pathname;

  console.log(`${method} ${pathname}`);

  // Handle CORS preflight
  if (method === 'OPTIONS') {
    setCors(res);
    res.writeHead(204);
    res.end();
    return;
  }

  const matched = matchRoute(pathname);
  if (!matched) {
    send404(res);
    return;
  }

  switch (matched.route) {
    case 'list':
      sendJson(res, {
        executions: fixtureData.executions,
        next_token: null,
      });
      break;

    case 'detail':
      sendJson(res, fixtureData.execution_detail);
      break;

    case 'history':
      sendJson(res, {
        execution_id: fixtureData.execution_detail.execution_id,
        events: fixtureData.execution_detail.history,
      });
      break;

    case 'stream':
      handleSSE(res);
      break;

    default:
      send404(res);
  }
}

// ---------------------------------------------------------------------------
// SSE handler
// ---------------------------------------------------------------------------

function handleSSE(res: ServerResponse): void {
  setCors(res);
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
  });

  // Send execution_info (detail without history)
  const { history: _history, ...detailWithoutHistory } = fixtureData.execution_detail;
  res.write(`event: execution_info\ndata: ${JSON.stringify(detailWithoutHistory)}\n\n`);

  // Send history
  res.write(`event: history\ndata: ${JSON.stringify(fixtureData.execution_detail.history)}\n\n`);

  // Fixture is terminal (SUCCEEDED), close the connection
  res.end();
}

// ---------------------------------------------------------------------------
// Server lifecycle
// ---------------------------------------------------------------------------

const server = createServer(handleRequest);

server.listen(port, () => {
  console.log(`Mock inspect server started on port ${port} (fixture: ${fixture})`);
});

function shutdown(): void {
  console.log('\nShutting down mock inspect server...');
  server.close(() => {
    process.exit(0);
  });
  // Force exit if graceful shutdown takes too long
  setTimeout(() => process.exit(0), 2000);
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
