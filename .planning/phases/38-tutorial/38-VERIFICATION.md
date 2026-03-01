---
phase: 38-tutorial
status: passed
verified: 2026-03-01
---

# Phase 38: Tutorial - Verification

## Phase Goal
Users can follow a step-by-step tutorial that walks them from adding the `lambda_url` DSL field through deploying via Terraform to invoking the workflow with a curl POST.

## Requirement Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| TUT-01 | Passed | Steps 12-13 cover lambda_url YAML config and rsf deploy |
| TUT-02 | Passed | Step 14 includes copy-pasteable curl POST command |

## Must-Have Verification

| Must-Have | Status | Evidence |
|-----------|--------|----------|
| docs/tutorial.md contains Step 12 covering lambda_url YAML configuration | Passed | `grep "## Step 12" docs/tutorial.md` finds the step |
| docs/tutorial.md contains Step 13 covering rsf deploy for Lambda URL provisioning | Passed | `grep "## Step 13" docs/tutorial.md` finds the step |
| docs/tutorial.md contains Step 14 with a copy-pasteable curl POST command | Passed | `grep "curl -X POST" docs/tutorial.md` finds the command |
| New steps follow existing tutorial patterns | Passed | MkDocs admonitions (!!! tip, !!! note), numbered steps, language-annotated code blocks |

## Success Criteria

1. A new tutorial document exists covering how to add `lambda_url` configuration to workflow YAML and how to run `rsf deploy` to provision the Lambda URL resource -- **PASSED** (Steps 12-13)
2. The tutorial includes a working curl command that users can copy-paste to POST to their Lambda URL and trigger a durable execution -- **PASSED** (Step 14)

## Automated Checks

- `grep -c "## Step 12\|## Step 13\|## Step 14" docs/tutorial.md` returns 3 -- PASSED
- `grep "lambda_url:" docs/tutorial.md` finds YAML config -- PASSED
- `grep "auth_type: NONE" docs/tutorial.md` confirms NONE auth shown -- PASSED
- `grep "AWS_IAM" docs/tutorial.md` confirms IAM auth mentioned -- PASSED
- `grep "curl -X POST" docs/tutorial.md` finds POST command -- PASSED
- `grep "rsf deploy" docs/tutorial.md` finds deploy instructions -- PASSED
- `grep "## Next steps" docs/tutorial.md` confirms section at end -- PASSED

## Result

**VERIFICATION PASSED** -- All must-haves verified, all success criteria met.

---
*Phase: 38-tutorial*
*Verified: 2026-03-01*
