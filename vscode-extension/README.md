# RSF Workflows

YAML schema validation, go-to-definition, and live graph preview for RSF workflow files in VS Code.

## Features

### Schema Validation

Real-time validation of workflow.yaml files against the RSF JSON Schema. Errors appear as inline squiggly underlines and in the Problems panel.

- Validates all DSL fields: states, triggers, sub-workflows, DynamoDB tables, alarms, dead letter queues, timeout, and stages
- ~500ms debounce for responsive feedback without performance impact

### Semantic Validation

Cross-state validation matching `rsf validate` output:

- State reference resolution (Next, Default, Catch.Next)
- Reachability analysis (BFS from StartAt)
- Terminal state verification (Succeed, Fail, or End: true)
- States.ALL ordering in Retry/Catch arrays
- Recursive validation for Parallel branches and Map ItemProcessor

### Go-to-Definition

Press F12 or Ctrl+Click on a state name in Next, Default, or Catch fields to jump to the state's definition.

Additional navigation features:
- **Find All References** (Shift+F12): See everywhere a state is referenced
- **Document Highlights**: Clicking a state highlights its definition and all references
- **Autocomplete**: State name suggestions when typing in Next/Default fields
- **Quick Fix**: "Did you mean X?" suggestions for typo'd state names

### Graph Preview

Open a side panel showing a live graph preview of your workflow:

- **Command**: `RSF: Open Graph Preview` (Ctrl+Shift+V)
- Updates in real-time as you edit
- Pan (mouse drag) and zoom (scroll wheel)
- Click a node to jump to its YAML definition
- Error states highlighted with red borders

## Installation

Search for "RSF Workflows" in the VS Code Extensions sidebar, or install from the [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=rsf-workflows.rsf-workflows).

No local RSF installation required — all validation runs in the extension.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `rsf.validation.enabled` | `true` | Enable/disable real-time validation |
| `rsf.validation.debounce` | `500` | Debounce delay (ms) before validation runs |

## Requirements

- VS Code 1.85.0 or later
- Files must be named `workflow.yaml` or `workflow.yml`
