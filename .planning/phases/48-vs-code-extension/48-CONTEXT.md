# Phase 48: VS Code Extension - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a VS Code extension that provides YAML schema validation, go-to-definition for state references, and an inline graph preview panel for workflow.yaml files. The extension must be installable from the VS Code Marketplace and work without any local RSF installation.

</domain>

<decisions>
## Implementation Decisions

### Validation feedback
- Real-time validation as the user types (~500ms debounce), not on-save
- Full schema + semantic validation bundled in the extension — must match `rsf validate` output without requiring local RSF installation
- Errors displayed as inline squiggly underlines AND in the VS Code Problems panel
- Hover tooltips show error message with quick fix Code Actions where possible (e.g., "Did you mean 'ProcessOrders'?" for typo'd state names)

### Graph preview panel
- Read-only preview — pan and zoom, no editing in the graph (editing happens in YAML)
- Opens as a side panel (editor column split) like Markdown preview
- Click-to-navigate: clicking a state node in the graph jumps the YAML editor cursor to that state's definition
- States with validation errors get red border/glow highlighting in the graph

### Go-to-definition scope
- Go-to-definition for state names in Next, Default, Catch, Branches fields
- Autocomplete dropdown for state names when typing in Next/Default value fields
- Find All References (Shift+F12) shows everywhere a state is referenced
- Document highlights: clicking a state name highlights its definition and all references in the file

### Extension identity
- Marketplace display name: "RSF Workflows" (ID: rsf-workflows)
- Activates only for files named workflow.yaml or workflow.yml (matches existing SchemaStore entry)
- Minimalist/geometric icon suggesting a workflow graph — clean lines, monochrome or two-tone
- Status bar item showing validation status (checkmark with 0 errors or warning with error count)

### Claude's Discretion
- Graph layout algorithm choice (dagre, elk, or similar)
- Internal architecture (Language Server Protocol vs direct extension API)
- How to bundle/port the Python semantic validator to JS/TS
- Debounce timing and performance optimization
- Exact icon design
- Webview implementation details for graph preview

</decisions>

<specifics>
## Specific Ideas

- Graph preview placement should feel like the built-in Markdown preview experience in VS Code
- Quick fixes for state name typos should suggest closest matching state names
- Status bar validation indicator provides at-a-glance workflow health

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `schemas/rsf-workflow.json`: Generated JSON Schema (Draft 2020-12) from Pydantic models — foundation for YAML schema validation
- `schemas/schemastore-catalog-entry.json`: Already configured for `workflow.yaml`/`workflow.yml` file matching
- `src/rsf/schema/generate.py`: Schema generation from `StateMachineDefinition` Pydantic model via `model_json_schema()`
- `src/rsf/dsl/validator.py`: Semantic validation logic (state references, unreachable states) — needs porting to TS
- `src/rsf/dsl/parser.py` + `src/rsf/dsl/models.py`: Complete DSL models — define all state types and fields
- `ui/src/`: Full React graph editor using `@xyflow/react` (ReactFlow) — graph rendering patterns reusable for webview

### Established Patterns
- WebSocket handler (`src/rsf/editor/websocket.py`) shows the parse/validate/schema protocol already working
- Monaco Editor integration in the web UI (`ui/src/components/MonacoEditor.tsx`) — patterns for schema-aware YAML editing
- `useYamlToGraphSync` and `useGraphToYamlSync` hooks — bidirectional sync between YAML text and graph nodes

### Integration Points
- JSON Schema at `schemas/rsf-workflow.json` can be bundled directly into the extension for schema-level validation
- Semantic validation rules from `src/rsf/dsl/validator.py` need to be reimplemented in TypeScript for the extension
- ReactFlow node/edge patterns from `ui/src/nodes/` and `ui/src/edges/` can inform the webview graph rendering

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 48-vs-code-extension*
*Context gathered: 2026-03-02*
