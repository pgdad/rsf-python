# Phase 57: Core Lambda Example - Research

**Researched:** 2026-03-04
**Domain:** RSF custom provider integration, Bash deploy script design, Terraform registry module Lambda deployment, workflow scenario design, rsf.toml configuration, CLI teardown gap
**Confidence:** HIGH (primary sources: live codebase inspection, Phase 56 verified findings, official Terraform/AWS docs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Workflow scenario:** Claude's discretion on specific business logic — pick a scenario that naturally exercises multiple Task states and is interesting enough for a tutorial. Moderate complexity (4-5 states). Must include at least one Retry/Catch block. Workflow YAML declares DynamoDB table and DLQ configuration (for Phase 58 Terraform) but Phase 57 only implements Lambda + IAM Terraform.

**Deploy script design:**
- Bash script: `deploy.sh` starting with `set -euo pipefail`
- Single script with first-argument dispatch: `deploy.sh deploy` → zip + terraform apply, `deploy.sh destroy` → terraform destroy
- rsf.toml sets `args = ["deploy"]` and `teardown_args = ["destroy"]`
- deploy.sh runs `terraform init` automatically before apply/destroy (idempotent, no separate step)
- deploy.sh captures terraform output and prints the alias invoke ARN with a sample invocation command after successful deploy

**Metadata translation:** Claude's discretion on jq vs tfvars.json approach — pick what's simplest and most reliable for tutorial readers.

**Terraform file layout:**
- Split files: `main.tf` (lambda module + alias), `iam_durable.tf` (managed policy attachment + inline supplement), `variables.tf` (inputs), `outputs.tf` (alias ARN, function name, role ARN)
- `versions.tf` already exists from Phase 56 — do not recreate
- Local backend (no S3 setup needed) — state file is gitignored
- Must verify `AWSLambdaBasicDurableExecutionRolePolicy` availability in us-east-2 before writing iam_durable.tf — fallback to all-inline if unavailable

**Handler implementation:**
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PROV-01 | Custom provider Python script reads WorkflowMetadata via FileTransport and invokes terraform apply | FileTransport writes JSON to RSF_METADATA_FILE; deploy.sh reads this path; confirmed from transports.py and custom.py source |
| PROV-02 | rsf.toml configures provider="custom" with absolute path, FileTransport, and teardown_args | rsf.toml loads via config.py resolve_infra_config(); CustomProviderConfig model confirmed; metadata_transport="file" is default |
| PROV-03 | Deploy script handles both deploy and teardown via command dispatch argument | Single-arg dispatch (deploy.sh deploy / deploy.sh destroy) maps to args/teardown_args in rsf.toml; teardown path requires --teardown CLI flag (TOOL-01 gap) |
| PROV-04 | Deploy script zips RSF-generated source before terraform apply (resolves packaging conflict) | zip pattern confirmed from Phase 56: src/generated/ + handlers/ into build/function.zip; create_package=false prevents module zip conflict |
| REG-01 | Lambda deployed via terraform-aws-modules/lambda/aws with durable_config and create_package=false | All module parameters confirmed from Phase 56 SCHEMA-FINDINGS.md: exact variable names, coalesce() guard, alias convention, attach_policies triple |
| EXAM-01 | New example workflow YAML with Task states, DynamoDB table, and DLQ configuration | Workflow DSL confirmed: StateMachineDefinition with dynamodb_tables + dead_letter_queue fields; existing order-processing YAML is reference pattern |
| EXAM-02 | Example follows RSF directory convention (workflow.yaml, handlers/, tests/, terraform/, README.md) | order-processing confirms convention; deploy.sh and rsf.toml are new additions unique to custom provider |
| EXAM-03 | Example handlers implement business logic with structured logging | validate_order.py pattern: @state decorator + stdlib logging + json.dumps structured log; one file per Task state |
| TOOL-01 | Fix custom provider friction points discovered during tutorial development | GAP CONFIRMED: rsf deploy has no --teardown flag; teardown() exists on CustomProvider but deploy_cmd.py has no CLI path to invoke it |
</phase_requirements>

---

## Summary

Phase 57 constructs the complete `examples/registry-modules-demo/` example from scratch on top of the Phase 56 scaffold (`versions.tf`, `.gitignore`). The phase has three parallel tracks: (1) the RSF workflow YAML + Python handlers, (2) the Terraform files (`main.tf`, `iam_durable.tf`, `variables.tf`, `outputs.tf`, `backend.tf`), and (3) the integration layer (`deploy.sh`, `rsf.toml`, `README.md`). A fourth track handles TOOL-01: adding `--teardown` to `rsf deploy`.

The most important pre-implementation step is verifying that `AWSLambdaBasicDurableExecutionRolePolicy` is available in us-east-2. This check requires live AWS credentials (`aws iam get-policy ...`). If the policy is unavailable, `iam_durable.tf` falls back to all-inline IAM. Credentials were expired during research; Phase 57 Wave 0 must run this check before writing any IAM Terraform.

A critical gap discovered during research: `rsf deploy` has no `--teardown` flag. The `teardown()` method exists on `CustomProvider` (and all providers), but `deploy_cmd.py` never calls it. The TOOL-01 requirement canonically maps to adding `rsf deploy --teardown` as a CLI flag that routes to `provider.teardown(ctx)`. This is a small change to one file (`deploy_cmd.py`) and its test (`test_deploy.py`), but it is a prerequisite for the success criterion "rsf deploy --teardown destroys all AWS resources."

**Primary recommendation:** Build in wave order — TOOL-01 (teardown CLI flag) first so the teardown success criterion can be tested end-to-end, then workflow YAML + handlers, then Terraform, then deploy.sh + rsf.toml, then README.

---

## Standard Stack

### Core — RSF Custom Provider Integration

| Component | Version/Location | Purpose | Why Standard |
|-----------|-----------------|---------|--------------|
| `src/rsf/providers/custom.py` | v3.0 (current) | Invokes deploy.sh via shell=False subprocess | Already implemented; deploy() + teardown() dispatch via args/teardown_args |
| `src/rsf/providers/transports.py` | current | FileTransport writes metadata JSON, sets RSF_METADATA_FILE | FileTransport is canonical for list/dict metadata fields |
| `src/rsf/config.py` | current | Loads rsf.toml and resolves infrastructure config | Priority cascade: YAML > rsf.toml > default |
| `src/rsf/dsl/models.py` | current | CustomProviderConfig, InfrastructureConfig, StateMachineDefinition | Pydantic models validate rsf.toml and workflow YAML |
| `terraform-aws-modules/lambda/aws` | 8.7.0 (exact) | Lambda function + IAM role + log group via registry module | Confirmed from Phase 56; first version with durable_config support |

### Supporting

| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| `aws_lambda_alias` resource | AWS provider >= 6.25.0 | Create "live" alias; invoke by alias ARN (never $LATEST) | Required while Terraform issue #45800 is open |
| jq | system | Extract fields from RSF_METADATA_FILE JSON in deploy.sh | Simpler than writing a Python shim for metadata-to-tfvars |
| `bash set -euo pipefail` | bash | Propagate terraform failure exit code to rsf deploy | Required by PROV-03 success criterion |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| jq for metadata extraction | Python script for tfvars.json | Python is more verbose but eliminates jq dependency. jq is simpler for tutorial readers and universally available on Linux/macOS. Choose jq. |
| stdlib logging JSON | print-based JSON | stdlib logging is more idiomatic Python; print-based is simpler for handlers. Use stdlib logging (matches order-processing pattern). |
| Local backend (default) | S3 backend | S3 requires pre-created bucket. Local backend is zero-config for tutorial. Use local backend. |

---

## Architecture Patterns

### Recommended Project Structure

```
examples/registry-modules-demo/
├── deploy.sh                         # chmod +x; absolute path in rsf.toml
├── rsf.toml                          # provider="custom"; args=["deploy"]; teardown_args=["destroy"]
├── workflow.yaml                     # RSF DSL; 4-5 Task states; DynamoDB + DLQ declared
├── handlers/
│   ├── __init__.py                   # imports all @state-decorated handlers
│   ├── step_one.py                   # one file per Task state
│   ├── step_two.py
│   ├── step_three.py
│   └── step_four.py
├── tests/
│   ├── conftest.py                   # registry clear + module cache purge (order-processing pattern)
│   └── test_handlers.py              # pytest tests for happy path handler logic
├── terraform/
│   ├── versions.tf                   # EXISTS (Phase 56 deliverable — do not touch)
│   ├── main.tf                       # lambda module + alias resource
│   ├── iam_durable.tf                # managed policy attach + inline supplement
│   ├── variables.tf                  # workflow_name, execution_timeout, aws_region, name_prefix
│   ├── outputs.tf                    # alias_arn, function_name, role_arn
│   └── backend.tf                    # local backend comment (matches order-processing pattern)
├── build/                            # gitignored; created by deploy.sh zip step
│   └── function.zip                  # RSF orchestrator + handler source
└── README.md                         # example overview + quick start
```

### Pattern 1: rsf.toml Configuration for Custom Provider

**What:** rsf.toml provides InfrastructureConfig to RSF when the workflow YAML has no `infrastructure:` block. For tutorial clarity, put all provider config in rsf.toml (not workflow.yaml), keeping the workflow YAML focused on workflow logic.

**When to use:** Always for custom provider examples — separates deployment concern from workflow logic.

```toml
# examples/registry-modules-demo/rsf.toml
# Source: src/rsf/dsl/models.py CustomProviderConfig + src/rsf/config.py
[infrastructure]
provider = "custom"

[infrastructure.custom]
program = "/absolute/path/to/examples/registry-modules-demo/deploy.sh"
args = ["deploy"]
teardown_args = ["destroy"]
metadata_transport = "file"
```

**CRITICAL:** `program` must be an absolute path. `validate_config()` in custom.py checks `Path(config.program).is_absolute()` and raises ValueError if not. The planner should document that tutorial users must set this to the absolute path on their machine.

**Resolution approach:** Use a Makefile target or shell alias to auto-generate the absolute path, OR use `$(pwd)/deploy.sh` in a wrapper. For simplicity in Phase 57, document that users run `rsf deploy` from the example directory and the rsf.toml has a placeholder that they replace with their absolute path.

### Pattern 2: deploy.sh Structure with First-Argument Dispatch

**What:** Single Bash script handles both deploy and destroy via `$1` dispatch. RSF CustomProvider passes `args = ["deploy"]` or `teardown_args = ["destroy"]` as the first argument.

```bash
#!/usr/bin/env bash
# examples/registry-modules-demo/deploy.sh
# Source: CONTEXT.md decisions + custom.py implementation
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="${SCRIPT_DIR}/terraform"
BUILD_DIR="${SCRIPT_DIR}/build"
METADATA_FILE="${RSF_METADATA_FILE}"   # Set by RSF FileTransport

CMD="${1:-deploy}"

# ── Metadata extraction ────────────────────────────────────────────────────────
WORKFLOW_NAME=$(jq -r '.workflow_name' "${METADATA_FILE}")
EXECUTION_TIMEOUT=$(jq -r '.timeout_seconds // 86400' "${METADATA_FILE}")

# ── Dispatch ───────────────────────────────────────────────────────────────────
case "${CMD}" in
  deploy)
    # Step 1: Zip RSF-generated source + handlers
    mkdir -p "${BUILD_DIR}"
    cd "${SCRIPT_DIR}"
    zip -r "${BUILD_DIR}/function.zip" src/generated/ handlers/ \
      -x "**/__pycache__/*" "**/*.pyc"
    echo "Packaged function.zip"

    # Step 2: Terraform init + apply
    cd "${TF_DIR}"
    terraform init -input=false
    terraform apply -auto-approve \
      -var="workflow_name=${WORKFLOW_NAME}" \
      -var="execution_timeout=${EXECUTION_TIMEOUT}"

    # Step 3: Print alias ARN for immediate use
    ALIAS_ARN=$(terraform output -raw alias_arn)
    echo ""
    echo "Deploy complete. Invoke your durable function:"
    echo "  aws lambda invoke --function-name ${ALIAS_ARN} \\"
    echo "    --payload '{\"example\": \"input\"}' \\"
    echo "    --cli-binary-format raw-in-base64-out \\"
    echo "    response.json"
    ;;

  destroy)
    cd "${TF_DIR}"
    terraform init -input=false
    terraform destroy -auto-approve \
      -var="workflow_name=${WORKFLOW_NAME}" \
      -var="execution_timeout=${EXECUTION_TIMEOUT}"
    echo "Teardown complete."
    ;;

  *)
    echo "Unknown command: ${CMD}. Use 'deploy' or 'destroy'." >&2
    exit 1
    ;;
esac
```

**Key properties:**
- `set -euo pipefail` — terraform non-zero exit propagates to rsf deploy (success criterion 5)
- `SCRIPT_DIR` computed via `${BASH_SOURCE[0]}` — works when invoked from any directory
- `terraform init -input=false` runs before both apply and destroy (idempotent)
- Alias ARN printed after successful deploy (success criterion 4 + tutorial UX)
- Unknown command exits non-zero (defensive)

### Pattern 3: Metadata-to-Terraform via jq + CLI Variables

**Recommendation:** Use jq to extract fields from `RSF_METADATA_FILE` and pass them as `terraform apply -var="name=value"` arguments. Do NOT generate a tfvars.json file (more complex, harder to trace in tutorial).

**Why jq over tfvars.json:**
- No intermediate file to clean up
- Directly shows metadata field → Terraform variable mapping (tutorial clarity)
- jq is universally available on Linux/macOS
- Simpler error handling (jq exits non-zero on parse failure)

**jq patterns:**
```bash
# Source: jq documentation + WorkflowMetadata field names (metadata.py)
WORKFLOW_NAME=$(jq -r '.workflow_name' "${METADATA_FILE}")
EXECUTION_TIMEOUT=$(jq -r '.timeout_seconds // 86400' "${METADATA_FILE}")
# Note: // is jq's alternative operator — returns 86400 if timeout_seconds is null
```

### Pattern 4: TOOL-01 — Adding --teardown to rsf deploy

**GAP:** `rsf deploy` has no `--teardown` flag. The `teardown()` method exists on all providers but is never called from the CLI.

**Required change to `deploy_cmd.py`:**

```python
# Add --teardown flag to the deploy() function signature:
teardown: bool = typer.Option(False, "--teardown", help="Destroy all deployed infrastructure"),

# Add mutual exclusion with --teardown:
if teardown and (code_only or no_infra):
    console.print("[red]Error:[/red] --teardown cannot be combined with --code-only or --no-infra")
    raise typer.Exit(code=1)

# Add teardown dispatch after provider is resolved (before _deploy_full):
if teardown:
    _teardown_infra(provider, ctx)
    return

# New _teardown_infra function:
def _teardown_infra(provider: object, ctx: ProviderContext) -> None:
    """Run the provider teardown lifecycle."""
    console.print("\n[bold]Tearing down infrastructure...[/bold]")
    try:
        provider.teardown(ctx)
    except subprocess.CalledProcessError as exc:
        console.print(
            f"[red]Error:[/red] Infrastructure teardown failed (exit {exc.returncode})"
        )
        raise typer.Exit(code=1)
    except NotImplementedError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)
    console.print("\n[green]Teardown complete[/green]")
```

**Test additions to `test_deploy.py`:**
- `test_deploy_teardown_calls_provider_teardown` — verifies `provider.teardown()` is called
- `test_deploy_teardown_exits_nonzero_on_failure` — CalledProcessError → exit 1
- `test_deploy_teardown_not_implemented_errors_gracefully` — NotImplementedError → exit 1 with message
- `test_deploy_teardown_mutually_exclusive_with_code_only` — exit 1 error

### Pattern 5: Workflow YAML Design — Recommended Scenario

**Recommendation:** "Image Processing Pipeline" — a 4-state workflow that validates, resizes, analyzes, and catalogues images. This scenario:
- Naturally uses Task states with retries (network calls to external services)
- Has a clear Catch block (invalid image formats)
- Needs DynamoDB (catalogue storage) — forward-compatible with Phase 58
- Needs a DLQ for failed processing — forward-compatible with Phase 58
- Is tutorial-friendly (everyone understands image processing)
- Uses no real external dependencies in happy-path handlers (simulated processing)

```yaml
rsf_version: "1.0"
Comment: "image-processing"
StartAt: ValidateImage

dynamodb_tables:
  - table_name: "image-catalogue"
    partition_key:
      name: "image_id"
      type: S
    billing_mode: PAY_PER_REQUEST

dead_letter_queue:
  enabled: true
  max_receive_count: 3
  queue_name: "image-processing-dlq"

States:
  ValidateImage:
    Type: Task
    ResultPath: "$.validation"
    Retry:
      - ErrorEquals: ["States.TaskFailed"]
        IntervalSeconds: 1
        MaxAttempts: 2
        BackoffRate: 2.0
    Catch:
      - ErrorEquals: ["InvalidImageError"]
        Next: ProcessingFailed
        ResultPath: "$.error"
    Next: ResizeImage

  ResizeImage:
    Type: Task
    ResultPath: "$.resize"
    Retry:
      - ErrorEquals: ["ResizeServiceError"]
        IntervalSeconds: 2
        MaxAttempts: 3
        BackoffRate: 1.5
    Next: AnalyzeContent

  AnalyzeContent:
    Type: Task
    ResultPath: "$.analysis"
    Next: CatalogueImage

  CatalogueImage:
    Type: Task
    ResultPath: "$.catalogue"
    Next: ProcessingComplete

  ProcessingComplete:
    Type: Succeed

  ProcessingFailed:
    Type: Fail
    Error: "ImageProcessingFailed"
    Cause: "Image could not be processed"
```

**Alternative scenario if image processing seems too heavy:** "Report Generation Pipeline" — validate, fetch data, generate report, notify — also 4 states with Retry/Catch.

### Pattern 6: Handler Implementation Pattern

```python
# handlers/validate_image.py
# Source: examples/order-processing/handlers/validate_order.py pattern
"""ValidateImage handler — validates image format and dimensions."""

import json
import logging

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


class InvalidImageError(Exception):
    """Raised when image format or dimensions are invalid."""


@state("ValidateImage")
def validate_image(input_data: dict) -> dict:
    """Validate image format and size constraints.

    Args:
        input_data: dict with image_id, format, size_bytes fields.

    Returns:
        dict with valid, format, and size_bytes fields.

    Raises:
        InvalidImageError: If format is unsupported or size exceeds limits.
    """
    image_id = input_data.get("image_id", "unknown")
    _log("ValidateImage", "Starting image validation", image_id=image_id)

    fmt = input_data.get("format", "")
    if fmt.lower() not in {"jpeg", "png", "webp", "gif"}:
        _log("ValidateImage", "Invalid image format", format=fmt)
        raise InvalidImageError(f"Unsupported image format: {fmt}")

    size_bytes = input_data.get("size_bytes", 0)
    max_size = 10 * 1024 * 1024  # 10 MB
    if size_bytes > max_size:
        _log("ValidateImage", "Image too large", size_bytes=size_bytes)
        raise InvalidImageError(f"Image size {size_bytes} exceeds maximum {max_size}")

    _log("ValidateImage", "Image validated successfully", format=fmt, size_bytes=size_bytes)
    return {"valid": True, "format": fmt, "size_bytes": size_bytes}
```

### Pattern 7: Terraform main.tf with Registry Module

```hcl
# terraform/main.tf
# Source: Phase 56 SCHEMA-FINDINGS.md — all patterns confirmed from v8.7.0 tag

module "lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "8.7.0"  # exact pin — see versions.tf rationale

  function_name = var.workflow_name
  handler       = "generated.orchestrator.lambda_handler"
  runtime       = "python3.13"

  # RSF manages packaging — module must not create its own zip
  create_package          = false
  local_existing_package  = "${path.module}/../build/function.zip"
  ignore_source_code_hash = true

  # durable_config activation — MUST be non-null (coalesce guards against null propagation)
  durable_config_execution_timeout = coalesce(var.execution_timeout, 86400)
  durable_config_retention_period  = 14

  # IAM — module creates role; iam_durable.tf supplements with durable-specific permissions
  create_role                   = true
  attach_cloudwatch_logs_policy = true

  # Managed policy + inline supplement (see iam_durable.tf)
  attach_policies    = true
  number_of_policies = 1
  policies = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicDurableExecutionRolePolicy"
  ]
  attach_policy_json = true
  policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "DurableExtraPermissions"
      Effect = "Allow"
      Action = [
        "lambda:InvokeFunction",
        "lambda:ListDurableExecutionsByFunction",
        "lambda:GetDurableExecution"
      ]
      Resource = "*"
    }]
  })

  tags = {
    ManagedBy = "rsf"
    Workflow  = var.workflow_name
  }
}

resource "aws_lambda_alias" "live" {
  name             = "live"
  function_name    = module.lambda.lambda_function_name
  function_version = module.lambda.lambda_function_version
}
```

**FALLBACK (if AWSLambdaBasicDurableExecutionRolePolicy unavailable in us-east-2):** Replace `attach_policies` block with all-inline approach matching RSF's existing `iam.tf.j2`:

```hcl
# terraform/main.tf (fallback — all-inline IAM)
module "lambda" {
  # ... same as above except:
  attach_policies    = false  # remove managed policy attachment
  attach_policy_json = true
  policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DurableExecution"
        Effect = "Allow"
        Action = [
          "lambda:CheckpointDurableExecution",
          "lambda:GetDurableExecutionState",
          "lambda:GetDurableExecution",
          "lambda:ListDurableExecutionsByFunction",
          "lambda:InvokeFunction"
        ]
        Resource = "*"
      }
    ]
  })
}
```

### Anti-Patterns to Avoid

- **Relative path in rsf.toml `program` field:** CustomProvider.validate_config() raises ValueError if path is not absolute. Always use absolute path.
- **`durable_config_execution_timeout = null` (or missing coalesce):** Dynamic block gate silently drops durable_config. Use `coalesce(var.execution_timeout, 86400)`.
- **Forgetting `chmod +x deploy.sh`:** check_prerequisites() in CustomProvider checks os.access(X_OK) and fails with a clear error message, but better to prevent than diagnose.
- **`create_package = true` (module default):** Creates conflicting zip. Always `create_package = false`.
- **Invoking Lambda via $LATEST:** Issue #45800 unresolved. Use alias ARN.
- **`attach_policies = true` without `number_of_policies = 1`:** Silent no-op. Must set all three.
- **`terraform destroy` without `terraform init` first:** Terraform state may not be loaded. deploy.sh always runs init before destroy.
- **Using `src/generated/` path in zip before `rsf generate` runs:** deploy.sh zips after `rsf deploy` runs codegen (deploy_cmd.py Step 3 is codegen before Step 8 provider.deploy). Path will exist by the time deploy.sh is called.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Metadata delivery to deploy.sh | Custom env var scheme or CLI arg parsing | FileTransport (RSF_METADATA_FILE already set) | FileTransport is implemented, tested, and handles serialization/cleanup |
| Lambda IAM role | `aws_iam_role` + separate attachment resources | lambda module `create_role = true` (default) | Module creates trust policy, CW Logs, and attaches all policies in one block |
| Lambda packaging | `data.archive_file` in terraform/ | deploy.sh zip step + `create_package = false` | Two packaging systems conflict. RSF owns packaging; Terraform just deploys |
| Teardown CLI | Separate `rsf teardown` command | `rsf deploy --teardown` flag on existing command | Single command with flag is standard UX (follows `kubectl delete`, `terraform destroy`) |
| Python tfvars.json shim | Python script to write tfvars.json from metadata JSON | jq + `-var=` CLI flags | jq is 2 lines vs 20 lines of Python; tutorial-readable |
| Custom logging format | New logging library | stdlib logging + json.dumps | Matches order-processing pattern; no new dependency |

---

## Common Pitfalls

### Pitfall 1: rsf.toml Absolute Path Not Set

**What goes wrong:** rsf.toml ships with a placeholder or relative path for `program`. Tutorial user runs `rsf deploy` and gets `ValueError: Custom provider program must be an absolute path`.
**Why it happens:** rsf.toml is committed to git; absolute path varies per machine.
**How to avoid:** README must instruct users to replace the `program` path with their local absolute path. Consider a helper: `echo "$(pwd)/deploy.sh"` to show the correct value.
**Warning signs:** `rsf deploy` fails immediately at config validation with "must be an absolute path" error.

### Pitfall 2: deploy.sh Not Executable

**What goes wrong:** `rsf deploy` fails prerequisite check: "custom program is not executable: .../deploy.sh. Fix: chmod +x .../deploy.sh"
**Why it happens:** git does not preserve execute bits across platforms by default; users clone and forget to chmod.
**How to avoid:** Set execute bit via `git update-index --chmod=+x deploy.sh` so git tracks the bit. Mention in README.
**Warning signs:** Prerequisite check fails with executable error before any Terraform runs.

### Pitfall 3: AWSLambdaBasicDurableExecutionRolePolicy Unavailable in us-east-2

**What goes wrong:** `terraform apply` fails with "An error occurred (NoSuchEntity)" when attaching the managed policy.
**Why it happens:** Managed policy regional rollout may be incomplete. (Regional availability was unverifiable during research due to expired AWS credentials.)
**How to avoid:** Wave 0 MUST run `aws iam get-policy --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicDurableExecutionRolePolicy --region us-east-2` before writing iam_durable.tf. Use all-inline fallback if unavailable.
**Warning signs:** `terraform apply` errors on managed policy attachment resource.

### Pitfall 4: jq Returns Null for Missing Fields

**What goes wrong:** `EXECUTION_TIMEOUT=$(jq -r '.timeout_seconds' "${METADATA_FILE}")` returns `null` as a string when WorkflowMetadata.timeout_seconds is None. Terraform receives `null` as a string variable.
**Why it happens:** WorkflowMetadata.timeout_seconds defaults to None; FileTransport serializes it as JSON null; jq -r renders JSON null as the string "null".
**How to avoid:** Always use jq alternative operator: `jq -r '.timeout_seconds // 86400'`. The `//` operator returns the fallback when the left side is null or false.
**Warning signs:** terraform apply fails with "Invalid value for input variable: unsuitable value: null" or silently disables durable_config.

### Pitfall 5: deploy.sh Runs from Wrong Working Directory

**What goes wrong:** `zip -r build/function.zip src/generated/ handlers/` fails because paths are relative and deploy.sh was invoked from a different directory. CustomProvider sets `cwd=ctx.workflow_path.parent` (the example root) when calling deploy.sh, but `cd "${SCRIPT_DIR}"` in deploy.sh ensures the correct working directory regardless.
**Why it happens:** CustomProvider uses `cwd=ctx.workflow_path.parent`. deploy.sh should `cd "${SCRIPT_DIR}"` before zip.
**How to avoid:** SCRIPT_DIR computation is already in the pattern. Never rely on `$PWD` in deploy.sh.
**Warning signs:** `zip` error "No such file or directory" for src/generated/ or handlers/.

### Pitfall 6: Teardown CLI Gap — --teardown Not Yet Implemented

**What goes wrong:** Tutorial user runs `rsf deploy --teardown` and gets "No such option: --teardown".
**Why it happens:** `deploy_cmd.py` has no `--teardown` flag. The teardown() method exists on CustomProvider but is unreachable from the CLI.
**How to avoid:** TOOL-01 must be implemented in Wave 0 before documenting teardown in README.
**Warning signs:** `rsf deploy --help` shows no `--teardown` option.

### Pitfall 7: Two Packaging Systems Conflict

**What goes wrong:** `data.archive_file` in terraform (old approach) and deploy.sh's zip both produce artifacts; Terraform triggers re-deploy on every apply due to hash changes.
**Why it happens:** module default is `create_package = true`; if accidentally left on, module creates its own zip.
**How to avoid:** Always set `create_package = false` + `local_existing_package` + `ignore_source_code_hash = true`. Phase 56 SCHEMA-FINDINGS.md confirms these three are required together.

---

## Code Examples

Verified patterns from official sources:

### rsf.toml — Custom Provider Configuration

```toml
# examples/registry-modules-demo/rsf.toml
# Source: src/rsf/dsl/models.py CustomProviderConfig + src/rsf/config.py
# IMPORTANT: Replace /absolute/path/to/ with your actual path
[infrastructure]
provider = "custom"

[infrastructure.custom]
program         = "/absolute/path/to/examples/registry-modules-demo/deploy.sh"
args            = ["deploy"]
teardown_args   = ["destroy"]
metadata_transport = "file"
```

### FileTransport Data Contract (what deploy.sh reads)

```json
{
  "workflow_name": "image-processing",
  "stage": null,
  "handler_count": 4,
  "timeout_seconds": null,
  "triggers": [],
  "dynamodb_tables": [
    {
      "table_name": "image-catalogue",
      "partition_key": {"name": "image_id", "type": "S"},
      "billing_mode": "PAY_PER_REQUEST"
    }
  ],
  "alarms": [],
  "dlq_enabled": true,
  "dlq_max_receive_count": 3,
  "dlq_queue_name": "image-processing-dlq",
  "lambda_url_enabled": false,
  "lambda_url_auth_type": "NONE"
}
```

Source: `src/rsf/providers/metadata.py` WorkflowMetadata dataclass + FileTransport serialization.

### terraform/variables.tf

```hcl
# terraform/variables.tf
# Source: established pattern from examples/order-processing/terraform/variables.tf

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-2"
}

variable "workflow_name" {
  description = "Workflow name — used as Lambda function name and resource name prefix"
  type        = string
  # No default — must be provided by deploy.sh from RSF_METADATA_FILE
}

variable "execution_timeout" {
  description = "Durable execution timeout in seconds (1 to 31622400)"
  type        = number
  default     = 86400  # 24 hours

  validation {
    condition     = var.execution_timeout >= 1 && var.execution_timeout <= 31622400
    error_message = "execution_timeout must be between 1 and 31622400 seconds."
  }
}
```

### terraform/outputs.tf

```hcl
# terraform/outputs.tf
output "alias_arn" {
  description = "Invoke via alias ARN — never $LATEST (issue #45800)"
  value       = aws_lambda_alias.live.arn
}

output "function_name" {
  description = "Lambda function name"
  value       = module.lambda.lambda_function_name
}

output "role_arn" {
  description = "IAM role ARN"
  value       = module.lambda.lambda_role_arn
}
```

### terraform/backend.tf

```hcl
# terraform/backend.tf
# Source: examples/order-processing/terraform/backend.tf pattern

# No remote backend configured. State is stored locally.
# Terraform state file (terraform.tfstate) is gitignored.
# To enable S3 backend, add a backend "s3" block here.
```

### deploy_cmd.py --teardown Addition

```python
# src/rsf/cli/deploy_cmd.py — additions for TOOL-01
# Source: existing deploy_cmd.py pattern + InfrastructureProvider.teardown() interface

# Add to deploy() signature:
teardown: bool = typer.Option(
    False,
    "--teardown",
    help="Destroy all deployed infrastructure (runs provider teardown)",
),

# Add mutual exclusion check (after existing code_only/no_infra check):
if teardown and (code_only or no_infra):
    console.print(
        "[red]Error:[/red] --teardown cannot be combined with --code-only or --no-infra"
    )
    raise typer.Exit(code=1)

# Add teardown dispatch (before _deploy_full call):
if teardown:
    _teardown_infra(provider, ctx)
    return

# New function to add:
def _teardown_infra(provider: object, ctx: ProviderContext) -> None:
    """Invoke the provider teardown lifecycle."""
    console.print("\n[bold]Tearing down infrastructure...[/bold]")
    try:
        provider.teardown(ctx)
    except subprocess.CalledProcessError as exc:
        console.print(
            f"[red]Error:[/red] Infrastructure teardown failed (exit {exc.returncode})"
        )
        raise typer.Exit(code=1)
    except NotImplementedError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)
    console.print("\n[green]Teardown complete[/green]")
```

### conftest.py Pattern (from order-processing)

```python
# tests/conftest.py
# Source: examples/order-processing/tests/conftest.py — exact pattern to replicate
import sys
from pathlib import Path

import pytest

_example_root = str(Path(__file__).parent.parent)
_project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, _example_root)
sys.path.insert(0, str(_project_root / "src"))
sys.path.insert(0, str(_project_root / "tests"))

from rsf.registry.registry import clear  # noqa: E402


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear RSF registry and purge cached handler modules between tests."""
    clear()
    for mod_name in [k for k in sys.modules if k == "handlers" or k.startswith("handlers.")]:
        del sys.modules[mod_name]
    if _example_root in sys.path:
        sys.path.remove(_example_root)
    sys.path.insert(0, _example_root)
    yield
    clear()
```

---

## TOOL-01 Gap Analysis — CLI Teardown

### Current State (confirmed from codebase inspection)

| Component | Status |
|-----------|--------|
| `CustomProvider.teardown()` | EXISTS — invokes deploy.sh with teardown_args |
| `TerraformProvider.teardown()` | EXISTS — runs `terraform destroy -auto-approve` |
| `InfrastructureProvider.teardown()` | EXISTS — abstract method in base.py |
| `deploy_cmd.py --teardown flag` | MISSING — not in CLI |
| `deploy_cmd.py _teardown_infra()` | MISSING — not implemented |
| `test_deploy.py teardown tests` | MISSING — no tests for teardown path |

### Impact

Without `--teardown`, success criterion 3 ("rsf deploy --teardown destroys all AWS resources") CANNOT be met. TOOL-01 must be implemented before documenting teardown in the example README.

### Implementation Scope

Small, contained change:
- `src/rsf/cli/deploy_cmd.py` — add `--teardown` flag + `_teardown_infra()` function (~25 lines)
- `tests/test_cli/test_deploy.py` — add 4 test cases for teardown path (~60 lines)

No other files need changes. CustomProvider.teardown() is already implemented and tested in `tests/test_providers/test_custom_provider.py`.

---

## Open Questions

1. **AWSLambdaBasicDurableExecutionRolePolicy availability in us-east-2**
   - What we know: Policy confirmed to exist globally (v3, Feb 12, 2026). Regional rollout unverified.
   - What's unclear: Whether it's available in us-east-2 as of March 2026.
   - Recommendation: Wave 0 runs `aws iam get-policy --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicDurableExecutionRolePolicy --region us-east-2`. If ExpiredToken/unavailable: use all-inline IAM. **Decision must be made before iam_durable.tf is written.**

2. **Workflow scenario — image processing vs. alternatives**
   - What we know: 4-5 states, Retry/Catch required, DynamoDB + DLQ forward-compatibility needed.
   - What's unclear: Whether image processing or report generation is better for tutorial context.
   - Recommendation: Image processing is universally understood and naturally exercises all requirements. Use it unless planner has a stronger preference.

3. **Absolute path in rsf.toml — user experience**
   - What we know: CustomProvider requires absolute path; rsf.toml is committed to git.
   - What's unclear: Best UX for tutorial users to set their local path.
   - Recommendation: Ship rsf.toml with a clearly-marked placeholder (`/REPLACE/WITH/YOUR/ABSOLUTE/PATH/deploy.sh`) and explain in README. For Phase 60 tutorial, this becomes a pitfall to document.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (confirmed from pyproject.toml) |
| Config file | pyproject.toml (existing) |
| Quick run command | `pytest tests/ -x -q` |
| Example-local run | `pytest examples/registry-modules-demo/tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROV-01 | FileTransport sets RSF_METADATA_FILE; deploy.sh reads it | unit | `pytest tests/test_providers/test_transports.py -x -q` | ✅ (transport tests exist) |
| PROV-02 | rsf.toml CustomProviderConfig loads correctly | unit | `pytest tests/test_config.py -x -q` | ✅ (config tests exist) |
| PROV-03 | deploy --teardown calls provider.teardown() | unit | `pytest tests/test_cli/test_deploy.py -x -q -k teardown` | ❌ Wave 0 (--teardown not yet in CLI) |
| PROV-04 | deploy.sh creates build/function.zip before terraform apply | manual (bash) | `bash examples/registry-modules-demo/deploy.sh deploy` (dry run with mocked terraform) | ❌ Wave 0 (deploy.sh doesn't exist yet) |
| REG-01 | Lambda module main.tf has durable_config + create_package=false | manual (terraform plan) | `cd examples/registry-modules-demo/terraform && terraform plan` | ❌ Wave 0 (main.tf doesn't exist yet) |
| EXAM-01 | workflow.yaml parses correctly with dynamodb_tables + dead_letter_queue | unit | `pytest -x -q -k "registry" tests/test_dsl/` | ❌ Wave 0 (workflow.yaml doesn't exist yet) |
| EXAM-02 | Example directory follows RSF conventions | manual | `ls examples/registry-modules-demo/` | ❌ Wave 0 (files don't exist yet) |
| EXAM-03 | Handlers register correctly and return expected output | unit | `pytest examples/registry-modules-demo/tests/ -x -q` | ❌ Wave 0 (handlers + tests don't exist yet) |
| TOOL-01 | rsf deploy --teardown flag routes to provider.teardown() | unit | `pytest tests/test_cli/test_deploy.py -x -q -k teardown` | ❌ Wave 0 (not yet implemented) |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q` (full unit suite, ~30 seconds)
- **Per wave merge:** `pytest tests/ -v` + `pytest examples/registry-modules-demo/tests/ -v`
- **Phase gate:** Full suite green + manual `rsf deploy` on example before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `src/rsf/cli/deploy_cmd.py` — add `--teardown` flag and `_teardown_infra()` function (TOOL-01)
- [ ] `tests/test_cli/test_deploy.py` — add teardown test cases (4 tests)
- [ ] `examples/registry-modules-demo/workflow.yaml` — new example workflow
- [ ] `examples/registry-modules-demo/handlers/__init__.py` and handler files
- [ ] `examples/registry-modules-demo/tests/conftest.py` and `test_handlers.py`
- [ ] `examples/registry-modules-demo/terraform/main.tf` — after managed policy check
- [ ] `examples/registry-modules-demo/terraform/variables.tf`
- [ ] `examples/registry-modules-demo/terraform/outputs.tf`
- [ ] `examples/registry-modules-demo/terraform/backend.tf`
- [ ] `examples/registry-modules-demo/deploy.sh` (chmod +x via `git update-index`)
- [ ] `examples/registry-modules-demo/rsf.toml`
- [ ] `examples/registry-modules-demo/README.md`

*(No framework gaps — existing pytest infrastructure covers all tests)*

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw `aws_lambda_function` in Terraform | `terraform-aws-modules/lambda/aws` v8.7.0 | Feb 18, 2026 | Module replaces main.tf + iam.tf + cloudwatch.tf |
| No teardown CLI path | `rsf deploy --teardown` (TOOL-01) | Phase 57 | Enables clean destruction via custom provider |
| All-inline IAM policy (RSF existing) | Managed policy + inline supplement | Feb 2026 | AWSLambdaBasicDurableExecutionRolePolicy is AWS-recommended; inline only for self-invoke + list |
| `create_package = true` + `data.archive_file` | `create_package = false` + deploy.sh zip | Phase 57 | Eliminates packaging conflict between RSF codegen and Terraform |

**Deprecated/outdated:**
- `version = "~> 8.7"` on module: Not deprecated, but wrong for tutorial reproducibility
- Raw `aws_lambda_function` resource: Still valid but registry module is the tutorial-forward choice

---

## Sources

### Primary (HIGH confidence)

- `/home/esa/git/rsf-python/src/rsf/providers/custom.py` — CustomProvider.deploy(), teardown(), check_prerequisites(), validate_config() confirmed from live source
- `/home/esa/git/rsf-python/src/rsf/providers/transports.py` — FileTransport behavior, RSF_METADATA_FILE env var confirmed
- `/home/esa/git/rsf-python/src/rsf/providers/metadata.py` — WorkflowMetadata field names + JSON serialization confirmed
- `/home/esa/git/rsf-python/src/rsf/config.py` — rsf.toml loading and priority cascade confirmed
- `/home/esa/git/rsf-python/src/rsf/dsl/models.py` — CustomProviderConfig, InfrastructureConfig field names confirmed
- `/home/esa/git/rsf-python/src/rsf/cli/deploy_cmd.py` — confirmed absence of --teardown flag; deploy pipeline flow confirmed
- `/home/esa/git/rsf-python/examples/order-processing/` — reference conventions confirmed (handlers/, conftest.py pattern, Terraform layout)
- `.planning/phases/56-schema-verification/SCHEMA-FINDINGS.md` — all Terraform patterns (HIGH confidence, verified from live GitHub source in Phase 56)
- `/home/esa/git/rsf-python/examples/registry-modules-demo/terraform/versions.tf` — Phase 56 deliverable confirmed present

### Secondary (MEDIUM confidence)

- Phase 56 RESEARCH.md — IAM hybrid approach, alias convention, version pins (MEDIUM — verified from official sources in Phase 56 but that research is now 30 days valid)
- order-processing handlers (validate_order.py, process_payment.py) — handler pattern confirmed from live source

### Tertiary (LOW confidence — needs live validation)

- `AWSLambdaBasicDurableExecutionRolePolicy` regional availability in us-east-2 — unverifiable (AWS credentials expired during research). Must be checked in Wave 0.

---

## Metadata

**Confidence breakdown:**
- TOOL-01 gap (--teardown missing from CLI): HIGH — confirmed from live source inspection of deploy_cmd.py
- deploy.sh design patterns: HIGH — confirmed from custom.py + transports.py interface contract
- rsf.toml structure: HIGH — confirmed from config.py + models.py
- Terraform patterns (main.tf, iam_durable.tf): HIGH — all from Phase 56 SCHEMA-FINDINGS.md (verified from live v8.7.0 tag)
- Managed policy availability in us-east-2: LOW — unverified (expired credentials)
- Workflow scenario (image processing): MEDIUM — Claude's discretion; no external source needed
- jq vs tfvars.json recommendation: MEDIUM — based on tutorial simplicity analysis

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (30 days — codebase is stable; AWS IAM policy availability needs live check)
