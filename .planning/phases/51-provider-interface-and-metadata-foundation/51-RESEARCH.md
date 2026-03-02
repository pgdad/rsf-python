# Phase 51: Provider Interface and Metadata Foundation - Research

**Researched:** 2026-03-02
**Domain:** Python ABC design, dataclass-based DTOs, subprocess management, metadata transport patterns
**Confidence:** HIGH

## Summary

Phase 51 creates the foundational provider abstraction layer and metadata schema for RSF's pluggable infrastructure system. The core deliverables are: (1) an `InfrastructureProvider` ABC in `providers/base.py` with abstract lifecycle methods, (2) a `WorkflowMetadata` stdlib dataclass that captures all DSL infrastructure fields, (3) three metadata transport mechanisms (JSON file, env vars, CLI arg templates), and (4) supporting types (`ProviderContext`, `PrerequisiteCheck`).

The existing codebase provides a strong reference implementation in `export_cmd._extract_infrastructure_from_definition()` which already extracts all infrastructure fields from `StateMachineDefinition` into a plain dict. The `WorkflowMetadata` dataclass formalizes this pattern. The `doctor_cmd.py` already defines a `CheckResult` dataclass with `name`, `status`, `message` fields that maps closely to the planned `PrerequisiteCheck` return type.

**Primary recommendation:** Build the `providers/` package as a self-contained module with zero dependencies on existing CLI commands. The metadata factory function should accept a `StateMachineDefinition` and produce a `WorkflowMetadata` — this creates a clean seam for Phase 52 to refactor `deploy_cmd.py` and `export_cmd.py` to use it.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- WorkflowMetadata is stdlib `dataclass`, not Pydantic — matches success criteria (`dataclasses.asdict()` produces valid JSON)
- Signals this is a data-transfer object, not a DSL validation model
- Flat structure with typed lists: top-level fields for workflow_name, stage, triggers (list[dict]), dynamodb_tables (list[dict]), alarms (list[dict]), dlq_enabled, dlq_max_receive_count, dlq_queue_name, lambda_url_enabled, lambda_url_auth_type
- Mirrors the existing `_extract_infrastructure_from_definition()` output pattern from export_cmd.py
- Infra fields only — no reference to the raw StateMachineDefinition. Providers get the definition via ProviderContext if needed
- 5 abstract methods: `generate()`, `deploy()`, `teardown()`, `check_prerequisites()`, `validate_config()`
- `generate()` added beyond the 4 in success criteria — matches existing generate-then-deploy flow in deploy_cmd
- All abstract methods receive a single `ProviderContext` dataclass argument (metadata, output_dir, stage, workflow_path)
- `run_provider_command(cmd, cwd, env)` as a concrete (non-abstract) method on InfrastructureProvider — shared subprocess runner with shell=False, consistent logging, error handling, output streaming
- `check_prerequisites()` returns structured result: `list[PrerequisiteCheck]` with name, status (pass/warn/fail), message — feeds into rsf doctor's multi-check display
- One transport per invocation, not combinable — `metadata_transport: 'file' | 'env' | 'args'` in workflow YAML `infrastructure:` block
- Each provider can declare its default transport; Custom providers would typically specify this explicitly
- Terraform/CDK providers ignore metadata transport (they don't need external metadata delivery)
- RSF_ prefix as specified in success criteria: `RSF_WORKFLOW_NAME`, `RSF_STAGE`, `RSF_METADATA_JSON` at minimum
- `RSF_METADATA_JSON` contains the full JSON blob (same as file contents)
- No expanded individual field env vars beyond the minimum — keep it simple
- Python `str.format()` style: `{workflow_name}`, `{stage}`, `{metadata_file}` etc.
- Only WorkflowMetadata field names are valid placeholders
- Invalid placeholder raises error at validate time (not at deploy time)
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PROV-01 | User can deploy with any registered infrastructure provider via a common interface | ABC design with `deploy()`, `generate()`, `teardown()`, `check_prerequisites()`, `validate_config()` abstract methods; `ProviderContext` as single argument pattern |
| PROV-02 | Provider context (workflow metadata, output dir, stage) is passed as structured dataclass | `ProviderContext` dataclass with `metadata: WorkflowMetadata`, `output_dir: Path`, `stage: str | None`, `workflow_path: Path` fields |
| PROV-03 | Provider registry resolves provider name to implementation via dict-dispatch factory | Simple `dict[str, type[InfrastructureProvider]]` registry with `get_provider()` factory function |
| PROV-04 | All providers use shared `run_provider_command()` helper for subprocess invocation | Concrete method on ABC base class using `subprocess.run()` with `shell=False`, streaming output, structured error handling |
| META-01 | Canonical `WorkflowMetadata` schema captures all DSL infrastructure fields | Stdlib `dataclass` mirroring `_extract_infrastructure_from_definition()` output; factory function `from_definition()` converts `StateMachineDefinition` |
| META-02 | User can pass workflow metadata to external provider via JSON file | `FileTransport` writes `dataclasses.asdict()` JSON to tempfile with mode 0600, passes path as `RSF_METADATA_FILE` env var, auto-cleanup |
| META-03 | User can pass workflow metadata to external provider via environment variables | `EnvTransport` sets `RSF_WORKFLOW_NAME`, `RSF_STAGE`, `RSF_METADATA_JSON` environment variables |
| META-04 | User can pass workflow metadata to external provider via CLI arg templates | `ArgsTransport` uses `str.format()` with WorkflowMetadata field names as valid placeholders, validates at config time |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `abc` (stdlib) | Python 3.12+ | Abstract base class for `InfrastructureProvider` | Locked decision — gives runtime `TypeError` on missing abstract methods |
| `dataclasses` (stdlib) | Python 3.12+ | `WorkflowMetadata`, `ProviderContext`, `PrerequisiteCheck` DTOs | Locked decision — `dataclasses.asdict()` produces valid JSON per success criteria |
| `subprocess` (stdlib) | Python 3.12+ | `run_provider_command()` subprocess execution | Existing pattern in `deploy_cmd.py`, `doctor_cmd.py` |
| `tempfile` (stdlib) | Python 3.12+ | JSON file transport temp file creation | Locked decision — no working directory pollution |
| `json` (stdlib) | Python 3.12+ | JSON serialization for metadata transports | Standard for dict/dataclass serialization |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typing` (stdlib) | Python 3.12+ | Type hints (`Literal`, `Union`) | Type annotations for status literals, optional fields |
| `os` (stdlib) | Python 3.12+ | File permissions (`os.chmod`), env var manipulation | JSON file transport (mode 0600), env var transport |
| `pathlib` (stdlib) | Python 3.12+ | Path handling for output dirs, workflow paths | Consistent with existing RSF codebase pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `abc.ABC` | `typing.Protocol` | Protocol = structural typing (duck typing); ABC = nominal typing with runtime `TypeError`. ABC chosen (locked decision) because RSF owns all providers |
| `dataclasses` | Pydantic `BaseModel` | Pydantic adds validation overhead unnecessary for a DTO; locked decision favors `dataclasses.asdict()` simplicity |

**Installation:** No new dependencies required. All Phase 51 code uses Python stdlib only.

## Architecture Patterns

### Recommended Project Structure
```
src/rsf/
├── providers/
│   ├── __init__.py         # Package exports: InfrastructureProvider, ProviderContext, etc.
│   ├── base.py             # ABC + ProviderContext + PrerequisiteCheck + run_provider_command
│   ├── metadata.py         # WorkflowMetadata dataclass + from_definition() factory
│   ├── transports.py       # MetadataTransport ABC + FileTransport, EnvTransport, ArgsTransport
│   └── registry.py         # Provider name → class mapping, get_provider() factory
```

### Pattern 1: Single-Argument Context Object
**What:** All ABC abstract methods receive a single `ProviderContext` dataclass instead of multiple parameters.
**When to use:** When the set of arguments is likely to grow over time.
**Example:**
```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ProviderContext:
    metadata: WorkflowMetadata
    output_dir: Path
    stage: str | None
    workflow_path: Path

class InfrastructureProvider(ABC):
    @abstractmethod
    def deploy(self, ctx: ProviderContext) -> None: ...
```

### Pattern 2: Factory Function for Metadata Extraction
**What:** A `WorkflowMetadata.from_definition(definition, workflow_name, stage)` classmethod or module-level factory that converts a `StateMachineDefinition` to `WorkflowMetadata`.
**When to use:** When the source data (Pydantic model) differs structurally from the target (stdlib dataclass).
**Example:**
```python
def create_metadata(
    definition: StateMachineDefinition,
    workflow_name: str,
    stage: str | None = None,
) -> WorkflowMetadata:
    """Extract infrastructure metadata from a DSL definition."""
    # Mirrors _extract_infrastructure_from_definition() logic
    return WorkflowMetadata(
        workflow_name=workflow_name,
        stage=stage,
        triggers=[...],
        dynamodb_tables=[...],
        # ...
    )
```

### Pattern 3: Transport Strategy Pattern
**What:** `MetadataTransport` ABC with `prepare(metadata, env)` and `cleanup()` methods. Each transport (file, env, args) is a concrete implementation.
**When to use:** When multiple delivery mechanisms share the same interface.
**Example:**
```python
class MetadataTransport(ABC):
    @abstractmethod
    def prepare(self, metadata: WorkflowMetadata, env: dict[str, str]) -> list[str]:
        """Prepare transport. Mutates env dict, returns extra CLI args."""
        ...

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up transport resources (e.g., temp files)."""
        ...
```

### Pattern 4: Dict-Dispatch Registry
**What:** Provider names map to classes via a simple dict. No metaclass magic, no entry_points.
**When to use:** When the set of providers is known at compile time and explicitly registered.
**Example:**
```python
_PROVIDERS: dict[str, type[InfrastructureProvider]] = {}

def register_provider(name: str, cls: type[InfrastructureProvider]) -> None:
    _PROVIDERS[name] = cls

def get_provider(name: str) -> InfrastructureProvider:
    if name not in _PROVIDERS:
        raise ProviderNotFoundError(f"Unknown provider: {name}")
    return _PROVIDERS[name]()
```

### Anti-Patterns to Avoid
- **Leaky abstraction via IaC-tool semantics:** The interface must speak in DSL/workflow terms (WorkflowMetadata), not Terraform/CDK terms. Provider implementations translate.
- **Shell=True in subprocess calls:** Locked decision — always `shell=False` with explicit argument lists.
- **Metaclass-based auto-registration:** Over-engineering for 3 providers. Simple dict is sufficient and debuggable.
- **Mixing validation model with DTO:** WorkflowMetadata is deliberately NOT Pydantic. It's a data transfer object, not a validation boundary.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Temp file management | Custom file creation/cleanup | `tempfile.NamedTemporaryFile(delete=False)` + `try/finally` | Handles race conditions, OS-specific temp dirs |
| JSON serialization of dataclass | Custom dict builder | `dataclasses.asdict()` + `json.dumps()` | Standard, recursive, handles nested dataclasses |
| Subprocess streaming | Custom process management | `subprocess.run(capture_output=True)` or `subprocess.Popen` with line-by-line read | Well-tested, handles signals, cross-platform |
| String template validation | Regex-based placeholder detection | `string.Formatter().parse()` | Standard library, handles edge cases (escaped braces, format specs) |

**Key insight:** Phase 51 is 100% stdlib Python. No new dependencies. The complexity is in the interface design, not the implementation.

## Common Pitfalls

### Pitfall 1: dataclasses.asdict() with nested non-dataclass objects
**What goes wrong:** If WorkflowMetadata contains fields that are Pydantic models or custom classes, `dataclasses.asdict()` will fail or produce unexpected output.
**Why it happens:** `asdict()` recursively converts dataclass instances but doesn't handle arbitrary objects.
**How to avoid:** Keep all WorkflowMetadata fields as primitive types, `list[dict]`, or nested dataclasses. No Pydantic models, no custom classes.
**Warning signs:** `TypeError` from `asdict()` or `json.dumps()` on the result.

### Pitfall 2: tempfile cleanup on exception
**What goes wrong:** Temp file left on disk if provider command raises and cleanup is in a simple `finally` that itself can fail.
**Why it happens:** `os.unlink()` on a non-existent or locked file raises an exception that masks the original error.
**How to avoid:** Use `try/except` inside the `finally` block for cleanup: `try: os.unlink(path) except OSError: pass`.
**Warning signs:** Accumulating temp files in `/tmp`.

### Pitfall 3: str.format() with untrusted templates
**What goes wrong:** Templates like `{0.__class__.__bases__}` can access object attributes.
**Why it happens:** Python's `str.format()` supports attribute access and index access.
**How to avoid:** Validate template at config time — only allow placeholders that match `WorkflowMetadata` field names. Use `string.Formatter().parse()` to extract field names and reject anything with format_spec or conversion containing attribute access.
**Warning signs:** Template strings with dots or brackets inside placeholders.

### Pitfall 4: ABC with __init__ parameters
**What goes wrong:** If the ABC defines `__init__` with specific parameters, subclasses must call `super().__init__()` correctly.
**Why it happens:** Python ABC doesn't enforce `__init__` signatures.
**How to avoid:** Keep ABC `__init__` minimal or absent. If the provider needs configuration, pass it via a separate config object or class attribute — not constructor parameters.
**Warning signs:** `TypeError: __init__() got unexpected keyword argument` in provider subclasses.

### Pitfall 5: Environment variable pollution across tests
**What goes wrong:** `EnvTransport` sets `RSF_*` env vars that leak into subsequent test cases.
**Why it happens:** `os.environ` is process-global state.
**How to avoid:** Use `monkeypatch.setenv()` / `monkeypatch.delenv()` in pytest, or build the env dict without mutating `os.environ` (pass env dict to `subprocess.run(env=...)`).
**Warning signs:** Tests passing in isolation but failing when run together.

## Code Examples

### ABC with abstract and concrete methods
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
import subprocess
import logging

logger = logging.getLogger(__name__)

@dataclass
class PrerequisiteCheck:
    name: str
    status: Literal["pass", "warn", "fail"]
    message: str

class InfrastructureProvider(ABC):
    @abstractmethod
    def generate(self, ctx: ProviderContext) -> None: ...

    @abstractmethod
    def deploy(self, ctx: ProviderContext) -> None: ...

    @abstractmethod
    def teardown(self, ctx: ProviderContext) -> None: ...

    @abstractmethod
    def check_prerequisites(self, ctx: ProviderContext) -> list[PrerequisiteCheck]: ...

    @abstractmethod
    def validate_config(self, ctx: ProviderContext) -> None: ...

    def run_provider_command(
        self,
        cmd: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Shared subprocess runner for provider commands."""
        logger.info("Running: %s", " ".join(cmd))
        merged_env = {**os.environ, **(env or {})}
        return subprocess.run(
            cmd,
            cwd=cwd,
            env=merged_env,
            check=True,
            capture_output=True,
            text=True,
            shell=False,
        )
```

### WorkflowMetadata dataclass with factory
```python
from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass
class WorkflowMetadata:
    workflow_name: str
    stage: str | None = None
    handler_count: int = 0
    timeout_seconds: int | None = None
    triggers: list[dict[str, Any]] = field(default_factory=list)
    dynamodb_tables: list[dict[str, Any]] = field(default_factory=list)
    alarms: list[dict[str, Any]] = field(default_factory=list)
    dlq_enabled: bool = False
    dlq_max_receive_count: int = 3
    dlq_queue_name: str | None = None
    lambda_url_enabled: bool = False
    lambda_url_auth_type: str = "NONE"

def create_metadata(
    definition: StateMachineDefinition,
    workflow_name: str,
    stage: str | None = None,
) -> WorkflowMetadata:
    # Mirrors export_cmd._extract_infrastructure_from_definition()
    ...
```

### FileTransport with cleanup
```python
import tempfile
import json
import os

class FileTransport(MetadataTransport):
    def __init__(self):
        self._temp_path: str | None = None

    def prepare(self, metadata: WorkflowMetadata, env: dict[str, str]) -> list[str]:
        fd, path = tempfile.mkstemp(suffix=".json", prefix="rsf_metadata_")
        self._temp_path = path
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(asdict(metadata), f, indent=2, default=str)
            os.chmod(path, 0o600)
        except Exception:
            os.close(fd)
            raise
        env["RSF_METADATA_FILE"] = path
        return []

    def cleanup(self) -> None:
        if self._temp_path:
            try:
                os.unlink(self._temp_path)
            except OSError:
                pass
            self._temp_path = None
```

### CLI arg template validation
```python
import string

def validate_arg_template(template: str, valid_fields: set[str]) -> None:
    """Validate CLI arg template uses only valid WorkflowMetadata field names."""
    formatter = string.Formatter()
    for _, field_name, _, _ in formatter.parse(template):
        if field_name is None:
            continue
        # Reject attribute access (e.g., {metadata.__class__})
        base_name = field_name.split(".")[0].split("[")[0]
        if base_name not in valid_fields:
            raise ValueError(
                f"Invalid placeholder '{{{field_name}}}' in CLI arg template. "
                f"Valid placeholders: {sorted(valid_fields)}"
            )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Direct `subprocess.run()` in CLI commands | Shared `run_provider_command()` on ABC | Phase 51 (new) | Consistent logging, error handling, security across all providers |
| Infrastructure extraction as dict in export_cmd | Typed `WorkflowMetadata` dataclass | Phase 51 (new) | Type safety, IDE completion, JSON serialization guarantees |
| Terraform-only deployment | Provider-agnostic interface | Phase 51 (new) | Foundation for CDK, Custom providers in Phases 53-54 |

**Deprecated/outdated:**
- `export_cmd._extract_infrastructure_from_definition()` returns an untyped dict — will be superseded by `create_metadata()` returning `WorkflowMetadata` (refactoring happens in Phase 52)
- `deploy_cmd._deploy_full()` inline infrastructure extraction (~60 lines) — duplicates export_cmd logic; Phase 52 replaces with single `create_metadata()` call

## Open Questions

1. **Should `run_provider_command()` support real-time output streaming?**
   - What we know: Current `deploy_cmd.py` uses `subprocess.run()` with no `capture_output`, letting terraform output stream to terminal directly. The `doctor_cmd.py` uses `capture_output=True`.
   - What's unclear: Whether `capture_output=True` (capture and return) or streaming (no capture, direct terminal output) is the right default for deploy operations.
   - Recommendation: Default to `capture_output=True` for programmatic use. Add an optional `stream: bool` parameter that uses `subprocess.Popen` with line-by-line output forwarding when True. This preserves Terraform's interactive output during `rsf deploy`.

2. **Should `ProviderContext` include `definition: StateMachineDefinition` or just `metadata: WorkflowMetadata`?**
   - What we know: CONTEXT.md says "Infra fields only — no reference to the raw StateMachineDefinition. Providers get the definition via ProviderContext if needed."
   - What's unclear: The statement seems contradictory — "infra fields only" vs "via ProviderContext if needed."
   - Recommendation: Include `definition` as an optional field on `ProviderContext` (not on `WorkflowMetadata`). This way WorkflowMetadata stays clean as a DTO, but providers that need the full definition (e.g., TerraformProvider needs state definitions for codegen) can access it through the context.

## Sources

### Primary (HIGH confidence)
- Python stdlib `abc` module — ABC, abstractmethod behavior verified in Python 3.12 docs
- Python stdlib `dataclasses` module — `asdict()` behavior, `field(default_factory=...)` pattern verified in Python 3.12 docs
- Python stdlib `string.Formatter.parse()` — template placeholder extraction verified in Python 3.12 docs
- Existing RSF codebase: `export_cmd.py`, `deploy_cmd.py`, `doctor_cmd.py`, `dsl/models.py`, `terraform/generator.py`

### Secondary (MEDIUM confidence)
- None — all patterns verified against stdlib docs and existing codebase

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 100% stdlib Python, all APIs verified
- Architecture: HIGH — patterns derived from existing codebase (`export_cmd._extract_infrastructure_from_definition`, `doctor_cmd.CheckResult`, `terraform/generator.TerraformConfig`)
- Pitfalls: HIGH — common Python patterns, well-documented in stdlib

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stdlib is stable, 30-day window)
