# Feature Landscape

**Domain:** Tutorial/example teaching custom provider creation via Terraform registry modules
**Researched:** 2026-03-03
**Milestone:** v3.2 — Terraform Registry Modules Tutorial

## Context

The v3.0 provider system ships all the mechanisms (ABC interface, subprocess invocation, 3 metadata transports, rsf.toml config). v3.2 teaches users how to exercise those mechanisms by building a real custom provider using HashiCorp's official terraform-aws-modules registry modules instead of RSF's raw HCL generator. The "product" is a tutorial + working example, not a new SDK feature. Features in this milestone are tutorial coverage goals and example workflow capabilities — not new RSF runtime features.

## Existing RSF Infrastructure to Map

The tutorial must demonstrate all RSF infrastructure features mapped to registry modules:

| RSF DSL Feature | Existing Raw HCL Approach | Registry Module Equivalent |
|-----------------|--------------------------|---------------------------|
| Lambda function + durable_config | `aws_lambda_function` resource with inline `durable_config {}` | `terraform-aws-modules/lambda/aws` v8.7.0+ (added durable support Feb 2026) |
| IAM role + execution policy | `aws_iam_role` + `aws_iam_role_policy` inline JSON | Module `attach_policies` / `policies` inputs; AWSLambdaBasicDurableExecutionRolePolicy attachment |
| CloudWatch Log Group | `aws_cloudwatch_log_group` resource | Module `cloudwatch_logs_retention_in_days` input; module creates log group automatically |
| DynamoDB table | `aws_dynamodb_table` resource | `terraform-aws-modules/dynamodb-table/aws` |
| SQS queue (DLQ) | `aws_sqs_queue` resource | `terraform-aws-modules/sqs/aws` |

## Table Stakes

Features the tutorial must cover. Absent means the tutorial is incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Custom provider script that reads WorkflowMetadata | Core purpose of v3.0 custom provider system; tutorial must show how to consume RSF metadata | Low | Script reads RSF_METADATA_FILE (FileTransport) or RSF_METADATA_JSON (EnvTransport); picks a single transport to keep the example focused |
| rsf.toml wiring for custom provider | The config cascade (workflow YAML > rsf.toml > default) is the intended UX; tutorial must show project-wide config | Low | `rsf.toml` with `[infrastructure]` table and `provider = "custom"` and `[infrastructure.custom]` block |
| Registry module source + version pinning | Canonical pattern for using terraform-aws-modules; `source = "terraform-aws-modules/lambda/aws"` with `version = "~> 8.7"` | Low | Pinning to major.minor range (not exact) is idiomatic for modules; tutorial must show why |
| Lambda function via registry module | Central resource; everything else hangs off it | Medium | `create_package = false`, `local_existing_package` pointing to RSF-built zip; `durable_config` inputs |
| durable_config block via module inputs | RSF workflows require durable Lambda; tutorial must show this works through registry module | Low | Module v8.7.0+ exposes `durable_config` as map input; `execution_timeout` and `retention_period` keys |
| IAM via module (not manual resource) | Showing module handles IAM is a primary value proposition vs raw HCL | Medium | Module `attach_policies` + `attach_policy_arns` inputs for AWSLambdaBasicDurableExecutionRolePolicy; module auto-creates execution role |
| CloudWatch log group via module | Module creates log group by default with `cloudwatch_logs_retention_in_days` input; no separate resource needed | Low | Tutorial shows this as a "free" benefit vs raw HCL where RSF generates separate cloudwatch.tf |
| Tutorial walkthrough: step-by-step custom provider creation | Users need to understand how to write the script, configure rsf.toml, and invoke `rsf deploy` | Medium | Script writes Terraform with module sources, runs `terraform apply`; tutorial walks each step with annotated code |
| `rsf deploy` end-to-end with custom provider | Tutorial must verify the custom provider path actually deploys to AWS | High | Integration-level — requires real AWS; tutorial is the integration test |
| Metadata transport selection and explanation | Three transports exist; tutorial must explain trade-offs and pick one as canonical for registry modules use case | Low | FileTransport (RSF_METADATA_FILE) is safest for complex metadata; EnvTransport shown as simpler alternative |
| teardown_args configuration | Without teardown, `rsf deploy` works but cleanup is manual; tutorial must cover destroy | Low | `teardown_args` in rsf.toml custom block; script reads same metadata, runs `terraform destroy` |
| Example workflow YAML that exercises all RSF infra features | Tutorial needs a realistic workflow; not just Lambda alone | Medium | New `registry-modules` example workflow with DynamoDB table, DLQ, and task states |

## Differentiators

Features that elevate the tutorial from adequate to excellent.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Side-by-side comparison: raw HCL vs registry module | Shows exactly what the module eliminates vs what remains identical; makes the value tangible | Low | Inline callouts in tutorial prose, not a separate document |
| Module outputs piped to RSF-expected Terraform outputs | Tutorial shows how to re-export module outputs (`function_arn`, `function_name`, `role_arn`) in the expected format | Low | `outputs.tf` in custom provider script's generated Terraform; mirrors RSF convention |
| Annotated WorkflowMetadata schema | Tutorial documents every WorkflowMetadata field so provider authors know what they can use | Low | A table in the tutorial: field name, type, when populated, example value |
| Python script for the custom provider (not bash) | Matches RSF's Python ecosystem; easier to test; easier to parse JSON metadata reliably | Low | `deploy.py` script using `subprocess` + `json`; bash alternative shown briefly |
| `chmod +x` and absolute path pitfall callout | Most common failure when first configuring a custom provider; absolute path required by CustomProvider._validate_program | Low | Tip box in tutorial at the step where `program:` is configured in rsf.toml |
| DynamoDB via `terraform-aws-modules/dynamodb-table/aws` | Shows registry modules are composable; one module per resource type | Medium | Demonstrates multi-module composition; DynamoDB module passes table name to Lambda as env var |
| SQS DLQ via `terraform-aws-modules/sqs/aws` | Completes the full-stack mapping from RSF DSL to registry modules | Medium | Module's simplicity vs raw HCL shows the benefit |
| `rsf doctor` output before and after custom provider setup | Shows the user what doctor reports when program is missing vs correctly configured | Low | Captures expected terminal output in the tutorial |
| Local test of the custom provider script in isolation | Before wiring into RSF, test the script standalone with a synthetic RSF_METADATA_FILE | Low | `echo '{"workflow_name": "test", ...}' > /tmp/meta.json && RSF_METADATA_FILE=/tmp/meta.json ./deploy.py` |

## Anti-Features

Features to explicitly exclude from this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| New RSF DSL syntax for registry modules | Registry modules are a Terraform concept, not an RSF concept; RSF stays IaC-agnostic | The custom provider script handles the registry module calls; RSF just passes metadata |
| Pulumi or CDK registry equivalents | Out of scope; one complete tutorial is better than three partial ones | v3.2 is Terraform registry modules only; other IaC tools are future milestones |
| Auto-generating registry module HCL from the RSF Terraform generator | Would bake terraform-aws-modules into RSF core; defeats provider abstraction | Custom provider is the correct layer; RSF remains IaC-agnostic |
| Python RSF SDK for custom providers (class to subclass) | Tight coupling; not consistent with `shell=False` + executable-program model already shipped | Subprocess with metadata transports is the correct model; tutorial demonstrates this clearly |
| Multi-provider composition (Terraform + custom in one workflow) | Complex; out of scope; a single provider per workflow is the supported model | One provider per workflow; document this constraint clearly |
| Tutorial covering all three metadata transports in depth | Three tutorials worth of content; overwhelming for a single example | Pick FileTransport as primary; show EnvTransport as one-paragraph alternative |
| Custom Terraform module (user-authored module published to registry) | Publishing to Terraform Registry is a different skill; irrelevant to RSF custom provider | Tutorial consumes published modules; does not publish any |
| Serverless Framework or SAM equivalent | Different tools, different audiences | This tutorial is Terraform-ecosystem only |

## Feature Dependencies

```
[Custom provider script (deploy.py)]
    └── required by --> [rsf deploy end-to-end]
    └── requires --> [WorkflowMetadata consumed via transport]
    └── requires --> [registry module Terraform files generated by script]

[rsf.toml custom provider config]
    └── required by --> [rsf deploy end-to-end]
    └── requires --> [absolute path to deploy.py]
    └── requires --> [teardown_args for destroy]

[WorkflowMetadata FileTransport]
    └── required by --> [custom provider script reading RSF_METADATA_FILE]
    └── requires --> [metadata_transport: "file" in rsf.toml]

[Registry module: terraform-aws-modules/lambda/aws v8.7.0+]
    └── required by --> [Lambda function deployment]
    └── requires --> [pre-built zip from RSF; create_package = false]
    └── requires --> [durable_config inputs: execution_timeout, retention_period]

[Registry module: terraform-aws-modules/dynamodb-table/aws]
    └── required by --> [DynamoDB table deployment]
    └── depends on --> [Lambda module for function reference]

[Registry module: terraform-aws-modules/sqs/aws]
    └── required by --> [DLQ deployment]
    └── depends on --> [Lambda module for dead_letter_queue_arn wiring]

[New example workflow YAML]
    └── required by --> [integration test]
    └── uses --> [DynamoDB table DSL block]
    └── uses --> [dead_letter_queue DSL block]
    └── uses --> [Task states]
```

### Dependency Notes

- **Registry module v8.7.0 is a hard requirement.** terraform-aws-modules/lambda v8.7.0 (released February 18, 2026) is the first version with durable Lambda support. Tutorial must pin to `~> 8.7`. Earlier versions cannot configure `durable_config`.
- **`create_package = false` is mandatory.** RSF handles Lambda packaging (archive_file or pre-built zip). The registry module must not try to rebuild the package. This is the key integration point.
- **Absolute path to deploy.py is a hard requirement.** `CustomProvider._validate_program()` rejects relative paths with a `ValueError`. Users must configure an absolute path in rsf.toml.
- **teardown_args requires a separate destroy path.** The deploy script and destroy script can be the same Python file with a `--destroy` flag, or two separate scripts. Tutorial should show the single-file approach with a flag.
- **AWSLambdaBasicDurableExecutionRolePolicy must be attached.** The registry module does not auto-attach this managed policy. The tutorial's Terraform must explicitly attach it via the module's `attach_policy_arns` input.

## MVP Recommendation

Build in this order to maintain a working state throughout development:

1. **Custom provider Python script** — reads RSF_METADATA_FILE, generates minimal Terraform using lambda registry module, runs `terraform apply`. No DynamoDB or SQS yet.
2. **rsf.toml wiring** — configure `provider = "custom"`, absolute path to script, FileTransport.
3. **`rsf deploy` end-to-end** — verify Lambda deploys successfully to AWS via registry module.
4. **Add DynamoDB and SQS** — extend the script and example workflow to show multi-module composition.
5. **Add teardown_args** — complete the lifecycle with `terraform destroy` path.
6. **Tutorial prose** — wrap the working implementation in step-by-step narrative.

Defer: Annotated WorkflowMetadata schema table, side-by-side HCL comparison, `rsf doctor` screenshots. These are documentation polish, not blocking functionality.

## Sources

**Registry module version/capability:**
- [terraform-aws-modules/terraform-aws-lambda releases](https://github.com/terraform-aws-modules/terraform-aws-lambda/releases) — v8.7.0 adds durable Lambda support (February 18, 2026). HIGH confidence.
- [Terraform Registry: terraform-aws-modules/lambda/aws](https://registry.terraform.io/modules/terraform-aws-modules/lambda/aws/latest) — module inputs/outputs reference. MEDIUM confidence (JS-rendered, verified via GitHub).
- [Terraform Registry: terraform-aws-modules/dynamodb-table/aws](https://registry.terraform.io/modules/terraform-aws-modules/dynamodb-table/aws/latest) — DynamoDB module. MEDIUM confidence.
- [Terraform Registry: terraform-aws-modules/sqs/aws](https://registry.terraform.io/modules/terraform-aws-modules/sqs/aws/latest) — SQS module. MEDIUM confidence.

**durable_config structure:**
- [AWS Lambda durable functions IaC guide](https://docs.aws.amazon.com/lambda/latest/dg/durable-getting-started-iac.html) — complete Terraform example with durable_config block and AWSLambdaBasicDurableExecutionRolePolicy. HIGH confidence.
- RSF codebase: `examples/order-processing/terraform/main.tf` — existing raw HCL with durable_config block. HIGH confidence (source of truth for RSF convention).

**Custom provider system:**
- RSF codebase: `src/rsf/providers/custom.py`, `src/rsf/providers/transports.py`, `src/rsf/providers/metadata.py`, `src/rsf/providers/base.py` — full implementation read directly. HIGH confidence.
- RSF codebase: `src/rsf/dsl/models.py` — `CustomProviderConfig` and `InfrastructureConfig` models. HIGH confidence.

**Module usage patterns:**
- [HashiCorp: Find and use modules in the Terraform registry](https://developer.hashicorp.com/terraform/registry/modules/use) — canonical module source syntax and version pinning. HIGH confidence.
- [terraform-aws-modules/lambda GitHub](https://github.com/terraform-aws-modules/terraform-aws-lambda) — `create_package = false` + `local_existing_package` pattern for externally managed packages. HIGH confidence.
- [HashiCorp: Use registry modules in configuration](https://developer.hashicorp.com/terraform/tutorials/modules/module-use) — module composition tutorial. HIGH confidence.

---
*Feature research for: RSF v3.2 Terraform Registry Modules Tutorial*
*Researched: 2026-03-03*
