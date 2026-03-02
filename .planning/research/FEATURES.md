# Feature Research

**Domain:** Pluggable infrastructure provider system for CLI deployment tool
**Researched:** 2026-03-02
**Confidence:** HIGH (core patterns), MEDIUM (CDK-specific integration details)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Abstract provider interface (ABC/Protocol) | Any pluggable system needs a formal contract; Python tooling convention since 3.8+ | LOW | Use `abc.ABC` or `typing.Protocol`; Protocol is preferable for structural subtyping without inheritance coupling |
| Terraform provider (built-in, default) | Terraform is current behavior; must keep working identically | LOW | Wraps existing `subprocess.run()` + `generate_terraform()` flow behind the interface |
| Provider selection via workflow YAML | Users configure provider in their workflow definition, not in CLI flags | LOW | New `infrastructure.provider` key in DSL; falls back to "terraform" if absent |
| Provider selection via project config file | Team-wide provider choice shouldn't be repeated per workflow | LOW | `rsf.yaml` or `pyproject.toml [tool.rsf]` config; workflow YAML overrides project config |
| Informative error on missing/misconfigured provider | Deploy fails clearly when provider name is unknown or required config is absent | LOW | Validate provider name at load time, not at deploy time |
| `--no-infra` flag continues to work | Existing users rely on this; must not regress | LOW | `--no-infra` bypasses provider dispatch entirely — already implemented, must stay |
| Subprocess invocation for external providers | All real-world provider CLIs (terraform, cdk, pulumi) are external binaries | LOW | `subprocess.run()` with configurable program + args is the established pattern |
| Exit code propagation | External provider failure must surface as `rsf deploy` failure | LOW | Non-zero exit from provider program → non-zero exit from `rsf deploy` |
| Working directory control | Provider programs need to run from the right directory (e.g., CDK app dir) | LOW | Configurable `cwd` for subprocess invocation |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Metadata passing: JSON file | Structured workflow metadata (name, states, tables, triggers, stage) written to a known path for providers to read | MEDIUM | Serialise `WorkflowDefinition` fields to JSON; path configurable or defaults to `.rsf-metadata.json` in working dir |
| Metadata passing: environment variables | Zero-config metadata access for simple custom providers; no file I/O needed | LOW | `RSF_WORKFLOW_NAME`, `RSF_STAGE`, `RSF_LAMBDA_HANDLER`, etc. injected into provider subprocess env |
| Metadata passing: CLI args | Allows providers to receive metadata as positional/named args; fits shell script providers | MEDIUM | Configurable arg template in YAML: `args: ["deploy", "--name", "{workflow_name}", "--stage", "{stage}"]` with `{placeholder}` substitution |
| AWS CDK provider (built-in sample) | CDK is the #2 choice for AWS infrastructure; ships CDK app template so users can start immediately | HIGH | Requires CDK bootstrap check, `cdk synth` + `cdk deploy`; CDK app template generation via Jinja2 |
| Custom provider (any program + args) | Lets teams use Pulumi, Ansible, CloudFormation, internal tools — zero lock-in | LOW | `program: my-deploy-script.sh` + `args: [...]` in config; subprocess invocation with metadata env vars |
| Provider config in workflow YAML | Colocation of infra config with workflow definition; no separate config file required | LOW | `infrastructure:` block in workflow YAML DSL; consistent with existing DSL style |
| Generation Gap pattern for CDK templates | Protects user customisations in generated CDK app; matches existing Terraform pattern | MEDIUM | Same `# DO NOT EDIT` first-line marker already used for Terraform HCL files |
| `rsf doctor` provider checks | Provider binary presence (terraform, cdk, pulumi) surfaced in existing health diagnostics | LOW | Extend existing `doctor_cmd.py` with provider-specific binary checks |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Dynamic provider discovery via Python entry_points | Seems extensible; mirrors pytest plugin model | Entry_points require package installation; RSF is a CLI tool, not a library framework. Makes provider authoring unnecessarily complex. Adds a pip install step just to use a custom provider. | Custom provider with `program: ./my-script.sh` — any executable works, no entry_points needed |
| Provider SDK / Python base class users must subclass | Seems type-safe and OOP-elegant | Forces provider authors into RSF's Python object model; breaks polyglot use (bash, Go, etc.); creates tight version coupling. Real tools (Cookiecutter hooks, Serverless Framework) use subprocess/shell for extension, not class inheritance. | Subprocess with env vars + JSON file: any language, any tool |
| Auto-detect provider from installed binaries | "Smart" defaults seem friendly | Which provider wins if both `terraform` and `cdk` are installed? Ambiguity is worse than explicit config. Creates silent wrong-provider deploys. | Explicit `provider: terraform` in config; if absent, error with helpful message |
| Passing full Pydantic model object to provider | Type-safe handoff between RSF internals and provider | Creates tight coupling: providers must be Python, must import RSF internals, must track RSF schema version. | Serialise to JSON file or env vars; providers consume a stable documented format |
| Provider-specific CLI flags on `rsf deploy` | e.g., `--cdk-bootstrap`, `--pulumi-stack` seem convenient | Every new provider adds flags to the top-level CLI. Flag explosion + poor discoverability. | Provider-specific config goes in workflow YAML `infrastructure.options` block |
| Terraform state management built-in to RSF | "RSF should handle remote state for you" | Terraform state is a solved problem (S3 backend, Terraform Cloud). RSF owning this adds operational complexity with no return. Already supported via `backend_bucket` in TerraformConfig. | Document the existing backend config; let Terraform handle its own state |

## Feature Dependencies

```
[Provider interface (ABC/Protocol)]
    └──required by──> [Terraform provider wrapper]
    └──required by──> [CDK provider]
    └──required by──> [Custom provider]

[Provider selection: workflow YAML]
    └──requires──> [DSL parser extension for `infrastructure:` block]
    └──requires──> [Provider interface]

[Provider selection: project config]
    └──enhances──> [Provider selection: workflow YAML]
    └──requires──> [Config file loading logic]

[Metadata passing: JSON file]
    └──requires──> [Provider interface dispatch]
    └──enhances──> [CDK provider]
    └──enhances──> [Custom provider]

[Metadata passing: env vars]
    └──requires──> [Provider interface dispatch]
    └──enhances──> [Custom provider]
    └──conflicts-with──> [Metadata passing: CLI args] (pick primary; support both but document trade-offs)

[CDK provider]
    └──requires──> [Provider interface]
    └──requires──> [CDK app template generation]
    └──optionally-uses──> [Metadata passing: JSON file]

[Custom provider]
    └──requires──> [Provider interface]
    └──requires──> [Metadata passing: env vars] (minimum viable)
    └──optionally-uses──> [Metadata passing: JSON file]
    └──optionally-uses──> [Metadata passing: CLI args]

[rsf doctor provider checks]
    └──enhances──> [All providers]
    └──requires──> [Provider selection config loading]
```

### Dependency Notes

- **Provider interface required by all providers:** The abstract class or Protocol must be designed before any provider is implemented. It defines `generate()` and `deploy()` method signatures, the metadata payload shape, and error handling contract.
- **DSL parser extension required by YAML-based provider selection:** `infrastructure.provider` is a new top-level DSL key. Must add Pydantic model for `InfrastructureConfig` and wire into `WorkflowDefinition`.
- **CDK provider requires app template generation:** Unlike Terraform (which generates HCL from scratch), CDK generates a Python CDK app (`app.py`, `stack.py`, `cdk.json`) once; user edits from there. Generation Gap pattern applies.
- **Metadata passing env vars conflicts with CLI args:** Both are mechanisms for the same data. Design should pick a default (env vars) and allow CLI arg templates as an opt-in override. Don't require users to configure both.

## MVP Definition

### Launch With (v1 — v3.0 milestone)

Minimum viable product — what's needed to validate the concept.

- [ ] Provider interface (ABC or Protocol) — defines the contract all providers implement
- [ ] Terraform provider — wraps existing deploy flow behind the interface; zero behaviour change
- [ ] Custom provider — `program: <path>` + `args: [...]` with env var metadata injection
- [ ] Provider selection in workflow YAML (`infrastructure.provider`) and project config
- [ ] Metadata passing via environment variables (RSF_WORKFLOW_NAME, RSF_STAGE, RSF_LAMBDA_HANDLER, etc.)
- [ ] Metadata passing via JSON file (written to configurable path before provider invocation)
- [ ] CDK provider with sample CDK app template — ships ready-to-use; invokes `cdk deploy`

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] Metadata passing via CLI arg templates — when users need provider programs that don't read env vars
- [ ] `rsf doctor` provider-specific binary checks — extend existing doctor with provider-aware diagnostics
- [ ] CDK `--code-only` equivalent — targeted CDK deploy without full synth (CDK Hotswap)

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Pulumi provider — Pulumi Automation API exists in Python but requires pulumi SDK as dependency; adds weight
- [ ] CloudFormation/SAM provider — RSF already has `rsf export --format cloudformation`; a deploy path could use `aws cloudformation deploy`
- [ ] Provider dry-run / plan display — `rsf diff` already handles Terraform plan; extending to CDK diff would be v2+

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Provider interface (ABC/Protocol) | HIGH | LOW | P1 |
| Terraform provider wrapper | HIGH | LOW | P1 |
| Custom provider (program + args + env vars) | HIGH | LOW | P1 |
| Provider selection via workflow YAML | HIGH | LOW | P1 |
| Metadata passing: env vars | HIGH | LOW | P1 |
| Metadata passing: JSON file | HIGH | LOW | P1 |
| CDK provider + sample template | HIGH | HIGH | P1 |
| Provider selection via project config | MEDIUM | LOW | P2 |
| Metadata passing: CLI args template | MEDIUM | MEDIUM | P2 |
| `rsf doctor` provider checks | MEDIUM | LOW | P2 |
| CDK hotswap (code-only) | LOW | MEDIUM | P3 |
| Pulumi provider | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

How analogous tools handle pluggable provider/backend systems:

| Feature | Serverless Framework | Pulumi | Our Approach |
|---------|----------------------|--------|--------------|
| Provider selection | `provider:` key in serverless.yml | Provider packages installed via npm | `infrastructure.provider:` in workflow YAML or project config |
| Provider extension | JavaScript plugin class with lifecycle hooks | Provider binary + SDK package | Any executable program with env vars / JSON file metadata |
| Metadata to provider | Serverless object (JS runtime coupling) | Pulumi Automation API (SDK coupling) | Env vars + JSON file (language-agnostic, no SDK coupling) |
| Default provider | AWS (hardcoded) | N/A (provider is explicit) | Terraform (existing behavior, backwards compatible) |
| Code generation for provider | No (providers generate their own templates) | No | Yes: CDK app template generation with Generation Gap pattern |
| Multi-stage support | `--stage` flag → providers handle per-stage | Stacks handle environments | `--stage` passed as `RSF_STAGE` env var + included in metadata JSON |

**Key differentiator for RSF:** Unlike Serverless Framework (JS runtime coupling) and Pulumi (SDK coupling), RSF's custom provider is a plain subprocess with structured metadata — any language, any tool, no RSF dependency in the provider.

## Sources

- Existing RSF codebase: `src/rsf/terraform/generator.py`, `src/rsf/cli/deploy_cmd.py` — analysed directly
- Serverless Framework plugin architecture: [Creating Plugins](https://www.serverless.com/framework/docs/guides/plugins/creating-plugins)
- AWS CDK CLI reference: [cdk deploy docs](https://docs.aws.amazon.com/cdk/v2/guide/ref-cli-cmd-deploy.html), [Context values](https://docs.aws.amazon.com/cdk/v2/guide/context.html)
- Pulumi Automation API: [Embedding Pulumi](https://www.pulumi.com/docs/iac/automation-api/), [Python Automation API](https://www.pulumi.com/blog/automation-api-python/)
- IaC tool comparison (2026): [oneuptime.com IaC comparison](https://oneuptime.com/blog/post/2026-02-20-infrastructure-as-code-comparison/view)
- SST move from CDK to Pulumi: [Moving away from CDK](https://sst.dev/blog/moving-away-from-cdk/) — illustrates CDK limitations RSF should route around
- Python plugin systems: [Implementing a Plugin Architecture in Python](https://alysivji.com/simple-plugin-system.html)
- Cookiecutter hooks (subprocess + metadata pattern): [Hooks documentation](https://cookiecutter.readthedocs.io/en/stable/advanced/hooks.html)
- Infrastructure abstraction patterns: [DevOps.com multi-cloud abstraction](https://devops.com/infrastructure-abstraction-will-be-key-to-managing-multi-cloud/)

---
*Feature research for: RSF v3.0 Pluggable Infrastructure Providers*
*Researched: 2026-03-02*
