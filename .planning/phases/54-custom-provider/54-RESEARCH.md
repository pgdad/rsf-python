# Phase 54: Custom Provider - Research

**Researched:** 2026-03-02
**Domain:** Subprocess invocation, security-hardened external program execution, metadata transport
**Confidence:** HIGH

## Summary

Phase 54 implements a `CustomProvider` that allows users to configure any external program as an infrastructure provider via `infrastructure: provider: custom` in workflow YAML. The implementation sits on top of a mature foundation: the `InfrastructureProvider` ABC (Phase 51), the `MetadataTransport` hierarchy with `FileTransport`, `EnvTransport`, and `ArgsTransport` (Phase 51), the provider registry (Phase 51), and the `run_provider_command()` helper with `shell=False` (Phase 51). The `CDKProvider` (Phase 53) and `TerraformProvider` (Phase 52) serve as concrete reference implementations.

The core work is: (1) a typed Pydantic `CustomProviderConfig` model replacing the `dict[str, Any]` placeholder in `InfrastructureConfig`, (2) a `CustomProvider` class implementing all 5 abstract methods with security-hardened subprocess invocation, and (3) wiring the `metadata_transport` field to select which transport mechanism delivers metadata to the external program.

**Primary recommendation:** Implement `CustomProvider` as a thin orchestration layer that validates the program path, instantiates the correct `MetadataTransport`, and delegates subprocess execution to the existing `run_provider_command_streaming()` pattern from `CDKProvider`. All three transports already exist and are tested -- no transport code needs to be written.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
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
- `generate()`: Claude decides -- likely no-op since custom providers don't generate code
- `deploy()`: Invoke configured program with selected metadata transport and substituted args
- `teardown()`: Claude decides approach -- optional teardown program, same program with teardown action, or not-supported error
- `check_prerequisites()`: Claude decides -- verify program exists and is executable, or minimal pass-through
- `validate_config()`: Claude decides -- early validation of transport, placeholders, path format, or Pydantic-only
- Claude decides: streaming (real-time to terminal) vs captured output
- Claude decides: rich error messages with context vs pass-through CalledProcessError
- Claude decides: whether to log resolved command in non-verbose mode
- Claude decides: optional timeout field or no timeout (user Ctrl+C)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CUST-01 | User can configure an arbitrary program as infrastructure provider with specified arguments | `CustomProviderConfig` Pydantic model with `program`, `args`, `metadata_transport` fields; registered via `register_provider("custom", CustomProvider)` |
| CUST-02 | Custom provider invocation uses `shell=False` with security-hardened subprocess | Inherit `run_provider_command()` from base class (already uses `shell=False`); validate absolute path + executable bit; no string interpolation |
| CUST-03 | User can select which metadata transport (JSON file, env vars, CLI args) to use per provider | Wire `metadata_transport` config field to existing `FileTransport`, `EnvTransport`, `ArgsTransport` classes; all three already implemented and tested |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `subprocess` | stdlib | Process execution | `run_provider_command()` already wraps it with `shell=False` |
| Python `shutil` | stdlib | `which()` for executable detection | Same pattern used by CDK and Terraform providers |
| Python `pathlib` | stdlib | Path validation (absolute check, exists, executable) | Project standard for all path operations |
| Pydantic v2 | existing dep | `CustomProviderConfig` model | All provider configs use Pydantic models |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `os` | stdlib | `os.access()` for executable permission check | Validating program is executable before invocation |
| `logging` | stdlib | Debug/info logging of resolved commands | Same pattern as base.py and cdk.py |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `subprocess.run` | `asyncio.create_subprocess_exec` | Async not needed; all providers use sync subprocess |
| Custom streaming | `run_provider_command_streaming()` from CDK | CDK's streaming method is battle-tested; copy pattern |

## Architecture Patterns

### Recommended Project Structure
```
src/rsf/providers/
├── __init__.py         # Add register_provider("custom", CustomProvider)
├── base.py             # InfrastructureProvider ABC (unchanged)
├── cdk.py              # CDKProvider (reference for streaming pattern)
├── custom.py           # NEW: CustomProvider implementation
├── metadata.py         # WorkflowMetadata (unchanged)
├── registry.py         # Provider registry (unchanged)
├── terraform.py        # TerraformProvider (reference)
└── transports.py       # All 3 transports (unchanged, reused)

src/rsf/dsl/
└── models.py           # Replace custom: dict[str,Any] with CustomProviderConfig

tests/test_providers/
└── test_custom_provider.py  # NEW: CustomProvider tests
```

### Pattern 1: Single Program with Action Argument
**What:** Use a single `program` field; pass the action (deploy/teardown) as a positional arg that the user can template in `args:`
**When to use:** This is the recommended approach -- simpler config, matches how most deployment scripts work (e.g., `./deploy.sh deploy`, `./deploy.sh teardown`)
**Example:**
```yaml
infrastructure:
  provider: custom
  custom:
    program: /opt/deploy/my-infra.sh
    args: [deploy, --env, "{stage}", --workflow, "{workflow_name}"]
    metadata_transport: file
```

For teardown, the provider substitutes the action:
```yaml
# User configures args with action placeholder or provider prepends action
```

**Recommendation:** The `deploy()` method uses the user's `args` as-is. The `teardown()` method uses a separate optional `teardown_args` field, or if absent, raises a clear error that custom teardown is not configured. This avoids magic action substitution.

### Pattern 2: Transport Selection via Config Field
**What:** `metadata_transport:` field inside the `custom:` block selects which MetadataTransport to use
**When to use:** Always -- this is the CUST-03 requirement
**Example:**
```yaml
infrastructure:
  provider: custom
  custom:
    program: /opt/deploy/my-infra.sh
    args: [deploy, --meta, "{metadata_file}"]
    metadata_transport: file  # or "env" or "args"
```

**Transport mapping:**
- `file` -> `FileTransport()` (writes JSON to temp file, sets `RSF_METADATA_FILE` env var)
- `env` -> `EnvTransport()` (sets `RSF_WORKFLOW_NAME`, `RSF_STAGE`, `RSF_METADATA_JSON`)
- `args` -> `ArgsTransport(arg_templates)` (substitutes `{placeholder}` in args)

### Pattern 3: Security Validation Before Execution
**What:** Validate program path is absolute, exists, and is executable before ever calling subprocess
**When to use:** Every invocation -- both `deploy()` and `teardown()`
**Example:**
```python
def _validate_program(self, program: str) -> Path:
    path = Path(program)
    if not path.is_absolute():
        raise ValueError(f"Custom provider program must be absolute path, got: {program}")
    if not path.exists():
        raise FileNotFoundError(f"Custom provider program not found: {program}")
    if not os.access(path, os.X_OK):
        raise PermissionError(f"Custom provider program is not executable: {program}")
    return path
```

### Anti-Patterns to Avoid
- **Shell=True:** Never. The base class enforces `shell=False` but custom provider must not circumvent it.
- **String interpolation into commands:** Never use f-strings or `.format()` to build shell command strings. Always use list-of-strings for subprocess.
- **Relative paths:** Success criteria requires absolute path validation. Strictly enforce this.
- **Trusting user env vars:** Merge env from transport on top of `os.environ`, don't let user-supplied env override critical vars like `PATH` without awareness.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Metadata delivery | Custom file writing/env setting | `FileTransport`, `EnvTransport`, `ArgsTransport` | All three fully implemented and tested in `transports.py` |
| Subprocess execution | Direct `subprocess.run()` calls | `run_provider_command()` or `run_provider_command_streaming()` | Base class helper enforces `shell=False`, merges env, handles errors |
| Provider registration | Manual dict entries | `register_provider("custom", CustomProvider)` | Registry pattern in `__init__.py` |
| Config validation | Manual dict parsing | Pydantic `CustomProviderConfig` model | Type safety, defaults, validation errors for free |
| Placeholder substitution | Custom regex/template engine | `ArgsTransport._validate_templates()` | Already blocks attribute access, indexing, and invalid placeholders |

**Key insight:** Nearly all the infrastructure for this phase exists. The custom provider is primarily an integration/wiring exercise connecting existing components.

## Common Pitfalls

### Pitfall 1: Shell Injection via Args
**What goes wrong:** If args contain user-controlled content and `shell=True` is used, arbitrary command execution is possible.
**Why it happens:** Developer forgets that `{stage}` could contain semicolons or pipes.
**How to avoid:** Always use `shell=False` (enforced by `run_provider_command()`). The `ArgsTransport` already validates placeholders at construction time and only substitutes known field names.
**Warning signs:** Any use of `shell=True`, string concatenation of commands, or `os.system()`.

### Pitfall 2: Relative Path Resolution Ambiguity
**What goes wrong:** A relative path like `./deploy.sh` resolves differently depending on CWD at invocation time.
**Why it happens:** CWD varies between CLI invocation contexts.
**How to avoid:** Strictly require absolute paths per success criteria #2. Validate with `Path.is_absolute()` at config validation time.
**Warning signs:** Any `Path.resolve()` or `Path.cwd()` in path handling code.

### Pitfall 3: Transport Cleanup on Error
**What goes wrong:** If `deploy()` raises an exception, `FileTransport` temp file is never cleaned up.
**Why it happens:** Missing try/finally pattern around transport lifecycle.
**How to avoid:** Always use try/finally: `transport.prepare()` ... `finally: transport.cleanup()`.
**Warning signs:** `transport.prepare()` without corresponding `cleanup()` in a finally block.

### Pitfall 4: Forgetting to Pass Transport Args to Subprocess
**What goes wrong:** `ArgsTransport.prepare()` returns extra CLI args, but they never get appended to the subprocess command.
**Why it happens:** Developer only sets up env vars and forgets the return value.
**How to avoid:** Always capture `extra_args = transport.prepare(metadata, env)` and append to command list.
**Warning signs:** `transport.prepare()` return value discarded.

### Pitfall 5: Config Model Not Wired to InfrastructureConfig
**What goes wrong:** `CustomProviderConfig` exists but `InfrastructureConfig.custom` still typed as `dict[str, Any]`.
**Why it happens:** Forgetting to update the type annotation in `models.py`.
**How to avoid:** Replace `custom: dict[str, Any] | None = None` with `custom: CustomProviderConfig | None = None` in `InfrastructureConfig`.
**Warning signs:** Runtime errors about dict not having `.program` attribute.

## Code Examples

### CustomProviderConfig Pydantic Model
```python
# In src/rsf/dsl/models.py (or separate file imported there)
class CustomProviderConfig(BaseModel):
    """Custom provider configuration block."""
    model_config = {"extra": "forbid", "populate_by_name": True}

    program: str  # Absolute path to executable
    args: list[str] = []  # Arg templates with {placeholder} substitution
    teardown_args: list[str] | None = None  # Optional teardown arg templates
    metadata_transport: Literal["file", "env", "args"] = "file"
    env: dict[str, str] | None = None  # Optional extra env vars
    timeout: int | None = None  # Optional timeout in seconds
```

### Transport Factory
```python
def _create_transport(self, config: CustomProviderConfig) -> MetadataTransport:
    """Create the appropriate MetadataTransport from config."""
    if config.metadata_transport == "file":
        return FileTransport()
    elif config.metadata_transport == "env":
        return EnvTransport()
    elif config.metadata_transport == "args":
        return ArgsTransport(config.args)
    raise ValueError(f"Unknown metadata_transport: {config.metadata_transport}")
```

### Deploy Method Pattern
```python
def deploy(self, ctx: ProviderContext) -> None:
    """Invoke custom program with metadata transport."""
    config = self._get_config(ctx)
    program = self._validate_program(config.program)
    transport = self._create_transport(config)
    env: dict[str, str] = {}
    if config.env:
        env.update(config.env)
    try:
        extra_args = transport.prepare(ctx.metadata, env)
        cmd = [str(program)] + self._resolve_args(config.args, ctx) + extra_args
        self.run_provider_command_streaming(cmd, cwd=ctx.workflow_path.parent, env=env)
    finally:
        transport.cleanup()
```

### Program Validation
```python
def _validate_program(self, program: str) -> Path:
    """Validate program path: absolute, exists, executable."""
    path = Path(program)
    if not path.is_absolute():
        raise ValueError(
            f"Custom provider program must be an absolute path, got: {program}"
        )
    if not path.exists():
        raise FileNotFoundError(
            f"Custom provider program not found: {program}"
        )
    if not os.access(path, os.X_OK):
        raise PermissionError(
            f"Custom provider program is not executable: {program}\n"
            f"Fix: chmod +x {program}"
        )
    return path
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `custom: dict[str, Any]` placeholder | Typed `CustomProviderConfig` Pydantic model | This phase | Type safety, validation, IDE support |
| Only terraform/cdk providers | User-configurable custom provider | This phase | Users can use any deployment tool |

**Deprecated/outdated:**
- The `custom: dict[str, Any] | None` placeholder in `InfrastructureConfig` is from Phase 52 and must be replaced with the typed model.

## Open Questions

1. **Teardown args vs action pattern**
   - What we know: CDK and Terraform have distinct deploy/teardown commands. Custom scripts commonly accept an action argument.
   - What's unclear: Whether users prefer a single `args` field with action substitution or separate `teardown_args`.
   - Recommendation: Support both -- `teardown_args` for explicit teardown config, fallback to raising NotImplementedError if neither teardown_args nor a sensible default exists. This is the safest approach.

2. **Working directory for custom program**
   - What we know: CDK uses `output_dir`, Terraform uses `output_dir`. Custom providers don't generate files.
   - What's unclear: Whether users expect CWD to be the workflow directory or project root.
   - Recommendation: Use `ctx.workflow_path.parent` (workflow directory) as CWD. This is where the workflow YAML lives and is the most intuitive location.

## Sources

### Primary (HIGH confidence)
- Codebase: `src/rsf/providers/base.py` -- InfrastructureProvider ABC, run_provider_command()
- Codebase: `src/rsf/providers/transports.py` -- FileTransport, EnvTransport, ArgsTransport (all tested)
- Codebase: `src/rsf/providers/cdk.py` -- CDKProvider reference implementation with streaming
- Codebase: `src/rsf/providers/terraform.py` -- TerraformProvider reference implementation
- Codebase: `src/rsf/providers/__init__.py` -- Registration pattern
- Codebase: `src/rsf/dsl/models.py` -- InfrastructureConfig with `custom: dict[str, Any]` placeholder
- Codebase: `src/rsf/config.py` -- Config resolution cascade
- Codebase: `tests/test_providers/` -- Test patterns for providers and transports

### Secondary (MEDIUM confidence)
- Python subprocess documentation: `shell=False` security best practices

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries are stdlib or existing project dependencies
- Architecture: HIGH - Follows established provider patterns with CDK/Terraform as references
- Pitfalls: HIGH - Based on direct codebase analysis of existing patterns

**Research date:** 2026-03-02
**Valid until:** 2026-04-01 (stable -- no external dependencies changing)
