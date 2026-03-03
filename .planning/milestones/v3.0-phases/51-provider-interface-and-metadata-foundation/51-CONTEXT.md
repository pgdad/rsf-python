# Phase 51: Provider Interface and Metadata Foundation - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

The provider contract and metadata schema exist; all downstream providers (Terraform, CDK, Custom) have a stable interface to implement against. This phase creates the ABC, ProviderContext, WorkflowMetadata dataclass, and all three metadata transports (JSON file, env vars, CLI arg templates). No actual providers are implemented here — that's Phases 52-54.

</domain>

<decisions>
## Implementation Decisions

### WorkflowMetadata modeling
- Stdlib `dataclass`, not Pydantic — matches success criteria (`dataclasses.asdict()` produces valid JSON)
- Signals this is a data-transfer object, not a DSL validation model
- Flat structure with typed lists: top-level fields for workflow_name, stage, triggers (list[dict]), dynamodb_tables (list[dict]), alarms (list[dict]), dlq_enabled, dlq_max_receive_count, dlq_queue_name, lambda_url_enabled, lambda_url_auth_type
- Mirrors the existing `_extract_infrastructure_from_definition()` output pattern from export_cmd.py
- Infra fields only — no reference to the raw StateMachineDefinition. Providers get the definition via ProviderContext if needed

### ABC interface shape
- 5 abstract methods: `generate()`, `deploy()`, `teardown()`, `check_prerequisites()`, `validate_config()`
- `generate()` added beyond the 4 in success criteria — matches existing generate-then-deploy flow in deploy_cmd
- All abstract methods receive a single `ProviderContext` dataclass argument (metadata, output_dir, stage, workflow_path)
- `run_provider_command(cmd, cwd, env)` as a concrete (non-abstract) method on InfrastructureProvider — shared subprocess runner with shell=False, consistent logging, error handling, output streaming
- `check_prerequisites()` returns structured result: `list[PrerequisiteCheck]` with name, status (pass/warn/fail), message — feeds into rsf doctor's multi-check display

### Metadata transport configuration
- One transport per invocation, not combinable — `metadata_transport: 'file' | 'env' | 'args'` in workflow YAML `infrastructure:` block
- Each provider can declare its default transport; Custom providers would typically specify this explicitly
- Terraform/CDK providers ignore metadata transport (they don't need external metadata delivery)

### Env var transport
- RSF_ prefix as specified in success criteria: `RSF_WORKFLOW_NAME`, `RSF_STAGE`, `RSF_METADATA_JSON` at minimum
- `RSF_METADATA_JSON` contains the full JSON blob (same as file contents)
- No expanded individual field env vars beyond the minimum — keep it simple

### CLI arg template transport
- Python `str.format()` style: `{workflow_name}`, `{stage}`, `{metadata_file}` etc.
- Only WorkflowMetadata field names are valid placeholders
- Invalid placeholder raises error at validate time (not at deploy time)

### JSON file transport
- Written to system temp dir via `tempfile.NamedTemporaryFile` — no working directory pollution
- File path passed as `RSF_METADATA_FILE` env var to the provider command
- Mode 0600 as specified in success criteria
- Full `dataclasses.asdict(metadata)` output — file is the canonical metadata truth
- Pretty-printed JSON (indent=2) for debuggability
- Auto-cleanup after provider command completes (try/finally) — clean by default

### Claude's Discretion
- ProviderContext field naming and exact structure beyond metadata/output_dir/stage/workflow_path
- PrerequisiteCheck dataclass design (fields beyond name/status/message)
- Error types and exception hierarchy for provider failures
- Test structure and fixture design
- Whether to add a `cleanup()` lifecycle hook beyond the 5 abstract methods

</decisions>

<specifics>
## Specific Ideas

- WorkflowMetadata should mirror the output of `_extract_infrastructure_from_definition()` in export_cmd.py — that function is essentially the proto-metadata extractor
- The ~80-line infra extraction block in deploy_cmd.py (lines 114-175) duplicates export_cmd — WorkflowMetadata + a factory function will DRY both up (but actual refactoring of deploy_cmd happens in Phase 52)
- Package layout: `src/rsf/providers/__init__.py`, `providers/base.py` (ABC + ProviderContext), `providers/metadata.py` (WorkflowMetadata + transports)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `export_cmd._extract_infrastructure_from_definition()`: Already extracts all DSL infra fields into a dict — serves as reference implementation for WorkflowMetadata factory
- `StateMachineDefinition` in `dsl/models.py`: Source of truth for all infrastructure fields (triggers, dynamodb_tables, alarms, dead_letter_queue, lambda_url)
- `TerraformConfig` in `terraform/generator.py`: Existing structured config object for Terraform generation — will be consumed by TerraformProvider in Phase 52

### Established Patterns
- Pydantic BaseModel for DSL models — but WorkflowMetadata deliberately breaks this pattern as a stdlib dataclass (DTO vs validation model distinction)
- `subprocess.run()` for external tool invocation (deploy_cmd.py lines 210-228) — `run_provider_command()` will generalize this
- Typer + Rich console for CLI output
- Jinja2 for template rendering (terraform/templates/)

### Integration Points
- `deploy_cmd.py` will consume the provider interface in Phase 52 — the ABC must support the existing generate→deploy flow
- `doctor_cmd.py` will call `check_prerequisites()` — structured result must be compatible
- `validate_cmd.py` could call `validate_config()` in Phase 52
- No `providers/` module exists yet — this phase creates it from scratch

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 51-provider-interface-and-metadata-foundation*
*Context gathered: 2026-03-02*
