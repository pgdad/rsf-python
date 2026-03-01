---
phase: 36
phase_name: DSL and Terraform
status: passed
verified: 2026-03-01
requirements: [DSL-01, DSL-02, TF-01, TF-02, TF-03]
---

# Phase 36: DSL and Terraform — Verification

## Goal

Users can add a `lambda_url` block to their workflow YAML and the generated Terraform includes a complete `aws_lambda_function_url` resource with correct auth and IAM.

## Success Criteria Verification

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | User can add `lambda_url: {enabled: true, auth_type: NONE}` (or `AWS_IAM`) to workflow YAML and `rsf validate` accepts it | PASS | `StateMachineDefinition.model_validate()` accepts both auth types; TestLambdaUrlConfig tests pass |
| 2 | `rsf validate` rejects invalid `auth_type` values with a clear error message | PASS | Pydantic ValidationError raised for `auth_type: "BASIC"`; test `test_lambda_url_rejects_invalid_auth_type` passes |
| 3 | `rsf generate` followed by `rsf deploy` produces Terraform with `aws_lambda_function_url` resource when `lambda_url.enabled` is true | PASS | `generate_terraform()` with `lambda_url_enabled=True` creates `lambda_url.tf` containing `aws_lambda_function_url` resource; deploy_cmd.py wires DSL config to TerraformConfig |
| 4 | Generated Terraform outputs include the Lambda Function URL endpoint value after `terraform apply` | PASS | `outputs.tf` contains `function_url` output referencing `aws_lambda_function_url.<resource_id>_url.function_url` |
| 5 | When `auth_type: AWS_IAM` is set, the generated IAM policy includes the `lambda:InvokeFunctionUrl` permission | PASS | `iam.tf` contains `InvokeFunctionUrl` statement with `lambda:InvokeFunctionUrl` action when `lambda_url_auth_type == "AWS_IAM"` |

## Requirements Cross-Reference

| Requirement | Description | Status |
|-------------|-------------|--------|
| DSL-01 | Optional lambda_url configuration in workflow YAML | PASS |
| DSL-02 | DSL validation accepts and rejects appropriately | PASS |
| TF-01 | aws_lambda_function_url resource generated | PASS |
| TF-02 | Function URL output included | PASS |
| TF-03 | IAM InvokeFunctionUrl permission for AWS_IAM | PASS |

## Test Coverage

- **Total tests:** 760 passed, 13 deselected (integration), 0 failures
- **New tests:** 16 (8 DSL model + 8 Terraform generation)
- **Ruff lint:** 0 violations

## Artifacts Verified

| File | Exists | Contains |
|------|--------|----------|
| `src/rsf/dsl/types.py` | Yes | `class LambdaUrlAuthType` with NONE, AWS_IAM |
| `src/rsf/dsl/models.py` | Yes | `class LambdaUrlConfig`, `lambda_url` field on `StateMachineDefinition` |
| `src/rsf/dsl/__init__.py` | Yes | `LambdaUrlAuthType` and `LambdaUrlConfig` in exports |
| `src/rsf/terraform/templates/lambda_url.tf.j2` | Yes | `aws_lambda_function_url` resource |
| `src/rsf/terraform/templates/iam.tf.j2` | Yes | Conditional `InvokeFunctionUrl` statement |
| `src/rsf/terraform/templates/outputs.tf.j2` | Yes | Conditional `function_url` output |
| `src/rsf/terraform/generator.py` | Yes | `lambda_url_enabled` and `lambda_url_auth_type` on TerraformConfig |
| `src/rsf/cli/deploy_cmd.py` | Yes | Reads `definition.lambda_url` and passes to TerraformConfig |

## Verdict

**PASSED** — All 5 success criteria verified. All 5 requirement IDs (DSL-01, DSL-02, TF-01, TF-02, TF-03) accounted for and satisfied.
