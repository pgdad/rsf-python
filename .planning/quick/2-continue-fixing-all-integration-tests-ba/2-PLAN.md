---
phase: quick-2
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/test_codegen/test_generator.py
  - tests/test_integration/test_sdk_integration.py
  - tests/test_dsl/test_infra_config.py
  - fixtures/snapshots/order-processing.py.snapshot
  - fixtures/snapshots/data-pipeline.py.snapshot
  - fixtures/snapshots/intrinsic-showcase.py.snapshot
  - fixtures/snapshots/lambda-url-trigger.py.snapshot
  - fixtures/snapshots/approval-workflow.py.snapshot
  - fixtures/snapshots/retry-and-recovery.py.snapshot
autonomous: true
requirements: []
must_haves:
  truths:
    - "All non-AWS-dependent tests pass (0 failures)"
    - "Snapshot golden files match current orchestrator template output"
    - "SDK integration tests use correct module name and argument order"
  artifacts:
    - path: "fixtures/snapshots/*.py.snapshot"
      provides: "Updated golden files reflecting new SDK import and arg order"
    - path: "tests/test_codegen/test_generator.py"
      provides: "Import assertion matching new SDK module name"
    - path: "tests/test_integration/test_sdk_integration.py"
      provides: "Mock SDK with correct module name + correct call arg order"
    - path: "tests/test_dsl/test_infra_config.py"
      provides: "Test comparing against CustomProviderConfig model, not raw dict"
  key_links:
    - from: "src/rsf/codegen/templates/orchestrator.py.j2"
      to: "tests/test_codegen/test_generator.py"
      via: "import string assertion"
      pattern: "aws_durable_execution_sdk_python"
    - from: "src/rsf/codegen/templates/orchestrator.py.j2"
      to: "fixtures/snapshots/*.py.snapshot"
      via: "snapshot golden files"
      pattern: "aws_durable_execution_sdk_python"
---

<objective>
Fix all 16 failing non-integration tests caused by the SDK module rename
(aws_lambda_durable_execution_sdk_python -> aws_durable_execution_sdk_python),
the lambda_handler argument order swap (context,event -> event,context), and
the CustomProviderConfig model coercion change.

Purpose: All local tests pass, unblocking further development.
Output: Updated test files and regenerated snapshot golden files.
</objective>

<execution_context>
@/home/esa/.claude/get-shit-done/workflows/execute-plan.md
@/home/esa/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/rsf/codegen/templates/orchestrator.py.j2
@tests/test_codegen/test_generator.py
@tests/test_integration/test_sdk_integration.py
@tests/test_dsl/test_infra_config.py
@src/rsf/dsl/models.py (CustomProviderConfig class)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix SDK module rename and arg order in test files</name>
  <files>
    tests/test_codegen/test_generator.py,
    tests/test_integration/test_sdk_integration.py,
    tests/test_dsl/test_infra_config.py
  </files>
  <action>
Three distinct fixes across three test files:

1. **tests/test_codegen/test_generator.py** (line 140):
   Change the assertion from:
   `assert "from aws_lambda_durable_execution_sdk_python" in code`
   to:
   `assert "from aws_durable_execution_sdk_python" in code`
   The orchestrator template was renamed from aws_lambda_durable_execution_sdk_python
   to aws_durable_execution_sdk_python in the Jinja2 template.

2. **tests/test_integration/test_sdk_integration.py** — THREE changes:
   a. Lines 51-52: Change mock module name from `aws_lambda_durable_execution_sdk_python`
      to `aws_durable_execution_sdk_python` (the ModuleType name AND sys.modules key).
   b. Lines 55-56: Change config mock module name from
      `aws_lambda_durable_execution_sdk_python.config` to
      `aws_durable_execution_sdk_python.config` (ModuleType name AND sys.modules key).
   c. Lines 58-59: Update sys.modules dict keys accordingly.
   d. Lines 75-76: Update sys.modules.pop() cleanup keys accordingly.
   e. Line 72: Change `namespace["lambda_handler"](ctx, event)` to
      `namespace["lambda_handler"](event, ctx)` — the template now generates
      `lambda_handler(event: dict, context: DurableContext)` with event first.

3. **tests/test_dsl/test_infra_config.py** (line 78):
   Change `assert config.custom == {"program": "/usr/bin/deploy.sh"}` to:
   ```python
   assert config.custom.program == "/usr/bin/deploy.sh"
   ```
   The `custom` field is now coerced into a `CustomProviderConfig` Pydantic model
   (added in Phase 54, v3.0) rather than remaining a raw dict. Comparing individual
   attributes is the correct approach.
  </action>
  <verify>
    <automated>python3 -m pytest tests/test_codegen/test_generator.py::TestRenderOrchestrator::test_imports_present tests/test_integration/test_sdk_integration.py tests/test_dsl/test_infra_config.py::TestInfrastructureConfig::test_custom_provider_with_dict_config --tb=short -q 2>&1</automated>
  </verify>
  <done>
    - test_imports_present passes with new SDK module name
    - All 7 SDK integration tests pass with new module name and event,context arg order
    - test_custom_provider_with_dict_config passes comparing model attributes
  </done>
</task>

<task type="auto">
  <name>Task 2: Regenerate snapshot golden files</name>
  <files>
    fixtures/snapshots/order-processing.py.snapshot,
    fixtures/snapshots/data-pipeline.py.snapshot,
    fixtures/snapshots/intrinsic-showcase.py.snapshot,
    fixtures/snapshots/lambda-url-trigger.py.snapshot,
    fixtures/snapshots/approval-workflow.py.snapshot,
    fixtures/snapshots/retry-and-recovery.py.snapshot
  </files>
  <action>
Run the snapshot test suite with the --update-snapshots flag to regenerate all 6
golden files. This updates them to match the current orchestrator template output
which uses `aws_durable_execution_sdk_python` imports and
`lambda_handler(event, context)` argument order:

```bash
python3 -m pytest tests/test_codegen/test_snapshots.py --update-snapshots -q
```

After regeneration, verify the snapshots pass:

```bash
python3 -m pytest tests/test_codegen/test_snapshots.py -q
```
  </action>
  <verify>
    <automated>python3 -m pytest tests/test_codegen/test_snapshots.py --tb=short -q 2>&1</automated>
  </verify>
  <done>
    - All 6 snapshot tests pass (order-processing, data-pipeline, intrinsic-showcase, lambda-url-trigger, approval-workflow, retry-and-recovery)
    - Golden files contain `from aws_durable_execution_sdk_python` (not aws_lambda_...)
    - Golden files contain `lambda_handler(event: dict, context: DurableContext)` (not context, event)
  </done>
</task>

<task type="auto">
  <name>Task 3: Full test suite verification and commit</name>
  <files></files>
  <action>
Run the full test suite (excluding test_editor and test_inspect which have
unrelated missing-dependency collection errors for httpx/starlette) and confirm
zero failures:

```bash
python3 -m pytest tests/ --ignore=tests/test_editor --ignore=tests/test_inspect --tb=short -q
```

Expected: All tests pass. The 20 AWS integration test ERRORs (test_examples/)
are expected — they require AWS credentials and deployed infrastructure.
Only FAILURES count as real problems.

If any new failures appear, diagnose and fix them.

After all tests pass, stage and commit all changed files (both the previously
uncommitted working-tree changes and the newly fixed test files) with a single
descriptive commit.
  </action>
  <verify>
    <automated>python3 -m pytest tests/ --ignore=tests/test_editor --ignore=tests/test_inspect -q 2>&1 | tail -5</automated>
  </verify>
  <done>
    - 0 failures in full test run (errors from AWS integration tests are acceptable)
    - All changes committed to git
  </done>
</task>

</tasks>

<verification>
```bash
# Final check: zero FAILED in full test output
python3 -m pytest tests/ --ignore=tests/test_editor --ignore=tests/test_inspect --tb=short -q 2>&1 | grep -E "^(FAILED|ERROR|.*passed.*)"
```
Expected output: `N passed, M errors` with zero FAILED lines.
</verification>

<success_criteria>
- Zero test failures across the entire test suite (excluding httpx/starlette collection errors)
- Snapshot golden files regenerated and matching current template output
- All changes committed
</success_criteria>

<output>
After completion, create `.planning/quick/2-continue-fixing-all-integration-tests-ba/2-SUMMARY.md`
</output>
