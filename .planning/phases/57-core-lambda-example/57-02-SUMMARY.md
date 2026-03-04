---
phase: 57-core-lambda-example
plan: 02
subsystem: infra
tags: [terraform, lambda, durable-functions, iam, registry-modules, aws-lambda-alias]

# Dependency graph
requires:
  - phase: 56-schema-verification
    provides: "versions.tf scaffold with exact module version pins, SCHEMA-FINDINGS.md with verified durable_config variable names, IAM hybrid approach, alias convention, zip path"
provides:
  - "examples/registry-modules-demo/terraform/main.tf — lambda module v8.7.0 with durable_config, hybrid IAM, aws_lambda_alias live"
  - "examples/registry-modules-demo/terraform/iam_durable.tf — IAM policy split documentation (managed + inline supplement)"
  - "examples/registry-modules-demo/terraform/variables.tf — aws_region, workflow_name, execution_timeout with validation"
  - "examples/registry-modules-demo/terraform/outputs.tf — alias_arn, function_name, role_arn"
  - "examples/registry-modules-demo/terraform/backend.tf — local backend documentation"
  - "Confirmed AWSLambdaBasicDurableExecutionRolePolicy available in us-east-2 (v3, live AWS check)"
  - "terraform validate passes on all 5 files"
affects:
  - "Phase 57 Plan 03 (deploy.sh and rsf.toml integration)"
  - "Phase 58 (DynamoDB, SQS, CloudWatch, SNS Terraform)"
  - "Phase 59 (end-to-end deployment testing)"
  - "Phase 60 (tutorial documentation)"

# Tech tracking
tech-stack:
  added:
    - "terraform-aws-modules/lambda/aws v8.7.0 (first version with native durable_config support)"
  patterns:
    - "Hybrid IAM: managed AWSLambdaBasicDurableExecutionRolePolicy + inline DurableExtraPermissions supplement"
    - "coalesce(var.execution_timeout, 86400) null guard on durable_config_execution_timeout"
    - "attach_policies=true + number_of_policies=1 + policies=[...] — all three required for managed policy attachment"
    - "aws_lambda_alias live — always invoke durable functions via alias ARN, never $LATEST (issue #45800)"
    - "create_package=false + local_existing_package + ignore_source_code_hash=true for pre-built zips"

key-files:
  created:
    - "examples/registry-modules-demo/terraform/main.tf"
    - "examples/registry-modules-demo/terraform/iam_durable.tf"
    - "examples/registry-modules-demo/terraform/variables.tf"
    - "examples/registry-modules-demo/terraform/outputs.tf"
    - "examples/registry-modules-demo/terraform/backend.tf"
  modified: []

key-decisions:
  - "AWSLambdaBasicDurableExecutionRolePolicy confirmed available in us-east-2 (v3, verified live via aws iam get-policy) — hybrid approach used"
  - "Both GetDurableExecution and GetDurableExecutionState included: managed policy covers GetDurableExecutionState (replay-state), inline covers GetDurableExecution (describe API)"
  - "execution_timeout validated 1-31622400 seconds with coalesce guard in Terraform (prevents silent null propagation)"
  - "Local backend chosen for tutorial simplicity — no S3/DynamoDB lock table required, state gitignored"

patterns-established:
  - "Pattern: Hybrid IAM — three-field managed policy attachment (attach_policies + number_of_policies + policies)"
  - "Pattern: durable_config null guard via coalesce() on execution_timeout variable"
  - "Pattern: Lambda alias live referencing module.lambda.lambda_function_version"

requirements-completed: [REG-01]

# Metrics
duration: 13min
completed: 2026-03-04
---

# Phase 57 Plan 02: Core Lambda Example Summary

**terraform-aws-modules/lambda/aws v8.7.0 module with durable_config, hybrid IAM (managed AWSLambdaBasicDurableExecutionRolePolicy confirmed available in us-east-2 + inline DurableExtraPermissions), and aws_lambda_alias live — terraform validate passes**

## Performance

- **Duration:** 13 min
- **Started:** 2026-03-04T13:34:58Z
- **Completed:** 2026-03-04T13:47:28Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Ran live AWS IAM policy check and confirmed AWSLambdaBasicDurableExecutionRolePolicy is available in us-east-2 (v3, updated Feb 12, 2026) — hybrid IAM approach selected
- Created all 5 Terraform files (main.tf, iam_durable.tf, variables.tf, outputs.tf, backend.tf) with all required durable_config parameters, coalesce guard, hybrid IAM attachment, and aws_lambda_alias live
- terraform init + terraform validate passes cleanly; full test suite shows 1026 passed with 1 pre-existing failure (unrelated)

## Task Commits

Each task was committed atomically:

1. **Task 1: Check managed IAM policy availability and write Terraform files** - `7a4a36e` (feat)
2. **Task 2: Verify Terraform structure completeness** — no new commit (structural verification only, no code changes)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `examples/registry-modules-demo/terraform/main.tf` — lambda module v8.7.0 with durable_config (coalesce guard), create_package=false, hybrid IAM (managed + inline DurableExtraPermissions), aws_lambda_alias live
- `examples/registry-modules-demo/terraform/iam_durable.tf` — documentation-only comment block explaining managed+inline policy split rationale and action name mapping
- `examples/registry-modules-demo/terraform/variables.tf` — aws_region (default us-east-2), workflow_name (no default, set by deploy.sh), execution_timeout (default 86400, validated 1-31622400)
- `examples/registry-modules-demo/terraform/outputs.tf` — alias_arn (aws_lambda_alias.live.arn), function_name, role_arn
- `examples/registry-modules-demo/terraform/backend.tf` — comment-only local backend documentation with example remote state migration snippet

## Decisions Made

- **IAM approach confirmed hybrid:** Live AWS check showed AWSLambdaBasicDurableExecutionRolePolicy v3 exists in us-east-2. Used attach_policies=true + number_of_policies=1 + policies=[...] for managed policy, plus attach_policy_json=true + policy_json for inline supplement. Three-field pattern required — silent failure without attach_policies=true.
- **Both GetDurableExecution APIs in inline supplement:** GetDurableExecution (describe, user-facing) added alongside GetDurableExecutionState (replay-state, managed policy) to cover both invocation paths as recommended in SCHEMA-FINDINGS.md Section 7.
- **Local backend chosen:** No S3 setup required for tutorial readers, state gitignored. Remote backend snippet provided in comments for production guidance.
- **execution_timeout validation:** 1-31622400 seconds range enforced in Terraform validation block, coalesce guard in module block prevents null propagation from WorkflowMetadata defaults.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- AWS credentials expired at task start — refreshed automatically via /home/esa/bin/run-pcl.sh (8-hour credentials obtained)
- python command not found — used python3 for test suite (pre-existing environment behavior, no fix needed)
- test_editor and test_inspect excluded from test run due to pre-existing missing dependencies (httpx), not caused by this plan
- 1 pre-existing test failure (test_custom_provider_with_dict_config) confirmed on base commit before changes — not a regression

## User Setup Required

None — no external service configuration required. Terraform files created but not applied in this plan.

## Next Phase Readiness

- All 5 Terraform files ready for deploy.sh to call terraform apply with -var flags from RSF_METADATA_FILE
- versions.tf (Phase 56) + all 5 new files form complete Terraform configuration for Lambda Durable Function deployment
- Phase 57 Plan 03 can proceed: write deploy.sh, rsf.toml, workflow YAML, and handler files
- Terraform outputs (alias_arn, function_name, role_arn) ready for deploy.sh to print post-apply summary

---
*Phase: 57-core-lambda-example*
*Completed: 2026-03-04*
