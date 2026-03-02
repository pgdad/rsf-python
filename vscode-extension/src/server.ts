/**
 * RSF Workflows Language Server.
 *
 * Provides real-time validation, go-to-definition, references, completion,
 * hover, code actions, and document highlights for workflow.yaml files.
 */

import {
  createConnection,
  TextDocuments,
  ProposedFeatures,
  InitializeParams,
  InitializeResult,
  TextDocumentSyncKind,
  Diagnostic,
  CompletionItem,
  TextDocumentPositionParams,
  DefinitionParams,
  ReferenceParams,
  DocumentHighlightParams,
  HoverParams,
  CodeActionParams,
} from "vscode-languageserver/node";
import { TextDocument } from "vscode-languageserver-textdocument";
import { parseYaml, validateSchema } from "./validator";
import {
  validateSemantics,
  semanticErrorsToDiagnostics,
} from "./semanticValidator";
import {
  buildStateIndex,
  getDefinition,
  getReferences,
  getHighlights,
  getCompletions,
  getHover,
  getCodeActions,
  StateIndex,
} from "./stateNameProvider";

const connection = createConnection(ProposedFeatures.all);
const documents = new TextDocuments(TextDocument);

/** Debounce timers per document URI */
const debounceTimers = new Map<string, ReturnType<typeof setTimeout>>();

/** Cached state indices per document URI */
const stateIndices = new Map<string, StateIndex>();

/** Default debounce delay in ms */
let debounceMs = 500;

/** Whether validation is enabled */
let validationEnabled = true;

connection.onInitialize((_params: InitializeParams): InitializeResult => {
  return {
    capabilities: {
      textDocumentSync: TextDocumentSyncKind.Incremental,
      completionProvider: {
        resolveProvider: false,
        triggerCharacters: [" ", '"', "'"],
      },
      definitionProvider: true,
      referencesProvider: true,
      documentHighlightProvider: true,
      hoverProvider: true,
      codeActionProvider: true,
    },
  };
});

connection.onInitialized(() => {
  connection.console.log("RSF Workflows Language Server initialized");
});

/**
 * Check if a document URI matches workflow.yaml/workflow.yml.
 */
function isWorkflowFile(uri: string): boolean {
  return /workflow\.ya?ml$/i.test(uri);
}

/**
 * Run validation on a document and publish diagnostics.
 */
function validateDocument(document: TextDocument): void {
  if (!validationEnabled) {
    connection.sendDiagnostics({ uri: document.uri, diagnostics: [] });
    return;
  }

  if (!isWorkflowFile(document.uri)) {
    return;
  }

  const text = document.getText();
  const allDiagnostics: Diagnostic[] = [];

  // Parse YAML
  const { data, parseErrors, doc } = parseYaml(text);
  allDiagnostics.push(...parseErrors);

  if (data) {
    // Schema validation
    const schemaDiags = validateSchema(data, text);
    allDiagnostics.push(...schemaDiags);

    // Semantic validation
    const semanticErrors = validateSemantics(data);
    const semanticDiags = semanticErrorsToDiagnostics(semanticErrors, text);
    allDiagnostics.push(...semanticDiags);
  }

  // Build state index for navigation features
  const index = buildStateIndex(text);
  stateIndices.set(document.uri, index);

  // Publish diagnostics
  connection.sendDiagnostics({
    uri: document.uri,
    diagnostics: allDiagnostics,
  });

  // Send validation results to client for graph preview error highlighting
  connection.sendNotification("rsf/validationResults", {
    uri: document.uri,
    errors: allDiagnostics,
  });
}

/**
 * Schedule debounced validation for a document.
 */
function scheduleValidation(document: TextDocument): void {
  const existing = debounceTimers.get(document.uri);
  if (existing) clearTimeout(existing);

  debounceTimers.set(
    document.uri,
    setTimeout(() => {
      debounceTimers.delete(document.uri);
      validateDocument(document);
    }, debounceMs)
  );
}

// Document lifecycle
documents.onDidOpen((event) => {
  if (isWorkflowFile(event.document.uri)) {
    validateDocument(event.document);
  }
});

documents.onDidChangeContent((event) => {
  if (isWorkflowFile(event.document.uri)) {
    scheduleValidation(event.document);
  }
});

documents.onDidClose((event) => {
  stateIndices.delete(event.document.uri);
  debounceTimers.delete(event.document.uri);
  connection.sendDiagnostics({ uri: event.document.uri, diagnostics: [] });
});

// Configuration changes
connection.onDidChangeConfiguration((change) => {
  const settings = change.settings?.rsf;
  if (settings?.validation) {
    validationEnabled = settings.validation.enabled ?? true;
    debounceMs = settings.validation.debounce ?? 500;
  }

  // Re-validate all open documents
  documents.all().forEach((doc) => {
    if (isWorkflowFile(doc.uri)) {
      validateDocument(doc);
    }
  });
});

// Go-to-definition
connection.onDefinition((params: DefinitionParams) => {
  const index = stateIndices.get(params.textDocument.uri);
  if (!index) return null;
  return getDefinition(index, params.textDocument.uri, params.position);
});

// Find All References
connection.onReferences((params: ReferenceParams) => {
  const index = stateIndices.get(params.textDocument.uri);
  if (!index) return [];
  return getReferences(index, params.textDocument.uri, params.position);
});

// Document Highlights
connection.onDocumentHighlight((params: DocumentHighlightParams) => {
  const index = stateIndices.get(params.textDocument.uri);
  if (!index) return [];
  return getHighlights(index, params.position);
});

// Completion
connection.onCompletion((params: TextDocumentPositionParams): CompletionItem[] => {
  const index = stateIndices.get(params.textDocument.uri);
  if (!index) return [];
  const doc = documents.get(params.textDocument.uri);
  if (!doc) return [];
  return getCompletions(index, doc.getText(), params.position);
});

// Hover
connection.onHover((params: HoverParams) => {
  const index = stateIndices.get(params.textDocument.uri);
  if (!index) return null;
  return getHover(index, params.position);
});

// Code Actions
connection.onCodeAction((params: CodeActionParams) => {
  const index = stateIndices.get(params.textDocument.uri);
  if (!index) return [];
  const actions = getCodeActions(index, params.range);
  // Fill in the URI for code action edits
  for (const action of actions) {
    if (action.edit?.changes?.[""] !== undefined) {
      const edits = action.edit.changes[""];
      delete action.edit.changes[""];
      action.edit.changes[params.textDocument.uri] = edits;
    }
  }
  return actions;
});

documents.listen(connection);
connection.listen();
