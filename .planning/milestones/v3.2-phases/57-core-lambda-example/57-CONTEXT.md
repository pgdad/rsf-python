# Phase 57: Core Lambda Example - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can run `rsf deploy` on a real workflow and have RSF invoke a custom provider script (deploy.sh) that zips generated source and deploys a working Lambda Durable Function via terraform-aws-modules/lambda. Includes `rsf deploy --teardown` for clean destruction. Phase 57 delivers the Lambda + IAM Terraform only — DynamoDB, SQS, CloudWatch, and SNS registry modules are Phase 58.

</domain>

<decisions>
## Implementation Decisions

### Workflow scenario
- Claude's discretion on specific business logic — pick a scenario that naturally exercises multiple Task states and is interesting enough for a tutorial
- Workflow YAML should declare DynamoDB table and DLQ configuration (for Phase 58 Terraform) but Phase 57 only implements Lambda + IAM Terraform
- Moderate complexity (4-5 states) — enough to show real patterns without overwhelming the tutorial
- Must include at least one Retry/Catch block to demonstrate error handling in the workflow

### Deploy script design
- Bash script: `deploy.sh` starting with `set -euo pipefail`
- Single script with first-argument dispatch: `deploy.sh deploy` → zip + terraform apply, `deploy.sh destroy` → terraform destroy
- rsf.toml sets `args = ["deploy"]` and `teardown_args = ["destroy"]`
- deploy.sh runs `terraform init` automatically before apply/destroy (idempotent, no separate step)
- deploy.sh captures terraform output and prints the alias invoke ARN with a sample invocation command after successful deploy

### Metadata translation
- Claude's discretion on jq vs tfvars.json approach — pick what's simplest and most reliable for tutorial readers
- Variables should have clear, tutorial-friendly names (Claude picks naming convention)

### Terraform file layout
- Split files: `main.tf` (lambda module + alias), `iam_durable.tf` (managed policy attachment + inline supplement), `variables.tf` (inputs), `outputs.tf` (alias ARN, function name, role ARN)
- `versions.tf` already exists from Phase 56 — do not recreate
- Local backend (no S3 setup needed) — state file is gitignored
- Must verify `AWSLambdaBasicDurableExecutionRolePolicy` availability in us-east-2 before writing iam_durable.tf — fallback to all-inline if unavailable

### Handler implementation
- Follow existing RSF example conventions: `@state` decorator, one handler file per state, `__init__.py` with imports
- conftest.py follows the same pattern as order-processing (path setup, registry clear, module cache purge)
- Claude's discretion on structured logging approach (stdlib logging vs print-based JSON)
- Happy path handlers for Phase 57 — error scenarios can be added for testing in Phase 59

### Claude's Discretion
- Specific workflow business logic scenario and state names
- Whether to use jq extraction or tfvars.json file for metadata-to-Terraform translation
- Terraform variable naming convention (mirror metadata fields vs Terraform-idiomatic)
- Structured logging implementation (stdlib logging JSON vs print-based JSON)
- Handler file count and organization (driven by workflow state count)
- Exact DynamoDB table schema declared in workflow YAML (Phase 58 implements the Terraform)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/rsf/providers/custom.py`: CustomProvider with deploy/teardown dispatch via args/teardown_args, security-hardened subprocess (shell=False, absolute path validation)
- `src/rsf/providers/metadata.py`: WorkflowMetadata dataclass with all infrastructure fields (workflow_name, dynamodb_tables, alarms, dlq_enabled, timeout_seconds, etc.)
- `src/rsf/providers/transports.py`: FileTransport writes metadata JSON to RSF_METADATA_FILE path
- `examples/order-processing/`: Reference example with full RSF directory convention (workflow.yaml, handlers/, tests/, terraform/)
- `examples/order-processing/tests/conftest.py`: Test fixture pattern with registry clear, path setup, and module cache purge
- `.planning/phases/56-schema-verification/SCHEMA-FINDINGS.md`: All verified Terraform facts for lambda module, IAM, alias, zip path

### Established Patterns
- FileTransport (RSF_METADATA_FILE env var) is the canonical metadata transport
- Lambda alias `"live"` — never `$LATEST` (issue #45800)
- IAM: managed `AWSLambdaBasicDurableExecutionRolePolicy` + inline supplement for InvokeFunction, ListDurableExecutionsByFunction, GetDurableExecution
- `create_package = false` + `local_existing_package = "${path.module}/../build/function.zip"`
- `ignore_source_code_hash = true` to prevent re-deploy on zip hash changes
- `coalesce(var.execution_timeout, 86400)` to guard against null propagation from WorkflowMetadata
- `attach_policies = true` + `number_of_policies = 1` required for managed policy attachment (silent failure without)
- No existing deploy.sh or rsf.toml in any example — this is the first custom provider example

### Integration Points
- `examples/registry-modules-demo/terraform/versions.tf` — already created in Phase 56 with pinned versions
- `examples/registry-modules-demo/.gitignore` — already created in Phase 56
- `rsf.toml` at example root configures provider="custom" with absolute path and FileTransport
- CustomProvider reads `infrastructure.custom` block from workflow YAML or rsf.toml
- deploy.sh reads RSF_METADATA_FILE env var set by FileTransport during `rsf deploy`

</code_context>

<specifics>
## Specific Ideas

- deploy.sh should print the alias ARN with a sample `aws lambda invoke` command after successful terraform apply — gives tutorial readers an immediate next step to test their deployment
- The workflow YAML should declare DynamoDB and DLQ in its infrastructure/DSL section so Phase 58 can add Terraform without modifying the workflow — forward compatibility
- Phase 57 MUST run `aws iam get-policy` to verify managed policy availability before writing Terraform that depends on it (open question from Phase 56)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 57-core-lambda-example*
*Context gathered: 2026-03-04*
