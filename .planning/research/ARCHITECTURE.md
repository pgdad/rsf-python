# Architecture Research

**Domain:** Terraform Registry Modules Tutorial — Custom Provider Script Integration with RSF
**Researched:** 2026-03-03
**Confidence:** HIGH — based on direct source code analysis of existing RSF codebase + verified registry module documentation

---

## Standard Architecture

### System Overview: RSF v3.0 Provider System (Existing)

```
┌──────────────────────────────────────────────────────────────────────┐
│                           CLI Layer                                  │
│                       rsf deploy workflow.yaml                       │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    deploy_cmd.py pipeline                            │
│                                                                      │
│  load_definition() → codegen_generate() → resolve_infra_config()    │
│      → get_provider() → provider.generate() → provider.deploy()     │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
              ┌──────────────┼───────────────┐
              ▼              ▼               ▼
    ┌──────────────┐ ┌────────────┐ ┌───────────────┐
    │ Terraform    │ │ CDK        │ │ Custom        │
    │ Provider     │ │ Provider   │ │ Provider      │
    │              │ │            │ │               │
    │ generate()   │ │ generate() │ │ generate()    │
    │   → HCL      │ │   → CDK    │ │   → no-op     │
    │ deploy()     │ │ deploy()   │ │ deploy()      │
    │   → tf apply │ │   → cdk    │ │   → exec      │
    └──────────────┘ └────────────┘ │   user script │
                                    └───────┬───────┘
                                            │
                    ┌───────────────────────┤
                    ▼                       ▼
           ┌─────────────┐        ┌─────────────────┐
           │ FileTransport│        │ EnvTransport /  │
           │             │        │ ArgsTransport   │
           │ RSF_METADATA│        │ RSF_WORKFLOW_   │
           │ _FILE=       │        │ NAME, etc.      │
           └─────────────┘        └─────────────────┘
```

### What the Custom Provider Script Receives

When RSF invokes a custom provider script, `WorkflowMetadata` is delivered via the chosen transport. The script is a free-standing executable — shell script, Python script, or any binary.

**WorkflowMetadata fields (as of v3.0):**

```
workflow_name           str           — derived from Comment or file stem
stage                   str | None    — --stage flag value
handler_count           int           — number of Task states
timeout_seconds         int | None    — DSL TimeoutSeconds
triggers                list[dict]    — [{type, schedule_expression, ...}]
dynamodb_tables         list[dict]    — [{table_name, partition_key, ...}]
alarms                  list[dict]    — [{type, threshold, period, ...}]
dlq_enabled             bool
dlq_max_receive_count   int
dlq_queue_name          str | None
lambda_url_enabled      bool
lambda_url_auth_type    str           — "NONE" or "AWS_IAM"
```

**With FileTransport (recommended for Terraform scripts):**

```
RSF_METADATA_FILE=/tmp/rsf_metadata_XXXX.json   (JSON file path, mode 0600)

JSON structure mirrors WorkflowMetadata fields exactly:
{
  "workflow_name": "registry-modules-demo",
  "stage": "dev",
  "handler_count": 3,
  "timeout_seconds": null,
  "triggers": [],
  "dynamodb_tables": [...],
  "alarms": [],
  "dlq_enabled": false,
  ...
}
```

**With EnvTransport:**

```
RSF_WORKFLOW_NAME=registry-modules-demo
RSF_STAGE=dev
RSF_METADATA_JSON={"workflow_name": ...}     (full JSON blob)
```

### Custom Provider Script Interface Contract

A custom provider script must:

1. Accept being called with `[program] + args + transport_extra_args`
2. Exit 0 on success, non-zero on failure (RSF raises CalledProcessError)
3. Write stdout/stderr freely — RSF streams it live to terminal
4. Read metadata from the transport mechanism configured in workflow YAML

A custom provider script must NOT:
- Rely on shell interpolation (RSF always uses `shell=False`)
- Expect interactive TTY input (subprocess has no tty)
- Return data back to RSF (one-way communication only)

### Workflow YAML Configuration for Custom Provider

```yaml
# workflow.yaml
rsf_version: "1.0"
Comment: "Registry modules demo workflow"
StartAt: ProcessOrder

infrastructure:
  provider: custom
  custom:
    program: /absolute/path/to/examples/registry-modules-demo/deploy.sh
    args:
      - deploy
    teardown_args:
      - destroy
    metadata_transport: file   # file | env | args
    env:
      TF_VAR_name_prefix: rsf-registry
```

---

## New Components for v3.2

### What is New vs. Modified vs. Unchanged

**Unchanged (zero changes needed):**

| Component | Why Unchanged |
|-----------|---------------|
| `src/rsf/providers/` — all files | Provider system is already complete and correct |
| `src/rsf/dsl/models.py` | CustomProviderConfig already has all needed fields |
| `src/rsf/cli/deploy_cmd.py` | Already routes through provider system correctly |
| `src/rsf/providers/metadata.py` | WorkflowMetadata already carries all needed fields |
| All existing examples | Not modified by this milestone |
| All existing tutorials | Not modified; new tutorial is additive |

**New (created fresh for v3.2):**

| Component | Description |
|-----------|-------------|
| `examples/registry-modules-demo/` | New example directory — complete self-contained workflow |
| `examples/registry-modules-demo/workflow.yaml` | Workflow with `infrastructure.custom` block |
| `examples/registry-modules-demo/deploy.sh` | Custom provider script — Terraform using registry modules |
| `examples/registry-modules-demo/terraform/main.tf` | Root module using terraform-aws-modules/lambda/aws |
| `examples/registry-modules-demo/terraform/dynamodb.tf` | Using terraform-aws-modules/dynamodb-table/aws |
| `examples/registry-modules-demo/terraform/sqs.tf` | DLQ using terraform-aws-modules/sqs/aws |
| `examples/registry-modules-demo/terraform/variables.tf` | Input variables for registry module parameters |
| `examples/registry-modules-demo/terraform/outputs.tf` | Outputs (function_arn, function_name, etc.) |
| `examples/registry-modules-demo/terraform/versions.tf` | Required providers with pinned versions |
| `examples/registry-modules-demo/handlers/` | Python handler functions |
| `examples/registry-modules-demo/tests/test_local.py` | Local unit tests (no AWS) |
| `examples/registry-modules-demo/README.md` | Example documentation |
| `tutorials/09-custom-provider-registry-modules.md` | Step-by-step tutorial |
| `tests/test_examples/test_registry_modules_demo.py` | Integration test (real AWS) |

**Potentially modified (only if friction points found during build):**

| Component | Possible Change | Trigger |
|-----------|-----------------|---------|
| `src/rsf/providers/metadata.py` | Add `source_dir` or `zip_path` field to WorkflowMetadata | If custom scripts need the output_dir to find the Lambda zip |
| `src/rsf/providers/custom.py` | Add `cwd` config option to CustomProviderConfig | If scripts need to run from the example directory rather than workflow directory |

---

## Recommended Project Structure

```
examples/
└── registry-modules-demo/          # NEW example directory
    ├── workflow.yaml               # RSF DSL + infrastructure.custom block
    ├── deploy.sh                   # Custom provider entry point (chmod +x)
    ├── handlers/                   # Python @state-decorated handlers
    │   ├── __init__.py
    │   ├── validate_input.py
    │   ├── process_record.py
    │   └── store_result.py
    ├── src/                        # Auto-generated code lives here
    │   └── generated/
    │       └── orchestrator.py     # Generated by rsf generate
    ├── terraform/                  # Registry-modules-based HCL
    │   ├── main.tf                 # module "lambda" { source = "terraform-aws-modules/lambda/aws" }
    │   ├── dynamodb.tf             # module "table" { source = "terraform-aws-modules/dynamodb-table/aws" }
    │   ├── sqs.tf                  # module "dlq" { source = "terraform-aws-modules/sqs/aws" }
    │   ├── variables.tf            # Input vars (name_prefix, aws_region, workflow_name, ...)
    │   ├── outputs.tf              # function_arn, function_name, role_arn, log_group_name
    │   ├── versions.tf             # terraform { required_providers { aws >= 6.25.0 } }
    │   └── backend.tf              # Local state (same as existing examples)
    ├── tests/
    │   ├── conftest.py             # Mock SDK fixtures
    │   └── test_local.py           # Unit tests (no AWS required)
    └── README.md                   # Example documentation

tutorials/
└── 09-custom-provider-registry-modules.md   # NEW tutorial

tests/
└── test_examples/
    └── test_registry_modules_demo.py        # NEW integration test
```

### Structure Rationale

- **`examples/registry-modules-demo/`** follows the identical layout as the five existing examples (`order-processing`, `data-pipeline`, etc.). Users navigating examples see a consistent structure. The README documents the registry modules approach specifically.
- **`deploy.sh` at example root (not inside terraform/)** — the script is the RSF-facing entry point. It is in the workflow's directory so the `program` path in workflow.yaml can be resolved relative to it. The script cd's into `terraform/` internally.
- **`terraform/` subdirectory** — mirrors the existing examples. The distinction from existing examples is the HCL content: registry module `source` blocks instead of direct `aws_lambda_function` resources.
- **Tutorial at `tutorials/09-custom-provider-registry-modules.md`** — continues the tutorial numbering sequence (08 is execution inspector). There is no `tutorials/` subdirectory for examples; tutorials are flat markdown files.
- **No `tutorials/registry-modules/` subdirectory** — existing tutorials are single flat files. Creating a subdirectory breaks the numbering convention and makes navigation harder.

---

## Architectural Patterns

### Pattern 1: Custom Provider Script as Thin Terraform Wrapper

**What:** The deploy script is not a replacement for RSF's Terraform provider — it is a user-space Terraform wrapper that reads RSF metadata and passes it to Terraform as `-var` flags or a `.tfvars` file. This is the pedagogically correct pattern: show students that any program can be a provider.

**When to use:** When showing how custom providers integrate with Terraform registry modules.

**Trade-offs:** Slightly more indirection than the built-in TerraformProvider, but that is intentional — the point is to show the interface.

**Example:**

```bash
#!/usr/bin/env bash
# deploy.sh — custom provider script for registry-modules-demo
# Reads RSF metadata via RSF_METADATA_FILE and runs terraform apply.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="${SCRIPT_DIR}/terraform"
COMMAND="${1:-deploy}"

# Read metadata from RSF_METADATA_FILE (FileTransport)
METADATA_FILE="${RSF_METADATA_FILE:?RSF_METADATA_FILE not set}"
WORKFLOW_NAME="$(python3 -c "import json,sys; d=json.load(open('${METADATA_FILE}')); print(d['workflow_name'])")"
STAGE="$(python3 -c "import json,sys; d=json.load(open('${METADATA_FILE}')); print(d['stage'] or '')")"

case "${COMMAND}" in
  deploy)
    terraform -chdir="${TF_DIR}" init -upgrade
    terraform -chdir="${TF_DIR}" apply \
      -var="workflow_name=${WORKFLOW_NAME}" \
      -var="stage=${STAGE}" \
      -auto-approve
    ;;
  destroy)
    terraform -chdir="${TF_DIR}" destroy \
      -var="workflow_name=${WORKFLOW_NAME}" \
      -var="stage=${STAGE}" \
      -auto-approve
    ;;
  *)
    echo "Unknown command: ${COMMAND}" >&2
    exit 1
    ;;
esac
```

### Pattern 2: Registry Module HCL Instead of Direct Resources

**What:** Replace `resource "aws_lambda_function"` with `module "lambda"` using `terraform-aws-modules/lambda/aws`. This is the structural difference between the existing examples and the new example.

**When to use:** When demonstrating HashiCorp's registry module ecosystem.

**Trade-offs:** Registry modules abstract away boilerplate (IAM, packaging, CloudWatch) at the cost of less visible resource definitions. The trade-off is acceptable for a tutorial — students learn the module interface, not raw HCL.

**Example:**

```hcl
# terraform/main.tf (registry modules approach)

module "lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 7.0"

  function_name = "${var.name_prefix}-${var.workflow_name}"
  handler       = "generated.orchestrator.lambda_handler"
  runtime       = "python3.13"

  # Pre-built package: RSF generates the zip, we point the module at it
  create_package        = false
  local_existing_package = "${path.module}/../src/generated.zip"

  # Lambda Durable Functions support (added in module ~7.x)
  durable_config_execution_timeout = 86400
  durable_config_retention_period  = 14

  # IAM — module creates the role automatically
  attach_cloudwatch_logs_policy = true
  cloudwatch_logs_retention_in_days = 14

  # DLQ (if dlq_enabled in metadata)
  dead_letter_target_arn = var.dlq_enabled ? module.dlq[0].queue_arn : null
  attach_dead_letter_policy = var.dlq_enabled

  environment_variables = {
    RSF_WORKFLOW_NAME = var.workflow_name
    RSF_STAGE         = var.stage
  }
}

module "dynamodb_table" {
  source  = "terraform-aws-modules/dynamodb-table/aws"
  version = "~> 4.0"

  name         = "${var.name_prefix}-${var.workflow_name}-store"
  hash_key     = "pk"
  billing_mode = "PAY_PER_REQUEST"

  attributes = [
    { name = "pk", type = "S" }
  ]
}

module "dlq" {
  source  = "terraform-aws-modules/sqs/aws"
  version = "~> 4.0"

  count = var.dlq_enabled ? 1 : 0
  name  = "${var.name_prefix}-${var.workflow_name}-dlq"
}
```

### Pattern 3: Split Deploy/Destroy Commands in One Script

**What:** The RSF `CustomProviderConfig` supports `args` (deploy) and `teardown_args` (teardown) as separate argument lists. Both invoke the same `program`. The script dispatches on its first argument.

**When to use:** Always for custom provider scripts that manage Terraform state. Teardown must be supported for integration tests to clean up.

**Trade-offs:** Single script with `$1` dispatch is simpler than two separate scripts. Integration tests require teardown to work correctly.

**The workflow YAML configuration:**

```yaml
infrastructure:
  provider: custom
  custom:
    program: /path/to/examples/registry-modules-demo/deploy.sh
    args:
      - deploy
    teardown_args:
      - destroy
    metadata_transport: file
```

### Pattern 4: No Changes to RSF Core — Pure User-Space Integration

**What:** The tutorial demonstrates that adding a new Terraform approach requires zero changes to RSF itself. The custom provider system was designed to be extensible at the user level.

**When to use:** This is the architectural proof that the v3.0 provider system works as intended.

**Implication for build order:** The example and tutorial are built entirely outside of `src/rsf/`. No RSF source files are modified. All work is in `examples/registry-modules-demo/` and `tutorials/`.

---

## Data Flow

### Deploy Flow — Custom Provider with Registry Modules

```
rsf deploy examples/registry-modules-demo/workflow.yaml
    │
    ▼
load_definition(workflow.yaml)
    → StateMachineDefinition
    → infrastructure.provider = "custom"
    → infrastructure.custom.program = "/path/to/deploy.sh"
    → infrastructure.custom.metadata_transport = "file"
    │
    ▼
codegen_generate(definition)
    → src/generated/orchestrator.py
    → handlers/validate_input.py (created if not exists)
    │
    ▼
resolve_infra_config(definition, workflow.parent)
    → InfrastructureConfig(provider="custom", custom=CustomProviderConfig(...))
    │
    ▼
get_provider("custom")
    → CustomProvider instance
    │
    ▼
CustomProvider.check_prerequisites(ctx)
    → checks deploy.sh exists and is executable
    │
    ▼
CustomProvider.generate(ctx)   [no-op — custom providers don't generate code]
    │
    ▼
CustomProvider.deploy(ctx)
    │
    ├── _get_config(ctx) → CustomProviderConfig
    ├── _validate_program(config.program) → Path (absolute, exists, executable)
    ├── _create_transport(config) → FileTransport
    │
    ├── FileTransport.prepare(metadata, env)
    │   → writes /tmp/rsf_metadata_XXXX.json
    │   → sets env["RSF_METADATA_FILE"] = "/tmp/rsf_metadata_XXXX.json"
    │
    ├── cmd = ["/path/to/deploy.sh", "deploy"]
    │
    └── run_provider_command_streaming(cmd, cwd=workflow.parent, env=env)
        │
        └── subprocess.run(cmd, shell=False, ...)   [streams to terminal]
                │
                ▼
        deploy.sh receives RSF_METADATA_FILE in environment
                │
                ▼
        deploy.sh reads metadata JSON → extracts workflow_name, stage
                │
                ▼
        terraform init → terraform apply
        (using registry module HCL in terraform/)
```

### Teardown Flow

```
rsf teardown (or integration test cleanup)
    │
    ▼
CustomProvider.teardown(ctx)
    │
    ├── config.teardown_args = ["destroy"]
    ├── cmd = ["/path/to/deploy.sh", "destroy"]
    └── run_provider_command_streaming(cmd, ...)
            │
            ▼
    deploy.sh "destroy" → terraform destroy -auto-approve
```

### Integration Test Flow

```
pytest tests/test_examples/test_registry_modules_demo.py -m integration
    │
    ▼
@pytest.fixture(scope="class") setup
    → subprocess.run(["rsf", "deploy", ..., "--auto-approve"])
    → poll_execution() until complete
    → query_logs() for CloudWatch assertions
    │
    ▼
test assertions (same pattern as existing integration tests)
    │
    ▼
@pytest.fixture teardown
    → subprocess.run(["rsf", "teardown", ...])   OR
    → deploy.sh destroy (direct invocation)
    → delete_log_group() for orphaned logs
```

---

## Integration Points

### Integration Point 1: workflow.yaml `infrastructure.custom` Block

This is the primary integration seam. The workflow YAML declares what RSF needs to do; the `custom` block tells RSF how to do it.

**Key field:** `program` must be an absolute path. Since the example ships inside the repository, the tutorial must show students how to use `$(pwd)` or `realpath` to construct the absolute path before running `rsf deploy`.

**Resolution:** Two approaches are viable:
1. Teach students to set `program` in `rsf.toml` (project-wide) using an absolute path derived from their environment.
2. Show a setup step: `echo "program = \"$(pwd)/deploy.sh\"" >> rsf.toml`.

Approach 2 is more tutorial-friendly.

### Integration Point 2: WorkflowMetadata JSON Schema

The custom script must parse `RSF_METADATA_FILE`. The metadata schema is stable and defined in `src/rsf/providers/metadata.py`. The tutorial should show the exact JSON shape students can expect and explain each field.

**Key concern:** `handler_count` is the number of Task states, not the number of handler Python files. The script may use this to set Lambda memory or concurrency, but it should not use it to count files on disk.

### Integration Point 3: Lambda Zip Packaging

The terraform-aws-modules/lambda/aws module has two deployment modes:
- `create_package = true` — module builds the zip itself (uses Python/pip internally)
- `create_package = false` + `local_existing_package = "path/to/file.zip"` — module deploys a pre-built zip

RSF generates the orchestrator and handler Python files but does not produce a zip. The deploy script must zip the source before Terraform runs. This is a step the custom script handles, not RSF.

**The deploy script must:**

```bash
# Before terraform apply
cd "${SCRIPT_DIR}/src"
zip -r generated.zip generated/ handlers/ -x "*.pyc" -x "__pycache__/*"
cd "${SCRIPT_DIR}"
```

Then the Terraform `local_existing_package` points to this zip.

**Alternative:** Use `create_package = true` with `source_path` pointing to the `src/` directory. The module will use pip to install dependencies. Simpler for the tutorial but requires pip in the Terraform environment.

Recommendation: Use `create_package = false` with an explicit zip step in the deploy script. This gives students full visibility into the packaging process and matches how production deployments work.

### Integration Point 4: durable_config in terraform-aws-modules/lambda/aws

The module supports Lambda Durable Functions via:

```hcl
durable_config_execution_timeout = var.execution_timeout   # seconds, 1–31622400
durable_config_retention_period  = var.retention_period    # days, 1–90
```

This was confirmed from the module's `variables.tf` (GitHub source). The module wraps the `durable_config` block in the `aws_lambda_function` resource.

**Confidence: HIGH** — verified directly from `terraform-aws-modules/terraform-aws-lambda` `variables.tf`.

### Integration Point 5: IAM Permissions for Durable Execution

The terraform-aws-modules/lambda/aws module creates an IAM role automatically. However, it may not include the durable execution permissions by default. The deploy script's Terraform must attach an additional inline policy:

```hcl
resource "aws_iam_role_policy" "durable_execution" {
  name = "${module.lambda.lambda_function_name}-durable"
  role = module.lambda.lambda_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "lambda:CheckpointDurableExecution",
        "lambda:GetDurableExecution",
        "lambda:ListDurableExecutionsByFunction",
        "lambda:InvokeFunction"
      ]
      Resource = module.lambda.lambda_function_arn
    }]
  })
}
```

**Note:** This is the same IAM grant that RSF's built-in TerraformProvider generates in `iam.tf`. The tutorial must show students they are responsible for this permission when using a custom provider.

### Integration Point 6: Tests for the New Example

The new example follows the exact same test pattern as existing examples:

```
examples/registry-modules-demo/tests/test_local.py   — unit tests, no AWS
tests/test_examples/test_registry_modules_demo.py    — integration test, real AWS
```

The integration test uses the same `poll_execution()`, `query_logs()`, and teardown helpers as existing integration tests. No new test infrastructure is needed.

---

## Suggested Build Order

Dependencies determine the order. Since no RSF core files change, all work is in the example directory and tutorial.

```
Phase 1: Core example files (deploy + Terraform)
  1. examples/registry-modules-demo/workflow.yaml
     — defines the workflow and custom provider config
  2. examples/registry-modules-demo/deploy.sh
     — the provider script; drives everything else
  3. examples/registry-modules-demo/terraform/versions.tf
     — pinned provider versions first (gates everything else)
  4. examples/registry-modules-demo/terraform/variables.tf
     — input vars needed by all other .tf files
  5. examples/registry-modules-demo/terraform/main.tf
     — lambda module + durable_config + IAM
  6. examples/registry-modules-demo/terraform/outputs.tf
     — integration test needs function_name output

Phase 2: Optional infra (DynamoDB, DLQ, alarms)
  7. examples/registry-modules-demo/terraform/dynamodb.tf
     — optional; include if workflow uses dynamodb_tables
  8. examples/registry-modules-demo/terraform/sqs.tf
     — optional; include if workflow uses dead_letter_queue

Phase 3: Python application code
  9. examples/registry-modules-demo/handlers/*.py
     — handler functions that make the example meaningful
 10. rsf generate examples/registry-modules-demo/workflow.yaml
     — generates src/generated/orchestrator.py

Phase 4: Tests
 11. examples/registry-modules-demo/tests/conftest.py
     — mock SDK fixtures (copy pattern from existing examples)
 12. examples/registry-modules-demo/tests/test_local.py
     — unit tests (no AWS)
 13. tests/test_examples/test_registry_modules_demo.py
     — integration test (real AWS, last because it requires all above)

Phase 5: Documentation
 14. examples/registry-modules-demo/README.md
     — what the example demonstrates, how to run it
 15. tutorials/09-custom-provider-registry-modules.md
     — step-by-step tutorial for students
```

### Build Order Rationale

- `versions.tf` before `main.tf` — Terraform fails if provider version constraints are missing during `init`.
- `variables.tf` before all other `.tf` files — variables are referenced everywhere.
- Handler code before `rsf generate` — generate creates stubs only for missing handlers; existing handlers are preserved.
- Integration test last — it depends on all other pieces being correct and the AWS provider being >= 6.25.0.
- Tutorial last — it describes what was built; writing it last ensures accuracy.

---

## New vs. Modified Components (Explicit Summary)

| Component | Status | Notes |
|-----------|--------|-------|
| `src/rsf/providers/` | UNCHANGED | No modifications needed |
| `src/rsf/dsl/models.py` | UNCHANGED | CustomProviderConfig is complete |
| `src/rsf/cli/deploy_cmd.py` | UNCHANGED | Already handles custom provider |
| `src/rsf/providers/metadata.py` | UNCHANGED | WorkflowMetadata is sufficient |
| `examples/registry-modules-demo/` | NEW | Full example directory |
| `examples/registry-modules-demo/deploy.sh` | NEW | Core deliverable: provider script |
| `examples/registry-modules-demo/terraform/` | NEW | Registry modules HCL (not generated by RSF) |
| `examples/registry-modules-demo/workflow.yaml` | NEW | Workflow with custom provider config |
| `examples/registry-modules-demo/handlers/` | NEW | Python handler stubs (then implemented) |
| `examples/registry-modules-demo/tests/` | NEW | Unit + integration tests |
| `examples/registry-modules-demo/README.md` | NEW | Example documentation |
| `tutorials/09-custom-provider-registry-modules.md` | NEW | Tutorial document |
| `tests/test_examples/test_registry_modules_demo.py` | NEW | Integration test |

---

## Anti-Patterns

### Anti-Pattern 1: Using a Relative Path for `program` in workflow.yaml

**What people do:** Set `program: ./deploy.sh` in the workflow YAML.

**Why it's wrong:** CustomProvider validates that `program` is an absolute path and raises `ValueError` before the script runs. The cwd at execution time is the workflow's parent directory, which varies per user installation.

**Do this instead:** Show students to use an absolute path derived at setup time:
```bash
EXAMPLE_DIR="$(cd examples/registry-modules-demo && pwd)"
# Then set program: in workflow.yaml or rsf.toml using the absolute path
```

Or configure via `rsf.toml` (which allows environment-specific configuration without editing the versioned `workflow.yaml`).

### Anti-Pattern 2: Generating Terraform HCL in the Custom Script

**What people do:** Have the deploy script use Python/Jinja2 to generate `.tf` files before running `terraform apply`.

**Why it's wrong:** This duplicates RSF's existing TerraformProvider behavior. It conflates code generation with deployment. The tutorial's purpose is to show registry modules as an *alternative* to RSF's generated HCL — not to recreate RSF's generator in a script.

**Do this instead:** Write the registry module `.tf` files statically in `terraform/`. The deploy script only invokes `terraform init` and `terraform apply`. The Terraform files are version-controlled, human-readable, and never regenerated.

### Anti-Pattern 3: Putting the Script Inside `terraform/`

**What people do:** Place `deploy.sh` inside `examples/registry-modules-demo/terraform/deploy.sh`.

**Why it's wrong:** The script is the RSF-facing interface; it belongs at the workflow root. The `terraform/` directory is an artifact directory (HCL files, `.terraform/`, state). Mixing the provider script with Terraform artifacts confuses the structure.

**Do this instead:** `deploy.sh` at `examples/registry-modules-demo/deploy.sh`. It `cd`s into `terraform/` internally.

### Anti-Pattern 4: Hardcoding AWS Region and Account in Terraform

**What people do:** Set `aws_region = "us-east-2"` directly in `main.tf`.

**Why it's wrong:** The existing RSF examples use variables for region. Hardcoding region makes the example non-portable and breaks for users in other regions.

**Do this instead:** Use `variable "aws_region"` with a default, and show students how to override it via `TF_VAR_aws_region` or `terraform.tfvars`.

### Anti-Pattern 5: Skipping `teardown_args` in CustomProviderConfig

**What people do:** Only configure `args` for deploy, omitting `teardown_args`.

**Why it's wrong:** Without `teardown_args`, `CustomProvider.teardown()` raises `NotImplementedError`. The integration test teardown fixture calls teardown unconditionally — if it fails, AWS resources are orphaned and the test harness reports a cryptic error.

**Do this instead:** Always configure both `args` and `teardown_args`. The tutorial must show both. The deploy script dispatches on `$1` to handle both.

---

## Scaling Considerations

This is a local developer tool. Scaling concerns are code maintainability, not user load.

| Concern | Implication |
|---------|-------------|
| Adding more registry module examples | Each is independent; no shared state. Pattern established here is reusable. |
| Terraform module version upgrades | Pin versions in `versions.tf` with `~>` constraints. Tutorial should show how to upgrade. |
| Multi-module Terraform root | Starting with one root module per example keeps state management simple. |
| Lambda zip size | Use `source_path` with `pip_requirements` in the module if dependencies are large. Out of scope for initial tutorial. |

---

## Sources

- Direct source analysis: `src/rsf/providers/custom.py` — CustomProvider.deploy(), validate_program(), _create_transport()
- Direct source analysis: `src/rsf/providers/metadata.py` — WorkflowMetadata fields (11 fields confirmed)
- Direct source analysis: `src/rsf/providers/transports.py` — FileTransport, EnvTransport, ArgsTransport
- Direct source analysis: `src/rsf/providers/base.py` — ProviderContext, InfrastructureProvider ABC
- Direct source analysis: `src/rsf/dsl/models.py` — CustomProviderConfig fields confirmed
- Direct source analysis: `src/rsf/cli/deploy_cmd.py` — deploy pipeline confirmed; routes correctly to custom provider
- Direct source analysis: `examples/order-processing/` — example directory structure (canonical reference)
- Direct source analysis: `tests/test_providers/test_custom_integration.py` — confirms security hardening and interface contract
- GitHub: `terraform-aws-modules/terraform-aws-lambda` `variables.tf` — confirmed `durable_config_execution_timeout` and `durable_config_retention_period` inputs ([terraform-aws-modules/lambda/aws](https://registry.terraform.io/modules/terraform-aws-modules/lambda/aws/latest))
- GitHub: `terraform-aws-modules/terraform-aws-lambda` complete example — confirmed `create_package = false` + `local_existing_package` pattern
- Terraform Registry: [terraform-aws-modules/dynamodb-table/aws](https://registry.terraform.io/modules/terraform-aws-modules/dynamodb-table/aws/latest)
- Terraform Registry: [terraform-aws-modules/sqs/aws](https://registry.terraform.io/modules/terraform-aws-modules/sqs/aws/latest)
- `.planning/PROJECT.md` — v3.2 milestone scope and constraints

---

*Architecture research for: RSF v3.2 Terraform Registry Modules Tutorial*
*Researched: 2026-03-03*
