/**
 * RSF Workflows VS Code Extension — entry point.
 *
 * Activates the Language Server and provides:
 * - Real-time YAML schema + semantic validation
 * - Go-to-definition, Find All References, autocomplete for state names
 * - Graph preview webview panel
 * - Status bar validation indicator
 */

import * as path from "path";
import * as vscode from "vscode";
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
  TransportKind,
} from "vscode-languageclient/node";

let client: LanguageClient;
let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext): void {
  // Language Server path
  const serverModule = context.asAbsolutePath(path.join("dist", "server.js"));

  const serverOptions: ServerOptions = {
    run: { module: serverModule, transport: TransportKind.ipc },
    debug: {
      module: serverModule,
      transport: TransportKind.ipc,
      options: { execArgv: ["--nolazy", "--inspect=6009"] },
    },
  };

  const clientOptions: LanguageClientOptions = {
    documentSelector: [
      { scheme: "file", language: "yaml", pattern: "**/workflow.{yaml,yml}" },
    ],
    synchronize: {
      configurationSection: "rsf",
    },
  };

  client = new LanguageClient(
    "rsfWorkflows",
    "RSF Workflows",
    serverOptions,
    clientOptions
  );

  // Status bar item
  statusBarItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    100
  );
  statusBarItem.command = "workbench.actions.view.problems";
  context.subscriptions.push(statusBarItem);

  // Update status bar when diagnostics change
  context.subscriptions.push(
    vscode.languages.onDidChangeDiagnostics((e) => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      const uri = editor.document.uri;
      if (!isWorkflowFile(uri.fsPath)) return;

      const diagnostics = vscode.languages.getDiagnostics(uri);
      const errorCount = diagnostics.filter(
        (d) => d.severity === vscode.DiagnosticSeverity.Error
      ).length;
      const warningCount = diagnostics.filter(
        (d) => d.severity === vscode.DiagnosticSeverity.Warning
      ).length;

      if (errorCount === 0 && warningCount === 0) {
        statusBarItem.text = "$(check) RSF";
        statusBarItem.tooltip = "RSF Workflow: No issues";
        statusBarItem.backgroundColor = undefined;
      } else if (errorCount > 0) {
        statusBarItem.text = `$(warning) RSF: ${errorCount} error(s)`;
        statusBarItem.tooltip = `RSF Workflow: ${errorCount} error(s), ${warningCount} warning(s)`;
        statusBarItem.backgroundColor = new vscode.ThemeColor(
          "statusBarItem.errorBackground"
        );
      } else {
        statusBarItem.text = `$(warning) RSF: ${warningCount} warning(s)`;
        statusBarItem.tooltip = `RSF Workflow: ${warningCount} warning(s)`;
        statusBarItem.backgroundColor = new vscode.ThemeColor(
          "statusBarItem.warningBackground"
        );
      }
      statusBarItem.show();
    })
  );

  // Show/hide status bar based on active editor
  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      if (editor && isWorkflowFile(editor.document.uri.fsPath)) {
        statusBarItem.show();
      } else {
        statusBarItem.hide();
      }
    })
  );

  // Graph preview command — registered here, implementation in graphPreviewProvider
  context.subscriptions.push(
    vscode.commands.registerCommand("rsf.openGraphPreview", () => {
      // Will be wired to graphPreviewProvider in plan 48-03
      const { GraphPreviewProvider } = require("./graphPreviewProvider");
      GraphPreviewProvider.createOrShow(context, client);
    })
  );

  // Start the client
  client.start();

  // Show status bar if current editor is a workflow file
  const editor = vscode.window.activeTextEditor;
  if (editor && isWorkflowFile(editor.document.uri.fsPath)) {
    statusBarItem.text = "$(sync~spin) RSF";
    statusBarItem.tooltip = "RSF Workflow: Validating...";
    statusBarItem.show();
  }

  const outputChannel = vscode.window.createOutputChannel("RSF Workflows");
  outputChannel.appendLine("RSF Workflows extension activated");
  context.subscriptions.push(outputChannel);
}

function isWorkflowFile(filePath: string): boolean {
  const basename = path.basename(filePath);
  return basename === "workflow.yaml" || basename === "workflow.yml";
}

export function deactivate(): Thenable<void> | undefined {
  if (statusBarItem) {
    statusBarItem.dispose();
  }
  if (!client) {
    return undefined;
  }
  return client.stop();
}
