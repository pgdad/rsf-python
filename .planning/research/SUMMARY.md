# Project Research Summary

**Project:** RSF v3.0 — Pluggable Infrastructure Providers
**Domain:** Pluggable infrastructure provider abstraction for Python CLI deployment tool
**Researched:** 2026-03-02
**Confidence:** HIGH

## Executive Summary

RSF v3.0 adds a pluggable infrastructure provider system to a mature Python CLI tool that currently hard-codes Terraform as its sole deployment backend. The challenge is introducing a provider abstraction layer without regressing existing Terraform users, without adding RSF runtime dependencies, and without leaking Terraform-specific concepts into the shared interface. Research confirms this is a well-understood "driver pattern" in Python — an `abc.ABC` or `typing.Protocol` interface with a dict-dispatch factory is the correct choice for 3 known providers, with a clear upgrade path to entry-point-based plugins if more providers are added later. All new capability is implemented using stdlib modules only (`abc`, `json`, `os`, `tempfile`, `subprocess`, `shutil`); no new RSF runtime dependencies are required.

The recommended architecture introduces a `src/rsf/providers/` package that sits between the CLI commands and the existing `terraform/` package. The `deploy_cmd.py` infra extraction block (~80 LOC of manual field extraction) is replaced by `provider.generate()` and `provider.deploy()` calls. The existing `TerraformConfig` and `generate_terraform()` stay intact and are wrapped — not replaced — by `TerraformProvider`. A new `providers/metadata.py` module consolidates the infra extraction logic that is currently duplicated between `deploy_cmd.py` and `export_cmd.py`, yielding a single `extract_infra_config()` function used by all providers. The CDK provider generates a Python CDK app directory via Jinja2 (the same template engine already in the stack) and invokes the `cdk` CLI as a subprocess, matching the Terraform provider model exactly.

The dominant risk is the leaky abstraction: defining the provider interface around Terraform's mental model (`TerraformConfig` fields, `tf_dir`, `backend_bucket`) and then papering over it for CDK and custom providers. Prevention requires defining the interface in DSL/workflow semantics — `WorkflowMetadata` with `workflow_name`, `stage`, `triggers`, `dynamodb_tables`, `alarms`, etc. — and requiring all providers to translate internally. A secondary risk is breaking existing Terraform users during the refactor; this is mitigated by a hard default of `"terraform"` when no provider is configured, and a regression test that verifies a v2.0-style `workflow.yaml` (no `infrastructure:` block) continues to invoke Terraform unchanged.

## Key Findings

### Recommended Stack

The entire feature is implemented with existing dependencies plus stdlib. No new packages are added to RSF's `pyproject.toml`. The provider interface uses `abc.ABC` (chosen over `typing.Protocol` because RSF owns all provider implementations and ABC gives runtime `TypeError` on missing methods — safer when users can register custom providers via config). Workflow metadata serialization uses `json`, `os`, and `tempfile` from stdlib. The CDK provider ships a Jinja2-generated CDK app template (Jinja2 already in the stack); the `aws-cdk-lib` package goes only into the generated CDK app's own `requirements.txt`, not into RSF itself.

**Core technologies:**
- `abc.ABC` (stdlib): `InfrastructureProvider` abstract base class — forces `deploy()`, `teardown()`, and `check_prerequisites()` to be implemented; raises `TypeError` at instantiation if missing
- `dataclasses` (stdlib): `ProviderContext` and `ProviderResult` data types — consistent with existing `TerraformConfig`/`TerraformResult` pattern; `dataclasses.asdict()` gives free JSON serialization
- `json` + `tempfile` + `os` (stdlib): Three metadata transport modes — JSON file, environment variables, CLI args — all without new dependencies
- `aws-cdk-lib >= 2.241.0` + `constructs >= 10.0.0`: Goes into the generated CDK app's `requirements.txt` only; never imported by RSF
- `cdk` CLI (Node.js, globally installed): Invoked via `subprocess.run(["cdk", "deploy", ...])` — same model as the Terraform binary; user prerequisite, not RSF dependency

**What NOT to add:**
- `pluggy`: Hook-broadcast semantics don't fit the single-provider-per-deploy model; ABC factory is simpler and correct
- `aws-cdk-lib` in RSF's own dependencies: Would add ~200MB of transitive dependencies for all users, including those who only use Terraform
- `shell=True` in any subprocess call: Already correctly avoided in the codebase; must stay avoided

### Expected Features

**Must have (table stakes — v3.0 launch):**
- Abstract provider interface (`abc.ABC`) — defines the contract; all providers implement it
- Terraform provider — wraps existing deploy flow behind the interface with zero behavior change
- Custom provider — `program: <path>` + `args: [...]` with env var metadata injection; any language, any tool
- Provider selection in workflow YAML (`infrastructure.provider`) and project config (`rsf.toml`)
- Metadata passing via environment variables (`RSF_WORKFLOW_NAME`, `RSF_STAGE`, `RSF_METADATA_JSON`)
- Metadata passing via JSON file (written before provider invocation; path passed as `RSF_METADATA_FILE`)
- CDK provider with generated CDK app template — ships ready-to-use; invokes `cdk deploy` via subprocess

**Should have (add after core validates):**
- Metadata passing via CLI arg templates — for providers that don't read env vars
- `rsf doctor` provider-aware binary checks — Terraform check becomes WARN (not FAIL) for CDK/custom users
- CDK hotswap (`--code-only` equivalent) — targeted Lambda code update without full CDK synth

**Defer to v2+:**
- Pulumi provider — Automation API exists in Python but adds SDK weight
- CloudFormation/SAM provider — RSF already exports CF; a deploy path is a v2+ concern
- Entry-point-based plugin discovery — dict-dispatch factory is sufficient for 3 providers; upgrade path is clear

**Confirmed anti-features (do not build):**
- Dynamic provider discovery via `entry_points` — makes provider authoring unnecessarily complex for v3.0
- Provider SDK / Python base class that users must subclass — breaks polyglot use; subprocess + env vars is the correct extension model
- Auto-detect provider from installed binaries — ambiguous when both Terraform and CDK are installed; explicit config is required
- Provider-specific CLI flags on `rsf deploy` — flag explosion; provider-specific config belongs in `infrastructure.options` in the workflow YAML

### Architecture Approach

The architecture introduces a `providers/` package as a peer to the existing `terraform/` package. The build order is strictly bottom-up: `base.py` (interface) → `metadata.py` (shared extraction) → `config.py` (project config loading) → `terraform.py`, `cdk.py`, `custom.py` (providers) → `__init__.py` (registry/factory). The CLI commands slim down: `deploy_cmd.py` replaces its ~80-LOC infra extraction block with three lines (`get_provider()`, `provider.generate()`, `provider.deploy()`). Provider selection follows a four-level cascade: CLI flag → workflow YAML field → project config → hardcoded default `"terraform"`.

**Major components:**
1. `providers/base.py` — `InfrastructureProvider` ABC with `deploy()`, `teardown()`, `check_prerequisites()`, and `validate_config()` abstract methods; `ProviderContext` and `ProviderResult` dataclasses
2. `providers/metadata.py` — `extract_infra_config()` (single source of truth, eliminates duplication between `deploy_cmd` and `export_cmd`); `WorkflowMetadata` dataclass; JSON file, env var, and CLI arg serializers
3. `providers/config.py` — `load_project_config()` parsing `rsf.toml`; provider selection cascade logic
4. `providers/terraform.py` — `TerraformProvider` wrapping existing `generator.py` + `terraform/` package; no changes to HCL templates or Jinja2 engine
5. `providers/cdk.py` — `CDKProvider` generating CDK app via Jinja2; CDK bootstrap check; `subprocess.run(["cdk", "deploy", ...])`
6. `providers/custom.py` — `CustomProvider` executing user-specified program with metadata via chosen transport; security-hardened subprocess invocation
7. `providers/__init__.py` — dict-dispatch factory: `_PROVIDERS = {"terraform": TerraformProvider, "cdk": CDKProvider, "custom": CustomProvider}`

### Critical Pitfalls

1. **Leaky abstraction (Terraform-shaped interface)** — Define the interface in workflow/DSL semantics (`WorkflowMetadata` with `triggers`, `dynamodb_tables`, etc.), not IaC tool semantics. Warning sign: the words `terraform`, `tf_dir`, `hcl`, or `backend` appear in `providers/base.py`. Prevention: write a CDK provider stub in the same phase as the interface to validate it is genuinely tool-agnostic.

2. **Breaking existing Terraform users** — Default provider must be `"terraform"` with zero config required. The detection cascade (`workflow.yaml` → project config → `"terraform"`) must be verified by a regression test that runs `rsf deploy` against a v2.0-style `workflow.yaml` with no `infrastructure:` block. This test is a success criterion, not an afterthought.

3. **Subprocess deadlock on long-running `terraform apply` / `cdk deploy`** — Use passthrough mode (`subprocess.run(cmd, check=True)` with no PIPE) for interactive, user-facing deploys. Never use `Popen` with sequential `stdout.read()` then `stderr.read()`. Build a shared `run_provider_command()` helper in `base.py` that all providers use; no provider calls `subprocess` directly.

4. **Silent failure — swallowing provider error messages** — On `CalledProcessError`, always re-print `exc.stderr` (and `exc.stdout` for CDK, which mixes error streams) before raising. The `run_provider_command()` helper must handle this; providers must not catch it silently.

5. **Metadata format mismatch across providers** — Define a single canonical `WorkflowMetadata` JSON schema (snake_case, mirrors DSL YAML structure) before implementing any provider. Write serialization tests covering all DSL features (triggers, DynamoDB, alarms, DLQ, lambda_url) before any provider is written. Providers receive the JSON file path as a single argument and parse it themselves.

6. **Provider config validated too late** — Each provider implements `validate_config(config: dict) -> list[str]`; `rsf validate` calls it. Errors must surface at `rsf validate` time, not at `rsf deploy` time mid-execution.

7. **Terraform-coupled non-deploy commands left behind** — `diff_cmd.py`, `doctor_cmd.py`, and `watch_cmd.py` all have Terraform-specific paths. `doctor_cmd.py` must make the Terraform check a WARN (not FAIL) for CDK/custom users. A dedicated command audit phase is required.

8. **Shell injection via custom provider path** — Always `shell=False`; program path must be absolute and executable before invocation; metadata passed via JSON file with restricted permissions (mode 0600), never via string interpolation into env vars.

## Implications for Roadmap

Based on the research, the build order is strictly constrained by dependencies. The interface must exist before any provider; metadata serialization must be tested before any provider consumes it; the Terraform provider (wrapping existing behavior) must work before CDK or custom providers are added. The existing commands (`doctor`, `diff`, `watch`) need a provider-aware audit pass that is a distinct phase, not bundled into provider implementation.

### Phase 1: Provider Interface and Metadata Foundation

**Rationale:** The ABC interface and metadata schema are the foundation everything else depends on. Nothing can be built until the contract is defined. Writing a CDK stub in this phase (without implementing it) validates the interface is not Terraform-shaped. Metadata schema tests must pass before any provider is written.
**Delivers:** `providers/base.py` (InfrastructureProvider ABC, ProviderContext, ProviderResult), `providers/metadata.py` (WorkflowMetadata, extract_infra_config, JSON serializer), metadata schema tests covering all DSL features.
**Addresses:** Provider interface (P1), metadata passing JSON file (P1), metadata passing env vars (P1).
**Avoids:** Leaky abstraction pitfall (Pitfall 1), metadata format mismatch pitfall (Pitfall 5), provider config validated too late (Pitfall 6).

### Phase 2: Terraform Provider and deploy_cmd Refactor

**Rationale:** Terraform is the existing behavior. Wrapping it behind the new interface first proves the abstraction works and that no regression has been introduced, before any new provider is built. The `deploy_cmd.py` refactor is the primary integration point and must be done in this phase — it is what validates the interface design is complete.
**Delivers:** `providers/terraform.py` (TerraformProvider wrapping existing generator), `providers/config.py` (project config loading, provider selection cascade), `providers/__init__.py` (dict-dispatch factory), `deploy_cmd.py` refactored. Regression test confirming v2.0 workflow.yaml continues to invoke Terraform with zero config changes.
**Uses:** Existing `terraform/generator.py`, `terraform/engine.py`, 11 Jinja2 HCL templates — all unchanged.
**Implements:** TerraformProvider, provider registry, deploy command integration.
**Avoids:** Breaking existing Terraform users (Pitfall 2), subprocess deadlock (Pitfall 3).

### Phase 3: CDK Provider

**Rationale:** CDK is the #2 AWS infrastructure choice and the most-requested addition. It has the highest implementation complexity (CDK app template generation, bootstrap check, CDK-specific subprocess behavior, mixed stdout/stderr). It is isolated behind the interface established in Phase 1, so it can be built and tested without touching existing code paths.
**Delivers:** `providers/cdk.py` (CDKProvider with Jinja2-generated CDK app, bootstrap check, `cdk deploy` invocation), CDK app template files, `rsf doctor` CDK binary check.
**Uses:** Jinja2 (already in stack), `aws-cdk-lib >= 2.241.0` in generated app's `requirements.txt` (not in RSF), `cdk` CLI via subprocess.
**Implements:** CDKProvider, CDK app template generation (Generation Gap pattern).
**Avoids:** Silent error swallowing for CDK mixed streams (Pitfall 4), CDK bootstrap prerequisite (integration gotcha).

### Phase 4: Custom Provider

**Rationale:** The custom provider (arbitrary program execution with metadata injection) is the simplest provider to implement but has the most security surface area. It should be built after the interface and subprocess helper are proven by the Terraform and CDK providers.
**Delivers:** `providers/custom.py` (CustomProvider with shell=False subprocess, security-hardened invocation), all three metadata transports (JSON file, env vars, CLI args), security review checklist.
**Uses:** `subprocess` (stdlib, existing pattern), `tempfile` with 0o600 permissions.
**Implements:** CustomProvider, metadata transport modes, security controls.
**Avoids:** Shell injection via custom provider path (Pitfall 8), silent failure (Pitfall 4).

### Phase 5: Provider-Aware Command Audit

**Rationale:** `diff_cmd.py`, `doctor_cmd.py`, and `watch_cmd.py` retain Terraform-specific paths after the provider abstraction is applied to `deploy_cmd.py`. This is a distinct audit phase — each command requires a design decision about what non-Terraform behavior means, which cannot be made as an afterthought within provider implementation phases.
**Delivers:** `doctor_cmd.py` provider-aware binary check (Terraform check is WARN not FAIL for CDK/custom users), `diff_cmd.py` graceful degradation when no Terraform state exists, `watch_cmd.py` provider-aware hot deploy, `export_cmd.py` using shared `extract_infra_config()` to eliminate duplication.
**Avoids:** Terraform-coupled non-deploy commands left behind (Pitfall 7), `rsf doctor` false FAIL for CDK users (UX pitfall).

### Phase Ordering Rationale

- Phase 1 before all others: The interface contract cannot be designed by examining only Terraform. The CDK stub in Phase 1 forces the interface to be DSL-semantic, not tool-semantic.
- Phase 2 before Phase 3/4: Wrap existing behavior first; regression coverage is the safety net for subsequent provider additions.
- Phase 3 before Phase 4: CDK is higher-complexity and exercises the subprocess helper more thoroughly; this reveals bugs before the security-critical custom provider path is built.
- Phase 5 last: The command audit makes design decisions that depend on knowing what the provider interface looks like fully implemented (Phases 1-4).
- No cross-phase dependencies: Each phase delivers independently shippable value. If Phase 3 is deferred, Phases 1-2 and 4-5 still ship a working tool with Terraform and custom providers.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (CDK Provider):** CDK bootstrap detection logic, CDK context value passing conventions, and CDK synthesis output structure are not fully specified in research. Phase planning should include a CDK CLI invocation experiment before committing to the template structure.
- **Phase 5 (Command Audit):** The `watch_cmd.py` provider-aware hot deploy path requires understanding how CDK Hotswap works vs. Terraform `-target`; this is domain-specific and has limited documentation in research.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Interface and Metadata):** ABC vs. Protocol tradeoffs are well-documented; metadata serialization is pure stdlib; no unknowns.
- **Phase 2 (Terraform Provider + deploy_cmd):** Wrapping existing code behind an interface is a standard refactor; existing tests provide regression coverage.
- **Phase 4 (Custom Provider):** subprocess with `shell=False` is a well-understood pattern; security requirements are documented in research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All recommendations are stdlib or existing dependencies; no version conflicts; CDK v2.241.0 confirmed current on PyPI as of 2026-03-02 |
| Features | HIGH | Core features (interface, Terraform wrapper, custom provider, metadata) are well-understood; CDK-specific integration details are MEDIUM |
| Architecture | HIGH | Based on direct source code analysis of the existing codebase (279-LOC `deploy_cmd.py`, 217-LOC `generator.py`, 404-LOC `dsl/models.py`, `export_cmd.py`, `doctor_cmd.py`) |
| Pitfalls | HIGH | Pitfalls are derived from direct codebase analysis plus verified Python documentation and CDK/Terraform GitHub issue references |

**Overall confidence:** HIGH

### Gaps to Address

- **CDK app template structure:** Research specifies that a Jinja2-generated CDK Python app is the right approach, but the exact template structure (`app.py`, `stack.py`, `cdk.json` contents) needs to be defined during Phase 3 planning. Recommend a CDK CLI experiment (`cdk init app --language python`) before template authoring.
- **CDK bootstrap detection:** Research notes that RSF should check for the `CDKToolkit` CloudFormation stack before running `cdk deploy`, but the exact AWS API call or CLI invocation to detect this is not specified. This is a Phase 3 planning detail.
- **`watch_cmd.py` provider behavior:** The `watch --deploy` interaction with a slow provider (CDK deploy takes minutes) is noted as a UX pitfall but the solution (debounce, disable for slow providers, or provider timeout) is not decided. Needs a design decision in Phase 5.
- **`rsf.toml` vs. `pyproject.toml [tool.rsf]`:** Research mentions both as options for project config. Which to support (or both) needs a decision before Phase 2; `tomllib` (stdlib, Python 3.11+) handles TOML parsing for both.

## Sources

### Primary (HIGH confidence)

- Direct codebase analysis: `src/rsf/cli/deploy_cmd.py` (279 LOC), `src/rsf/terraform/generator.py` (217 LOC), `src/rsf/dsl/models.py` (404 LOC), `src/rsf/cli/export_cmd.py`, `src/rsf/cli/doctor_cmd.py`, `src/rsf/cli/watch_cmd.py`
- [aws-cdk-lib on PyPI](https://pypi.org/project/aws-cdk-lib/) — version 2.241.0 current as of 2026-03-02
- [AWS CDK CLI reference](https://docs.aws.amazon.com/cdk/v2/guide/cli.html) — cdk deploy flags, `--context`, `--require-approval`
- [AWS CDK bootstrapping guide](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping-env.html) — bootstrap required before first deploy
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html) — deadlock risks, `capture_output` behavior, `communicate()` contract
- [Python abc module documentation](https://docs.python.org/3/library/abc.html) — ABC vs. Protocol tradeoffs
- [PEP 544 Protocols](https://peps.python.org/pep-0544/) — structural subtyping; `isinstance` behavior with `@runtime_checkable`

### Secondary (MEDIUM confidence)

- [AWS CDK GitHub: "Subprocess exited with error null"](https://github.com/aws/aws-cdk/issues/28637) — CDK exit code opacity
- [Sourcery: Python subprocess tainted env args vulnerability](https://www.sourcery.ai/vulnerabilities/python-lang-security-audit-dangerous-subprocess-use-tainted-env-args) — injection via env
- [Branch by Abstraction pattern (AWS Prescriptive Guidance)](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/branch-by-abstraction.html) — migration without breakage
- [Real-time subprocess output — Eli Bendersky](https://eli.thegreenplace.net/2017/interacting-with-a-long-running-child-process-in-python/) — correct Popen streaming patterns
- [WebSearch: ABC vs Protocol 2025-2026](https://jellis18.github.io/post/2022-01-11-abc-vs-protocol/) — recommendation for internal plugin systems
- [Serverless Framework plugin architecture](https://www.serverless.com/framework/docs/guides/plugins/creating-plugins) — comparison reference

### Tertiary (LOW confidence)

- [SST move from CDK to Pulumi](https://sst.dev/blog/moving-away-from-cdk/) — CDK limitations; informs what RSF should route around
- [CDKTF sunset notice (December 2025)](https://github.com/hashicorp/terraform-cdk) — confirms native AWS CDK (`aws-cdk-lib`) is the correct CDK target (not CDKTF)
- IaC tool comparison 2026 — confirms Terraform + CDK as the top two AWS IaC choices for the target audience

---
*Research completed: 2026-03-02*
*Ready for roadmap: yes*
