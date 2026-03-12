---
phase: quick-19
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: true
requirements: [INTEG-ALL]

must_haves:
  truths:
    - "All 6 standard example integration tests pass with real AWS infrastructure"
    - "Registry-modules-demo integration tests pass with custom terraform provider"
    - "All terraform infrastructure is torn down after tests complete"
    - "No orphaned AWS resources remain"
  artifacts: []
  key_links:
    - from: "tests/test_examples/test_*.py"
      to: "examples/*/terraform/"
      via: "conftest terraform_deploy/terraform_teardown fixtures"
      pattern: "terraform_deploy|terraform_teardown"
---

<objective>
Run all 20 integration tests across all 7 examples with real AWS infrastructure deployment.

Purpose: Validate that all examples deploy, execute correctly, and teardown cleanly on real AWS, confirming end-to-end functionality after recent changes (tags, CI fixes, graph editor updates).

Output: Test results documented in summary. All infrastructure deployed and torn down.
</objective>

<execution_context>
@/home/esa/.claude/get-shit-done/workflows/execute-plan.md
@/home/esa/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@tests/test_examples/conftest.py
@tests/test_examples/test_registry_modules_demo.py
@examples/registry-modules-demo/rsf.toml
</context>

<tasks>

<task type="auto">
  <name>Task 1: Run 6 standard example integration tests</name>
  <files></files>
  <action>
Run all integration tests for the 6 standard examples that use the conftest terraform_deploy/terraform_teardown pattern. Each test class fixture handles its own deploy -> test -> teardown lifecycle.

Set AWS environment and run tests one example at a time to keep infrastructure footprint minimal and failures isolated:

```bash
export AWS_PROFILE=adfs
export AWS_DEFAULT_REGION=us-east-2
```

Run each test file individually so that if one example fails, the others still get tested. Order does not matter but run them sequentially:

```bash
cd /home/esa/git/rsf-python

# 1. order-processing (3 tests: happy path, log entries, fail state)
pytest tests/test_examples/test_order_processing.py -v -m integration --timeout=600 -s 2>&1 | tee /tmp/integ-order-processing.log

# 2. data-pipeline (3 tests: success, log entries, DynamoDB writes)
pytest tests/test_examples/test_data_pipeline.py -v -m integration --timeout=600 -s 2>&1 | tee /tmp/integ-data-pipeline.log

# 3. approval-workflow (3 tests: approved path, rejected path, log entries)
pytest tests/test_examples/test_approval_workflow.py -v -m integration --timeout=600 -s 2>&1 | tee /tmp/integ-approval-workflow.log

# 4. retry-and-recovery (2 tests: retry success, log entries)
pytest tests/test_examples/test_retry_recovery.py -v -m integration --timeout=600 -s 2>&1 | tee /tmp/integ-retry-recovery.log

# 5. intrinsic-showcase (2 tests: success, log entries)
pytest tests/test_examples/test_intrinsic_showcase.py -v -m integration --timeout=600 -s 2>&1 | tee /tmp/integ-intrinsic-showcase.log

# 6. lambda-url-trigger (4 tests: function URL response, log entries, etc.)
pytest tests/test_examples/test_lambda_url_trigger.py -v -m integration --timeout=600 -s 2>&1 | tee /tmp/integ-lambda-url-trigger.log
```

IMPORTANT:
- The `-s` flag ensures real-time output so you can see deploy/test/teardown progress.
- The `--timeout=600` gives each test up to 10 minutes (terraform deploy + IAM propagation + polling + teardown).
- Each test class fixture calls `terraform_deploy()` at setup and `terraform_teardown()` at cleanup automatically.
- If a test fails, record the failure but continue with the remaining examples.
- After all tests complete, verify no leftover terraform state exists in any example:

```bash
for dir in order-processing data-pipeline approval-workflow retry-and-recovery intrinsic-showcase lambda-url-trigger; do
  echo "=== $dir ==="
  terraform -chdir=examples/$dir/terraform state list 2>/dev/null || echo "(no state file)"
done
```

If any terraform state remains, manually destroy it:
```bash
terraform -chdir=examples/$EXAMPLE/terraform destroy -auto-approve -input=false
```
  </action>
  <verify>
    <automated>grep -c "PASSED\|FAILED\|ERROR" /tmp/integ-order-processing.log /tmp/integ-data-pipeline.log /tmp/integ-approval-workflow.log /tmp/integ-retry-recovery.log /tmp/integ-intrinsic-showcase.log /tmp/integ-lambda-url-trigger.log</automated>
  </verify>
  <done>All 17 integration tests across 6 standard examples have been executed. Pass/fail results recorded for each. All terraform infrastructure torn down (no orphaned resources).</done>
</task>

<task type="auto">
  <name>Task 2: Run registry-modules-demo integration tests</name>
  <files>examples/registry-modules-demo/rsf.toml</files>
  <action>
Run the registry-modules-demo integration tests. This example uses a custom terraform provider via deploy.sh and rsf.toml, NOT the conftest terraform_deploy helper.

The test fixture in test_registry_modules_demo.py automatically:
1. Patches rsf.toml placeholder with the real deploy.sh absolute path
2. Runs `rsf generate workflow.yaml`
3. Runs `rsf deploy workflow.yaml --auto-approve` (which invokes deploy.sh via CustomProvider)
4. Reads terraform outputs for alias_arn and function_name
5. Invokes the Lambda and polls for SUCCEEDED
6. On teardown: runs `rsf deploy workflow.yaml --teardown --auto-approve`
7. Restores the rsf.toml placeholder in the finally block
8. Safety net: direct terraform destroy if state is non-empty

IMPORTANT PRE-CHECK: Before running the test, verify the rsf.toml still has the placeholder path (not a stale absolute path from a previous run):

```bash
export AWS_PROFILE=adfs
export AWS_DEFAULT_REGION=us-east-2
cd /home/esa/git/rsf-python

# Verify rsf.toml has the placeholder (test fixture will patch it)
grep "REPLACE" examples/registry-modules-demo/rsf.toml
```

If rsf.toml has a real path instead of the placeholder, restore it:
```bash
sed -i 's|program.*=.*"/.*deploy.sh"|program         = "/REPLACE/WITH/YOUR/ABSOLUTE/PATH/TO/examples/registry-modules-demo/deploy.sh"|' examples/registry-modules-demo/rsf.toml
```

Then run the tests:

```bash
pytest tests/test_examples/test_registry_modules_demo.py -v -m integration --timeout=600 -s 2>&1 | tee /tmp/integ-registry-modules-demo.log
```

The test includes 3 assertions:
- test_a_execution_succeeds: Durable execution reaches SUCCEEDED
- test_b_handler_log_entries: CloudWatch logs contain all 4 handler names (ValidateImage, ResizeImage, AnalyzeContent, CatalogueImage)
- test_z_teardown_leaves_empty_state: rsf deploy --teardown exits 0 and terraform state is empty

After test completes, verify cleanup:
```bash
# Verify rsf.toml was restored to placeholder
grep "REPLACE" examples/registry-modules-demo/rsf.toml

# Verify terraform state is empty
terraform -chdir=examples/registry-modules-demo/terraform state list 2>/dev/null || echo "(no state file)"
```

If terraform state is not empty (test fixture safety net failed), manually destroy:
```bash
terraform -chdir=examples/registry-modules-demo/terraform destroy -auto-approve -input=false -var-file=terraform.tfvars.json
```
  </action>
  <verify>
    <automated>grep -c "PASSED\|FAILED\|ERROR" /tmp/integ-registry-modules-demo.log</automated>
  </verify>
  <done>All 3 registry-modules-demo integration tests executed. Results recorded. Custom provider pipeline (rsf.toml -> deploy.sh -> terraform) verified end-to-end. Infrastructure torn down, rsf.toml restored to placeholder.</done>
</task>

<task type="auto">
  <name>Task 3: Compile results and create summary</name>
  <files></files>
  <action>
After Tasks 1 and 2 complete, compile all test results from the log files:

```bash
echo "=== INTEGRATION TEST RESULTS ==="
for log in /tmp/integ-*.log; do
  echo ""
  echo "--- $(basename $log .log) ---"
  tail -5 "$log"
done
```

Create a results table showing:
- Example name
- Number of tests
- Pass/Fail status
- Any error messages for failures

Also do a final sweep to ensure no AWS resources are orphaned:
```bash
export AWS_PROFILE=adfs
export AWS_DEFAULT_REGION=us-east-2

# Check for any rsf-related Lambda functions still deployed
aws lambda list-functions --query "Functions[?starts_with(FunctionName, 'rsf-') || starts_with(FunctionName, 'order-') || starts_with(FunctionName, 'data-') || starts_with(FunctionName, 'approval-') || starts_with(FunctionName, 'retry-') || starts_with(FunctionName, 'intrinsic-') || starts_with(FunctionName, 'lambda-url-') || starts_with(FunctionName, 'registry-')].FunctionName" --output text 2>/dev/null || echo "Could not list functions"
```

If any orphaned functions are found, note them in the summary and clean up manually.

Write the summary to `.planning/quick/19-run-all-integration-tests-and-examples-w/19-SUMMARY.md` using the standard summary template.
  </action>
  <verify>
    <automated>test -f /home/esa/git/rsf-python/.planning/quick/19-run-all-integration-tests-and-examples-w/19-SUMMARY.md && echo "Summary exists"</automated>
  </verify>
  <done>Summary document created with full test results table. All 7 examples tested with real infrastructure. Orphaned resource check completed. Total: 20 integration tests across 7 examples with pass/fail status documented.</done>
</task>

</tasks>

<verification>
- All 20 integration tests across 7 examples have been executed
- Each test log file exists in /tmp/integ-*.log
- No terraform state remains in any example's terraform/ directory
- rsf.toml in registry-modules-demo is restored to placeholder path
- No orphaned Lambda functions or CloudWatch log groups remain
</verification>

<success_criteria>
- All 17 standard integration tests pass (order-processing: 3, data-pipeline: 3, approval-workflow: 3, retry-recovery: 2, intrinsic-showcase: 2, lambda-url-trigger: 4)
- All 3 registry-modules-demo integration tests pass
- All infrastructure torn down after each example's tests complete
- Results documented in summary with pass/fail per example
</success_criteria>

<output>
After completion, create `.planning/quick/19-run-all-integration-tests-and-examples-w/19-SUMMARY.md`
</output>
