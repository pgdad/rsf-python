# Pitfalls Research

**Domain:** Terraform Registry Modules Tutorial for Infrastructure Generation Tool (RSF v3.2)
**Researched:** 2026-03-03
**Confidence:** MEDIUM — durable_config is a very new feature (re:Invent 2025, Terraform provider v6.25.0 released Dec 4 2025, terraform-aws-modules/lambda v8.7.0 released Feb 18 2026). Official AWS docs and GitHub issues verified; some module internals confirmed via DeepWiki and release notes.

---

## Critical Pitfalls

### Pitfall 1: terraform-aws-modules/lambda durable_config Exposure Gap

**What goes wrong:**
The terraform-aws-modules/lambda module only added durable Lambda support in v8.7.0 (February 18, 2026). Before this, the module had no `durable_config` input variable at all. Even with v8.7.0, the module exposes `durable_config` as a nested block passthrough — the exact input variable name and structure must be confirmed against the live registry before the tutorial ships code. If the tutorial assumes the module variable is named `durable_config` (mirroring the provider resource block) but the module uses a different name or a flat variable (e.g., `durable_execution_timeout`, `durable_retention_period`), the generated Terraform will silently create a Lambda without durable execution enabled.

**Why it happens:**
The module was released very recently, its documentation is sparse, and the JavaScript-rendered Terraform Registry page is not machine-readable. Developers assume the module transparently passes through the underlying provider block name without checking the actual variable schema.

**How to avoid:**
Before writing tutorial code: fetch the live module variable list via `terraform-aws-modules/terraform-aws-lambda` releases page or DeepWiki and confirm the exact input variable name for durable config. Pin to `version = "8.7.0"` (exact) in the tutorial's module source block. Add an integration test that verifies the deployed function has `durable_config` set by calling `aws lambda get-function --query 'Configuration.DurableConfig'`.

**Warning signs:**
- Tutorial Terraform applies successfully but `aws lambda get-function` shows no `DurableConfig` key in the response
- Module version used in tutorial is < 8.7.0
- No `durable_config` or analogous variable appears in the module's input schema

**Phase to address:**
Tutorial scaffolding phase (before writing any example Terraform). Verify live module schema before locking in variable names.

---

### Pitfall 2: Missing AllowInvokeLatest in Terraform Provider — Silent Behavioral Difference

**What goes wrong:**
The AWS `durable_config` block has three fields: `execution_timeout`, `retention_period`, and `AllowInvokeLatest`. As of January 5, 2026, `AllowInvokeLatest` is missing from the Terraform AWS provider (GitHub issue #45800, open). Without it, tutorial readers cannot configure whether the `$LATEST` version can be used for durable execution via Terraform. If the tutorial invokes the function via unqualified ARN (pointing at `$LATEST`) but `AllowInvokeLatest` defaults to `false` in the AWS API, invocations may fail with `ResourceConflictException` or be rejected by the durable runtime.

**Why it happens:**
The feature was not present in the AWS SDK for Go v2 at the time of the Terraform provider release. Developers writing tutorials copy invocation patterns from non-durable Lambda tutorials that use `$LATEST` without checking whether durable functions require qualified ARNs.

**How to avoid:**
Use a Lambda alias (e.g., `"live"`) in all tutorial invocation examples rather than `$LATEST`. Document this explicitly: "Durable functions require a qualified ARN (alias or version). The tutorial always uses the `live` alias." Monitor issue #45800 — if resolved before release, update the tutorial to show how to configure `AllowInvokeLatest = true` once Terraform supports it.

**Warning signs:**
- `rsf deploy` succeeds but `aws lambda invoke --function-name arn:...:$LATEST` returns an error referencing durable config
- Tutorial tests fail with `InvalidParameterValueException` when using the unqualified function name
- No Lambda alias resource appears in the tutorial's Terraform code

**Phase to address:**
Tutorial design phase. Establish the "always use alias" convention before writing any invocation examples.

---

### Pitfall 3: IAM Policy Action Names Mismatched — Custom Inline Policy vs. AWS Managed Policy

**What goes wrong:**
RSF's existing Terraform generator produces a custom inline IAM policy with these durable execution actions: `lambda:CheckpointDurableExecution`, `lambda:GetDurableExecution`, `lambda:ListDurableExecutionsByFunction`. The AWS official IaC tutorial uses the managed policy `arn:aws:iam::aws:policy/service-role/AWSLambdaBasicDurableExecutionRolePolicy`, which includes `lambda:CheckpointDurableExecutions` and `lambda:GetDurableExecutionState` — different action names. If the registry module tutorial uses the managed policy ARN but the actions in the managed policy do not match what RSF's inline policy grants, the tutorial will create IAM setups that behave differently from the existing RSF examples, either causing runtime authorization failures or silent over-permissioning.

**Why it happens:**
Lambda Durable Functions launched at re:Invent 2025. IAM action names were finalized while early tooling was still being built. RSF's existing generator was written before the managed policy name was published. The managed policy was also referenced in a Pulumi issue (#6100) as recently absent from provider registries, indicating it was still rolling out.

**How to avoid:**
Before the tutorial ships: (1) run `aws iam get-policy-version --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicDurableExecutionRolePolicy --version-id v1` in the target AWS account to confirm the exact actions it grants; (2) cross-reference with the actions used in the existing RSF Terraform generator; (3) reconcile differences. Document which IAM approach the tutorial uses and why. Test with an actual durable invocation — not just Terraform apply success — before finalizing.

**Warning signs:**
- Tutorial Terraform applies but first invocation fails with `AccessDeniedException` referencing a `lambda:*Durable*` action
- `aws iam simulate-principal-policy` shows missing permissions for durable actions
- Managed policy ARN exists in AWS docs but `aws iam get-policy` returns NoSuchEntity in the target region

**Phase to address:**
IAM design phase. Validate actual permissions with a live invocation before finalizing the tutorial IAM section.

---

### Pitfall 4: Module Version Pinning — No Lock File for Registry Modules

**What goes wrong:**
Unlike provider versions (which are locked in `.terraform.lock.hcl`), Terraform module versions from the registry are not captured in the lock file. If the tutorial uses a range constraint like `version = "~> 8.7"` instead of an exact pin, a future patch release of `terraform-aws-modules/lambda` (e.g., 8.8.0) could introduce changes that break the tutorial's documented behavior — changing an output name, adding a required variable, or altering the packaging behavior — the moment a reader runs `terraform init` after the module is updated.

**Why it happens:**
Developers apply the same version constraint philosophy to modules as to providers. Providers use lock files; modules do not. A `~>` constraint that worked at tutorial authoring time silently upgrades on the next `terraform init` for every reader.

**How to avoid:**
Pin modules to an exact version in all tutorial Terraform code: `version = "8.7.0"`. Add a comment explaining the pin: `# Pinned to exact version — module versions are not locked by .terraform.lock.hcl`. Document the upgrade procedure separately if the tutorial is intended to be long-lived. In the tutorial text, explicitly call out that readers should not change this version without reviewing the module changelog.

**Warning signs:**
- Tutorial uses `~>` or `>=` instead of an exact version string for the module source block
- `terraform init -upgrade` changes the module version being downloaded
- A `terraform init` run weeks after tutorial authoring shows a different module version than tested

**Phase to address:**
Tutorial Terraform scaffolding phase, before any code review.

---

### Pitfall 5: ArgsTransport Failure on Complex WorkflowMetadata Fields

**What goes wrong:**
The `ArgsTransport` metadata transport substitutes `{placeholder}` patterns using Python `str.format(**asdict(metadata))`. WorkflowMetadata fields like `triggers`, `dynamodb_tables`, and `alarms` are `list[dict[str, Any]]`. When serialized via `dataclasses.asdict()`, these become Python list/dict objects. `str.format()` renders them as Python repr strings (e.g., `[{'type': 'sqs', 'queue_name': 'my-queue', ...}]`), not JSON. A tutorial that tries to pass `{triggers}` as a CLI arg to a shell script receives a Python-repr string that cannot be parsed as JSON, causing silent data corruption or runtime parse errors.

Additionally, `ArgsTransport.prepare()` splits formatted strings on whitespace (`formatted.split()`), which means any metadata value containing spaces (e.g., a workflow name like `"Order Processing"`) is incorrectly split into multiple CLI arguments.

**Why it happens:**
`ArgsTransport` was designed for simple scalar fields (`workflow_name`, `stage`, `handler_count`). The v3.2 tutorial is the first user-facing demonstration of the custom provider system and will expose these design limitations to readers who try to pass richer metadata fields via CLI args.

**How to avoid:**
(1) Tutorial must use `FileTransport` (not `ArgsTransport`) as the primary demonstrated transport for any workflow that has non-scalar metadata (DynamoDB tables, triggers, alarms). (2) Tutorial text must explicitly state: "Use `metadata_transport: file` when your workflow has DynamoDB tables, triggers, or alarms. The `args` transport is only reliable for scalar fields like `workflow_name` and `stage`." (3) Consider whether `ArgsTransport` should JSON-encode list/dict fields before splitting — this is a candidate tooling enhancement the tutorial might surface.

**Warning signs:**
- Custom provider script receives `triggers` that looks like `"[{'type':` split across multiple argv positions
- Shell script `jq` or `python3 -c "import json"` call fails on the `triggers` argument
- Tutorial example workflow has `dynamodb_tables:` defined but uses `metadata_transport: args`

**Phase to address:**
Tutorial design phase, when choosing the transport for the example workflow. If the decision is made to enhance `ArgsTransport` to JSON-serialize complex fields, that is a tooling phase before the tutorial phase.

---

### Pitfall 6: Custom Provider Script Exit Code Swallowing — User Sees No Error

**What goes wrong:**
The `CustomProvider` uses `subprocess.run(..., check=True)` which raises `subprocess.CalledProcessError` on non-zero exit. However, `run_provider_command_streaming` passes all stdout/stderr directly to the terminal (not captured). If the provider script internally catches exceptions and exits 0 despite a logical failure (e.g., Terraform apply partially succeeds then the script's cleanup step fails but the script still exits 0), RSF will report success. Tutorial readers writing their first provider script are likely to make this mistake because shell scripts do not propagate errors unless `set -e` is used.

**Why it happens:**
Bash scripts do not propagate errors by default. A script like `terraform init && terraform apply` will exit 0 if `terraform apply` succeeds even if a post-apply step fails. First-time provider script authors do not know to add `set -e` or `set -euo pipefail` at the top of their script.

**How to avoid:**
Tutorial provider script must start with `#!/usr/bin/env bash` and `set -euo pipefail` as the first substantive line. The tutorial text must explain what this does and why it is required. Add a callout box: "If any command in your provider script fails, `set -e` ensures the script exits non-zero — which causes RSF to report the failure. Without this, errors are silently ignored." The tutorial's integration test must deliberately inject a failure into the script and confirm RSF reports it.

**Warning signs:**
- Provider script is missing `set -e` or `set -euo pipefail`
- Tutorial's test step does not verify the deployed Lambda actually works (only checks that RSF exited 0)
- Terraform state is in an inconsistent state but `rsf deploy` reported success

**Phase to address:**
Tutorial provider script authoring phase.

---

### Pitfall 7: terraform-aws-modules/lambda Packaging Conflict with RSF's Existing Zip Workflow

**What goes wrong:**
RSF's existing Terraform generator uses `data.archive_file.lambda_zip` to create a deployment package from the source directory at apply time. The terraform-aws-modules/lambda module has its own built-in packaging system (`source_path`, `create_package = true`) that runs a Python `package.py` script during `terraform plan`. If the tutorial uses the module's packaging without explicitly setting `create_package = false` and providing the pre-built zip RSF produces, two packaging systems run in parallel, creating confusing output, potential hash mismatches, and non-deterministic deployments.

Additionally, the module's packaging system requires the local Python version to match the Lambda runtime (`python3.13`) — if the developer's machine has a different Python version active, packaging may silently produce an incompatible package.

**Why it happens:**
Developers assume the simplest module configuration (just set `source_path`) works for all cases, not realizing RSF already manages packaging. The module's packaging feature is prominent in its documentation and seems like the right thing to use.

**How to avoid:**
Tutorial must use `create_package = false` and `local_existing_package` pointing to the zip RSF produces. Explicitly explain: "We disable the module's built-in packaging (`create_package = false`) because RSF already creates the deployment package. We pass the path to RSF's zip file." Test that only one archive is created and that it contains the correct handler.

**Warning signs:**
- Tutorial `module` block uses `source_path` without `create_package = false`
- Two zip files appear in the project directory after deploy
- `terraform plan` shows packaging output (pip install, zip creation) that was not expected
- Handler path `generated.orchestrator.lambda_handler` is not found after deploy

**Phase to address:**
Tutorial scaffolding phase, when writing the module block.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Use `~>` version constraint on registry module | Automatically gets patch fixes | Silent breaking changes when reader runs tutorial months later | Never in a tutorial |
| Use `create_role = false` + hardcoded role ARN in tutorial | Simplifies IAM discussion | Hardcoded ARN is account-specific; breaks for every reader | Never |
| Skip `set -euo pipefail` in provider script | Shorter, simpler script | Errors silently swallowed; RSF reports false success | Never |
| Use `ArgsTransport` for all metadata fields | Single transport example | Breaks on any list/dict field; Python repr output is not JSON parseable | Only if tutorial workflow has purely scalar metadata |
| Omit Lambda alias, invoke via `$LATEST` | Simpler invocation command | Fails if `AllowInvokeLatest=false` (current Terraform provider default due to issue #45800) | Only if issue #45800 is resolved before tutorial ships |
| Copy IAM actions verbatim from RSF generator without live verification | Reuses known-working config | IAM action names may have changed since generator was written (Durable Functions launched Dec 2025) | Only after live verification |
| Omit integration test for durable invocation | Faster tutorial authoring | Tutorial may describe a configuration that deploys but does not actually run durable executions | Never |
| Use module's `source_path` packaging without `create_package = false` | Simpler module block | Two packaging systems run in parallel; hash mismatches; non-deterministic | Never when RSF manages packaging |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| terraform-aws-modules/lambda durable_config | Assuming module variable name matches provider block name exactly | Verify live module input schema at exact pinned version (v8.7.0) before writing tutorial code |
| terraform-aws-modules/lambda packaging | Using `source_path` auto-packaging when RSF already produces a zip file | Use `create_package = false` + `local_existing_package` pointing to the pre-built zip RSF produces |
| RSF custom provider `program` path | Passing a relative path (e.g., `./provider.sh`) | `program` must be an absolute path — `CustomProvider._validate_program()` raises `ValueError` on relative paths. Tutorial must use `$(pwd)/provider.sh` or an absolute path at config time |
| FileTransport temp file lifetime | Assuming temp file persists after provider script exits for post-processing | Temp file is deleted in `finally` block immediately after provider script returns; script must read and use it before exiting |
| Terraform state after partial failure | Running `terraform apply` again after failed partial apply without `terraform plan` first | Always run `terraform plan` to assess state before re-apply; tutorial should document recovery procedure |
| AWS provider version for durable_config | Using Terraform AWS provider `>= 5.0` (or any version < 6.25.0) | `durable_config` block requires AWS provider `>= 6.25.0`, released December 4, 2025 |
| Lambda durable invocation | Invoking via unqualified function name or `$LATEST` suffix | Create and invoke via a Lambda alias ARN while Terraform provider issue #45800 (AllowInvokeLatest) is unresolved |
| WorkflowMetadata JSON parsing in provider script | Expecting `triggers` to be a JSON array when received via `ArgsTransport` | Use `FileTransport`; read the JSON file and parse it with `jq` or `python3 -c "import json, sys; data=json.load(open(sys.argv[1]))"` |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| terraform-aws-modules/lambda auto-packaging on every `rsf deploy` | Each deploy re-packages the entire source tree; slow for large codebases | Use `create_package = false` + pre-built zip (RSF already produces the zip) | Any workflow with > 50 MB of source or dependencies |
| Long `execution_timeout` without cost awareness | Tutorial users set 366-day timeout "to be safe" | Document cost implications: durable execution state is stored and billed per execution-second; default to the RSF generator's 24-hour default | Every workflow if timeout far exceeds actual execution time |
| Missing `lifecycle { ignore_changes = [filename, source_code_hash] }` on Lambda | Terraform forces Lambda update on every plan/apply because zip content hash changes | Include `lifecycle` block in tutorial Lambda resource or verify the module sets this automatically | Every deploy cycle without this protection |
| Provider script re-running `terraform init` on every deploy | `terraform init` downloads providers and modules each time; slow without caching | Add `if [ ! -d .terraform ]; then terraform init; fi` guard or use `-upgrade=false` on repeat runs | After first deploy |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Provider script using `shell=True` workaround to bypass absolute path requirement | Shell injection — attacker-controlled metadata values expand in the shell | Never use shell=True; RSF's `CustomProvider` already enforces `shell=False`. Tutorial must not suggest workarounds |
| Committing `terraform.tfstate` to the example repository | State file contains plaintext Lambda ARNs, role ARNs, and account ID | Tutorial `.gitignore` must exclude `*.tfstate`, `*.tfstate.backup`, `.terraform/`, and the module cache |
| Hardcoding AWS account ID in tutorial Terraform | Tutorial fails for readers in different accounts; exposes real account ID in git history | Use `data "aws_caller_identity"` and `data "aws_region"` instead of hardcoded values |
| Over-broad IAM policy (e.g., `Resource: "*"` for durable execution actions) | Excessive permissions granted to Lambda function | Scope durable execution IAM actions to the specific Lambda function ARN, not wildcard |
| Storing sensitive metadata in `ArgsTransport` CLI args | Process args are visible in `ps aux` and system logs | Use `FileTransport` (0600 temp file) for any metadata that might contain sensitive values |
| Module `create_role = false` with hardcoded role ARN | Account-specific ARN leaks into tutorial code committed to a public repo | Use `aws_iam_role` resource data source or parameterize the ARN via variable |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Tutorial shows registry module code before explaining why it differs from raw HCL | Reader is confused about what they are learning and why they need a module | Open with: "Previous tutorials generated raw HCL. This tutorial uses HashiCorp's official Lambda module, which encapsulates best practices and reduces boilerplate. Here is what changes and why." |
| Tutorial does not show the WorkflowMetadata JSON received by the provider script | Reader cannot debug provider script because they do not know what input to expect | Add a debug step: instruct reader to print the JSON file content before Terraform runs; show example JSON output |
| Requiring `jq` without listing it in prerequisites | Tutorial fails at an unexplained parse step | List `jq` in prerequisites, or write provider script to use Python's stdlib JSON module (always available since RSF requires Python 3.13+) |
| Showing `terraform init` output in tutorial without explaining module download | Reader is alarmed by "Downloading modules..." output not seen in previous tutorials | Add a callout: "You will see 'Downloading modules...' — Terraform downloads `terraform-aws-modules/lambda` from the Terraform Registry. This is expected." |
| Tutorial teardown step uses `terraform destroy` directly, bypassing RSF CLI | Breaks the mental model that `rsf` manages the full lifecycle | Use the custom provider's `teardown_args` config and show `rsf teardown` (if it exists) or document how `teardown_args` enables RSF-managed teardown |
| No explanation of what custom provider does differently from TerraformProvider | Reader does not understand the value of the custom provider approach | Show side-by-side: raw HCL the TerraformProvider generates vs. registry module HCL the custom provider script produces |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Module version pinned:** Tutorial uses exact version pin `version = "8.7.0"` (not `~> 8.7` or `>= 8.7`) — verify every `module` block
- [ ] **durable_config actually enabled:** Run `aws lambda get-function --query 'Configuration.DurableConfig'` after deploy — a null or missing key means durable config was silently dropped
- [ ] **Lambda alias created and used for invocation:** All invocation examples reference alias ARN, not `$LATEST` — verify no `$LATEST` references exist in invocation commands
- [ ] **IAM permissions verified with live invocation:** Do not just apply Terraform — invoke the function with a real payload and confirm no `AccessDeniedException`
- [ ] **Provider script has `set -euo pipefail`:** First executable line of `provider.sh` must be this directive — verify in code review
- [ ] **Teardown leaves zero orphaned resources:** Run `aws lambda list-functions --query "Functions[?starts_with(FunctionName, 'rsf-')]"` and `aws logs describe-log-groups --log-group-name-prefix /aws/lambda/rsf-` after teardown
- [ ] **WorkflowMetadata fields map correctly:** Confirm the tutorial workflow's DSL features (triggers, DynamoDB tables) all appear correctly in the metadata JSON received by the provider script — print and inspect before automating
- [ ] **AWS provider version in tutorial `versions.tf`:** Must specify `>= 6.25.0` for `durable_config` block — tutorial must fail fast if reader has older provider cached
- [ ] **Module packaging disabled:** Tutorial module block includes `create_package = false` and `local_existing_package` — verify no `source_path` auto-packaging is active
- [ ] **Integration test invokes a real durable execution:** Tutorial test suite does not just check that `rsf deploy` exited 0 — it must actually invoke the function and poll for durable execution completion

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Module variable name wrong — durable_config silently dropped | MEDIUM | Update variable name, run `terraform apply`; Lambda updates in place without destroy |
| AllowInvokeLatest blocked — invocation fails | LOW | Switch invocation to alias ARN; no infrastructure changes needed |
| IAM action name mismatch — AccessDeniedException | MEDIUM | Update IAM policy document, run `terraform apply`; policy updates in place; re-run invocation test |
| Module version unpinned — tutorial breaks after module release | MEDIUM | Pin to tested version, instruct existing readers to run `terraform init -upgrade=false` |
| ArgsTransport received malformed list data | LOW | Switch `metadata_transport` to `file` in workflow YAML; no infrastructure changes needed |
| Provider script swallowed error — Terraform state may be inconsistent | HIGH | Run `terraform plan` to assess divergence; may need manual `terraform state` commands; document recovery in tutorial appendix |
| `terraform.tfstate` committed to git | HIGH | Revoke any exposed credentials; rotate IAM keys if account ID was exposed; use `git filter-repo` to purge state from history |
| Module packaging conflict — wrong handler included in zip | MEDIUM | Set `create_package = false`, confirm RSF zip is used, redeploy; verify handler path in Lambda console |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| durable_config module exposure gap | Phase 1: Module research and schema verification | `aws lambda get-function --query Configuration.DurableConfig` returns non-null after deploy |
| AllowInvokeLatest missing from provider | Phase 1: Tutorial design — adopt "always use alias" convention | All invocation examples reference alias ARN; no `$LATEST` in tutorial |
| IAM policy action mismatch | Phase 2: IAM design and live permission test | `aws iam simulate-principal-policy` passes; actual durable invocation succeeds with no AccessDeniedException |
| Module version not pinned | Phase 2: Tutorial Terraform scaffolding | Code review: all module source blocks use exact version strings |
| ArgsTransport complex field failure | Phase 2: Transport selection for example workflow | Tutorial uses `file` transport; integration test reads metadata JSON and verifies list fields are present as valid JSON |
| Provider script exit code swallowing | Phase 3: Provider script authoring | Script begins with `set -euo pipefail`; test deliberately injects a failing command and confirms RSF reports failure |
| Lambda packaging conflict | Phase 2: Tutorial Terraform scaffolding | Only one zip file present; correct handler path verified in Lambda console after deploy |
| Missing integration test for durable invocation | Phase 4: Integration testing | Test suite invokes function and polls for durable execution completion — not just exit code check |
| Orphaned resources after teardown | Phase 4: Teardown verification | Post-teardown `aws lambda list-functions` and `aws logs describe-log-groups` show no RSF resources |

---

## Sources

- [terraform-aws-modules/terraform-aws-lambda releases — v8.7.0 durable support added Feb 18 2026](https://github.com/terraform-aws-modules/terraform-aws-lambda/releases)
- [Lambda durable functions Terraform provider issue #45354 — v6.25.0 released Dec 4 2025](https://github.com/hashicorp/terraform-provider-aws/issues/45354)
- [Lambda durable config AllowInvokeLatest missing — issue #45800, open Jan 2026](https://github.com/hashicorp/terraform-provider-aws/issues/45800)
- [Deploy Lambda durable functions with IaC — AWS official documentation](https://docs.aws.amazon.com/lambda/latest/dg/durable-getting-started-iac.html)
- [Configure Lambda durable functions — AWS official docs (AllowInvokeLatest, RetentionPeriodInDays, full durable_config schema)](https://docs.aws.amazon.com/lambda/latest/dg/durable-configuration.html)
- [AWSLambdaBasicDurableExecutionRolePolicy — Pulumi issue #6100 (managed policy rollout timing)](https://github.com/pulumi/pulumi-aws/issues/6100)
- [Module Variables — terraform-aws-modules/terraform-aws-lambda DeepWiki](https://deepwiki.com/terraform-aws-modules/terraform-aws-lambda/2.4-module-variables)
- [Terraform module version constraints — HashiCorp official docs](https://developer.hashicorp.com/terraform/language/expressions/version-constraints)
- [Terraform module version pinning best practices — Masterpoint (module lock file gap)](https://masterpoint.io/blog/ultimate-terraform-versioning-guide/)
- RSF source code: `src/rsf/providers/custom.py`, `src/rsf/providers/transports.py`, `src/rsf/providers/metadata.py`

---
*Pitfalls research for: Terraform Registry Modules Tutorial (RSF v3.2)*
*Researched: 2026-03-03*
