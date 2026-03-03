# Phase 55: Provider-Aware Command Audit - Research

**Researched:** 2026-03-02
**Domain:** CLI command provider-awareness
**Confidence:** HIGH

## Summary

Phase 55 audits four CLI commands (doctor, diff, watch, export) that previously assumed Terraform as the sole infrastructure provider. With the v3.0 pluggable provider system now in place (Terraform, CDK, Custom), these commands must gracefully handle any configured provider.

The codebase already has strong foundations: `deploy_cmd.py` is fully provider-aware and serves as the reference pattern. `doctor_cmd.py` already supports `is_active` parameter and provider prerequisite checks. The remaining work is primarily in `diff_cmd.py` (add provider detection before Terraform state loading), `watch_cmd.py` (replace hard-coded `terraform apply` with provider routing), `export_cmd.py` (replace duplicated extraction logic with `create_metadata()`), and enhancing `doctor_cmd.py` output to visually distinguish provider-relevant checks and skip irrelevant project checks.

**Primary recommendation:** Follow the established `deploy_cmd.py` pattern (resolve_infra_config -> get_provider -> provider methods) for watch and diff commands; use `create_metadata()` + `dataclasses.asdict()` to replace the duplicated extraction in export_cmd.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Terraform binary check already uses `is_active` param -- behavior is correct (WARN not FAIL when non-TF provider active)
- Output should visually distinguish which checks are relevant to the active provider
- Provider prerequisite checks (e.g., CDK's Node.js/CDK CLI checks) should appear in the output
- The `terraform/` directory check under Project should be skipped when Terraform is not the active provider
- Auto-detect provider from workflow via `resolve_infra_config()` (same pattern as deploy_cmd)
- When provider is not Terraform, print a clear message: diff is not available for this provider
- Do not crash or show misleading "No deployed state found -- showing all as new" for non-TF providers
- Detect provider before attempting any Terraform state loading
- `rsf watch --deploy` should route through the provider interface, not hard-code Terraform commands
- Follow the same provider detection pattern as deploy_cmd (resolve_infra_config -> get_provider)
- Replace the hard-coded `terraform apply` in `run_cycle()` with provider-based deploy
- The watch loop itself (file monitoring, validate, generate) stays unchanged -- only the deploy step changes
- Replace `_extract_infrastructure_from_definition()` in export_cmd.py with `create_metadata()` from providers/metadata.py
- The two functions are near-identical -- metadata.py is the canonical source
- `_build_sam_template()` should work with the result of create_metadata() (convert via dataclasses.asdict if needed)
- Delete the duplicated function entirely after replacement

### Claude's Discretion
- Doctor output formatting details (grouping, dimming, annotations) -- pick what fits existing Rich console patterns
- Whether to show "Active provider: X" header in doctor output
- Diff exit code when provider doesn't support diff (0 vs 1)
- Whether diff message suggests native provider CLI alternatives (e.g., "use cdk diff")
- Whether to structure diff for future provider extensibility
- Watch deploy scope per cycle (code-only vs full deploy)
- Whether watch shows provider name in status line
- Whether watch runs prerequisite checks at startup
- Whether export_cmd becomes provider-aware or stays SAM-only

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CMDI-01 | `rsf doctor` shows provider binary as WARN (not FAIL) for non-Terraform providers | Already implemented via `is_active` param. Phase adds visual distinction of active vs inactive checks, provider label, and skipping `terraform/` directory check for non-TF providers. |
| CMDI-02 | `rsf diff` gracefully degrades when no Terraform state exists (non-Terraform providers) | Add provider detection at start of `diff()`, short-circuit with clear message before any Terraform state loading when provider is not terraform. |
| CMDI-03 | `rsf watch --deploy` works with the configured provider | Replace hard-coded `terraform apply` in `run_cycle()` with provider-based deploy using `resolve_infra_config()` + `get_provider()` + `provider.deploy()`. |
| CMDI-04 | `rsf export` uses shared `extract_infra_config()` eliminating code duplication | Replace `_extract_infrastructure_from_definition()` with `create_metadata()` + `dataclasses.asdict()`. Delete duplicate function. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rsf.config.resolve_infra_config | internal | Provider detection from workflow YAML | Canonical config cascade (YAML > rsf.toml > default) |
| rsf.providers.get_provider | internal | Provider instance by name | Dict-dispatch registry pattern |
| rsf.providers.base.ProviderContext | internal | Context for provider operations | Single-argument pattern for provider methods |
| rsf.providers.metadata.create_metadata | internal | Extract infrastructure metadata from DSL | Canonical metadata extraction (replaces export_cmd duplicate) |
| dataclasses.asdict | stdlib | Convert dataclass to dict | Needed for WorkflowMetadata -> dict conversion for SAM template builder |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rich.console.Console | existing | Rich terminal output | All CLI command output formatting |
| typer | existing | CLI framework | Command definitions, exit codes |

## Architecture Patterns

### Pattern 1: Provider Detection (from deploy_cmd.py)
**What:** Detect configured provider from workflow YAML using config cascade
**When to use:** Any command that needs to know the active provider
**Example:**
```python
from rsf.config import resolve_infra_config
from rsf.dsl.parser import load_definition

definition = load_definition(workflow)
infra_config = resolve_infra_config(definition, workflow.parent)
provider_name = infra_config.provider  # "terraform", "cdk", or "custom"
```

### Pattern 2: Provider Routing (from deploy_cmd.py)
**What:** Route operations through provider interface instead of hard-coding
**When to use:** When a command needs to invoke provider-specific operations
**Example:**
```python
from rsf.providers import get_provider
from rsf.providers.base import ProviderContext
from rsf.providers.metadata import create_metadata

provider = get_provider(infra_config.provider)
metadata = create_metadata(definition, workflow_name, stage=stage)
ctx = ProviderContext(metadata=metadata, output_dir=output_dir, stage=stage, workflow_path=workflow)
provider.deploy(ctx)
```

### Pattern 3: Metadata Extraction (from metadata.py)
**What:** Extract infrastructure configuration using canonical create_metadata()
**When to use:** Any command that needs infrastructure metadata from DSL definition
**Example:**
```python
from dataclasses import asdict
from rsf.providers.metadata import create_metadata

metadata = create_metadata(definition, workflow_name)
infra_dict = asdict(metadata)
# infra_dict has same structure as old _extract_infrastructure_from_definition() output
```

### Anti-Patterns to Avoid
- **Hard-coding provider commands:** Don't shell out to `terraform` directly; use provider.deploy()
- **Loading Terraform state for non-TF providers:** Detect provider first, skip state loading entirely
- **Duplicating metadata extraction:** Use create_metadata(), not a local copy of the extraction logic

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Provider detection | Manual YAML parsing of infrastructure block | `resolve_infra_config()` | Handles cascade (YAML > rsf.toml > default) |
| Infrastructure extraction | Local `_extract_infrastructure_from_definition()` | `create_metadata()` + `asdict()` | Already canonical, tested, maintained |
| Provider operations | Direct subprocess calls to terraform/cdk/custom | `get_provider()` + provider methods | Provider interface handles all providers uniformly |

## Common Pitfalls

### Pitfall 1: Breaking existing tests
**What goes wrong:** Changing function signatures or removing functions breaks tests that import them directly
**Why it happens:** Tests import `_extract_infrastructure_from_definition` from `export_cmd`
**How to avoid:** Update test imports to use `create_metadata` + `asdict` instead. Or keep a thin wrapper that calls `create_metadata` internally.
**Warning signs:** ImportError in test_export.py after removing the function

### Pitfall 2: Dict key mismatch between WorkflowMetadata and old infra dict
**What goes wrong:** `_build_sam_template()` expects specific dict keys that don't match `asdict(WorkflowMetadata)`
**Why it happens:** WorkflowMetadata has a `stage` field not in old dict; old dict has `workflow_name` as key
**How to avoid:** Compare the two schemas side by side. WorkflowMetadata.asdict() produces identical keys for all infrastructure fields. The only extras are `stage` which `_build_sam_template` doesn't use and will ignore.
**Warning signs:** KeyError or missing template resources

### Pitfall 3: Watch deploy needs full provider context
**What goes wrong:** Provider deploy requires ProviderContext with metadata, but run_cycle doesn't create it
**Why it happens:** run_cycle currently only uses subprocess.run directly
**How to avoid:** Build ProviderContext inside run_cycle's deploy branch, following deploy_cmd pattern
**Warning signs:** AttributeError on provider.deploy() or missing metadata fields

### Pitfall 4: Diff exit code semantics
**What goes wrong:** Non-zero exit on "diff not available" could break CI pipelines
**Why it happens:** Current behavior exits 1 when differences exist
**How to avoid:** Exit 0 with informational message when provider doesn't support diff (it's not an error, just not applicable)
**Warning signs:** CI scripts failing unexpectedly with non-Terraform providers

## Code Examples

### Doctor: Skip terraform/ directory check for non-TF
```python
# In run_all_checks(), conditionally add terraform/ directory check
if workflow_path and (workflow_path.exists() or workflow_path.parent.exists()):
    results.append(_check_workflow(workflow_path))
    if tf_dir and provider_name == "terraform":  # Only check terraform/ dir for TF provider
        results.append(_check_directory("terraform/", tf_dir))
    if handlers_dir:
        results.append(_check_directory("handlers/", handlers_dir))
```

### Doctor: Show active provider label
```python
# In _render_results(), add provider info after Environment header
console.print(f"\n[bold]Environment[/bold] [dim](provider: {provider_name})[/dim]")
```

### Diff: Provider detection and early exit
```python
from rsf.config import resolve_infra_config

# Detect provider before any Terraform-specific operations
try:
    infra_config = resolve_infra_config(local_def, workflow.parent)
    provider_name = infra_config.provider
except Exception:
    provider_name = "terraform"  # fallback to default

if provider_name != "terraform":
    console.print(
        f"[yellow]Diff is not available for the {provider_name} provider.[/yellow]\n"
        f"The diff command compares local workflow with Terraform state."
    )
    raise typer.Exit(code=0)
```

### Watch: Provider-based deploy
```python
from rsf.config import resolve_infra_config
from rsf.providers import get_provider
from rsf.providers.base import ProviderContext
from rsf.providers.metadata import create_metadata

# In run_cycle deploy branch:
infra_config = resolve_infra_config(definition, workflow.parent)
provider = get_provider(infra_config.provider)
workflow_name = definition.comment or workflow.stem.replace("_", "-")
metadata = create_metadata(definition, workflow_name, stage=stage)
ctx = ProviderContext(
    metadata=metadata,
    output_dir=tf_dir or (workflow.parent / "terraform"),
    stage=stage,
    workflow_path=workflow,
    definition=definition,
    auto_approve=True,  # watch mode always auto-approves
)
provider.generate(ctx)
provider.deploy(ctx)
```

### Export: Replace duplicate with create_metadata
```python
from dataclasses import asdict
from rsf.providers.metadata import create_metadata

# Replace _extract_infrastructure_from_definition call:
metadata = create_metadata(definition, workflow_name)
infra = asdict(metadata)
template = _build_sam_template(infra)
```

## Open Questions

1. **Watch deploy: full vs code-only**
   - What we know: Current watch deploy does targeted `terraform apply -target=aws_lambda_function.*` (code-only pattern)
   - What's unclear: Should provider-based watch deploy do full deploy or code-only equivalent?
   - Recommendation: Use full provider.deploy() since not all providers support targeted deploys. The provider's deploy method handles the appropriate scope.

2. **Doctor: Active provider in JSON output**
   - What we know: `--json` output currently has checks and summary
   - What's unclear: Should JSON include `provider_name` field?
   - Recommendation: Add `provider` field to JSON output for programmatic consumers.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `deploy_cmd.py` (lines 29-227) -- gold standard provider-aware command
- Codebase analysis: `doctor_cmd.py` (lines 63-123, 301-344) -- existing `is_active` and provider prerequisite support
- Codebase analysis: `watch_cmd.py` (lines 82-117) -- hard-coded terraform commands to replace
- Codebase analysis: `diff_cmd.py` (lines 190-226, 279-345) -- Terraform-specific state loading
- Codebase analysis: `export_cmd.py` (lines 26-115) -- duplicate extraction to remove
- Codebase analysis: `metadata.py` (lines 44-152) -- canonical create_metadata

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all internal, well-understood code
- Architecture: HIGH - deploy_cmd provides proven reference pattern
- Pitfalls: HIGH - clear code overlap between metadata.py and export_cmd.py makes impact predictable

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable internal codebase)
