---
phase: 20
phase_name: Advanced Tools
status: passed
verified: 2026-02-26
requirements_verified: [MIGR-01, VIS-01, VIS-02, VIS-03]
---

# Phase 20: Advanced Tools — Verification Report

## Goal
Users can migrate existing ASL workflows to RSF, visually edit workflows in the graph editor, and inspect live executions with time machine debugging.

## Must-Have Verification

### 1. rsf import tutorial (MIGR-01)
**Criteria:** User can follow the rsf import tutorial, provide a real ASL JSON file, and receive RSF YAML + handler stubs they can immediately validate and generate from.
**Status:** PASSED
**Evidence:**
- `tutorials/06-asl-import.md` exists (277 lines, min 200)
- Tutorial provides complete sample ASL JSON (order-processing.asl.json)
- Shows `rsf import` command with exact expected output including 3 Resource removal warnings
- Reviews generated YAML with `rsf_version: "1.0"` injection and Resource field removal
- Reviews handler stubs with `@state` decorator explanation
- Runs `rsf validate` to confirm imported YAML passes validation
- Runs `rsf generate` to confirm immediate pipeline integration
- Documents all 5 conversion rules in reference section

### 2. rsf ui graph editor tutorial (VIS-01)
**Criteria:** User can follow the rsf ui tutorial, launch the graph editor, make a visual change to a workflow, and see the YAML update in the Monaco editor in real time.
**Status:** PASSED
**Evidence:**
- `tutorials/07-graph-editor.md` exists (266 lines, min 180)
- Covers `rsf ui` launch with expected terminal output
- Two-panel layout described: graph view + Monaco YAML editor
- Step 3: YAML edit (add SendConfirmation state) → graph updates
- Step 4: Graph edit (rename state) → YAML updates
- Bidirectional sync demonstrated in both directions
- Validation errors shown (remove StartAt → red indicator → fix)
- Save to disk via Save button
- Command reference table (--port, --no-browser, workflow path)

### 3. Inspection workflow deployment (VIS-02)
**Criteria:** User can follow the inspection workflow tutorial, deploy the dedicated inspection workflow to AWS using the provided Terraform, and have a running target for the inspector.
**Status:** PASSED
**Evidence:**
- `tutorials/08-execution-inspector.md` exists (441 lines, min 280)
- Steps 1-2: Create inspection workflow with 4 Task states + 1 Choice + handler implementations
- Step 3: Deploy with `rsf deploy --auto-approve`
- Step 4: Two invocations triggering different Choice branches (quality_score 85 vs 60)
- Cost warning included

### 4. rsf inspect tutorial (VIS-03)
**Criteria:** User can follow the rsf inspect tutorial, attach to a live execution, scrub through historical execution states with the time machine, and observe structural data diffs between steps.
**Status:** PASSED
**Evidence:**
- Step 5: Launch `rsf inspect` with ARN auto-discovery from Terraform state
- Step 6: Execution list with status descriptions
- Step 7: Time machine scrubber walkthrough with step-by-step data at each event
- Data diff view showing structural changes (FetchData → TransformData → PublishResults)
- Step 8: Compare different execution paths (quality pass vs flagged)
- Step 9: Live SSE streaming for running executions
- Step 10: Teardown with `terraform destroy` and ResourceNotFoundException verification
- Tutorial series summary table

## Requirements Cross-Reference

| Requirement | Plan | Artifact | Status |
|-------------|------|----------|--------|
| MIGR-01 | 20-01 | tutorials/06-asl-import.md | Verified |
| VIS-01 | 20-02 | tutorials/07-graph-editor.md | Verified |
| VIS-02 | 20-03 | tutorials/08-execution-inspector.md (Steps 1-4) | Verified |
| VIS-03 | 20-03 | tutorials/08-execution-inspector.md (Steps 5-10) | Verified |

## Score

**4/4 must-haves verified.**

## Conclusion

Phase 20: Advanced Tools is complete. All four requirements are satisfied by the three tutorial documents. The tutorials follow established conventions (prerequisites, numbered steps, fenced code blocks, blockquotes for tips, forward pointers) and cover the complete advanced tools workflow.
