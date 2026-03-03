# Phase 52: Terraform Provider, deploy_cmd Refactor, and Configuration - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

`rsf deploy` routes through the provider interface; Terraform is the default with zero-config backward compatibility; provider config can be set in workflow YAML or rsf.toml; provider config errors surface at validate time. The ~80-LOC infra extraction block in deploy_cmd.py is replaced by provider dispatch.

</domain>

<decisions>
## Implementation Decisions

### rsf.toml design
- Location: same directory as the workflow YAML file (no upward traversal, no git root lookup)
- Scope: `[infrastructure]` table only — no project metadata, no non-provider config
- Structure: nested `[infrastructure.terraform]` for provider-specific config, `provider` key at `[infrastructure]` level
- Creation: manual only — no auto-generation from `rsf init` or any other command
- Example:
  ```toml
  [infrastructure]
  provider = "terraform"

  [infrastructure.terraform]
  tf_dir = "terraform"
  ```

### Infrastructure YAML schema
- Placement: top-level sibling in workflow YAML (same level as `StartAt`, `States`, `triggers`)
- Provider-specific config: nested under provider name key
- Example:
  ```yaml
  infrastructure:
    provider: terraform
    terraform:
      tf_dir: terraform
      backend_bucket: my-bucket
  ```
- Merge behavior: YAML `infrastructure:` block fully overrides rsf.toml — no deep merge. What you see in YAML is what you get.
- Validation: strict `extra = "forbid"` on all infrastructure models — unknown fields cause errors (consistent with entire DSL)

### CLI flag handling
- `--tf-dir` renamed to `--output-dir` — generic name, works for any provider. Default value stays "terraform" for backward compatibility
- `--code-only` stays Terraform-specific — error if used with non-Terraform provider: "--code-only is only supported with the terraform provider"
- `--auto-approve` becomes provider-agnostic — passed to any provider that supports confirmation prompts (Terraform uses `-auto-approve`, CDK uses `--require-approval never`)
- `--stage` becomes provider-agnostic via ProviderContext — each provider decides how to use stage (Terraform uses tfvars, CDK could use environment config). Stage isolation (separate output dirs) stays.

### Validation UX
- Error display: inline with existing DSL validation errors using `infrastructure.` field paths (e.g., `infrastructure.provider: Unknown provider 'pulumi'`)
- Unknown provider: show name + available list (matches existing ProviderNotFoundError pattern in registry.py)
- Scope: validate = config correctness only. No prerequisite checks (binary exists, AWS creds) — that's `rsf doctor`
- rsf.toml: validated at both `rsf validate` time (if file exists) and `rsf deploy` time. Config errors surface early.

### Claude's Discretion
- InfrastructureConfig Pydantic model design and field names
- How TerraformProvider wraps the existing TerraformConfig/generate_terraform flow
- Provider registration mechanism (module-level vs lazy import)
- rsf.toml parsing library choice (tomllib vs tomli)
- Exact error message wording beyond the patterns decided above

</decisions>

<specifics>
## Specific Ideas

- rsf.toml structure mirrors the YAML infrastructure block — same nesting pattern for consistency
- Zero-config backward compat is the top priority — existing workflows with no `infrastructure:` block must produce identical behavior
- The ~80-LOC infra extraction block in deploy_cmd.py (lines 114-195) is the primary target for removal

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `InfrastructureProvider` ABC (`providers/base.py`): already has `generate()`, `deploy()`, `teardown()`, `check_prerequisites()`, `validate_config()` — Phase 51 complete
- `ProviderContext` dataclass (`providers/base.py`): has `metadata`, `output_dir`, `stage`, `workflow_path`, `definition` fields — ready for use
- `PrerequisiteCheck` dataclass (`providers/base.py`): feeds into doctor command
- Provider registry (`providers/registry.py`): `get_provider()`, `register_provider()`, `list_providers()` — dict-dispatch ready
- `WorkflowMetadata` dataclass and `create_metadata()` factory (`providers/metadata.py`): metadata extraction already implemented
- `TerraformConfig` and `generate_terraform()` (`terraform/generator.py`): the existing generation flow to wrap
- Jinja2 templates (`terraform/templates/`): 11 HCL template files for Terraform generation

### Established Patterns
- Pydantic `extra = "forbid"` on all DSL models — infrastructure models must follow this
- `model_config = {"extra": "forbid", "populate_by_name": True}` — standard model config
- Rich console for CLI output with `[red]Error:[/red]` and `[green]Success[/green]` patterns
- Typer for CLI argument/option definitions
- Field-path error display in validate_cmd.py: `{field_path}: {message}`

### Integration Points
- `deploy_cmd.py` — primary refactor target, replace direct Terraform calls with provider dispatch
- `validate_cmd.py` — add infrastructure config validation step
- `dsl/models.py` `StateMachineDefinition` — add `infrastructure` field (optional, Pydantic model)
- `dsl/parser.py` — infrastructure block parsed along with rest of YAML
- `providers/__init__.py` — register TerraformProvider on import

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 52-terraform-provider-deploy-cmd-refactor-and-configuration*
*Context gathered: 2026-03-02*
