# Phase 63: Complete Property Editors and Validation Enforcement - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Every state type has a correct, complete property editor matching its Pydantic model fields. Required fields are visually marked and enforced. Mutually exclusive fields use radio group selectors. Requirements: EDIT-04, EDIT-05, EDIT-06. Phase 62 delivered Task/Pass/Wait editors and the expand/collapse infrastructure. This phase completes the remaining 5 state types, adds required-field validation, converts mutual-exclusion fields to radio groups, and adds I/O processing fields to all applicable types.

</domain>

<decisions>
## Implementation Decisions

### Required field indicators
- Red asterisk after label text for required fields (e.g., "Resource *")
- Empty required fields get a red border
- Collapse is blocked when a required field is empty — chevron click does nothing, empty required fields highlight with red border + brief shake animation
- Only Pydantic-required fields (no default in model) are marked required — not "practically useful" fields
- For radio groups: the active radio option's input gets a red asterisk to indicate the selected value is required

### Radio group selectors (mutual exclusion)
- All mutually exclusive field pairs/groups use the same radio pattern across all state types
- **Wait state:** 4 radio buttons with inline inputs — Seconds, Timestamp, SecondsPath, TimestampPath. Selecting one enables its input and grays out/disables others
- **Task state:** TimeoutSeconds/TimeoutSecondsPath as a radio pair; HeartbeatSeconds/HeartbeatSecondsPath as another radio pair
- **Fail state:** Error/ErrorPath as a radio pair; Cause/CausePath as another radio pair
- Switching radio selection clears the old value from YAML immediately — only one value exists at a time, matching the Pydantic validator constraint

### Complex nested fields
- Read-only summary + "edit in YAML" hint for complex array/object fields:
  - Choice rules: "3 rules (edit in YAML)"
  - Parallel branches: "2 branches (edit in YAML)"
  - Retry policies: "2 policies (edit in YAML)"
  - Catch handlers: "1 catcher (edit in YAML)"
  - ItemProcessor: summary + "edit in YAML"
- Simple scalar fields (Comment, Default, MaxConcurrency, ItemsPath, etc.) get normal editable inputs

### State type migration to BaseNode
- ChoiceNode, SucceedNode, and FailNode must be refactored to use BaseNode (currently have custom layouts without expand/collapse)
- This gives them the chevron toggle, accordion behavior, and expandedContent slot
- ParallelNode and MapNode already use BaseNode — just need expandedContent added

### Field completeness
- All Pydantic model fields shown for every state type — "no missing fields, no extra fields"
- Succeed: Comment, I/O Processing section, Assign, Output, QueryLanguage — all visible
- Fail: Comment, Error/ErrorPath (radio), Cause/CausePath (radio), QueryLanguage
- Choice: Comment, Default (text input), Choices (read-only summary), I/O fields, Assign, Output, QueryLanguage
- Parallel: Comment, Branches (read-only summary), Retry (read-only), Catch (read-only), End toggle, I/O fields, QueryLanguage
- Map: Comment, ItemProcessor (read-only), ItemsPath (text), MaxConcurrency (number), ItemSelector (read-only), Retry (read-only), Catch (read-only), End toggle, I/O fields, QueryLanguage

### I/O processing fields
- Collapsible "I/O Processing" sub-section within the expanded node editor
- Click to expand/collapse independently of the node expansion
- Path fields (InputPath, OutputPath, ResultPath) are simple text inputs
- JSON/dict fields (Parameters, ResultSelector, Assign, Output) shown as read-only summary + "edit in YAML" hint (e.g., "Parameters: {3 keys} (edit in YAML)")
- QueryLanguage included in the I/O Processing section as text input
- Applies to all state types that have I/O fields in their Pydantic model

### Claude's Discretion
- Exact CSS for red asterisk, red border, shake animation
- Collapsible I/O section toggle design (chevron, arrow, +/- icon)
- Radio button styling (native vs custom styled)
- Read-only summary badge styling for complex fields
- Field ordering within each state type's editor
- How to display "edit in YAML" hint (tooltip, inline text, icon)

</decisions>

<specifics>
## Specific Ideas

- Radio group pattern should be consistent across Wait, Task, and Fail — same visual language for all mutual-exclusion fields
- The existing Task/Pass/Wait editors from Phase 62 need to be updated (Task gets radio pairs for Timeout/Heartbeat, Wait gets full radio group, all three get I/O Processing section)
- "Edit in YAML" hints should be non-intrusive — the YAML editor is always visible in the split view

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BaseNode.tsx`: Expand/collapse infrastructure with `expandedContent` prop — all 8 types will use this
- `TaskNode.tsx`, `WaitNode.tsx`, `PassNode.tsx`: Working property editors with debounced sync + focus guard pattern — extend these
- `flowStore.ts`: `updateStateProperty(nodeId, key, value)` action — works for all field types
- `mergeGraphIntoYaml.ts`: Already writes stateData properties to YAML AST with TRANSITION_MANAGED_KEYS guard
- `rsf-graph-change` CustomEvent: Bridges node components to sync pipeline — all new editors use this

### Established Patterns
- **Zustand + immer** for state — new validation state goes here
- **Debounce 300ms** for text fields, immediate sync for number/boolean
- **Focus guard** via useEffect + document.activeElement check on input refs
- **syncSource flag** prevents infinite YAML<->graph loops
- **Per-type node components** each render in BaseNode's children/expandedContent slots

### Integration Points
- `ChoiceNode.tsx`, `SucceedNode.tsx`, `FailNode.tsx`: Must be refactored to use BaseNode
- `ParallelNode.tsx`, `MapNode.tsx`: Already use BaseNode — add expandedContent
- `TaskNode.tsx`: Add radio pairs for Timeout/Heartbeat, add I/O Processing section
- `WaitNode.tsx`: Convert 4 independent inputs to radio group
- All node components: Add I/O Processing collapsible section
- `flowStore.ts`: May need validation state for collapse-prevention logic

</code_context>

<deferred>
## Deferred Ideas

- Undo/redo for property changes — ADVEDIT-02 (future requirement)
- Inline JSON editor for Parameters/ResultSelector — complex, better left for YAML
- Choice rule condition editing in graph — explicitly out of scope per requirements
- Parallel/Map branch sub-workflow editing — separate milestone per requirements

</deferred>

---

*Phase: 63-complete-property-editors-and-validation-enforcement*
*Context gathered: 2026-03-06*
