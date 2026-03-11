---
phase: quick-12
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - ui/src/store/flowStore.ts
  - ui/src/App.tsx
  - ui/src/index.css
  - ui/src/test/flowStore.test.ts
  - src/rsf/editor/static/index.html
  - src/rsf/editor/static/assets/index-BigKWUMt.js
  - src/rsf/editor/static/assets/index-By6Nq0QI.css
autonomous: true
requirements: [QUICK-12]

must_haves:
  truths:
    - "Header shows 'Saved' indicator (green) when yamlContent matches last-saved YAML"
    - "Header shows 'Unsaved' indicator (warning color) when yamlContent differs from last-saved YAML"
    - "Pressing Ctrl+S (or Cmd+S on Mac) saves current YAML to disk via WebSocket save_file message"
    - "After successful save, indicator switches from Unsaved to Saved"
    - "On initial file load, state is marked as saved (not dirty)"
  artifacts:
    - path: "ui/src/store/flowStore.ts"
      provides: "savedYaml, filePath state + markSaved/setFilePath actions"
    - path: "ui/src/App.tsx"
      provides: "Ctrl+S handler, file_saved response handler, save indicator in header"
    - path: "ui/src/index.css"
      provides: "Styles for save-status indicator"
  key_links:
    - from: "ui/src/App.tsx"
      to: "websocket save_file message"
      via: "Ctrl+S keydown handler calls send({ type: 'save_file', path, yaml })"
      pattern: "save_file"
    - from: "ui/src/App.tsx"
      to: "ui/src/store/flowStore.ts"
      via: "file_saved response calls markSaved, file_loaded sets savedYaml+filePath"
      pattern: "markSaved|savedYaml|filePath"
---

<objective>
Add a saved/unsaved visual indicator to the RSF Graph Editor header, with Ctrl+S to save.

Purpose: Users currently have no way to know if their workflow changes have been persisted to disk, and no keyboard shortcut to trigger a save. This adds both.

Output: Updated UI with save indicator in header, Ctrl+S save shortcut, and rebuilt static assets.
</objective>

<execution_context>
@/Users/esa/.claude/get-shit-done/workflows/execute-plan.md
@/Users/esa/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@ui/src/store/flowStore.ts
@ui/src/App.tsx
@ui/src/index.css
@ui/src/types/index.ts
@ui/src/sync/useWebSocket.ts
@src/rsf/editor/websocket.py
@ui/src/test/flowStore.test.ts
</context>

<interfaces>
<!-- Key types and contracts the executor needs. -->

From ui/src/types/index.ts:
```typescript
export interface FileSavedResponse {
  type: 'file_saved';
  path: string;
}

export interface FileLoadedResponse {
  type: 'file_loaded';
  yaml: string;
  path: string;
}

export interface SaveFileMessage {
  type: 'save_file';
  path: string;
  yaml: string;
}
```

From src/rsf/editor/websocket.py (save_file handler):
```python
# Accepts: { type: "save_file", path: str, yaml: str }
# Returns: { type: "file_saved", path: str }
```

From ui/src/App.tsx (handleMessage switch):
```typescript
// Currently handles: parsed, validated, file_loaded, schema, error
// Does NOT handle: file_saved (needs to be added)
```

From ui/src/store/flowStore.ts (FlowState interface):
```typescript
// Current state includes: yamlContent, syncSource, nodes, edges, etc.
// Needs: savedYaml (string), filePath (string | null), markSaved(), setFilePath()
```
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Add save tracking state to flowStore and wire save/load in App.tsx</name>
  <files>ui/src/store/flowStore.ts, ui/src/App.tsx, ui/src/index.css, ui/src/test/flowStore.test.ts</files>
  <action>
**flowStore.ts changes:**
1. Add to FlowState interface:
   - `savedYaml: string` — the YAML content as of the last save or load (initialized to `''`)
   - `filePath: string | null` — the file path being edited (initialized to `null`)
   - `markSaved: () => void` — action: sets `savedYaml = yamlContent`
   - `setFilePath: (path: string | null) => void` — action: sets `filePath`
2. Add initial values: `savedYaml: ''`, `filePath: null`
3. Add action implementations:
   - `markSaved: () => set((state) => { state.savedYaml = state.yamlContent; })`
   - `setFilePath: (path) => set({ filePath: path })`

**App.tsx changes:**
1. In `EditorApp`, subscribe to new store fields:
   - `const filePath = useFlowStore((s) => s.filePath);`
   - `const yamlContent = useFlowStore((s) => s.yamlContent);`
   - `const savedYaml = useFlowStore((s) => s.savedYaml);`
   - `const markSaved = useFlowStore((s) => s.markSaved);`
   - `const setFilePath = useFlowStore((s) => s.setFilePath);`
   - Derive: `const isDirty = yamlContent !== savedYaml;`

2. In the `handleMessage` callback, update `file_loaded` case to also set filePath and savedYaml:
   ```typescript
   case 'file_loaded':
     setSyncSource('editor');
     setYamlContent(response.yaml);
     setFilePath(response.path);
     // Mark as saved since this is the on-disk state
     useFlowStore.setState({ savedYaml: response.yaml });
     break;
   ```

3. Add `file_saved` case to handleMessage:
   ```typescript
   case 'file_saved':
     markSaved();
     break;
   ```

4. Add Ctrl+S / Cmd+S keyboard handler via useEffect:
   ```typescript
   useEffect(() => {
     const handleKeyDown = (e: KeyboardEvent) => {
       if ((e.ctrlKey || e.metaKey) && e.key === 's') {
         e.preventDefault();
         const { filePath, yamlContent } = useFlowStore.getState();
         if (filePath) {
           send({ type: 'save_file', path: filePath, yaml: yamlContent });
         }
       }
     };
     window.addEventListener('keydown', handleKeyDown);
     return () => window.removeEventListener('keydown', handleKeyDown);
   }, [send]);
   ```

5. Add save status indicator in the header, between the h1 and header-right div:
   ```tsx
   <span className={`save-status ${isDirty ? 'unsaved' : 'saved'}`}>
     {isDirty ? 'Unsaved' : 'Saved'}
   </span>
   ```

6. Also add a save button next to the indicator for discoverability (only enabled when dirty and filePath exists):
   ```tsx
   {filePath && isDirty && (
     <button
       className="save-btn"
       onClick={() => send({ type: 'save_file', path: filePath, yaml: yamlContent })}
     >
       Save
     </button>
   )}
   ```
   Place the save-status and save-btn together in a `<div className="save-controls">` between h1 and header-right.

**index.css changes:**
Add styles after the existing `.app-header h1` block:
```css
/* Save status indicator */
.save-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.save-status {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 3px;
}

.save-status.saved {
  color: var(--success);
}

.save-status.unsaved {
  color: var(--warning);
}

.save-btn {
  padding: 2px 10px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}

.save-btn:hover {
  background: #3a7bc8;
}
```

**flowStore.test.ts changes:**
Add test cases for the new state and actions:
- Test initial values: `savedYaml` is `''`, `filePath` is `null`
- Test `markSaved`: sets `savedYaml` to current `yamlContent`
- Test `setFilePath`: sets `filePath`
- Test dirty detection: `yamlContent !== savedYaml` after content change
- Add `savedYaml: ''` and `filePath: null` to the `resetStore()` function
  </action>
  <verify>
    <automated>cd /Users/esa/git/rsf-python/ui && npx vitest run</automated>
  </verify>
  <done>
    - flowStore has savedYaml, filePath state with markSaved/setFilePath actions
    - App.tsx handles file_saved response, sets savedYaml on file_loaded, has Ctrl+S handler
    - Header shows Saved/Unsaved indicator with appropriate colors
    - Save button appears when dirty and filePath is set
    - All existing + new tests pass
  </done>
</task>

<task type="auto">
  <name>Task 2: Build and deploy static assets</name>
  <files>src/rsf/editor/static/index.html, src/rsf/editor/static/assets/*</files>
  <action>
Run the UI build to compile the React app into the static assets served by the FastAPI backend:

```bash
cd /Users/esa/git/rsf-python/ui && npm run build
```

This compiles TypeScript, bundles with Vite, and outputs to `src/rsf/editor/static/` (configured in vite.config.ts `build.outDir`).

Verify the build succeeds with no errors and the output directory contains updated files.
  </action>
  <verify>
    <automated>cd /Users/esa/git/rsf-python/ui && npm run build 2>&1 | tail -5</automated>
  </verify>
  <done>
    - Build completes without errors
    - src/rsf/editor/static/ contains updated index.html and assets
    - The built app includes the save indicator and Ctrl+S functionality
  </done>
</task>

</tasks>

<verification>
1. `cd ui && npx vitest run` — all tests pass including new save-tracking tests
2. `cd ui && npm run build` — build succeeds
3. Manual: run `rsf ui workflow.yaml`, edit YAML, observe "Unsaved" indicator, press Ctrl+S, observe "Saved" indicator
</verification>

<success_criteria>
- Header displays "Saved" (green) when workflow matches disk, "Unsaved" (yellow/warning) when modified
- Ctrl+S / Cmd+S triggers save via WebSocket save_file message
- file_saved response updates indicator to Saved
- file_loaded on connect sets initial state as Saved
- Save button visible only when there are unsaved changes
- All vitest tests pass
- Static assets rebuilt successfully
</success_criteria>

<output>
After completion, create `.planning/quick/12-add-saved-unsaved-indicator-to-rsf-ui-fo/12-SUMMARY.md`
</output>
