# Phase 46: Inspector Replay and SchemaStore - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can replay any past execution from the inspector UI with the same or modified payload, and RSF's workflow.yaml JSON Schema is published to SchemaStore for automatic IDE auto-complete. This phase delivers two capabilities: (1) execution replay from the inspector, and (2) SchemaStore publication with bundled CLI export.

</domain>

<decisions>
## Implementation Decisions

### Replay trigger & flow
- Replay button in the ExecutionHeader bar, next to the status badge
- Only available for terminal execution statuses (SUCCEEDED, FAILED, TIMED_OUT, STOPPED)
- Click Replay opens a modal dialog with the pre-filled payload editor
- Replay always targets the same Lambda function as the original execution

### Payload editor
- Pre-filled with the original execution's input_payload
- Syntax validation (valid JSON check) before allowing Execute
- Execute button disabled until JSON is valid

### Post-replay behavior
- After successful Execute: close modal, add new execution to the list, auto-navigate to it
- SSE stream auto-connects to the new execution for live progress monitoring
- New execution shows a "Replay" badge/indicator in the execution list with lineage to the original
- On invocation failure: show error in the modal, keep it open so user can fix payload and retry

### Schema file matching & distribution
- JSON Schema published to SchemaStore AND bundled in the RSF Python package
- CLI command (`rsf schema export` or similar) to export the schema locally for offline use
- Schema $id uses GitHub raw URL (no custom domain needed)

### Claude's Discretion
- JSON editor implementation choice (Monaco, textarea, or lightweight alternative) — balance bundle size vs UX
- Whether to show a diff view between original and edited payload
- How to handle null/empty input_payload in the editor (empty object vs blank)
- SchemaStore filename patterns (workflow.yaml only vs broader matching)
- Whether to meta-validate the generated schema against the JSON Schema meta-schema
- Exact replay badge design and lineage display format
- Loading states and animations during replay invocation

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ExecutionHeader` (ui/src/inspector/ExecutionHeader.tsx): Natural location for the Replay button — already shows status badge, timing, and execution ID
- `ExecutionDetail` model (src/rsf/inspect/models.py): Has `input_payload` field for pre-filling the replay editor
- `inspectStore` (ui/src/store/inspectStore.ts): Zustand store with `selectExecution`, `setExecutionDetail` — can be extended for replay state
- `useSSE` hook (ui/src/inspector/useSSE.ts): Auto-connects SSE stream when `selectedExecutionId` changes — replay auto-streams for free
- `generate_json_schema()` (src/rsf/schema/generate.py): Already generates Draft 2020-12 JSON Schema from `StateMachineDefinition` Pydantic model
- `write_json_schema()` (src/rsf/schema/generate.py): Already writes schema to file — extend for CLI export command
- `TERMINAL_STATUSES` (src/rsf/inspect/models.py): Frozenset of terminal statuses — use to gate Replay button visibility

### Established Patterns
- FastAPI APIRouter for backend endpoints — replay endpoint follows same pattern
- boto3 with `asyncio.to_thread` for AWS API calls — replay invocation uses same wrapper
- `TokenBucketRateLimiter` for rate limiting Lambda API calls — replay invocations should respect this
- Zustand + immer for frontend state management — replay modal state follows same pattern
- SSE streaming for live execution updates — new execution auto-streams via existing `useSSE`

### Integration Points
- New POST endpoint needed in `src/rsf/inspect/router.py` for replay invocation
- New `invoke_execution` method needed on `LambdaInspectClient` (src/rsf/inspect/client.py)
- Replay modal component added to `ui/src/inspector/` directory
- Schema export CLI command added alongside existing CLI commands in `src/rsf/cli/`
- SchemaStore catalog entry requires PR to github.com/SchemaStore/schemastore

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 46-inspector-replay-and-schemastore*
*Context gathered: 2026-03-02*
