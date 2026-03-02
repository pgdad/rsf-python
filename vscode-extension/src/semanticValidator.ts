/**
 * Semantic cross-state validation — TypeScript port of src/rsf/dsl/validator.py.
 *
 * Performs validations that JSON Schema cannot:
 * 1. All Next/Default/Catch.Next references resolve to existing states
 * 2. All states are reachable from StartAt (BFS)
 * 3. At least one terminal state exists (Succeed, Fail, or End: true)
 * 4. States.ALL must be last in Retry/Catch arrays
 * 5. Recursive validation for Parallel branches and Map ItemProcessor
 * 6. Timeout validation (> 30 days warning)
 */

import type { Diagnostic } from "vscode-languageserver";
import { DiagnosticSeverity } from "vscode-languageserver";

export interface SemanticError {
  message: string;
  path: string;
  severity: "error" | "warning";
}

/**
 * Find the line number of a YAML key path in the document text.
 * Handles nested paths like "States.ProcessOrder.Next".
 */
function findYamlPosition(
  text: string,
  path: string
): { line: number; character: number } {
  const segments = path.split(".");
  const lines = text.split("\n");
  let bestLine = 0;
  let bestChar = 0;
  let searchFromLine = 0;

  for (const seg of segments) {
    // Handle array indices like "Choices[0]"
    const baseSeg = seg.replace(/\[\d+\]$/, "");
    for (let i = searchFromLine; i < lines.length; i++) {
      const trimmed = lines[i].trimStart();
      const indent = lines[i].length - trimmed.length;
      if (
        trimmed.startsWith(`${baseSeg}:`) ||
        trimmed.startsWith(`"${baseSeg}":`) ||
        trimmed.startsWith(`'${baseSeg}':`) ||
        trimmed === `${baseSeg}:` ||
        // For state names in States mapping
        trimmed.startsWith(`${baseSeg}:`)
      ) {
        bestLine = i;
        bestChar = indent;
        searchFromLine = i + 1;
        break;
      }
    }
  }

  return { line: bestLine, character: bestChar };
}

/**
 * Convert semantic errors to LSP Diagnostic objects with correct positions.
 */
export function semanticErrorsToDiagnostics(
  errors: SemanticError[],
  text: string
): Diagnostic[] {
  return errors.map((err) => {
    const pos = findYamlPosition(text, err.path);
    return {
      severity:
        err.severity === "warning"
          ? DiagnosticSeverity.Warning
          : DiagnosticSeverity.Error,
      range: {
        start: { line: pos.line, character: pos.character },
        end: { line: pos.line, character: pos.character + 50 },
      },
      message: err.message,
      source: "rsf-semantic",
    };
  });
}

/**
 * Run all semantic validations on a parsed workflow definition.
 */
export function validateSemantics(data: any): SemanticError[] {
  if (!data || typeof data !== "object") {
    return [];
  }

  const errors: SemanticError[] = [];

  validateTimeout(data, errors);
  validateTriggers(data, errors);
  validateSubWorkflows(data, errors);
  validateDynamodbTables(data, errors);
  validateAlarms(data, errors);
  validateDlq(data, errors);
  validateStateMachine(data.States || {}, data.StartAt || "", "", errors);

  return errors;
}

function validateTimeout(data: any, errors: SemanticError[]): void {
  if (
    data.TimeoutSeconds !== undefined &&
    data.TimeoutSeconds !== null &&
    data.TimeoutSeconds > 2592000
  ) {
    errors.push({
      message: `TimeoutSeconds value ${data.TimeoutSeconds} exceeds 30 days — this is unusually large`,
      path: "TimeoutSeconds",
      severity: "warning",
    });
  }
}

function validateTriggers(data: any, errors: SemanticError[]): void {
  if (!data.triggers) return;

  if (Array.isArray(data.triggers) && data.triggers.length === 0) {
    errors.push({
      message:
        "Triggers list is empty — remove it or add at least one trigger",
      path: "triggers",
      severity: "warning",
    });
    return;
  }

  for (let i = 0; i < data.triggers.length; i++) {
    const trigger = data.triggers[i];
    if (trigger.type === "eventbridge") {
      if (!trigger.schedule_expression && !trigger.event_pattern) {
        errors.push({
          message:
            "EventBridge trigger must have at least one of schedule_expression or event_pattern",
          path: `triggers[${i}]`,
          severity: "error",
        });
      }
    } else if (trigger.type === "sqs") {
      if (trigger.batch_size && trigger.batch_size >= 10000) {
        errors.push({
          message: `SQS batch_size ${trigger.batch_size} is very large — consider a smaller value for most use cases`,
          path: `triggers[${i}].batch_size`,
          severity: "warning",
        });
      }
    }
  }
}

function validateSubWorkflows(data: any, errors: SemanticError[]): void {
  if (!data.sub_workflows) return;

  const declaredNames = new Set<string>(
    data.sub_workflows.map((sw: any) => sw.name)
  );
  const referencedNames = new Set<string>();

  collectSubWorkflowRefs(
    data.States || {},
    referencedNames,
    errors,
    declaredNames
  );

  for (const name of declaredNames) {
    if (!referencedNames.has(name)) {
      errors.push({
        message: `Sub-workflow '${name}' is declared but never referenced`,
        path: "sub_workflows",
        severity: "warning",
      });
    }
  }
}

function collectSubWorkflowRefs(
  states: Record<string, any>,
  referenced: Set<string>,
  errors: SemanticError[],
  declared: Set<string>
): void {
  for (const [name, state] of Object.entries(states)) {
    if (state.Type === "Task" && state.SubWorkflow) {
      referenced.add(state.SubWorkflow);
      if (!declared.has(state.SubWorkflow)) {
        errors.push({
          message: `SubWorkflow '${state.SubWorkflow}' in state '${name}' is not declared in sub_workflows`,
          path: `States.${name}.SubWorkflow`,
          severity: "error",
        });
      }
    }
    if (state.Type === "Parallel" && state.Branches) {
      for (const branch of state.Branches) {
        collectSubWorkflowRefs(
          branch.States || {},
          referenced,
          errors,
          declared
        );
      }
    }
    if (state.Type === "Map" && state.ItemProcessor) {
      collectSubWorkflowRefs(
        state.ItemProcessor.States || {},
        referenced,
        errors,
        declared
      );
    }
  }
}

function validateDynamodbTables(data: any, errors: SemanticError[]): void {
  if (!data.dynamodb_tables) return;

  if (
    Array.isArray(data.dynamodb_tables) &&
    data.dynamodb_tables.length === 0
  ) {
    errors.push({
      message:
        "DynamoDB tables list is empty — remove it or add at least one table",
      path: "dynamodb_tables",
      severity: "warning",
    });
    return;
  }

  const seenNames = new Set<string>();
  for (let i = 0; i < data.dynamodb_tables.length; i++) {
    const table = data.dynamodb_tables[i];
    if (seenNames.has(table.table_name)) {
      errors.push({
        message: `Duplicate DynamoDB table name '${table.table_name}'`,
        path: `dynamodb_tables[${i}].table_name`,
        severity: "error",
      });
    }
    seenNames.add(table.table_name);

    if (table.billing_mode === "PROVISIONED") {
      if (!table.read_capacity || !table.write_capacity) {
        errors.push({
          message: `DynamoDB table '${table.table_name}' uses PROVISIONED billing but is missing read_capacity or write_capacity`,
          path: `dynamodb_tables[${i}]`,
          severity: "error",
        });
      }
    }
  }
}

function validateAlarms(data: any, errors: SemanticError[]): void {
  if (!data.alarms) return;

  if (Array.isArray(data.alarms) && data.alarms.length === 0) {
    errors.push({
      message:
        "Alarms list is empty — remove it or add at least one alarm",
      path: "alarms",
      severity: "warning",
    });
    return;
  }

  const seenTypes: Record<string, number> = {};
  for (let i = 0; i < data.alarms.length; i++) {
    const alarm = data.alarms[i];
    if (alarm.type === "error_rate" && alarm.threshold > 100) {
      errors.push({
        message: `Error rate alarm threshold ${alarm.threshold} exceeds 100% — error rate is a percentage, >100% is unusual`,
        path: `alarms[${i}].threshold`,
        severity: "warning",
      });
    }
    if (alarm.type in seenTypes) {
      errors.push({
        message: `Multiple alarms of type '${alarm.type}' — consider combining into a single alarm`,
        path: `alarms[${i}]`,
        severity: "warning",
      });
    } else {
      seenTypes[alarm.type] = i;
    }
  }
}

function validateDlq(data: any, errors: SemanticError[]): void {
  if (!data.dead_letter_queue) return;
  if (!data.dead_letter_queue.enabled) return;

  if (data.dead_letter_queue.max_receive_count > 100) {
    errors.push({
      message: `DLQ max_receive_count ${data.dead_letter_queue.max_receive_count} is unusually high — messages will retry many times before reaching DLQ`,
      path: "dead_letter_queue.max_receive_count",
      severity: "warning",
    });
  }
}

/**
 * Validate a state machine (top-level or nested branch).
 */
function validateStateMachine(
  states: Record<string, any>,
  startAt: string,
  pathPrefix: string,
  errors: SemanticError[]
): void {
  const stateNames = new Set(Object.keys(states));

  // 1. StartAt must reference an existing state
  if (startAt && !stateNames.has(startAt)) {
    errors.push({
      message: `StartAt '${startAt}' does not reference an existing state`,
      path: `${pathPrefix}StartAt`,
      severity: "error",
    });
  }

  // 2. Validate all references resolve
  validateReferences(states, stateNames, pathPrefix, errors);

  // 3. BFS reachability
  validateReachability(states, startAt, stateNames, pathPrefix, errors);

  // 4. Terminal state check
  validateTerminalExists(states, pathPrefix, errors);

  // 5. States.ALL ordering
  validateStatesAllOrdering(states, pathPrefix, errors);

  // 6. Recurse into Parallel/Map
  validateBranchesRecursive(states, pathPrefix, errors);
}

function validateReferences(
  states: Record<string, any>,
  stateNames: Set<string>,
  pathPrefix: string,
  errors: SemanticError[]
): void {
  for (const [name, state] of Object.entries(states)) {
    const statePath = `${pathPrefix}States.${name}`;

    // Next field
    if (state.Next && !stateNames.has(state.Next)) {
      errors.push({
        message: `Next '${state.Next}' does not reference an existing state`,
        path: `${statePath}.Next`,
        severity: "error",
      });
    }

    // Choice state: Default and Choices[].Next
    if (state.Type === "Choice") {
      if (state.Default && !stateNames.has(state.Default)) {
        errors.push({
          message: `Default '${state.Default}' does not reference an existing state`,
          path: `${statePath}.Default`,
          severity: "error",
        });
      }
      if (state.Choices) {
        for (let i = 0; i < state.Choices.length; i++) {
          validateChoiceRuleReferences(
            state.Choices[i],
            stateNames,
            `${statePath}.Choices[${i}]`,
            errors
          );
        }
      }
    }

    // Catch handlers
    if (state.Catch) {
      for (let i = 0; i < state.Catch.length; i++) {
        if (state.Catch[i].Next && !stateNames.has(state.Catch[i].Next)) {
          errors.push({
            message: `Catch.Next '${state.Catch[i].Next}' does not reference an existing state`,
            path: `${statePath}.Catch[${i}].Next`,
            severity: "error",
          });
        }
      }
    }
  }
}

function validateChoiceRuleReferences(
  rule: any,
  stateNames: Set<string>,
  path: string,
  errors: SemanticError[]
): void {
  if (rule.Next && !stateNames.has(rule.Next)) {
    errors.push({
      message: `Choice rule Next '${rule.Next}' does not reference an existing state`,
      path: `${path}.Next`,
      severity: "error",
    });
  }
  // Recurse into boolean combinators
  if (rule.And) {
    for (let i = 0; i < rule.And.length; i++) {
      validateChoiceRuleReferences(
        rule.And[i],
        stateNames,
        `${path}.And[${i}]`,
        errors
      );
    }
  }
  if (rule.Or) {
    for (let i = 0; i < rule.Or.length; i++) {
      validateChoiceRuleReferences(
        rule.Or[i],
        stateNames,
        `${path}.Or[${i}]`,
        errors
      );
    }
  }
  if (rule.Not) {
    validateChoiceRuleReferences(rule.Not, stateNames, `${path}.Not`, errors);
  }
}

function validateReachability(
  states: Record<string, any>,
  startAt: string,
  stateNames: Set<string>,
  pathPrefix: string,
  errors: SemanticError[]
): void {
  if (!stateNames.has(startAt)) return; // Already reported

  const visited = new Set<string>();
  const queue: string[] = [startAt];

  while (queue.length > 0) {
    const current = queue.shift()!;
    if (visited.has(current) || !stateNames.has(current)) continue;
    visited.add(current);
    const state = states[current];

    const targets: string[] = [];

    if (state.Next) targets.push(state.Next);

    if (state.Type === "Choice") {
      if (state.Default) targets.push(state.Default);
      if (state.Choices) {
        for (const rule of state.Choices) {
          collectChoiceTargets(rule, targets);
        }
      }
    }

    if (state.Catch) {
      for (const catcher of state.Catch) {
        if (catcher.Next) targets.push(catcher.Next);
      }
    }

    for (const target of targets) {
      if (!visited.has(target)) queue.push(target);
    }
  }

  const unreachable = [...stateNames].filter((n) => !visited.has(n)).sort();
  for (const name of unreachable) {
    errors.push({
      message: `State '${name}' is not reachable from StartAt`,
      path: `${pathPrefix}States.${name}`,
      severity: "warning",
    });
  }
}

function collectChoiceTargets(rule: any, targets: string[]): void {
  if (rule.Next) targets.push(rule.Next);
  if (rule.And) {
    for (const child of rule.And) collectChoiceTargets(child, targets);
  }
  if (rule.Or) {
    for (const child of rule.Or) collectChoiceTargets(child, targets);
  }
  if (rule.Not) collectChoiceTargets(rule.Not, targets);
}

function validateTerminalExists(
  states: Record<string, any>,
  pathPrefix: string,
  errors: SemanticError[]
): void {
  let hasTerminal = false;
  for (const state of Object.values(states)) {
    if (state.Type === "Succeed" || state.Type === "Fail") {
      hasTerminal = true;
      break;
    }
    if (state.End === true) {
      hasTerminal = true;
      break;
    }
  }
  if (!hasTerminal) {
    errors.push({
      message:
        "State machine must have at least one terminal state (Succeed, Fail, or End: true)",
      path: `${pathPrefix}States`,
      severity: "error",
    });
  }
}

function validateStatesAllOrdering(
  states: Record<string, any>,
  pathPrefix: string,
  errors: SemanticError[]
): void {
  for (const [name, state] of Object.entries(states)) {
    const statePath = `${pathPrefix}States.${name}`;

    if (state.Retry) {
      for (let i = 0; i < state.Retry.length; i++) {
        const retry = state.Retry[i];
        if (
          retry.ErrorEquals &&
          retry.ErrorEquals.includes("States.ALL") &&
          i < state.Retry.length - 1
        ) {
          errors.push({
            message: "States.ALL in Retry must be the last entry",
            path: `${statePath}.Retry[${i}]`,
            severity: "error",
          });
        }
      }
    }

    if (state.Catch) {
      for (let i = 0; i < state.Catch.length; i++) {
        const catcher = state.Catch[i];
        if (
          catcher.ErrorEquals &&
          catcher.ErrorEquals.includes("States.ALL") &&
          i < state.Catch.length - 1
        ) {
          errors.push({
            message: "States.ALL in Catch must be the last entry",
            path: `${statePath}.Catch[${i}]`,
            severity: "error",
          });
        }
      }
    }
  }
}

function validateBranchesRecursive(
  states: Record<string, any>,
  pathPrefix: string,
  errors: SemanticError[]
): void {
  for (const [name, state] of Object.entries(states)) {
    const statePath = `${pathPrefix}States.${name}.`;

    if (state.Type === "Parallel" && state.Branches) {
      for (let i = 0; i < state.Branches.length; i++) {
        const branch = state.Branches[i];
        validateStateMachine(
          branch.States || {},
          branch.StartAt || "",
          `${statePath}Branches[${i}].`,
          errors
        );
      }
    }

    if (state.Type === "Map" && state.ItemProcessor) {
      validateStateMachine(
        state.ItemProcessor.States || {},
        state.ItemProcessor.StartAt || "",
        `${statePath}ItemProcessor.`,
        errors
      );
    }
  }
}
