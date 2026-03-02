# Phase 54: Custom Provider - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can configure any external program as an infrastructure provider via `infrastructure: provider: custom` in workflow YAML. The custom program receives workflow metadata through the user's chosen transport mechanism (JSON file, env vars, or CLI arg templates). Subprocess invocation is security-hardened with `shell=False`, absolute path validation, and executable checks. No string interpolation into shell commands.

</domain>

<decisions>
## Implementation Decisions

### YAML Config Shape
- `custom:` sub-block inside `infrastructure:` with typed Pydantic model (replace `dict[str, Any]` placeholder)
- Required fields: `program:` (absolute path to executable)
- Optional fields: `args:` (list of arg templates with `{placeholder}` substitution)
- Success criteria locks: program path must be absolute, validated as executable before invocation

### Claude's Discretion
- Whether to support a single program with action arg vs separate deploy/teardown programs -- pick what fits the provider pattern best
- Whether to allow extra `env:` mapping for static key-value pairs beyond metadata transport vars
- Whether to accept relative paths (resolved from workflow dir) in addition to absolute, or strictly absolute only
- Working directory for custom program execution (workflow dir, project root, or configurable)
- Whether `metadata_transport:` field lives inside `custom:` block or at `infrastructure:` level
- For `args` transport, whether arg templates reuse the existing `args:` field or have a separate field
- Whether to support combining multiple transports or single transport only
- Default metadata transport when user doesn't specify (file transport is the most universal)

### Lifecycle Behavior
- `generate()`: Claude decides -- likely no-op since custom providers don't generate code
- `deploy()`: Invoke configured program with selected metadata transport and substituted args
- `teardown()`: Claude decides approach -- optional teardown program, same program with teardown action, or not-supported error
- `check_prerequisites()`: Claude decides -- verify program exists and is executable, or minimal pass-through
- `validate_config()`: Claude decides -- early validation of transport, placeholders, path format, or Pydantic-only

### Output & Error Handling
- Claude decides: streaming (real-time to terminal) vs captured output
- Claude decides: rich error messages with context vs pass-through CalledProcessError
- Claude decides: whether to log resolved command in non-verbose mode
- Claude decides: optional timeout field or no timeout (user Ctrl+C)

</decisions>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches. The success criteria are prescriptive enough to guide implementation:
1. `infrastructure: provider: custom` + `program:` + `args:` in workflow YAML
2. `shell=False`, absolute path validation, executable check, no string interpolation
3. `metadata_transport:` field selects between file/env/args -- all three work independently

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `InfrastructureProvider` ABC (`providers/base.py`): All 5 abstract methods defined; `run_provider_command()` helper already uses `shell=False`
- `MetadataTransport` hierarchy (`providers/transports.py`): `FileTransport`, `EnvTransport`, `ArgsTransport` all implemented and tested; `ArgsTransport` already validates placeholders against `WorkflowMetadata` fields
- `ProviderContext` dataclass (`providers/base.py`): Single-argument pattern for all provider methods
- `CDKProvider.run_provider_command_streaming()` (`providers/cdk.py`): Streaming subprocess runner available as reference

### Established Patterns
- Provider registration: `register_provider("custom", CustomProvider)` in `providers/__init__.py`
- Config model: `InfrastructureConfig` in `dsl/models.py` already has `custom: dict[str, Any] | None` placeholder ready to be replaced with a typed Pydantic model
- Config cascade: `config.py` resolves infrastructure config from workflow YAML > rsf.toml > default
- Security: All providers use `shell=False` via `run_provider_command()`; `ArgsTransport` blocks attribute access and indexing in placeholders

### Integration Points
- `providers/__init__.py`: Add `register_provider("custom", CustomProvider)` and update `__all__`
- `dsl/models.py`: Replace `custom: dict[str, Any]` with typed `CustomProviderConfig` Pydantic model
- `cli/deploy_cmd.py`: Already routes through provider interface -- custom provider should work with zero deploy_cmd changes
- `cli/doctor_cmd.py`: Already calls `check_prerequisites()` per provider -- custom provider checks will appear automatically
- `cli/validate_cmd.py`: Already validates provider name via registry lookup

</code_context>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 54-custom-provider*
*Context gathered: 2026-03-02*
