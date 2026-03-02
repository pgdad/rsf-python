/**
 * State name intelligence — go-to-definition, Find All References,
 * autocomplete, document highlights, hover, and quick-fix code actions.
 *
 * Parses YAML to build a state name index with exact line/column positions,
 * then provides LSP-compatible responses.
 */

import type {
  Definition,
  Location,
  CompletionItem,
  Hover,
  DocumentHighlight,
  CodeAction,
  Range,
  Position,
  TextEdit,
} from "vscode-languageserver";
import {
  CompletionItemKind,
  DocumentHighlightKind,
  CodeActionKind,
} from "vscode-languageserver";

export interface StateDefinition {
  name: string;
  type: string;
  line: number;
  character: number;
  endLine: number;
}

export interface StateReference {
  stateName: string;
  field: string; // "Next", "Default", "Catch.Next", "StartAt", "Choices[N].Next"
  line: number;
  character: number;
  endCharacter: number;
}

export interface StateIndex {
  definitions: Map<string, StateDefinition>;
  references: StateReference[];
}

/**
 * Build a state name index from YAML text.
 * Scans for state definitions in the States mapping and references in
 * Next, Default, StartAt, Catch.Next, and Choice branch fields.
 */
export function buildStateIndex(text: string): StateIndex {
  const lines = text.split("\n");
  const definitions = new Map<string, StateDefinition>();
  const references: StateReference[] = [];

  let inStates = false;
  let statesIndent = -1;
  let currentStateName: string | null = null;
  let currentStateStartLine = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trimStart();
    const indent = line.length - trimmed.length;

    // Detect States: block
    if (trimmed.startsWith("States:") && !trimmed.startsWith("States.ALL")) {
      inStates = true;
      statesIndent = indent;
      continue;
    }

    // Detect StartAt reference
    if (trimmed.startsWith("StartAt:")) {
      const value = extractYamlValue(trimmed, "StartAt");
      if (value) {
        const valueStart = line.indexOf(value, indent + "StartAt:".length);
        references.push({
          stateName: value,
          field: "StartAt",
          line: i,
          character: valueStart >= 0 ? valueStart : indent + 9,
          endCharacter:
            (valueStart >= 0 ? valueStart : indent + 9) + value.length,
        });
      }
    }

    if (inStates) {
      // Check if we've left the States block
      if (indent <= statesIndent && trimmed.length > 0 && !trimmed.startsWith("#")) {
        // Finish last state
        if (currentStateName && definitions.has(currentStateName)) {
          const def = definitions.get(currentStateName)!;
          def.endLine = i - 1;
        }
        inStates = false;
        currentStateName = null;
        continue;
      }

      // State definition (one level deeper than States:)
      if (indent === statesIndent + 2 && trimmed.match(/^[\w][\w-]*\s*:/) && !isKnownField(trimmed)) {
        // Finish previous state
        if (currentStateName && definitions.has(currentStateName)) {
          const def = definitions.get(currentStateName)!;
          def.endLine = i - 1;
        }

        const colonIdx = trimmed.indexOf(":");
        const name = trimmed.substring(0, colonIdx).trim();
        currentStateName = name;
        currentStateStartLine = i;

        definitions.set(name, {
          name,
          type: "Unknown",
          line: i,
          character: indent,
          endLine: i,
        });
      }

      // Detect Type field for current state
      if (currentStateName && trimmed.startsWith("Type:")) {
        const typeVal = extractYamlValue(trimmed, "Type");
        if (typeVal && definitions.has(currentStateName)) {
          definitions.get(currentStateName)!.type = typeVal;
        }
      }

      // Detect Next reference
      if (trimmed.startsWith("Next:")) {
        const value = extractYamlValue(trimmed, "Next");
        if (value) {
          const valueStart = line.indexOf(value, indent + "Next:".length);
          references.push({
            stateName: value,
            field: "Next",
            line: i,
            character: valueStart >= 0 ? valueStart : indent + 6,
            endCharacter:
              (valueStart >= 0 ? valueStart : indent + 6) + value.length,
          });
        }
      }

      // Detect Default reference
      if (trimmed.startsWith("Default:")) {
        const value = extractYamlValue(trimmed, "Default");
        if (value) {
          const valueStart = line.indexOf(value, indent + "Default:".length);
          references.push({
            stateName: value,
            field: "Default",
            line: i,
            character: valueStart >= 0 ? valueStart : indent + 9,
            endCharacter:
              (valueStart >= 0 ? valueStart : indent + 9) + value.length,
          });
        }
      }
    }
  }

  // Finish last state
  if (currentStateName && definitions.has(currentStateName)) {
    const def = definitions.get(currentStateName)!;
    def.endLine = lines.length - 1;
  }

  return { definitions, references };
}

function extractYamlValue(line: string, key: string): string | null {
  const match = line.match(new RegExp(`^\\s*${key}:\\s*["']?([\\w-]+)["']?`));
  return match ? match[1] : null;
}

function isKnownField(trimmed: string): boolean {
  const fields = [
    "Type:", "Next:", "End:", "Default:", "Comment:", "InputPath:",
    "OutputPath:", "ResultPath:", "ResultSelector:", "Parameters:",
    "Resource:", "Retry:", "Catch:", "Choices:", "Branches:",
    "ItemProcessor:", "Iterator:", "MaxConcurrency:", "Seconds:",
    "Timestamp:", "SecondsPath:", "TimestampPath:", "Error:", "Cause:",
    "Result:", "HeartbeatSeconds:", "TimeoutSeconds:", "Items:", "ItemsPath:",
    "ErrorEquals:", "IntervalSeconds:", "MaxAttempts:", "BackoffRate:",
    "SubWorkflow:",
  ];
  return fields.some((f) => trimmed.startsWith(f));
}

/**
 * Get go-to-definition for a state name at the given position.
 */
export function getDefinition(
  index: StateIndex,
  _uri: string,
  position: Position
): Definition | null {
  // Check if position is on a reference
  const ref = findReferenceAtPosition(index, position);
  if (ref) {
    const def = index.definitions.get(ref.stateName);
    if (def) {
      return {
        uri: _uri,
        range: {
          start: { line: def.line, character: def.character },
          end: { line: def.line, character: def.character + def.name.length },
        },
      };
    }
  }
  return null;
}

/**
 * Get all references to a state name at the given position.
 */
export function getReferences(
  index: StateIndex,
  uri: string,
  position: Position
): Location[] {
  const stateName = getStateNameAtPosition(index, position);
  if (!stateName) return [];

  const locations: Location[] = [];

  // Include definition
  const def = index.definitions.get(stateName);
  if (def) {
    locations.push({
      uri,
      range: {
        start: { line: def.line, character: def.character },
        end: { line: def.line, character: def.character + def.name.length },
      },
    });
  }

  // Include all references
  for (const ref of index.references) {
    if (ref.stateName === stateName) {
      locations.push({
        uri,
        range: {
          start: { line: ref.line, character: ref.character },
          end: { line: ref.line, character: ref.endCharacter },
        },
      });
    }
  }

  return locations;
}

/**
 * Get document highlights for a state name at the given position.
 */
export function getHighlights(
  index: StateIndex,
  position: Position
): DocumentHighlight[] {
  const stateName = getStateNameAtPosition(index, position);
  if (!stateName) return [];

  const highlights: DocumentHighlight[] = [];

  // Definition highlight
  const def = index.definitions.get(stateName);
  if (def) {
    highlights.push({
      range: {
        start: { line: def.line, character: def.character },
        end: { line: def.line, character: def.character + def.name.length },
      },
      kind: DocumentHighlightKind.Write,
    });
  }

  // Reference highlights
  for (const ref of index.references) {
    if (ref.stateName === stateName) {
      highlights.push({
        range: {
          start: { line: ref.line, character: ref.character },
          end: { line: ref.line, character: ref.endCharacter },
        },
        kind: DocumentHighlightKind.Read,
      });
    }
  }

  return highlights;
}

/**
 * Get state name completions at the given position.
 */
export function getCompletions(
  index: StateIndex,
  text: string,
  position: Position
): CompletionItem[] {
  const lines = text.split("\n");
  const line = lines[position.line] || "";
  const trimmed = line.trimStart();

  // Only complete in Next/Default value positions
  if (
    !trimmed.startsWith("Next:") &&
    !trimmed.startsWith("Default:") &&
    !trimmed.startsWith("StartAt:")
  ) {
    return [];
  }

  return [...index.definitions.values()].map((def) => ({
    label: def.name,
    kind: CompletionItemKind.Reference,
    detail: `State (${def.type})`,
    insertText: def.name,
  }));
}

/**
 * Get hover information for a state name at the given position.
 */
export function getHover(
  index: StateIndex,
  position: Position
): Hover | null {
  const stateName = getStateNameAtPosition(index, position);
  if (!stateName) return null;

  const def = index.definitions.get(stateName);
  if (!def) {
    return {
      contents: {
        kind: "markdown",
        value: `**${stateName}** — *undefined state*\n\nThis state is referenced but not defined in the States mapping.`,
      },
    };
  }

  const refCount = index.references.filter(
    (r) => r.stateName === stateName
  ).length;

  return {
    contents: {
      kind: "markdown",
      value: `**${stateName}** — ${def.type} state\n\nDefined at line ${def.line + 1}\n\n${refCount} reference(s)`,
    },
  };
}

/**
 * Get code actions (quick fixes) for unresolved state references.
 */
export function getCodeActions(
  index: StateIndex,
  range: Range
): CodeAction[] {
  const actions: CodeAction[] = [];

  for (const ref of index.references) {
    if (ref.line < range.start.line || ref.line > range.end.line) continue;
    if (index.definitions.has(ref.stateName)) continue;

    // Find closest matching state names using Levenshtein distance
    const suggestions = findClosestStateNames(
      ref.stateName,
      [...index.definitions.keys()],
      3
    );

    for (const suggestion of suggestions) {
      const edit: TextEdit = {
        range: {
          start: { line: ref.line, character: ref.character },
          end: { line: ref.line, character: ref.endCharacter },
        },
        newText: suggestion,
      };

      actions.push({
        title: `Did you mean '${suggestion}'?`,
        kind: CodeActionKind.QuickFix,
        edit: {
          changes: {
            // Will be filled by caller with actual URI
            "": [edit],
          },
        },
      });
    }
  }

  return actions;
}

// --- Helpers ---

function findReferenceAtPosition(
  index: StateIndex,
  position: Position
): StateReference | null {
  for (const ref of index.references) {
    if (
      ref.line === position.line &&
      position.character >= ref.character &&
      position.character <= ref.endCharacter
    ) {
      return ref;
    }
  }
  return null;
}

function getStateNameAtPosition(
  index: StateIndex,
  position: Position
): string | null {
  // Check references first
  const ref = findReferenceAtPosition(index, position);
  if (ref) return ref.stateName;

  // Check definitions
  for (const [name, def] of index.definitions) {
    if (
      def.line === position.line &&
      position.character >= def.character &&
      position.character <= def.character + name.length
    ) {
      return name;
    }
  }

  return null;
}

/**
 * Levenshtein distance between two strings.
 */
function levenshteinDistance(a: string, b: string): number {
  const matrix: number[][] = [];

  for (let i = 0; i <= b.length; i++) matrix[i] = [i];
  for (let j = 0; j <= a.length; j++) matrix[0][j] = j;

  for (let i = 1; i <= b.length; i++) {
    for (let j = 1; j <= a.length; j++) {
      if (b.charAt(i - 1) === a.charAt(j - 1)) {
        matrix[i][j] = matrix[i - 1][j - 1];
      } else {
        matrix[i][j] = Math.min(
          matrix[i - 1][j - 1] + 1, // substitution
          matrix[i][j - 1] + 1, // insertion
          matrix[i - 1][j] + 1 // deletion
        );
      }
    }
  }

  return matrix[b.length][a.length];
}

/**
 * Find closest matching state names using Levenshtein distance.
 */
function findClosestStateNames(
  target: string,
  candidates: string[],
  maxResults: number
): string[] {
  const scored = candidates
    .map((name) => ({ name, distance: levenshteinDistance(target, name) }))
    .filter((s) => s.distance <= Math.max(3, target.length / 2))
    .sort((a, b) => a.distance - b.distance);

  return scored.slice(0, maxResults).map((s) => s.name);
}
