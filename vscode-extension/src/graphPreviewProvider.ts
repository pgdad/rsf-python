/**
 * Graph Preview webview panel manager.
 *
 * Opens a side panel showing a live graph preview of the current workflow.
 * Updates as the user edits workflow.yaml.
 */

import * as vscode from "vscode";
import * as path from "path";
import {
  yamlToGraph,
  layoutGraph,
  applyErrorHighlights,
  extractErrorStateNames,
} from "./graphPreview";
import { parseDocument } from "yaml";
import { buildStateIndex } from "./stateNameProvider";

let currentPanel: vscode.WebviewPanel | undefined;
let debounceTimer: ReturnType<typeof setTimeout> | undefined;

export class GraphPreviewProvider {
  static createOrShow(
    context: vscode.ExtensionContext,
    _client?: any
  ): void {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showInformationMessage(
        "Open a workflow.yaml file first"
      );
      return;
    }

    const fileName = path.basename(editor.document.uri.fsPath);
    if (!/^workflow\.ya?ml$/i.test(fileName)) {
      vscode.window.showInformationMessage(
        "RSF Graph Preview only works with workflow.yaml files"
      );
      return;
    }

    if (currentPanel) {
      currentPanel.reveal(vscode.ViewColumn.Beside);
      updatePreview(editor.document);
      return;
    }

    currentPanel = vscode.window.createWebviewPanel(
      "rsfGraphPreview",
      `RSF: ${fileName} Preview`,
      vscode.ViewColumn.Beside,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [
          vscode.Uri.joinPath(context.extensionUri, "media"),
        ],
      }
    );

    const mediaUri = currentPanel.webview.asWebviewUri(
      vscode.Uri.joinPath(context.extensionUri, "media")
    );

    currentPanel.webview.html = getWebviewContent(
      currentPanel.webview,
      mediaUri
    );

    // Handle messages from webview (click-to-navigate)
    currentPanel.webview.onDidReceiveMessage(
      (message) => {
        if (message.type === "navigate" && message.stateName) {
          navigateToState(message.stateName);
        }
      },
      undefined,
      context.subscriptions
    );

    // Clean up on dispose
    currentPanel.onDidDispose(
      () => {
        currentPanel = undefined;
      },
      null,
      context.subscriptions
    );

    // Listen for document changes
    const changeDisposable = vscode.workspace.onDidChangeTextDocument(
      (e) => {
        if (
          currentPanel &&
          isWorkflowFile(e.document.uri.fsPath)
        ) {
          if (debounceTimer) clearTimeout(debounceTimer);
          debounceTimer = setTimeout(() => {
            updatePreview(e.document);
          }, 500);
        }
      }
    );
    context.subscriptions.push(changeDisposable);

    // Listen for active editor changes
    const editorDisposable = vscode.window.onDidChangeActiveTextEditor(
      (editor) => {
        if (
          editor &&
          currentPanel &&
          isWorkflowFile(editor.document.uri.fsPath)
        ) {
          currentPanel.title = `RSF: ${path.basename(
            editor.document.uri.fsPath
          )} Preview`;
          updatePreview(editor.document);
        }
      }
    );
    context.subscriptions.push(editorDisposable);

    // Listen for diagnostic changes
    const diagDisposable = vscode.languages.onDidChangeDiagnostics(() => {
      const activeEditor = vscode.window.activeTextEditor;
      if (
        activeEditor &&
        currentPanel &&
        isWorkflowFile(activeEditor.document.uri.fsPath)
      ) {
        updatePreview(activeEditor.document);
      }
    });
    context.subscriptions.push(diagDisposable);

    // Initial render
    updatePreview(editor.document);
  }
}

function isWorkflowFile(filePath: string): boolean {
  const basename = path.basename(filePath);
  return basename === "workflow.yaml" || basename === "workflow.yml";
}

function updatePreview(document: vscode.TextDocument): void {
  if (!currentPanel) return;

  const text = document.getText();
  let data: any = null;

  try {
    const doc = parseDocument(text);
    data = doc.toJS();
  } catch {
    currentPanel.webview.postMessage({
      type: "update",
      error: "YAML parse error",
      nodes: [],
      edges: [],
    });
    return;
  }

  if (!data || !data.States) {
    currentPanel.webview.postMessage({
      type: "update",
      error: "No states found in workflow",
      nodes: [],
      edges: [],
    });
    return;
  }

  let graphData = yamlToGraph(data);
  graphData = layoutGraph(graphData);

  // Apply error highlights from diagnostics
  const diagnostics = vscode.languages.getDiagnostics(document.uri);
  const errorNames = extractErrorStateNames(
    diagnostics.map((d) => ({ message: d.message, source: d.source }))
  );
  graphData = applyErrorHighlights(graphData, errorNames);

  currentPanel.webview.postMessage({
    type: "update",
    nodes: graphData.nodes,
    edges: graphData.edges,
  });
}

function navigateToState(stateName: string): void {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;

  const text = editor.document.getText();
  const index = buildStateIndex(text);
  const def = index.definitions.get(stateName);

  if (def) {
    const position = new vscode.Position(def.line, def.character);
    editor.selection = new vscode.Selection(position, position);
    editor.revealRange(
      new vscode.Range(position, position),
      vscode.TextEditorRevealType.InCenter
    );
  }
}

function getWebviewContent(
  webview: vscode.Webview,
  _mediaUri: vscode.Uri
): string {
  const nonce = getNonce();

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RSF Graph Preview</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: var(--vscode-editor-background, #1e1e1e);
      color: var(--vscode-editor-foreground, #d4d4d4);
      font-family: var(--vscode-font-family, 'Segoe UI', sans-serif);
      overflow: hidden;
      width: 100vw;
      height: 100vh;
    }
    #container {
      width: 100%;
      height: 100%;
      cursor: grab;
    }
    #container.dragging { cursor: grabbing; }
    svg { width: 100%; height: 100%; }
    .state-node {
      cursor: pointer;
      transition: opacity 0.2s;
    }
    .state-node:hover { opacity: 0.85; }
    .state-node rect, .state-node polygon {
      stroke-width: 2;
      rx: 6;
      ry: 6;
    }
    .state-node.error rect, .state-node.error polygon {
      stroke: #f44336 !important;
      stroke-width: 3;
      filter: drop-shadow(0 0 4px rgba(244, 67, 54, 0.5));
    }
    .state-label {
      fill: var(--vscode-editor-foreground, #d4d4d4);
      font-size: 12px;
      text-anchor: middle;
      dominant-baseline: central;
      pointer-events: none;
    }
    .edge-path {
      fill: none;
      stroke: var(--vscode-editorWidget-foreground, #888);
      stroke-width: 1.5;
      marker-end: url(#arrowhead);
    }
    .edge-label {
      fill: var(--vscode-descriptionForeground, #999);
      font-size: 10px;
      text-anchor: middle;
    }
    #message {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      color: var(--vscode-descriptionForeground, #888);
      font-size: 14px;
      display: none;
    }

    /* State type colors */
    .type-Task rect { fill: #264f78; stroke: #3d7ab5; }
    .type-Pass rect { fill: #404040; stroke: #666; }
    .type-Choice polygon { fill: #8b5e00; stroke: #c48500; }
    .type-Wait rect { fill: #4a2080; stroke: #7b4dbd; }
    .type-Succeed rect { fill: #1b5e20; stroke: #388e3c; }
    .type-Fail rect { fill: #b71c1c; stroke: #e53935; }
    .type-Parallel rect { fill: #264f78; stroke: #3d7ab5; stroke-dasharray: 6 3; }
    .type-Map rect { fill: #264f78; stroke: #3d7ab5; stroke-dasharray: 2 2; }
    .type-Unknown rect { fill: #555; stroke: #777; }
  </style>
</head>
<body>
  <div id="container">
    <svg id="graph"></svg>
  </div>
  <div id="message">No workflow states to display</div>

  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    const container = document.getElementById('container');
    const svg = document.getElementById('graph');
    const message = document.getElementById('message');

    let transform = { x: 0, y: 0, scale: 1 };
    let isDragging = false;
    let dragStart = { x: 0, y: 0 };
    let graphGroup = null;

    // Pan: mouse drag on background
    container.addEventListener('mousedown', (e) => {
      if (e.target === svg || e.target === container || e.target === graphGroup) {
        isDragging = true;
        dragStart = { x: e.clientX - transform.x, y: e.clientY - transform.y };
        container.classList.add('dragging');
      }
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      transform.x = e.clientX - dragStart.x;
      transform.y = e.clientY - dragStart.y;
      applyTransform();
    });

    window.addEventListener('mouseup', () => {
      isDragging = false;
      container.classList.remove('dragging');
    });

    // Zoom: scroll wheel
    container.addEventListener('wheel', (e) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      const newScale = Math.max(0.2, Math.min(3, transform.scale * delta));

      // Zoom toward cursor
      const rect = container.getBoundingClientRect();
      const cx = e.clientX - rect.left;
      const cy = e.clientY - rect.top;

      transform.x = cx - (cx - transform.x) * (newScale / transform.scale);
      transform.y = cy - (cy - transform.y) * (newScale / transform.scale);
      transform.scale = newScale;
      applyTransform();
    });

    function applyTransform() {
      if (graphGroup) {
        graphGroup.setAttribute('transform',
          'translate(' + transform.x + ',' + transform.y + ') scale(' + transform.scale + ')');
      }
    }

    function renderGraph(nodes, edges) {
      if (!nodes || nodes.length === 0) {
        svg.innerHTML = '';
        message.style.display = 'block';
        return;
      }
      message.style.display = 'none';

      // Build SVG
      let svgContent = '<defs><marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill="#888" /></marker></defs>';
      svgContent += '<g id="graphGroup">';

      // Draw edges first (behind nodes)
      for (const edge of edges) {
        const src = nodes.find(n => n.id === edge.source);
        const tgt = nodes.find(n => n.id === edge.target);
        if (!src || !tgt) continue;

        const x1 = src.x;
        const y1 = src.y + src.height / 2;
        const x2 = tgt.x;
        const y2 = tgt.y - tgt.height / 2;

        // Simple curved path
        const midY = (y1 + y2) / 2;
        svgContent += '<path class="edge-path" d="M ' + x1 + ' ' + y1 + ' C ' + x1 + ' ' + midY + ', ' + x2 + ' ' + midY + ', ' + x2 + ' ' + y2 + '" />';

        if (edge.label) {
          const labelX = (x1 + x2) / 2;
          const labelY = midY - 8;
          svgContent += '<text class="edge-label" x="' + labelX + '" y="' + labelY + '">' + escapeHtml(edge.label) + '</text>';
        }
      }

      // Draw nodes
      for (const node of nodes) {
        const errorClass = node.hasError ? ' error' : '';
        const typeClass = 'type-' + node.type;
        const x = node.x - node.width / 2;
        const y = node.y - node.height / 2;

        svgContent += '<g class="state-node ' + typeClass + errorClass + '" data-state="' + escapeHtml(node.id) + '">';

        if (node.type === 'Choice') {
          // Diamond shape for Choice
          const cx = node.x;
          const cy = node.y;
          const hw = node.width / 2;
          const hh = node.height / 2;
          svgContent += '<polygon points="' + cx + ',' + (cy - hh) + ' ' + (cx + hw) + ',' + cy + ' ' + cx + ',' + (cy + hh) + ' ' + (cx - hw) + ',' + cy + '" />';
        } else {
          svgContent += '<rect x="' + x + '" y="' + y + '" width="' + node.width + '" height="' + node.height + '" rx="6" ry="6" />';
        }

        svgContent += '<text class="state-label" x="' + node.x + '" y="' + node.y + '">' + escapeHtml(node.label) + '</text>';
        svgContent += '</g>';
      }

      svgContent += '</g>';
      svg.innerHTML = svgContent;
      graphGroup = document.getElementById('graphGroup');

      // Center graph
      if (nodes.length > 0) {
        const minX = Math.min(...nodes.map(n => n.x - n.width / 2));
        const maxX = Math.max(...nodes.map(n => n.x + n.width / 2));
        const minY = Math.min(...nodes.map(n => n.y - n.height / 2));
        const maxY = Math.max(...nodes.map(n => n.y + n.height / 2));
        const gWidth = maxX - minX;
        const gHeight = maxY - minY;
        const cWidth = container.clientWidth;
        const cHeight = container.clientHeight;
        const scale = Math.min(cWidth / (gWidth + 80), cHeight / (gHeight + 80), 1.5);
        transform.scale = scale;
        transform.x = (cWidth - gWidth * scale) / 2 - minX * scale;
        transform.y = (cHeight - gHeight * scale) / 2 - minY * scale;
        applyTransform();
      }

      // Click-to-navigate handlers
      document.querySelectorAll('.state-node').forEach(el => {
        el.addEventListener('click', (e) => {
          const stateName = el.getAttribute('data-state');
          if (stateName) {
            vscode.postMessage({ type: 'navigate', stateName: stateName });
          }
        });
      });
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    // Listen for messages from extension
    window.addEventListener('message', (event) => {
      const msg = event.data;
      if (msg.type === 'update') {
        if (msg.error) {
          message.textContent = msg.error;
          message.style.display = 'block';
          svg.innerHTML = '';
          return;
        }
        renderGraph(msg.nodes, msg.edges);
      }
    });
  </script>
</body>
</html>`;
}

function getNonce(): string {
  let text = "";
  const possible =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  for (let i = 0; i < 32; i++) {
    text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return text;
}
