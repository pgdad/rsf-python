# Phase 52: Terraform Provider, deploy_cmd Refactor, and Configuration - Research

**Researched:** 2026-03-02
**Domain:** Infrastructure provider integration, CLI refactoring, TOML configuration
**Confidence:** HIGH

## Summary

Phase 52 wires the Phase 51 provider abstraction layer into the actual `rsf deploy` command. The core work is: (1) implement `TerraformProvider` wrapping the existing `generator.py` + subprocess calls, (2) refactor `deploy_cmd.py` to call `get_provider()` / `provider.generate()` / `provider.deploy()` instead of the ~80-LOC inline extraction block, (3) add `infrastructure:` block to the DSL YAML schema with Pydantic validation, (4) add `rsf.toml` loading for project-wide provider defaults, and (5) surface config errors at `rsf validate` time.

The existing codebase is well-structured for this: the provider ABC, registry, metadata extraction, and transports are all complete from Phase 51. The main risk is ensuring zero-config backward compatibility -- existing v2.0 workflows with no `infrastructure:` block must produce identical Terraform output and behavior.

**Primary recommendation:** Start with the `InfrastructureConfig` Pydantic model and `rsf.toml` loader, then implement `TerraformProvider`, then refactor `deploy_cmd.py`, then add validation -- building from the inside out to keep each step testable.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- rsf.toml location: same directory as the workflow YAML file (no upward traversal, no git root lookup)
- rsf.toml scope: `[infrastructure]` table only -- no project metadata, no non-provider config
- rsf.toml structure: nested `[infrastructure.terraform]` for provider-specific config, `provider` key at `[infrastructure]` level
- rsf.toml creation: manual only -- no auto-generation from `rsf init` or any other command
- Infrastructure YAML placement: top-level sibling in workflow YAML (same level as `StartAt`, `States`, `triggers`)
- Provider-specific config: nested under provider name key in YAML
- Merge behavior: YAML `infrastructure:` block fully overrides rsf.toml -- no deep merge
- Validation: strict `extra = "forbid"` on all infrastructure models
- `--tf-dir` renamed to `--output-dir` -- generic name, default value stays "terraform"
- `--code-only` stays Terraform-specific -- error if used with non-Terraform provider
- `--auto-approve` becomes provider-agnostic
- `--stage` becomes provider-agnostic via ProviderContext
- Error display: inline with existing DSL validation errors using `infrastructure.` field paths
- Unknown provider: show name + available list (matches existing ProviderNotFoundError pattern)
- Validate = config correctness only, no prerequisite checks (binary exists, AWS creds)
- rsf.toml validated at both `rsf validate` and `rsf deploy` time

### Claude's Discretion
- InfrastructureConfig Pydantic model design and field names
- How TerraformProvider wraps the existing TerraformConfig/generate_terraform flow
- Provider registration mechanism (module-level vs lazy import)
- rsf.toml parsing library choice (tomllib vs tomli)
- Exact error message wording beyond the patterns decided above

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TFPR-01 | TerraformProvider wraps existing generator.py and Jinja2 templates with zero behavior change | Architecture pattern: TerraformProvider delegates to existing TerraformConfig + generate_terraform(); uses create_metadata() for metadata extraction |
| TFPR-02 | rsf deploy delegates to provider interface (generate -> deploy) instead of direct Terraform calls | deploy_cmd refactor pattern: replace ~80-LOC inline extraction with get_provider() + provider.generate() + provider.deploy() |
| TFPR-03 | Existing v2.0 workflows (no infrastructure: block) continue to deploy via Terraform unchanged | Default provider cascade: no config -> "terraform" default; InfrastructureConfig.provider defaults to "terraform" |
| TFPR-04 | Terraform is the default provider when no provider is configured | Registry registration + default in InfrastructureConfig model |
| CONF-01 | User can configure provider in workflow YAML via infrastructure: block | Add optional `infrastructure` field to StateMachineDefinition Pydantic model |
| CONF-02 | User can configure project-wide provider defaults in rsf.toml | tomllib-based loader, same-directory lookup, [infrastructure] table |
| CONF-03 | Workflow YAML infrastructure: overrides rsf.toml defaults | Resolution cascade in deploy_cmd: YAML > rsf.toml > hardcoded default |
| CONF-04 | DSL Pydantic model validates InfrastructureConfig block | Pydantic model with extra="forbid", validated during parse_definition() |
| PROV-05 | Provider configuration errors surface at rsf validate time, not at deploy time | Add infrastructure validation step to validate_cmd.py |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| tomllib | stdlib (3.11+) | Parse rsf.toml files | Project requires Python >= 3.12; no external dependency needed |
| pydantic | existing | InfrastructureConfig model with strict validation | Already used for all DSL models; extra="forbid" pattern established |
| typer | existing | CLI option definitions (--output-dir rename) | Already used for all CLI commands |
| rich | existing | Console output for error display | Already used for all CLI output |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dataclasses | stdlib | ProviderContext, WorkflowMetadata (already exist) | Data transfer between components |
| pathlib | stdlib | File path handling for rsf.toml | Already used throughout codebase |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| tomllib (stdlib) | tomli (PyPI) | tomli needed for Python < 3.11 only; project requires 3.12+ so tomllib is correct |
| Pydantic extra="forbid" | Manual validation | Inconsistent with rest of DSL; Pydantic already handles this pattern |

## Architecture Patterns

### Recommended Project Structure
```
src/rsf/
├── providers/
│   ├── __init__.py          # (exists) Re-exports + TerraformProvider registration
│   ├── base.py              # (exists) ABC, ProviderContext, PrerequisiteCheck
│   ├── registry.py          # (exists) get_provider(), register_provider()
│   ├── metadata.py          # (exists) WorkflowMetadata, create_metadata()
│   ├── transports.py        # (exists) File/Env/Args transports
│   └── terraform.py         # NEW: TerraformProvider implementation
├── dsl/
│   ├── models.py            # MODIFY: add InfrastructureConfig, TerraformProviderConfig
│   └── parser.py            # (no change needed -- Pydantic handles new field)
├── cli/
│   ├── deploy_cmd.py        # MODIFY: refactor to use provider interface
│   └── validate_cmd.py      # MODIFY: add infrastructure validation step
└── config.py                # NEW: rsf.toml loader (load_project_config)
```

### Pattern 1: TerraformProvider wraps existing flow
**What:** TerraformProvider.generate() converts WorkflowMetadata to TerraformConfig and calls generate_terraform(). TerraformProvider.deploy() runs terraform init + terraform apply using run_provider_command().
**When to use:** Always -- this is the canonical pattern for wrapping existing infrastructure in the provider interface.
**Example:**
```python
class TerraformProvider(InfrastructureProvider):
    def generate(self, ctx: ProviderContext) -> None:
        config = self._build_terraform_config(ctx)
        generate_terraform(config=config, output_dir=ctx.output_dir)

    def deploy(self, ctx: ProviderContext) -> None:
        self.run_provider_command(["terraform", "init"], cwd=ctx.output_dir)
        apply_cmd = ["terraform", "apply"]
        if ctx.auto_approve:
            apply_cmd.append("-auto-approve")
        self.run_provider_command(apply_cmd, cwd=ctx.output_dir)
```

### Pattern 2: Configuration cascade (YAML > rsf.toml > default)
**What:** Resolve infrastructure config by checking workflow YAML first, then rsf.toml, then hardcoded default "terraform".
**When to use:** In deploy_cmd.py and validate_cmd.py when resolving which provider to use.
**Example:**
```python
def resolve_infra_config(definition, workflow_path):
    """Resolve infrastructure config: YAML > rsf.toml > default."""
    if definition.infrastructure:
        return definition.infrastructure
    toml_config = load_project_config(workflow_path.parent)
    if toml_config:
        return toml_config
    return InfrastructureConfig()  # defaults to provider="terraform"
```

### Pattern 3: Pydantic model hierarchy for infrastructure config
**What:** `InfrastructureConfig` at top level with `provider` field and optional provider-specific sub-models.
**When to use:** For the `infrastructure:` block in workflow YAML and rsf.toml parsing.
**Example:**
```python
class TerraformProviderConfig(BaseModel):
    model_config = {"extra": "forbid"}
    tf_dir: str = "terraform"
    backend_bucket: str | None = None
    backend_key: str | None = None
    backend_dynamodb_table: str | None = None

class InfrastructureConfig(BaseModel):
    model_config = {"extra": "forbid"}
    provider: str = "terraform"
    terraform: TerraformProviderConfig | None = None
    cdk: dict[str, Any] | None = None       # stub for Phase 53
    custom: dict[str, Any] | None = None     # stub for Phase 54
```

### Anti-Patterns to Avoid
- **Deep-merging YAML over rsf.toml:** User decided full override. Do NOT implement merging logic.
- **Validating prerequisites at validate time:** User decided validate = config correctness only. Binary checks belong in `rsf doctor`.
- **Adding rsf.toml auto-generation:** User decided manual only.
- **Upward rsf.toml traversal:** User decided same-directory only. No git root or parent directory scanning.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TOML parsing | Custom parser | `tomllib` (stdlib) | Handles all TOML edge cases; zero dependencies |
| Config validation | Manual field checks | Pydantic `model_validate()` with `extra="forbid"` | Consistent with DSL models; free error messages |
| Provider lookup | if/elif chain | `get_provider()` from registry.py | Already implemented with clear error messages |
| Metadata extraction | Inline in deploy_cmd | `create_metadata()` from metadata.py | Already implemented, eliminates the ~80-LOC duplication |

**Key insight:** Phase 51 built the infrastructure (ABC, registry, metadata, transports). Phase 52 wires it in. Resist the urge to re-implement what already exists.

## Common Pitfalls

### Pitfall 1: Breaking backward compatibility with --tf-dir rename
**What goes wrong:** Renaming `--tf-dir` to `--output-dir` breaks existing scripts/CI pipelines that use `--tf-dir`.
**Why it happens:** Direct rename without deprecation period.
**How to avoid:** Keep `--tf-dir` as a hidden alias (Typer supports this). The new canonical name is `--output-dir`, but `--tf-dir` still works. Log a deprecation warning when `--tf-dir` is used.
**Warning signs:** Tests that use `--tf-dir` start failing.

### Pitfall 2: TerraformProvider.deploy() not passing stage var file
**What goes wrong:** `--stage prod` stops working because the stage variable file path is not passed through the provider interface.
**Why it happens:** Stage handling is currently embedded in deploy_cmd.py, not in the provider.
**How to avoid:** Add stage-related fields to ProviderContext or pass as part of provider-specific config. The TerraformProvider.deploy() must handle `-var-file` for stages.
**Warning signs:** `rsf deploy --stage prod` fails or ignores stage overrides.

### Pitfall 3: rsf.toml validation rejecting unknown provider-specific sections
**What goes wrong:** `extra="forbid"` on the top-level InfrastructureConfig rejects `[infrastructure.cdk]` before CDK provider exists.
**Why it happens:** Strict validation applied too broadly.
**How to avoid:** Only validate the provider-specific section that matches the configured provider. Other provider sections can use `dict[str, Any]` or be ignored during validation.
**Warning signs:** Valid rsf.toml with future provider config is rejected.

### Pitfall 4: Circular import between providers and dsl.models
**What goes wrong:** Adding InfrastructureConfig to dsl/models.py and importing it from providers creates circular imports.
**Why it happens:** dsl/models.py is imported by providers/metadata.py which imports from dsl/models.py.
**How to avoid:** InfrastructureConfig lives in dsl/models.py (it's part of the DSL schema). Provider-specific config models also live in dsl/models.py. Providers import from dsl/models.py, never the reverse.
**Warning signs:** ImportError at module load time.

### Pitfall 5: ProviderContext missing auto_approve and stage_var_file
**What goes wrong:** TerraformProvider cannot pass --auto-approve to terraform or use -var-file for staged deployments.
**Why it happens:** ProviderContext was designed in Phase 51 before the deploy_cmd integration details were clear.
**How to avoid:** Extend ProviderContext with `auto_approve: bool = False` and any other fields needed by providers. The dataclass is designed to be extensible.
**Warning signs:** Provider.deploy() doesn't have access to CLI flags it needs.

## Code Examples

### rsf.toml loading with tomllib
```python
# src/rsf/config.py
import tomllib
from pathlib import Path
from rsf.dsl.models import InfrastructureConfig

def load_project_config(directory: Path) -> InfrastructureConfig | None:
    """Load rsf.toml from the given directory. Returns None if not found."""
    toml_path = directory / "rsf.toml"
    if not toml_path.exists():
        return None
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
    infra_data = data.get("infrastructure")
    if not infra_data:
        return None
    return InfrastructureConfig.model_validate(infra_data)
```

### Adding infrastructure field to StateMachineDefinition
```python
# In dsl/models.py, add to StateMachineDefinition:
infrastructure: InfrastructureConfig | None = Field(
    default=None, alias="infrastructure"
)
```

### TerraformProvider building TerraformConfig from metadata
```python
def _build_terraform_config(self, ctx: ProviderContext) -> TerraformConfig:
    """Convert ProviderContext metadata to TerraformConfig."""
    md = ctx.metadata  # WorkflowMetadata
    return TerraformConfig(
        workflow_name=md.workflow_name,
        triggers=md.triggers,
        has_sqs_triggers=any(t["type"] == "sqs" for t in md.triggers),
        dynamodb_tables=md.dynamodb_tables,
        has_dynamodb_tables=bool(md.dynamodb_tables),
        alarms=md.alarms,
        has_alarms=bool(md.alarms),
        dlq_enabled=md.dlq_enabled,
        dlq_max_receive_count=md.dlq_max_receive_count,
        dlq_queue_name=md.dlq_queue_name,
        lambda_url_enabled=md.lambda_url_enabled,
        lambda_url_auth_type=md.lambda_url_auth_type,
        stage=ctx.stage,
    )
```

### Infrastructure validation in validate_cmd.py
```python
# After semantic validation (step 4), add:
# 5. Infrastructure config validation
if definition.infrastructure:
    try:
        provider = get_provider(definition.infrastructure.provider)
        # Provider-specific config validation could go here
    except ProviderNotFoundError as exc:
        console.print(f"[red]Validation errors in[/red] {workflow}:")
        console.print(f"  [yellow]infrastructure.provider[/yellow]: {exc}")
        raise typer.Exit(code=1)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Direct Terraform calls in deploy_cmd.py | Provider interface dispatch | Phase 52 (this phase) | Enables multi-provider support |
| ~80-LOC inline metadata extraction | create_metadata() from providers/metadata.py | Phase 51 | Eliminates duplication |
| No configuration file | rsf.toml with [infrastructure] table | Phase 52 (this phase) | Project-wide provider defaults |

## Open Questions

1. **ProviderContext extensibility for CLI flags**
   - What we know: ProviderContext has metadata, output_dir, stage, workflow_path, definition
   - What's unclear: Should auto_approve, code_only, stage_var_file be on ProviderContext or passed differently?
   - Recommendation: Add auto_approve to ProviderContext. code_only is Terraform-specific so it should be handled in TerraformProvider. stage_var_file can be derived from stage + workflow_path.

2. **Provider registration timing**
   - What we know: registry.py has register_provider() and get_provider()
   - What's unclear: Should TerraformProvider be registered at import time (in providers/__init__.py) or lazily?
   - Recommendation: Register at import time in providers/__init__.py since it's the default provider and must always be available. Use a simple `register_provider("terraform", TerraformProvider)` call.

3. **CDK and Custom provider stubs in InfrastructureConfig**
   - What we know: Phase 53 adds CDK, Phase 54 adds Custom
   - What's unclear: Should InfrastructureConfig have typed fields for cdk/custom now, or add them later?
   - Recommendation: Use `dict[str, Any] | None` for cdk and custom now. This allows users to write `infrastructure: provider: cdk` with config, but actual provider implementation comes in later phases. The registry will raise ProviderNotFoundError for unregistered providers.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `src/rsf/providers/` (Phase 51 provider abstraction layer)
- Codebase inspection: `src/rsf/cli/deploy_cmd.py` (current ~80-LOC extraction block, lines 114-195)
- Codebase inspection: `src/rsf/cli/export_cmd.py` (`_extract_infrastructure_from_definition()` duplication)
- Codebase inspection: `src/rsf/dsl/models.py` (StateMachineDefinition, `extra="forbid"` pattern)
- Codebase inspection: `src/rsf/terraform/generator.py` (TerraformConfig, generate_terraform)
- Python docs: `tomllib` module (stdlib since 3.11, project requires 3.12+)

### Secondary (MEDIUM confidence)
- Pydantic v2 documentation: model_validate(), extra="forbid" behavior with nested models

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in use or in stdlib
- Architecture: HIGH - patterns follow established codebase conventions
- Pitfalls: HIGH - identified from direct codebase analysis

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable domain, no external API changes expected)
