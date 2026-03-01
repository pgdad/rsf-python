---
phase: 36-dsl-and-terraform
plan: 02
subsystem: terraform
tags: [terraform, hcl, jinja2, lambda-url, iam]

requires:
  - phase: 36-dsl-and-terraform
    provides: LambdaUrlConfig model and LambdaUrlAuthType enum from Plan 01
provides:
  - lambda_url.tf.j2 template for aws_lambda_function_url resource
  - Conditional InvokeFunctionUrl IAM statement in iam.tf.j2
  - Conditional function_url output in outputs.tf.j2
  - lambda_url_enabled and lambda_url_auth_type on TerraformConfig
  - Deploy command wiring from DSL to Terraform
affects: [37-example-workflow, 38-tutorial]

tech-stack:
  added: []
  patterns: [conditional Jinja2 blocks in HCL templates with custom delimiters]

key-files:
  created:
    - src/rsf/terraform/templates/lambda_url.tf.j2
  modified:
    - src/rsf/terraform/generator.py
    - src/rsf/terraform/templates/iam.tf.j2
    - src/rsf/terraform/templates/outputs.tf.j2
    - src/rsf/cli/deploy_cmd.py
    - tests/test_terraform/test_terraform.py

key-decisions:
  - "Lambda URL template is entirely conditional — file only generated when enabled, no Jinja2 conditionals within"
  - "InvokeFunctionUrl IAM statement only added for AWS_IAM auth type, not NONE"
  - "Deploy command uses hasattr guard for backward compatibility with non-StateMachineDefinition objects"

patterns-established:
  - "Conditional template file generation: skip in generator loop rather than wrap entire template in conditional"

requirements-completed: [TF-01, TF-02, TF-03]

duration: 5min
completed: 2026-03-01
---

# Plan 36-02: Terraform Lambda URL Generation Summary

**Lambda Function URL Terraform generation with conditional IAM and outputs, wired end-to-end from DSL through deploy command**

## Performance

- **Duration:** 5 min
- **Tasks:** 2
- **Files modified:** 6 (1 created)

## Accomplishments
- Created lambda_url.tf.j2 template generating aws_lambda_function_url resource
- Updated iam.tf.j2 with conditional InvokeFunctionUrl statement for AWS_IAM auth
- Updated outputs.tf.j2 with conditional function_url output
- Added lambda_url_enabled and lambda_url_auth_type fields to TerraformConfig
- Generator skips lambda_url.tf when not enabled (preserves existing 6-file behavior)
- Wired deploy command to pass lambda_url config from parsed DSL definition
- All 760 tests pass (16 new across both plans), 0 failures

## Task Commits

1. **Task 1: Terraform templates and generator** - `a59d639` (feat)
2. **Task 2: Deploy command wiring** - `b7815ab` (feat)

## Files Created/Modified
- `src/rsf/terraform/templates/lambda_url.tf.j2` - New template for aws_lambda_function_url resource
- `src/rsf/terraform/generator.py` - Added lambda_url fields to TerraformConfig, context, and skip logic
- `src/rsf/terraform/templates/iam.tf.j2` - Conditional InvokeFunctionUrl IAM statement
- `src/rsf/terraform/templates/outputs.tf.j2` - Conditional function_url output
- `src/rsf/cli/deploy_cmd.py` - Reads lambda_url from definition and passes to TerraformConfig
- `tests/test_terraform/test_terraform.py` - 8 new tests in TestLambdaUrlTerraform class

## Decisions Made
- Lambda URL template file is wholly conditional (skipped in loop, not wrapped in Jinja2 if/endif)
- InvokeFunctionUrl IAM permission only added for AWS_IAM auth type (NONE auth does not need it)
- Used hasattr guard in deploy command for robustness with the definition parameter typed as object

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 36 complete: DSL model + Terraform generation for Lambda Function URLs
- Ready for Phase 37 (Example Workflow) to create a working example using the lambda_url feature

---
*Phase: 36-dsl-and-terraform*
*Completed: 2026-03-01*
