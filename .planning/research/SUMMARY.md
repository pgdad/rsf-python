# Project Research Summary

**Project:** RSF v3.2 — Terraform Registry Modules Tutorial
**Domain:** Tutorial and example demonstrating RSF custom provider integration with HashiCorp Terraform registry modules
**Researched:** 2026-03-03
**Confidence:** HIGH (stack/architecture verified from source); MEDIUM on durable_config module internals due to newness of feature (lambda module v8.7.0 released February 18, 2026)

## Executive Summary

RSF v3.2 is a documentation and example milestone, not a code milestone. The RSF provider system (CustomProvider, transports, WorkflowMetadata) was completed in v3.0 and requires zero changes. The entire v3.2 scope lives in one new example directory (`examples/registry-modules-demo/`) and one new tutorial (`tutorials/09-custom-provider-registry-modules.md`). The deliverable teaches users to write a custom provider script that deploys Lambda Durable Functions via HashiCorp's official terraform-aws-modules instead of RSF's raw HCL generator — demonstrating the provider system's IaC-agnosticism in practice.

The recommended approach is a self-contained bash deploy script that reads WorkflowMetadata via FileTransport, then runs `terraform apply` against a static HCL directory using five registry modules: lambda (v8.7.0+), dynamodb-table (v5.5.0), sqs (v5.2.1), cloudwatch metric-alarm (v5.7.2), and sns (v7.1.0). The lambda module version is a hard dependency: terraform-aws-modules/lambda/aws only added native durable Lambda support in v8.7.0 (February 18, 2026). The tutorial must pin all modules to exact versions, not range constraints, because Terraform does not lock module versions in `.terraform.lock.hcl`.

The primary risks are all IAM-related and specific to Lambda Durable Functions, a feature that launched at re:Invent 2025. The Terraform AWS provider (GitHub issue #45800) does not yet support the `AllowInvokeLatest` durable_config field, requiring all invocations to use a Lambda alias rather than `$LATEST`. Additionally, the durable execution IAM permissions (checkpoint, get, list, self-invoke) are not included in the registry lambda module's auto-created role and must be manually attached. Both issues are well-understood and have clear workarounds; neither blocks the tutorial.

## Key Findings

### Recommended Stack

The stack adds no new Python dependencies to RSF. All additions are Terraform-only and are downloaded automatically by `terraform init`. The only tooling prerequisite beyond what RSF already requires is Terraform >= 1.5.7 (required by the sqs and sns modules) and optionally `jq` for bash-based metadata parsing. The existing AWS provider constraint (`>= 6.25.0`) satisfies all module requirements without a version bump.

**Core technologies:**
- `terraform-aws-modules/lambda/aws` v8.7.0 — Lambda + IAM role + CloudWatch log group as an integrated unit; first version with native durable_config support; use `create_package = false` + `local_existing_package` to avoid conflicting with RSF's own zip workflow
- `terraform-aws-modules/dynamodb-table/aws` v5.5.0 — direct 1:1 mapping to RSF's `dynamodb_tables` WorkflowMetadata field; use with `for_each` over the list
- `terraform-aws-modules/sqs/aws` v5.2.1 — DLQ; wires to lambda module's `dead_letter_target_arn`; gated by `count = var.dlq_enabled ? 1 : 0`
- `terraform-aws-modules/cloudwatch/aws` (metric-alarm submodule) v5.7.2 — maps to RSF's three alarm types (error_rate, duration, throttle); requires `//modules/metric-alarm` submodule path
- `terraform-aws-modules/sns/aws` v7.1.0 — SNS topic for alarm notifications; feeds `alarm_actions`
- Bash (`deploy.sh`) — custom provider entry point invoked by RSF CustomProvider; must be `chmod +x` with absolute path; dispatches on `$1` for deploy/destroy
- FileTransport (`RSF_METADATA_FILE`) — recommended metadata transport for Terraform scripts; persists JSON for inspection; supports nested structures (dynamodb_tables, alarms) that ArgsTransport cannot handle reliably

### Expected Features

The tutorial is the product. Features are tutorial coverage goals, not new RSF runtime capabilities.

**Must have (table stakes):**
- Custom provider script that reads WorkflowMetadata via `RSF_METADATA_FILE` and runs `terraform apply`
- `rsf.toml` wiring for `provider = "custom"` with absolute path to provider script
- Lambda deployed via registry module with `create_package = false` and `local_existing_package` pointing to RSF-built zip
- `durable_config` block wired through the lambda module (v8.7.0 required)
- Durable execution IAM: module auto-creates base role; separate inline policy adds CheckpointDurableExecution, GetDurableExecution, ListDurableExecutionsByFunction, self-invoke permissions
- Lambda alias created and used for all invocations (workaround for Terraform provider issue #45800)
- `teardown_args` configuration with matching destroy path in deploy script
- Example workflow YAML with DynamoDB table, DLQ, and Task states (exercises all RSF infrastructure features)
- End-to-end `rsf deploy` verification against real AWS
- Integration test that invokes a real durable execution (not just exit code check)

**Should have (differentiators):**
- Side-by-side comparison of raw HCL (RSF TerraformProvider output) vs. registry module HCL
- Python script variant of the custom provider (not just bash) — matches RSF's ecosystem
- Annotated WorkflowMetadata schema table in tutorial prose
- Debug step showing how to print and inspect the metadata JSON before Terraform runs
- `rsf doctor` output callout at the provider path configuration step
- Local test of provider script in isolation before wiring to RSF

**Defer (future milestones):**
- Pulumi or CDK registry equivalents
- New RSF DSL syntax or SDK for custom providers
- Multi-provider workflow composition
- Coverage of all three metadata transports in depth (FileTransport is sufficient)
- Custom Terraform module authoring or publishing to Terraform Registry

### Architecture Approach

This is a pure user-space integration. Zero RSF core files are modified. The custom provider system was designed for exactly this use case: an external executable receives WorkflowMetadata and handles deployment autonomously. The deploy script is a thin Terraform wrapper — it reads RSF metadata, passes values to Terraform as `-var` flags, and calls `terraform apply`. The Terraform HCL files in `terraform/` are static and version-controlled; the deploy script never generates or modifies them. Split deploy/destroy commands in a single script dispatching on `$1` is the canonical pattern supported by `args` / `teardown_args` in CustomProviderConfig.

**Major components:**
1. `examples/registry-modules-demo/deploy.sh` — RSF-facing entry point; reads RSF_METADATA_FILE, zips source, dispatches to terraform init/apply/destroy based on `$1`
2. `examples/registry-modules-demo/terraform/` — static HCL using registry modules (main.tf, dynamodb.tf, sqs.tf, variables.tf, outputs.tf, versions.tf, backend.tf)
3. `examples/registry-modules-demo/workflow.yaml` — RSF DSL with `infrastructure.custom` block and FileTransport config
4. `tutorials/09-custom-provider-registry-modules.md` — step-by-step tutorial document
5. `tests/test_examples/test_registry_modules_demo.py` — integration test (real AWS, follows existing example test pattern)

### Critical Pitfalls

1. **Lambda module durable_config variable names unverified** — terraform-aws-modules/lambda v8.7.0 was released February 18, 2026. The exact input variable names for durable config must be confirmed from the live module schema before writing tutorial Terraform code. A silently omitted durable_config means the tutorial deploys a non-durable Lambda with no error. Prevention: pin to `version = "8.7.0"` (exact), verify with `aws lambda get-function --query Configuration.DurableConfig` after deploy.

2. **AllowInvokeLatest missing from Terraform AWS provider (issue #45800)** — invoking durable functions via `$LATEST` may fail. All invocation examples must use a Lambda alias ARN. Establish this convention in Phase 1 design before writing any invocation code.

3. **IAM action name mismatch between RSF generator and AWS managed policy** — `AWSLambdaBasicDurableExecutionRolePolicy` may use different action names than RSF's existing inline policy (durable_config launched December 2025; IAM actions were still stabilizing). Prevention: verify the managed policy with `aws iam get-policy-version` before finalizing IAM; validate with a live durable invocation, not just `terraform apply` success.

4. **Module version not pinned — silent upgrades** — `~>` version constraints on registry modules silently upgrade on `terraform init` because module versions are not in `.terraform.lock.hcl`. Pin all modules to exact versions (`version = "8.7.0"`, not `~> 8.7`).

5. **Lambda packaging conflict** — the lambda module's built-in packaging system (`source_path`, `create_package = true`) conflicts with RSF's own zip workflow. Always use `create_package = false` + `local_existing_package`. The deploy script must zip the RSF-generated source before `terraform apply`.

6. **ArgsTransport fails on complex metadata fields** — `dynamodb_tables`, `triggers`, and `alarms` are list/dict types that ArgsTransport serializes as Python repr strings (not JSON). Tutorial must use FileTransport for any workflow with non-scalar metadata fields.

7. **Provider script exit code swallowing** — bash scripts do not propagate errors by default. `set -euo pipefail` must be the first substantive line of every provider script. Without it, RSF reports success when Terraform partially failed.

## Implications for Roadmap

The work is purely additive with no RSF core changes. The architectural pattern is well-defined and all hard blockers are IAM/durable_config verification steps that must happen before code is finalized. The build order is driven by two constraints: (1) module schema must be confirmed before writing Terraform, and (2) the core Lambda-only example must work end-to-end before optional components are added.

### Phase 1: Scaffolding and Schema Verification

**Rationale:** All subsequent Terraform code depends on confirmed module variable names (durable_config inputs) and the "always use alias" invocation convention. These must be resolved before writing a single line of Terraform. This is the highest-risk phase because terraform-aws-modules/lambda v8.7.0 is three weeks old and documentation is sparse.
**Delivers:** Confirmed lambda module input schema at v8.7.0, `versions.tf` with exact version pins, Lambda alias convention decision, IAM approach decision (managed policy vs. inline policy)
**Addresses:** Pitfalls 1, 2, 3, 4 (durable_config verification, AllowInvokeLatest workaround, IAM action names, version pinning)
**Research flag:** Yes — verify live module schema from v8.7.0 `variables.tf`; verify `AWSLambdaBasicDurableExecutionRolePolicy` availability in target AWS account

### Phase 2: Core Example — Lambda Only

**Rationale:** Build the smallest working end-to-end first. workflow.yaml + deploy.sh + terraform/main.tf (lambda module only). Verify `rsf deploy` invokes the script, the script reads metadata, Terraform deploys a working durable Lambda, and teardown destroys it cleanly. No DynamoDB, SQS, or alarms yet. This validates the entire provider system integration before adding optional components.
**Delivers:** Working `examples/registry-modules-demo/` with Lambda-only deploy/teardown; first AWS integration verification
**Implements:** deploy.sh (dispatch pattern), versions.tf + variables.tf + main.tf + outputs.tf, workflow.yaml with custom provider config, deploy script zipping source before apply
**Avoids:** Packaging conflict (Pitfall 5), exit code swallowing (Pitfall 7), absolute path validation
**Research flag:** No — established patterns from RSF source and existing examples

### Phase 3: Full Example — DynamoDB, SQS DLQ, CloudWatch Alarms

**Rationale:** Extend the working Lambda-only example with optional infrastructure components. Each module is independent and can be added sequentially. DynamoDB via `for_each` demonstrates multi-module composition. DLQ demonstrates conditional infrastructure. CloudWatch alarms demonstrate the metric-alarm submodule pattern and the SNS topic output chaining.
**Delivers:** Complete `examples/registry-modules-demo/terraform/` with all five registry modules; full WorkflowMetadata field mapping demonstrated
**Uses:** dynamodb-table v5.5.0, sqs v5.2.1, cloudwatch metric-alarm v5.7.2, sns v7.1.0 from STACK.md
**Avoids:** ArgsTransport for complex fields (Pitfall 6) — FileTransport is required when DynamoDB tables or alarms are present

### Phase 4: Tests

**Rationale:** Unit tests and integration tests are written after the implementation is verified manually. Integration test follows the identical pattern to existing RSF integration tests — no new test infrastructure is needed. The critical quality gate is that the integration test invokes a real durable execution and polls for completion, not just checks `rsf deploy` exit code.
**Delivers:** `examples/registry-modules-demo/tests/test_local.py` (unit, no AWS) + `tests/test_examples/test_registry_modules_demo.py` (real AWS, real durable invocation, teardown verification)
**Research flag:** No — established patterns from existing RSF test suite

### Phase 5: Tutorial Document

**Rationale:** Written last so it accurately describes what was built. Working code is the source of truth; the tutorial prose describes it. All differentiator features (side-by-side comparison, annotated metadata schema, debug steps) are documentation polish that belongs here.
**Delivers:** `tutorials/09-custom-provider-registry-modules.md` with step-by-step narrative, annotated WorkflowMetadata schema, side-by-side HCL comparison (raw vs. registry module), debug tips, prerequisite list
**Research flag:** No — content is derived from the working implementation

### Phase Ordering Rationale

- Phase 1 before Phase 2: Module variable names must be confirmed before any Terraform code is written. Discovering wrong variable names after Terraform files are written means rewriting everything downstream.
- Phase 2 before Phase 3: Validate the core integration path (RSF CLI → CustomProvider → deploy.sh → terraform apply → working Lambda) before adding optional complexity. DynamoDB, SQS, and alarms are additive; a broken core is masked by additional complexity.
- Phase 3 before Phase 4: Integration tests target a complete implementation. Writing tests against partial implementation creates churn.
- Phase 4 before Phase 5: The tutorial must describe the final implementation accurately. Writing prose about code that will change is waste.
- No RSF core changes in any phase: The example and tutorial are built entirely outside `src/rsf/`. Any discovery that core changes are needed (e.g., adding `source_dir` to WorkflowMetadata) would be surfaced in Phase 2 and addressed before proceeding.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** High-priority. Confirm exact durable_config variable names in terraform-aws-modules/lambda v8.7.0 `variables.tf`. Verify `AWSLambdaBasicDurableExecutionRolePolicy` is available in the target AWS account (policy was still rolling out to regions in early 2026 per Pulumi issue #6100). Verify Terraform provider issue #45800 resolution status.

Phases with standard patterns (skip research-phase):
- **Phase 2:** CustomProvider system fully analyzed from RSF source; deploy/destroy dispatch pattern is established; file structure mirrors existing examples
- **Phase 3:** All module interfaces verified from GitHub source; `for_each` over list metadata is standard Terraform; SQS `count` gate pattern is well-documented
- **Phase 4:** RSF integration test pattern is directly reusable from existing examples with no new test infrastructure
- **Phase 5:** Tutorial follows existing `tutorials/` flat-file conventions; no research needed

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All 5 module versions verified from GitHub releases pages; provider version compatibility cross-checked; RSF AWS provider constraint (>= 6.25.0) satisfies all module requirements |
| Features | HIGH | Custom provider system analyzed from source (custom.py, transports.py, metadata.py); WorkflowMetadata fields confirmed; dependency order verified; anti-features clearly reasoned |
| Architecture | HIGH | Based on direct source analysis of all RSF provider files and existing examples; build order has clear dependency rationale; file structure follows established conventions |
| Pitfalls | MEDIUM | durable_config is three weeks old (lambda module v8.7.0, Feb 18 2026); IAM managed policy (`AWSLambdaBasicDurableExecutionRolePolicy`) confirmed in AWS docs but regional availability verified only via Pulumi issue, not direct API call; Terraform provider issue #45800 is open and unresolved as of research date |

**Overall confidence:** HIGH for scope, architecture, and build order. MEDIUM for durable_config-specific implementation details that require live verification in Phase 1.

### Gaps to Address

- **Exact durable_config input variable names in lambda module v8.7.0:** Research confirmed the module supports durable_config but the precise Terraform variable names (e.g., `durable_config_execution_timeout` vs. a nested map input) must be verified from the live v8.7.0 `variables.tf` before finalizing Phase 2 Terraform. Handle in Phase 1 schema verification step.

- **AWSLambdaBasicDurableExecutionRolePolicy availability:** The managed policy exists per AWS docs but was still rolling out to regions in early 2026. Before Phase 2 deploys, run `aws iam get-policy --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicDurableExecutionRolePolicy` in the target account. If absent, fall back to the inline policy approach used in RSF's existing Terraform generator.

- **Terraform provider issue #45800 resolution status:** Check whether `AllowInvokeLatest` has been added to the AWS Terraform provider before tutorial publication. If resolved, show `AllowInvokeLatest = true` in the tutorial. If still unresolved, maintain the "always use alias" convention throughout.

- **Lambda zip path convention:** RSF generates code to `src/generated/` but does not produce a zip. The deploy script must create the zip before `terraform apply`. The exact path (`src/generated.zip` vs. `src/generated/source.zip`) must be established in Phase 1 and used consistently in `local_existing_package` and all documentation.

## Sources

### Primary (HIGH confidence)
- GitHub: `terraform-aws-modules/terraform-aws-lambda` releases + `variables.tf` source — v8.7.0 durable_config support confirmed
- GitHub: `terraform-aws-modules/terraform-aws-{dynamodb-table,sqs,sns,cloudwatch}` releases + `variables.tf` — module inputs/outputs verified
- RSF source: `src/rsf/providers/custom.py`, `transports.py`, `metadata.py`, `base.py`, `src/rsf/dsl/models.py` — provider system interface confirmed
- RSF source: `src/rsf/cli/deploy_cmd.py` — deploy pipeline routing verified
- RSF source: `examples/order-processing/` — canonical example directory structure
- RSF source: `tests/test_providers/test_custom_integration.py` — interface contract and security hardening confirmed
- AWS docs: Lambda Durable Functions IaC guide — durable_config block schema, `AWSLambdaBasicDurableExecutionRolePolicy`

### Secondary (MEDIUM confidence)
- Terraform Registry: terraform-aws-modules/lambda, dynamodb-table, sqs, sns (JS-rendered; supplemented with GitHub source reads)
- DeepWiki: terraform-aws-modules/terraform-aws-lambda module variables — confirmed durable_config inputs
- GitHub issue #45800: AllowInvokeLatest missing from Terraform AWS provider — open as of research date

### Tertiary (LOW confidence — needs live verification)
- Pulumi issue #6100: `AWSLambdaBasicDurableExecutionRolePolicy` regional rollout timing — confirms the policy exists but not current availability in specific accounts
- STACK.md note on `dlq_max_receive_count` not being a SQS queue attribute — inferred from WorkflowMetadata field semantics, not directly tested against the SQS module

---
*Research completed: 2026-03-03*
*Ready for roadmap: yes*
