# Phase 60: Tutorial Document - Research

**Researched:** 2026-03-04
**Domain:** Technical documentation — RSF custom provider tutorial writing
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Tutorial structure:**
- Linear walkthrough: Prerequisites -> Project setup -> Custom provider config -> Deploy script -> Terraform -> Deploy -> Verify -> Understand architecture -> Pitfalls -> Teardown
- Reference the existing examples/registry-modules-demo/ files — reader clones the repo and follows along (not type-from-scratch)
- Side-by-side HCL comparison and schema table appear AFTER deploy succeeds — "Now let's understand what just happened"
- Coarse granularity: 8-12 numbered steps, each covering a logical phase (matches tutorial 04 density)

**Side-by-side HCL comparison (TUT-02):**
- Consecutive labeled code blocks: "RSF TerraformProvider output (raw HCL):" then "Registry module equivalent:" — works in all markdown renderers
- Compare Lambda AND DynamoDB resources (satisfies "at least Lambda and DynamoDB" requirement)
- Include IAM differences as a callout box after the Lambda comparison — highlights raw aws_iam_role vs module-created role
- Raw HCL sourced from RSF's Jinja2 templates (src/rsf/terraform/templates/main.tf.j2, dynamodb.tf.j2)
- Registry module HCL sourced from examples/registry-modules-demo/terraform/main.tf, dynamodb.tf

**WorkflowMetadata schema table (TUT-03):**
- 3-column markdown table: Field | Description | Example Value
- Cover the fields used in the example: workflow_name, timeout_seconds, dynamodb_tables, dlq_enabled, dlq_max_receive_count, dlq_queue_name, alarms
- Annotated with how each field maps to Terraform variables (the metadata -> tfvars.json -> Terraform pipeline)

**Common Pitfalls section (TUT-04):**
- Dedicated section after the architecture explanation (not inline warnings)
- Each pitfall: Problem + Symptom (what error you see) + Fix
- Four required pitfalls:
  1. Absolute path requirement in rsf.toml program field
  2. chmod +x requirement for deploy.sh
  3. Packaging conflict (create_package=false + local_existing_package)
  4. Exact version pinning rationale (Terraform does not lock module versions)
  5. Durable IAM permissions not included in module defaults (hybrid approach required)

**Audience & tone:**
- Assumes reader completed tutorials 01-05 (knows workflow.yaml, rsf generate, rsf deploy with built-in Terraform)
- Assumes basic Terraform familiarity (has run terraform apply, understands resources/modules/variables)
- Direct and practical tone matching tutorials 01-08: imperative instructions, bash commands with expected output, brief "why" explanations
- "What You'll Learn" + "What You'll Build" text summary at top listing components (custom provider, deploy.sh, 5 registry modules)
- Cost warning matching tutorial 04 pattern

### Claude's Discretion
- Exact step numbering and step titles
- How much deploy.sh code to inline vs reference
- Whether to show full .tf file contents or excerpts with file path references
- Terraform output formatting in expected-output blocks
- How to present the metadata -> tfvars.json -> Terraform pipeline visually
- Exact wording of the "What You'll Learn" and "What You'll Build" sections
- Whether to include a "Next Steps" section at the end (future tutorials, advanced usage)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TUT-01 | Step-by-step tutorial (tutorials/09-custom-provider-registry-modules.md) walks through custom provider creation | Linear walkthrough structure confirmed; existing file set in examples/registry-modules-demo/ fully verified; tutorial 04 format established as template |
| TUT-02 | Tutorial includes side-by-side comparison of raw HCL vs registry module HCL | Raw HCL source: src/rsf/terraform/templates/main.tf.j2, dynamodb.tf.j2 — both read and verified; registry module HCL: examples/registry-modules-demo/terraform/main.tf, dynamodb.tf — both read and verified |
| TUT-03 | Tutorial includes annotated WorkflowMetadata schema table for provider authors | WorkflowMetadata dataclass fully read from src/rsf/providers/metadata.py; all fields identified; tfvars pipeline traced through deploy.sh generate_tfvars() |
| TUT-04 | Tutorial covers pitfalls: absolute path, chmod +x, packaging conflict, version pinning, durable IAM | All five pitfalls fully documented from source artifacts; exact error symptoms researchable from code |
</phase_requirements>

## Summary

Phase 60 produces a single Markdown file: `tutorials/09-custom-provider-registry-modules.md`. Unlike code phases, the deliverable is entirely textual — the implementation work is finding, extracting, and organizing information already present in the completed example code (Phases 56-59).

All source material required for the tutorial is present in the repository and has been read during this research. The tutorial documents the `examples/registry-modules-demo/` example, which is already deployed and verified. The planner's task is to write prose and code blocks from existing artifacts, not discover new technical facts.

The tutorial format is established by `tutorials/04-deploy-to-aws.md`: numbered steps with `## Step N: Title` headings, bash code blocks with expected output, blockquote cost warnings, and imperative instructions. Tutorial 09 follows this pattern but is longer because it adds three structural elements not present in tutorials 01-08: a side-by-side HCL comparison, a schema table, and a Common Pitfalls section.

**Primary recommendation:** Write the tutorial as a single Wave 0 plan that produces the complete file, following the locked step sequence and the established format from tutorial 04.

## Source File Inventory

All source files for the tutorial have been read and verified. This section records what each file contributes.

### What the Tutorial Documents

| File | Role in Tutorial |
|------|-----------------|
| `examples/registry-modules-demo/rsf.toml` | Step: custom provider config — program, args, teardown_args, metadata_transport |
| `examples/registry-modules-demo/deploy.sh` | Step: deploy script walkthrough — CMD dispatch, generate_tfvars(), zip, terraform apply |
| `examples/registry-modules-demo/workflow.yaml` | Step: workflow definition — image-processing, 4 Task states, DynamoDB, DLQ, alarms |
| `examples/registry-modules-demo/handlers/__init__.py` | Step: handler registration — auto-import of 4 handlers |
| `examples/registry-modules-demo/handlers/validate_image.py` | Tone reference — @state decorator, structured logging pattern |
| `examples/registry-modules-demo/terraform/main.tf` | TUT-02: registry module Lambda HCL for right side of comparison |
| `examples/registry-modules-demo/terraform/dynamodb.tf` | TUT-02: registry module DynamoDB HCL for right side of comparison |
| `examples/registry-modules-demo/terraform/sqs.tf` | Supporting: DLQ module (mentioned but not in primary comparison) |
| `examples/registry-modules-demo/terraform/alarms.tf` | Supporting: CloudWatch alarms (mentioned but not in primary comparison) |
| `examples/registry-modules-demo/terraform/sns.tf` | Supporting: SNS topic (mentioned but not in primary comparison) |
| `examples/registry-modules-demo/terraform/variables.tf` | TUT-03: confirms Terraform variable names that map from WorkflowMetadata fields |
| `examples/registry-modules-demo/terraform/versions.tf` | TUT-04 pitfall 4: exact version pinning rationale (comment in file) |
| `examples/registry-modules-demo/terraform/iam_durable.tf` | TUT-04 pitfall 5: hybrid IAM rationale documented in comment block |
| `examples/registry-modules-demo/terraform/outputs.tf` | Verify step: alias_arn output used for invocation |
| `examples/registry-modules-demo/terraform/backend.tf` | Context: local backend, no S3 required |
| `src/rsf/terraform/templates/main.tf.j2` | TUT-02: raw HCL Lambda template for left side of comparison |
| `src/rsf/terraform/templates/dynamodb.tf.j2` | TUT-02: raw HCL DynamoDB template for left side of comparison |
| `src/rsf/providers/metadata.py` | TUT-03: WorkflowMetadata dataclass — all fields with types and defaults |
| `tutorials/04-deploy-to-aws.md` | Format reference — step titles, code block style, cost warning format, output examples |

## Tutorial Structure (Locked)

The locked step sequence maps to these numbered sections:

```
## Step 1: Prerequisites
## Step 2: Clone the Example
## Step 3: Configure rsf.toml (absolute path)
## Step 4: Prepare deploy.sh (chmod +x)
## Step 5: Review the Workflow and Terraform
## Step 6: Deploy
## Step 7: Verify
## Step 8: Understand the Architecture
## Step 9: Common Pitfalls
## Step 10: Tear Down
```

This is 10 steps, within the locked 8-12 range, matching tutorial 04's density. Exact step titles are Claude's discretion.

## Architecture Patterns

### Tutorial 04 Format (Established Reference)

The established pattern from `tutorials/04-deploy-to-aws.md`:

```markdown
# Tutorial N: Title

## What You'll Learn

In this tutorial you will:

- [bullet items]

---

## Prerequisites

- [prerequisite with tool check command]

Verify your tools are ready:

\`\`\`bash
[verification command]
\`\`\`

> **Cost warning:** [text]

---

## Step 1: Title

[prose paragraph]

\`\`\`bash
[command]
\`\`\`

Expected output:

\`\`\`
[output]
\`\`\`

[explanation of what happened]

---
```

Key formatting rules confirmed from tutorial 04:
- `---` horizontal rules between every section
- `> **Cost warning:**` blockquote format
- `Expected output:` as plain text label before output block
- Step headings: `## Step N: Title` (H2)
- Sub-sections within steps: `### subsection` (H3)
- Account ID placeholder: `123456789012`
- ARN placeholders: full example with placeholder account ID

### Side-by-Side HCL Comparison Pattern (Consecutive Labeled Blocks)

The locked approach uses consecutive labeled code blocks — no special Markdown table or tabs needed:

```markdown
**RSF TerraformProvider output (raw HCL):**

\`\`\`hcl
[raw HCL from Jinja2 template, simplified]
\`\`\`

**Registry module equivalent:**

\`\`\`hcl
[registry module HCL from examples/]
\`\`\`
```

This renders correctly in GitHub, VS Code, and all standard Markdown renderers.

### WorkflowMetadata -> tfvars.json -> Terraform Pipeline

The data flow is:

```
workflow.yaml
    |
    v (rsf generate / rsf deploy)
WorkflowMetadata (dataclass)
    |
    v (FileTransport writes RSF_METADATA_FILE)
/tmp/rsf-metadata-XXXXX.json
    |
    v (deploy.sh reads RSF_METADATA_FILE)
terraform.tfvars.json (via generate_tfvars() in deploy.sh)
    |
    v (terraform apply -var-file=terraform.tfvars.json)
AWS infrastructure
```

This pipeline is the tutorial's core conceptual teaching. The schema table sits at the "WorkflowMetadata -> tfvars.json" transition point.

### Visual Pipeline Presentation (Claude's Discretion)

Options verified from context:
1. Text arrow diagram (as above) — simple, works everywhere
2. Numbered list with indented descriptions — prose-heavy
3. Code block with comments — shows both JSON and Terraform side

Recommendation: Use the text arrow diagram as a code block (no language tag) at the start of the "Understand the Architecture" section. This matches how RSF documentation presents flows elsewhere.

## WorkflowMetadata Schema (TUT-03)

Full schema extracted from `src/rsf/providers/metadata.py`. Fields relevant to this example:

| Field | Python Type | Default | deploy.sh jq mapping | Terraform variable |
|-------|-------------|---------|---------------------|-------------------|
| `workflow_name` | `str` | (required) | `.workflow_name` | `var.workflow_name` |
| `timeout_seconds` | `int \| None` | `None` | `.timeout_seconds // 86400` | `var.execution_timeout` |
| `dynamodb_tables` | `list[dict]` | `[]` | `.dynamodb_tables // []` | `var.dynamodb_tables` |
| `dlq_enabled` | `bool` | `False` | `.dlq_enabled // false` | `var.dlq_enabled` |
| `dlq_max_receive_count` | `int` | `3` | `.dlq_max_receive_count // 3` | `var.dlq_max_receive_count` |
| `dlq_queue_name` | `str \| None` | `None` | `.dlq_queue_name` | `var.dlq_queue_name` |
| `alarms` | `list[dict]` | `[]` | strips `sns_topic_arn` field | `var.alarms` |

Fields in WorkflowMetadata NOT covered in the example table (not relevant to this provider):
- `stage`, `handler_count`, `triggers`, `lambda_url_enabled`, `lambda_url_auth_type`

The 3-column tutorial table format (Field | Description | Example Value) will include an implicit 4th concept: "Maps to Terraform variable" — this can be a note row or a 4-column table. Claude's discretion.

## Side-by-Side HCL Content (TUT-02)

### Lambda: Raw HCL vs Registry Module

**Raw HCL (from `src/rsf/terraform/templates/main.tf.j2`, simplified for tutorial):**

```hcl
# RSF TerraformProvider generates this directly

resource "aws_lambda_function" "image_processing" {
  function_name    = local.function_name
  handler          = "generated.orchestrator.lambda_handler"
  runtime          = "python3.13"
  role             = aws_iam_role.lambda_exec.arn
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = var.timeout
  memory_size      = var.memory_size

  durable_config {
    execution_timeout = var.execution_timeout
    retention_period  = var.retention_period
  }

  logging_config {
    log_format = "JSON"
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}
```

**Registry module equivalent (from `examples/registry-modules-demo/terraform/main.tf`):**

```hcl
# Custom provider uses terraform-aws-modules/lambda/aws v8.7.0

module "lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.7.0"

  function_name = var.workflow_name
  handler       = "orchestrator.lambda_handler"
  runtime       = "python3.13"

  create_package          = false
  local_existing_package  = "${path.module}/../build/function.zip"
  ignore_source_code_hash = true

  durable_config_execution_timeout = coalesce(var.execution_timeout, 86400)
  durable_config_retention_period  = 14

  logging_log_format = "JSON"

  create_role                   = true
  attach_cloudwatch_logs_policy = true
  # ... plus managed policy + inline supplement
}

resource "aws_lambda_alias" "live" {
  name             = "live"
  function_name    = module.lambda.lambda_function_name
  function_version = module.lambda.lambda_function_version
}
```

### DynamoDB: Raw HCL vs Registry Module

**Raw HCL (from `src/rsf/terraform/templates/dynamodb.tf.j2`, simplified for one table):**

```hcl
# RSF TerraformProvider generates one resource block per table

resource "aws_dynamodb_table" "image_processing_image_catalogue" {
  name         = "image-catalogue"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "image_id"

  attribute {
    name = "image_id"
    type = "S"
  }
}
```

**Registry module equivalent (from `examples/registry-modules-demo/terraform/dynamodb.tf`):**

```hcl
# Custom provider uses terraform-aws-modules/dynamodb-table/aws v5.5.0
# for_each creates one module instance per table in var.dynamodb_tables

module "dynamodb_table" {
  source   = "terraform-aws-modules/dynamodb-table/aws"
  version  = "5.5.0"
  for_each = { for t in var.dynamodb_tables : t.table_name => t }

  name         = each.value.table_name
  hash_key     = each.value.partition_key.name
  billing_mode = each.value.billing_mode

  attributes = [
    {
      name = each.value.partition_key.name
      type = each.value.partition_key.type
    }
  ]

  tags = { ManagedBy = "rsf", Workflow = var.workflow_name }
}
```

### IAM Callout (After Lambda Comparison)

Key IAM difference to highlight in callout box:

- Raw HCL: RSF generates explicit `aws_iam_role` + `aws_iam_role_policy` resources with all 5 durable execution actions inline
- Registry module: `create_role = true` generates the role; IAM is split into:
  - `attach_cloudwatch_logs_policy = true` (module shortcut for CW Logs)
  - `attach_policies` + `number_of_policies` + `policies` (managed policy attachment — BOTH attributes required)
  - `attach_policy_json` + `policy_json` (inline supplement for 3 actions not in managed policy)
- Critical gotcha: `attach_policies` + `number_of_policies` must BOTH be set — setting only `policies = [...]` silently attaches nothing

## Common Pitfalls Documentation (TUT-04)

All five pitfalls have been verified from source code. Error symptoms are inferable from the code.

### Pitfall 1: Absolute Path in rsf.toml program Field

**Problem:** rsf.toml `program` field uses a relative path or the placeholder value.

**Symptom:**
```
Error: custom provider script not found: /REPLACE/WITH/YOUR/ABSOLUTE/PATH/TO/examples/registry-modules-demo/deploy.sh
```
Or if a relative path is used, the script may silently fail when RSF invokes it from a different working directory.

**Fix:** Use the placeholder helper command:
```bash
echo "$(cd examples/registry-modules-demo && pwd)/deploy.sh"
```
Paste the output into `rsf.toml` as the `program` value.

**Source:** `examples/registry-modules-demo/rsf.toml` lines 8-9 and line 14.

### Pitfall 2: chmod +x Not Set on deploy.sh

**Problem:** deploy.sh exists but is not executable.

**Symptom:**
```
Error: permission denied: /path/to/examples/registry-modules-demo/deploy.sh
```

**Fix:**
```bash
chmod +x examples/registry-modules-demo/deploy.sh
```

**Source:** Standard Unix executable requirement. The rsf.toml does not set this automatically.

### Pitfall 3: Packaging Conflict (create_package=false + local_existing_package)

**Problem:** `create_package = false` tells the lambda module "I will supply the zip myself." If `build/function.zip` does not exist when `terraform apply` runs (e.g., the reader runs terraform directly instead of via deploy.sh), Terraform fails with a missing file error.

**Symptom:**
```
Error: local_existing_package file does not exist: /path/to/build/function.zip
```

**Fix:** Always deploy via deploy.sh (`rsf deploy`), never by running `terraform apply` directly. The deploy.sh Step 1 creates `build/function.zip` before calling Terraform.

**Source:** `examples/registry-modules-demo/deploy.sh` lines 60-81 (packaging step) and `examples/registry-modules-demo/terraform/main.tf` lines 22-24 (create_package + local_existing_package).

### Pitfall 4: Exact Version Pinning Rationale

**Problem:** Using `~>` version constraints instead of exact strings for registry module versions.

**Symptom:** No immediate error, but `terraform init` silently upgrades the module to a newer version that may have breaking changes or different `durable_config` variable names. Tutorial instructions break on next `terraform init`.

**Why it matters:** Terraform locks provider versions in `.terraform.lock.hcl` but does NOT lock module versions. `version = "~> 8.7"` allows 8.8, 8.9, ... which may change behavior.

**Fix:** Use exact version strings as shown in `versions.tf`:
```hcl
version = "8.7.0"  # not ~> 8.7
```

**Source:** `examples/registry-modules-demo/terraform/versions.tf` — comment block explains rationale explicitly.

### Pitfall 5: Durable IAM Permissions Not Included in Module Defaults

**Problem:** Using `create_role = true` with only `attach_cloudwatch_logs_policy = true` gives the function CW Logs access but not the durable execution permissions.

**Symptom:** Lambda deploys successfully but durable executions fail immediately with:
```
AccessDeniedException: User: ... is not authorized to perform: lambda:CheckpointDurableExecution
```

**Why it happens:** `AWSLambdaBasicDurableExecutionRolePolicy` is NOT attached by default by the lambda module. The module's `attach_cloudwatch_logs_policy` shortcut only attaches `AWSLambdaBasicExecutionRole` (CW Logs only).

**Fix:** Hybrid approach — both `attach_policies` (managed policy) and `attach_policy_json` (inline supplement) are required:
- Managed policy covers: CheckpointDurableExecution, GetDurableExecutionState, CW Logs
- Inline supplement covers: InvokeFunction, ListDurableExecutionsByFunction, GetDurableExecution
- Critical: `attach_policies = true` AND `number_of_policies = 1` BOTH required — setting only `policies = [...]` silently attaches nothing

**Source:** `examples/registry-modules-demo/terraform/iam_durable.tf` documents the full rationale.

## Architecture Explanation Content

The "Understand the Architecture" section (after deploy succeeds) covers:

### Component Inventory

5 registry modules deployed:
1. `terraform-aws-modules/lambda/aws` v8.7.0 — Lambda function + IAM role
2. `terraform-aws-modules/dynamodb-table/aws` v5.5.0 — image-catalogue table
3. `terraform-aws-modules/sqs/aws` v5.2.1 — image-processing-dlq queue
4. `terraform-aws-modules/cloudwatch/aws` v5.7.2 — 3 metric alarms (error_rate, duration, throttle)
5. `terraform-aws-modules/sns/aws` v7.1.0 — alarm-notifications topic

### Lambda Alias Convention

The `aws_lambda_alias.live` resource is a mandatory workaround for Terraform AWS provider issue #45800 (`AllowInvokeLatest` unresolved as of Jan 7, 2026). Always invoke via alias ARN, never `$LATEST` or unqualified ARN.

```bash
# Correct — use alias ARN from terraform output
aws lambda invoke \
  --function-name 'arn:aws:lambda:us-east-2:123456789012:function:image-processing:live' \
  ...

# Wrong — $LATEST invocation fails with durable functions
aws lambda invoke \
  --function-name 'image-processing' \
  ...
```

## Verify Step Content

After deploy, verify with:

```bash
# Get alias ARN from Terraform output
terraform -chdir=examples/registry-modules-demo/terraform output alias_arn

# Invoke via alias ARN
aws lambda invoke \
  --function-name "$(terraform -chdir=examples/registry-modules-demo/terraform output -raw alias_arn)" \
  --payload '{"image_id": "img-001", "format": "jpeg", "size_bytes": 1048576}' \
  --cli-binary-format raw-in-base64-out \
  --region us-east-2 \
  response.json && cat response.json
```

Expected output on success:
```json
{"executionId": "...", "status": "RUNNING"}
```

## Teardown Step Content

Teardown via RSF custom provider (calls deploy.sh destroy):

```bash
rsf teardown
```

Or directly via deploy.sh:

```bash
examples/registry-modules-demo/deploy.sh destroy
```

The teardown path in deploy.sh:
1. Calls `generate_tfvars()` — tfvars.json must exist for destroy (Pitfall 5 note: generate_tfvars is called in BOTH deploy and destroy branches)
2. Runs `terraform init -input=false`
3. Runs `terraform destroy -auto-approve -var-file="${TFVARS_FILE}"`

## Prerequisites for Tutorial 09

The reader must have:
- Completed tutorials 01-05 (knows workflow.yaml, rsf generate, rsf deploy with built-in Terraform)
- RSF installed (`pip install rsf` or cloned repo)
- AWS CLI configured with credentials
- Terraform CLI >= 1.5.7 (required by sqs v5.x and sns v7.x)
- `jq` installed (used by deploy.sh for tfvars generation)
- Python 3.13 (for Lambda runtime match)
- Git (to clone the repository)

Verification commands:
```bash
rsf --version
aws sts get-caller-identity
terraform --version  # need >= 1.5.7
jq --version
python3 --version   # need >= 3.13
```

## Common Pitfalls (Documentation Anti-Patterns to Avoid)

These are pitfalls in writing the tutorial itself, not pitfalls in the user's deployment:

- **Do not inline all of deploy.sh** — it is 136 lines. Walk through it in sections with explanatory prose; reference the file for the full content.
- **Do not show full terraform apply output** — it is very long. Show the banner, the "Apply complete! Resources: N added" line, and the alias ARN output.
- **Do not reproduce every .tf file** — show key excerpts with file path references like `(see examples/registry-modules-demo/terraform/main.tf)`.
- **Do not use tabs/columns for HCL comparison** — use consecutive labeled code blocks (locked decision).
- **Include the exact rsf.toml placeholder** — the `/REPLACE/WITH/YOUR/ABSOLUTE/PATH/...` string must appear verbatim so readers know what to look for.

## State of the Art

| Old Approach | Current Approach | Impact on Tutorial |
|--------------|-----------------|-------------------|
| rsf deploy (built-in Terraform) | rsf.toml provider="custom" + deploy.sh | Tutorial 09 teaches the custom provider path, not built-in |
| Inline IAM policies | Hybrid managed + inline (iam_durable.tf) | Pitfall 5 must explain the hybrid approach and why both policies are required |
| $LATEST Lambda invocation | Lambda alias "live" | Alias ARN convention must be explained in verify step |
| Range version constraints (~>) | Exact version strings | Pitfall 4 explains why exact pinning is required for modules |

## Validation Architecture

> nyquist_validation is not explicitly set to false in .planning/config.json — the key is absent, so validation is enabled.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None for documentation phase — tutorial is a Markdown file |
| Quick run command | `test -f tutorials/09-custom-provider-registry-modules.md` |
| Full suite command | manual review against success criteria |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TUT-01 | tutorials/09-custom-provider-registry-modules.md exists with 8-12 numbered steps from prerequisites through teardown | smoke | `test -f tutorials/09-custom-provider-registry-modules.md && grep -c "^## Step" tutorials/09-custom-provider-registry-modules.md` | No — Wave 0 creates it |
| TUT-02 | Side-by-side HCL comparison with labeled consecutive blocks for Lambda and DynamoDB | smoke | `grep -c "RSF TerraformProvider output" tutorials/09-custom-provider-registry-modules.md` — expect >= 2 | No — Wave 0 creates it |
| TUT-03 | WorkflowMetadata schema table with all required fields | smoke | `grep -c "workflow_name\|dynamodb_tables\|dlq_enabled" tutorials/09-custom-provider-registry-modules.md` | No — Wave 0 creates it |
| TUT-04 | Common Pitfalls section with all four documented risks | smoke | `grep -c "Pitfall\|absolute path\|chmod\|create_package\|version pin\|durable IAM" tutorials/09-custom-provider-registry-modules.md` | No — Wave 0 creates it |

### Wave 0 Gaps

- [ ] `tutorials/09-custom-provider-registry-modules.md` — the tutorial itself (Phase 60 deliverable)

*(No test framework gaps — documentation phases verified by smoke grep commands against the output file.)*

## Sources

### Primary (HIGH confidence)

All findings sourced directly from in-repository code. No external verification needed.

- `examples/registry-modules-demo/rsf.toml` — custom provider config, absolute path pitfall
- `examples/registry-modules-demo/deploy.sh` — full deploy/destroy logic, packaging step, generate_tfvars pipeline
- `examples/registry-modules-demo/workflow.yaml` — image-processing workflow definition
- `examples/registry-modules-demo/handlers/validate_image.py` — handler pattern reference
- `examples/registry-modules-demo/terraform/main.tf` — registry module Lambda HCL
- `examples/registry-modules-demo/terraform/dynamodb.tf` — registry module DynamoDB HCL
- `examples/registry-modules-demo/terraform/sqs.tf` — SQS DLQ module
- `examples/registry-modules-demo/terraform/alarms.tf` — CloudWatch alarms
- `examples/registry-modules-demo/terraform/sns.tf` — SNS topic
- `examples/registry-modules-demo/terraform/variables.tf` — variable names for schema table mapping
- `examples/registry-modules-demo/terraform/versions.tf` — exact version pins and rationale
- `examples/registry-modules-demo/terraform/iam_durable.tf` — hybrid IAM rationale
- `examples/registry-modules-demo/terraform/outputs.tf` — alias_arn output for verify step
- `src/rsf/terraform/templates/main.tf.j2` — raw HCL Lambda template for comparison
- `src/rsf/terraform/templates/dynamodb.tf.j2` — raw HCL DynamoDB template for comparison
- `src/rsf/providers/metadata.py` — WorkflowMetadata dataclass with all fields
- `tutorials/04-deploy-to-aws.md` — established tutorial format and tone reference
- `.planning/phases/60-tutorial-document/60-CONTEXT.md` — all locked decisions

### Secondary (MEDIUM confidence)

- `.planning/STATE.md` — Phase decisions log confirming pitfall rationale and version choices

### Tertiary (LOW confidence)

None.

## Metadata

**Confidence breakdown:**
- Tutorial structure: HIGH — all source files read; format established by tutorial 04
- HCL comparison content: HIGH — both raw template and registry module HCL read verbatim
- WorkflowMetadata schema: HIGH — dataclass read from source; deploy.sh jq mapping verified
- Pitfalls documentation: HIGH — all 5 pitfalls traceable to specific source lines
- Step content: HIGH — all file contents available; only prose wording is discretionary

**Research date:** 2026-03-04
**Valid until:** N/A — documentation phase, source files are stable (no external dependencies)
