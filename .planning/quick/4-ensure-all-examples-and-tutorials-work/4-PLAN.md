---
phase: quick-4
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - src/rsf/cli/templates/api-gateway-crud/workflow.yaml
  - src/rsf/cli/templates/s3-event-pipeline/workflow.yaml
  - src/rsf/cli/test_cmd.py
  - tutorials/01-project-setup.md
  - tutorials/03-code-generation.md
  - tutorials/04-deploy-to-aws.md
  - tutorials/05-iterate-invoke-teardown.md
  - tutorials/06-asl-import.md
  - tutorials/08-execution-inspector.md
  - tutorials/09-custom-provider-registry-modules.md
autonomous: true
must_haves:
  truths:
    - "rsf init creates a project that passes rsf validate and rsf generate"
    - "rsf init -t api-gateway-crud creates a project that passes rsf validate"
    - "rsf init -t s3-event-pipeline creates a project that passes rsf validate"
    - "rsf test works on all 7 examples without duplicate handler errors"
    - "All 7 examples pass their local pytest test suites"
    - "Tutorial docs reference correct file paths matching rsf init output"
  artifacts:
    - path: "src/rsf/cli/templates/api-gateway-crud/workflow.yaml"
      provides: "Valid workflow without Handler field"
    - path: "src/rsf/cli/templates/s3-event-pipeline/workflow.yaml"
      provides: "Valid workflow without Handler field"
    - path: "src/rsf/cli/test_cmd.py"
      provides: "Handler loading that checks src/handlers/ then handlers/"
  key_links:
    - from: "src/rsf/cli/test_cmd.py"
      to: "examples/*/handlers/"
      via: "_load_handler path resolution"
      pattern: "handler_path.*=.*handlers"
---

<objective>
Fix all broken examples and tutorials so they work end-to-end with the current RSF CLI.

Purpose: Users following tutorials or running examples hit validation errors, duplicate handler registration, and outdated path references. These failures make the project look broken on first contact.

Output: All examples pass `rsf validate`, `rsf generate`, `rsf test`, and `pytest`; tutorials reference correct paths; init templates produce valid projects.
</objective>

<execution_context>
@/home/esa/.claude/get-shit-done/workflows/execute-plan.md
@/home/esa/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

Key findings from investigation:

1. TEMPLATE VALIDATION FAILURES: Both `api-gateway-crud` and `s3-event-pipeline` templates use
   an invalid `Handler:` field in Task states (e.g. `Handler: handlers/create_item.py`).
   RSF does NOT support a Handler field in workflow YAML -- handler discovery uses the `@state`
   decorator in Python files. `rsf validate` and `rsf generate` fail with
   "Task.Handler: Extra inputs are not permitted".

2. DUPLICATE HANDLER DIRECTORIES: 6 of 7 examples (all except registry-modules-demo) have BOTH
   `handlers/` (old root-level) and `src/handlers/` (new structure) with identical handler .py
   files. This causes `rsf test` to crash with "Duplicate handler for state 'X': already registered"
   because both directories get imported. The `handlers/` directory is the canonical location used
   by `rsf test` (test_cmd.py line 134). The `src/handlers/` directory is used by the generated
   orchestrator for Lambda deployment. The root `handlers/` files are the ones actually used by
   tests (conftest.py imports from `handlers/`).

3. TUTORIAL PATH DISCREPANCIES: `rsf init` now generates `src/handlers/` and `src/generated/`
   but all 9 tutorials reference the old `handlers/` path. Tutorial 01 shows an outdated
   `rsf init` output and directory structure.

4. `rsf test` HANDLER RESOLUTION: `_load_handler()` in test_cmd.py hardcodes
   `workflow_dir / "handlers"` (line 134). This works with the old layout and the examples'
   root `handlers/` dir, but NOT with `rsf init`'s new `src/handlers/` output. Need to check
   `src/handlers/` first, falling back to `handlers/`.

5. TEMPLATES CREATE OLD STRUCTURE: The template scaffolding creates `handlers/` not `src/handlers/`.
   This is actually a separate issue from the templates' invalid Handler field. The templates
   themselves are in `src/rsf/cli/templates/{name}/handlers/`.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix template workflows and rsf test handler resolution</name>
  <files>
    src/rsf/cli/templates/api-gateway-crud/workflow.yaml
    src/rsf/cli/templates/s3-event-pipeline/workflow.yaml
    src/rsf/cli/test_cmd.py
  </files>
  <action>
1. Fix `src/rsf/cli/templates/api-gateway-crud/workflow.yaml`:
   - Remove all `Handler:` lines from Task states. RSF discovers handlers via `@state` decorator,
     not YAML references. The handler file names are derived from the state name (PascalCase ->
     snake_case.py). Valid Task states just have Type, Next, and optionally Parameters/Retry/Catch/etc.
   - Verify the workflow validates after changes: `rsf validate` from a temp init.

2. Fix `src/rsf/cli/templates/s3-event-pipeline/workflow.yaml`:
   - Same fix: remove all `Handler:` lines from Task states.
   - Note: `NotifyFailure` state reuses `handlers/notify_complete.py` via Handler field. Since RSF
     uses `@state` decorator matching by state name, NotifyFailure needs its own handler file.
     Either: (a) create a `handlers/notify_failure.py` in the template that reuses the notify logic,
     or (b) rename the state to reuse NotifyComplete handler. Option (a) is cleaner -- add a
     `notify_failure.py` handler stub to `src/rsf/cli/templates/s3-event-pipeline/handlers/`.

3. Fix `src/rsf/cli/test_cmd.py` `_load_handler()` function (around line 131-153):
   - Change handler path resolution to check `src/handlers/` first, then fall back to `handlers/`.
   - This makes `rsf test` work with both the new `rsf init` layout (src/handlers/) and existing
     examples (handlers/).
   - The change: try `workflow_dir / "src" / "handlers" / f"{module_name}.py"` first; if not found,
     try `workflow_dir / "handlers" / f"{module_name}.py"`. Use whichever exists. If neither exists,
     raise the existing FileNotFoundError with both paths mentioned.

4. Verify both template workflows validate:
   ```bash
   cd /tmp && rm -rf tmpl-verify
   rsf init -t api-gateway-crud tmpl-verify-api
   cd tmpl-verify-api && rsf validate workflow.yaml
   cd /tmp && rsf init -t s3-event-pipeline tmpl-verify-s3
   cd tmpl-verify-s3 && rsf validate workflow.yaml
   rm -rf /tmp/tmpl-verify-api /tmp/tmpl-verify-s3
   ```

5. Verify `rsf test` works on examples after handler resolution fix:
   ```bash
   cd examples/approval-workflow && rsf test workflow.yaml
   cd examples/order-processing && rsf test workflow.yaml
   ```
  </action>
  <verify>
    <automated>cd /tmp && rm -rf tmpl-v && rsf init -t api-gateway-crud tmpl-v-api && cd tmpl-v-api && rsf validate workflow.yaml && cd /tmp && rsf init -t s3-event-pipeline tmpl-v-s3 && cd tmpl-v-s3 && rsf validate workflow.yaml && rm -rf /tmp/tmpl-v-api /tmp/tmpl-v-s3 && cd /home/esa/git/rsf-python && python3 -m pytest tests/test_cli/test_init.py tests/test_cli/test_init_templates.py tests/test_cli/test_validate.py -q --tb=short</automated>
  </verify>
  <done>
    - Both init templates produce valid workflows that pass `rsf validate`
    - `rsf test` can find handlers in both `src/handlers/` and `handlers/` layouts
    - Existing CLI tests still pass
  </done>
</task>

<task type="auto">
  <name>Task 2: Remove duplicate handler directories from examples and update tutorials</name>
  <files>
    examples/approval-workflow/src/handlers/
    examples/data-pipeline/src/handlers/
    examples/intrinsic-showcase/src/handlers/
    examples/lambda-url-trigger/src/handlers/
    examples/order-processing/src/handlers/
    examples/retry-and-recovery/src/handlers/
    tutorials/01-project-setup.md
    tutorials/03-code-generation.md
    tutorials/04-deploy-to-aws.md
    tutorials/05-iterate-invoke-teardown.md
    tutorials/06-asl-import.md
    tutorials/08-execution-inspector.md
    tutorials/09-custom-provider-registry-modules.md
  </files>
  <action>
1. Remove `src/handlers/` directories from 6 examples that have BOTH `handlers/` and `src/handlers/`:
   - approval-workflow, data-pipeline, intrinsic-showcase, lambda-url-trigger, order-processing,
     retry-and-recovery
   - Keep the root `handlers/` directory (canonical location used by conftest.py and rsf test)
   - Keep `src/generated/` directory (used by orchestrator for Lambda deployment)
   - The `src/handlers/` contained identical copies of the handler files plus auto-generated
     `__init__.py` imports. These imports are unnecessary because the conftest.py discovers
     handlers via `rsf.registry.discover_handlers(HANDLERS_DIR)` pointing to root `handlers/`.
   - Do NOT touch registry-modules-demo (it only has root `handlers/`, no `src/handlers/`)

2. Update tutorials to reference correct `src/handlers/` paths matching current `rsf init` output.
   The tutorials describe the `rsf init` experience for NEW users, so they should match what
   `rsf init` actually produces:

   **Tutorial 01 (01-project-setup.md):**
   - Update the `rsf init` output block (lines ~53-65) to show `src/handlers/` and `src/generated/`
   - Update the directory tree (lines ~85-95) to show `src/handlers/` and `src/generated/`
   - Update section "handlers/example_handler.py" heading and references to `src/handlers/`
   - Update section "handlers/__init__.py" heading and references to `src/handlers/`
   - Update the pip install editable mode note about importing from handlers

   **Tutorial 03 (03-code-generation.md):**
   - Update all `handlers/` references to `src/handlers/` in rsf generate output, directory trees,
     file references, and explanations
   - Update "Skipped: handlers/X" output lines to "Skipped: src/handlers/X"

   **Tutorial 04 (04-deploy-to-aws.md):**
   - Update directory tree to show `src/handlers/` structure

   **Tutorial 05 (05-iterate-invoke-teardown.md):**
   - Update `handlers/validate_order.py` references to `src/handlers/validate_order.py`

   **Tutorial 06 (06-asl-import.md):**
   - Update `handlers/` references in import output, ls commands, cat commands, and explanations
   - Note: rsf import may still create handlers/ at root -- check actual behavior and match docs

   **Tutorial 08 (08-execution-inspector.md):**
   - Update `handlers/` file references to `src/handlers/`

   **Tutorial 09 (09-custom-provider-registry-modules.md):**
   - Update `handlers/` references to `src/handlers/` where applicable

   IMPORTANT: Be careful with context. The tutorials describe NEW project setup via `rsf init`.
   The existing examples use root `handlers/` (legacy layout that still works). The tutorials
   should match what `rsf init` actually creates, which is `src/handlers/`.

   However, check `rsf generate` and `rsf import` actual behavior first -- if they output to
   `src/handlers/` then update docs. If they still output to `handlers/`, keep docs matching
   actual output. Run:
   ```bash
   cd /tmp && rsf init test-check && cd test-check && rsf generate workflow.yaml --no-infra
   ```
   to see actual paths in output.

3. Verify no example tests broke:
   ```bash
   for d in examples/*/; do pytest "$d/tests/test_local.py" -q; done
   ```
  </action>
  <verify>
    <automated>cd /home/esa/git/rsf-python && for d in examples/*/; do python3 -m pytest "$d/tests/" -q --tb=short || exit 1; done && echo "ALL EXAMPLE TESTS PASS"</automated>
  </verify>
  <done>
    - No example has both `handlers/` and `src/handlers/` (no duplicate registration)
    - `rsf test` works on all examples without "Duplicate handler" errors
    - All 7 example test suites pass
    - Tutorial docs reference paths that match actual `rsf init` output
  </done>
</task>

<task type="auto">
  <name>Task 3: End-to-end verification of full rsf workflow on all examples</name>
  <files></files>
  <action>
Run full verification across all examples and templates:

1. Test all examples with `rsf validate`:
   ```bash
   for d in examples/*/; do rsf validate "$d/workflow.yaml" || exit 1; done
   ```

2. Test all examples with `rsf generate --no-infra`:
   ```bash
   for d in examples/*/; do
     (cd "$d" && rsf generate workflow.yaml --no-infra) || exit 1
   done
   ```

3. Test `rsf test` on all examples (except registry-modules-demo which needs special input):
   ```bash
   for d in examples/approval-workflow examples/data-pipeline examples/intrinsic-showcase \
            examples/lambda-url-trigger examples/order-processing examples/retry-and-recovery; do
     (cd "$d" && rsf test workflow.yaml) || echo "WARN: rsf test failed in $d"
   done
   ```

4. Test full init + validate + generate cycle for all templates:
   ```bash
   cd /tmp
   # Default template
   rsf init verify-default && cd verify-default && rsf validate && rsf generate --no-infra && cd /tmp
   # API template
   rsf init -t api-gateway-crud verify-api && cd verify-api && rsf validate && rsf generate --no-infra && cd /tmp
   # S3 template
   rsf init -t s3-event-pipeline verify-s3 && cd verify-s3 && rsf validate && rsf generate --no-infra && cd /tmp
   rm -rf verify-default verify-api verify-s3
   ```

5. Run the project example tests (non-integration):
   ```bash
   cd /home/esa/git/rsf-python
   python3 -m pytest tests/test_examples/ -q --tb=short -m "not integration"
   ```

6. Run all example local tests one final time:
   ```bash
   for d in examples/*/; do python3 -m pytest "$d/tests/" -q --tb=short || exit 1; done
   ```

If any step fails, diagnose and fix before proceeding. This task is verification-only -- all
fixes should already be done in Tasks 1 and 2.
  </action>
  <verify>
    <automated>cd /home/esa/git/rsf-python && for d in examples/*/; do rsf validate "$d/workflow.yaml" || exit 1; done && for d in examples/*/; do (cd "$d" && rsf generate workflow.yaml --no-infra) || exit 1; done && for d in examples/*/; do python3 -m pytest "$d/tests/" -q --tb=short || exit 1; done && python3 -m pytest tests/test_examples/ -q --tb=short -m "not integration" && echo "ALL VERIFICATIONS PASS"</automated>
  </verify>
  <done>
    - All 7 examples pass rsf validate, rsf generate, and pytest
    - All 3 init templates (default, api-gateway-crud, s3-event-pipeline) produce valid projects
    - No duplicate handler registration errors anywhere
    - tests/test_examples/ non-integration tests pass
  </done>
</task>

</tasks>

<verification>
- `rsf validate` succeeds on all 7 example workflow.yaml files
- `rsf generate --no-infra` succeeds on all 7 examples
- `rsf test` succeeds on 6 examples (registry-modules-demo excluded -- custom provider)
- All 7 example pytest suites pass (195+ total tests)
- Both init templates produce valid, validateable, generatable projects
- `rsf init` default template works end-to-end
- No example has both handlers/ and src/handlers/ directories
- Tutorial paths match actual rsf init output
</verification>

<success_criteria>
- Zero validation errors across all examples and templates
- Zero duplicate handler registration errors
- All 195+ example tests pass
- Tutorials reference correct file paths for current rsf init layout
</success_criteria>

<output>
After completion, create `.planning/quick/4-ensure-all-examples-and-tutorials-work/4-SUMMARY.md`
</output>
