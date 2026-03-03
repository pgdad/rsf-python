# Phase 55: Provider-Aware Command Audit - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Audit and fix all CLI commands that assumed Terraform so they behave correctly for CDK and custom providers. No command should produce false errors or silently do the wrong thing when a non-Terraform provider is configured. Four commands need changes: doctor, diff, watch, and export.

</domain>

<decisions>
## Implementation Decisions

### Doctor check labeling
- Terraform binary check already uses `is_active` param — behavior is correct (WARN not FAIL when non-TF provider active)
- Output should visually distinguish which checks are relevant to the active provider
- Provider prerequisite checks (e.g., CDK's Node.js/CDK CLI checks) should appear in the output
- The `terraform/` directory check under Project should be skipped when Terraform is not the active provider

### Diff provider messaging
- Auto-detect provider from workflow via `resolve_infra_config()` (same pattern as deploy_cmd)
- When provider is not Terraform, print a clear message: diff is not available for this provider
- Do not crash or show misleading "No deployed state found — showing all as new" for non-TF providers
- Detect provider before attempting any Terraform state loading

### Watch deploy routing
- `rsf watch --deploy` should route through the provider interface, not hard-code Terraform commands
- Follow the same provider detection pattern as deploy_cmd (resolve_infra_config → get_provider)
- Replace the hard-coded `terraform apply` in `run_cycle()` with provider-based deploy
- The watch loop itself (file monitoring, validate, generate) stays unchanged — only the deploy step changes

### Export deduplication
- Replace `_extract_infrastructure_from_definition()` in export_cmd.py with `create_metadata()` from providers/metadata.py
- The two functions are near-identical — metadata.py is the canonical source
- `_build_sam_template()` should work with the result of create_metadata() (convert via dataclasses.asdict if needed)
- Delete the duplicated function entirely after replacement

### Claude's Discretion
- Doctor output formatting details (grouping, dimming, annotations) — pick what fits existing Rich console patterns
- Whether to show "Active provider: X" header in doctor output
- Diff exit code when provider doesn't support diff (0 vs 1)
- Whether diff message suggests native provider CLI alternatives (e.g., "use cdk diff")
- Whether to structure diff for future provider extensibility
- Watch deploy scope per cycle (code-only vs full deploy)
- Whether watch shows provider name in status line
- Whether watch runs prerequisite checks at startup
- Whether export_cmd becomes provider-aware or stays SAM-only

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `deploy_cmd.py`: Already fully refactored for provider interface — use as reference pattern for watch_cmd and diff_cmd
- `resolve_infra_config()` from `rsf.config`: Canonical provider detection from workflow YAML
- `get_provider()` from `rsf.providers`: Provider instance lookup by name
- `ProviderContext` from `rsf.providers.base`: Context object for provider operations
- `create_metadata()` from `rsf.providers.metadata`: Canonical infra extraction (replaces export_cmd duplicate)
- `_check_terraform(is_active=)` in doctor_cmd: Already supports active/inactive distinction
- `_check_provider_prerequisites()` in doctor_cmd: Already runs provider-specific checks
- `_DYNAMIC_ENV_NAMES` set in doctor_cmd: Already tracks dynamically added provider check names

### Established Patterns
- Provider detection: `resolve_infra_config(definition, workflow.parent)` → `infra_config.provider`
- Provider instantiation: `get_provider(provider_name)` → provider instance with `check_prerequisites()`, `generate()`, `deploy()`
- Context creation: `ProviderContext(metadata=, output_dir=, stage=, workflow_path=, ...)`
- Rich console output: All commands use `rich.console.Console` with `[green]`, `[red]`, `[yellow]`, `[bold]` markup
- Exit codes: `typer.Exit(code=0)` for success, `typer.Exit(code=1)` for errors

### Integration Points
- `watch_cmd.run_cycle()` lines 87-116: Hard-coded terraform commands to replace with provider routing
- `diff_cmd.diff()`: Needs provider detection before `_load_deployed_definition()` call
- `diff_cmd._load_deployed_definition()`: Looks for terraform.tfstate — should be bypassed for non-TF providers
- `export_cmd._extract_infrastructure_from_definition()`: Duplicate to remove, replace with `create_metadata()` + `dataclasses.asdict()`
- `doctor_cmd.run_all_checks()`: Already has `provider_name` param — rendering could be enhanced

</code_context>

<specifics>
## Specific Ideas

- deploy_cmd.py is the gold standard for provider-aware command patterns — doctor, diff, watch, and export should follow its approach
- The duplicated extraction logic in export_cmd.py and providers/metadata.py is a clear DRY violation — metadata.py's `create_metadata()` is canonical

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 55-provider-aware-command-audit*
*Context gathered: 2026-03-02*
