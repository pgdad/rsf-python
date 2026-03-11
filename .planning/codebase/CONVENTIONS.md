# Coding Conventions

**Analysis Date:** 2026-03-11

## Language & Version

**Python:** 3.12+ (required)
- Uses `from __future__ import annotations` in all modules for forward-compatible type hints
- Type hints are mandatory throughout the codebase

## Naming Patterns

**Files:**
- Lowercase with underscores: `config.py`, `task_handler.py`, `jsonpath.py`
- Test files: `test_<module>.py` or `test_<area>_<feature>.py`
- Private/helper modules within packages: `_parser.py`, `_engine.py`

**Functions & Methods:**
- Lowercase with underscores (snake_case): `load_project_config()`, `evaluate_jsonpath()`, `register_provider()`
- Private methods: Prefixed with single underscore: `_resolve_dotted_path()`, `_Parser` (private class)
- Test methods in classes: `test_<specific_behavior>`: `test_create_factory()`, `test_get_missing_raises()`

**Variables & Constants:**
- Local/instance variables: snake_case: `execution_id`, `state_name`, `poll_interval`
- Constants: UPPERCASE: `MAX_NESTING_DEPTH = 10`, `TERMINAL_STATUSES = frozenset({...})`
- Private module constants: `_PROVIDERS: dict[str, type[InfrastructureProvider]] = {}`

**Types & Classes:**
- PascalCase: `ExecutionContext`, `ContextObject`, `TaskState`, `ProviderNotFoundError`
- Enums: PascalCase: `ExecutionStatus`, `QueryLanguage`
- Dataclasses: `@dataclass` with PascalCase names and field names matching AWS ASL convention (PascalCase for ASL fields)
- Pydantic models: `BaseModel` subclasses in PascalCase with `model_config = {"extra": "forbid"}` for strict validation

**Modules/Packages:**
- Directory structure: lowercase with underscores: `inspect/`, `dsl/`, `cdk/`
- Top-level packages: `rsf.*`, example: `rsf.context`, `rsf.providers`, `rsf.io`

## Import Organization

**Order of imports:**
1. `from __future__ import annotations` (always first)
2. Standard library imports (grouped): `import os`, `from pathlib import Path`, `from typing import ...`
3. Third-party imports: `import pydantic`, `import typer`, `import fastapi`, `import boto3`
4. Local/package imports: `from rsf.dsl.models import ...`

**Style:**
- Group related imports from standard library together
- One blank line between each group
- Use fully qualified module imports, not `from ... import *`
- Explicit imports with long lines allowed (line length 120)

**Path aliases:**
- Direct package imports: `from rsf.context.model import ContextObject`
- No barrel file abuse; each file has specific imports

## Code Style

**Formatting:**
- Line length: 120 characters (configured in `pyproject.toml`)
- Tool: `ruff` formatter (will be used, configured in `pyproject.toml`)

**Linting:**
- Tool: `ruff`
- Configuration: `[tool.ruff]` in `pyproject.toml`
- Selected rules: `["E", "F", "W"]` (errors, undefined names, warnings)
- Enforced but not extensive; focuses on critical issues

**String formatting:**
- Double quotes for strings: `"hello"` (not single quotes)
- F-strings for interpolation: `f"value: {var}"`
- Formatted strings in error messages: `f"Unknown provider: {name}. Available: {available}"`

## Documentation & Comments

**Module docstrings:**
- Always present at top of file
- Triple-quoted: `"""..."""`
- First line is summary, blank line, then detailed description if needed
- Format (example from `rsf/config.py`):
  ```python
  """RSF project configuration -- rsf.toml loader and config resolution.

  Loads provider configuration from rsf.toml files and resolves the
  infrastructure configuration cascade: workflow YAML > rsf.toml > default.
  """
  ```

**Function docstrings:**
- Google-style docstrings (or compatible style)
- Sections: description, Args, Returns, Raises
- Example from `rsf/providers/registry.py`:
  ```python
  def get_provider(name: str) -> InfrastructureProvider:
      """Look up and instantiate a provider by name.

      Args:
          name: Registered provider name.

      Returns:
          An instance of the registered provider class.

      Raises:
          ProviderNotFoundError: If no provider is registered with the given name.
      """
  ```

**Class docstrings:**
- Single line for simple classes: `"""Raised when a provider name is not registered."""`
- Multi-line for complex classes with detailed explanation

**Inline comments:**
- Used sparingly
- Explain *why*, not *what*
- When needed, prefix with # and space: `# Propagation buffer (HARN-07)`

## Error Handling

**Custom exceptions:**
- Inherit from standard `Exception` or specific exception type
- Named in PascalCase ending with `Error`: `JSONPathError`, `ProviderNotFoundError`, `IntrinsicParseError`
- Example: `class ProviderNotFoundError(KeyError):`

**Raising exceptions:**
- Provide meaningful messages with context
- Include available options when relevant: `f"Unknown provider: {name}. Available: {available}"`
- Use specific exception types, not bare `Exception`

**Handling exceptions:**
- Catch specific exceptions, not bare `except:`
- Re-raise with context when wrapping: `except FileNotFoundError: raise ValueError(f"ASL file not found: {path}")`
- Use `ClientError as e` pattern for AWS exceptions with error code extraction: `e.response["Error"]["Code"]`

## Logging

**Framework:** `logging` (standard library)

**Setup pattern:**
- Module level: `logger = logging.getLogger(__name__)`
- Used in: `inspect/`, `providers/`, `editor/websocket.py`

**When to log:**
- Info level: Operational events (execution status, deploy steps)
- Warning level: Degraded conditions (throttling backoff, empty results)
- Exception handling: Include in logging context: `logger.warning("poll_execution: throttled, backing off %.1fs", backoff)`

**Format:**
- Descriptive function context: `logger.info("terraform_deploy: init %s", tf_dir)`
- Include relevant parameters in message: `logger.info("query_logs: got %d results on attempt %d", len(results), attempt)`

## Type Hints

**Usage:**
- Mandatory on all functions and methods
- Mandatory on class attributes (via dataclass/Pydantic fields)
- Use `|` syntax for unions (Python 3.10+): `dict[str, Any] | None`
- Use `from typing import Annotated, Any, Literal, Union` for complex types

**Patterns:**
- Optional fields: `field: str | None = None`
- Generic collections: `list[str]`, `dict[str, Any]`, `frozenset[str]`
- Callable types: `type[InfrastructureProvider]` for class objects
- Return types: Always specified, including `None`

## Validation & Data Classes

**Pydantic models:**
- Version 2.x required (in dependencies)
- Strict config: `model_config = {"extra": "forbid"}` prevents unknown fields
- Field aliases for ASL/external formats: `Field(alias="InputPath", alias="OutputPath")`
- Validators: `@model_validator(mode="after")` for complex validation rules

**Dataclasses:**
- Standard `@dataclass` for simple structures
- Example: `rsf/context/model.py` uses dataclasses with field factories for nested objects

**Pydantic field validation:**
- Use `field_validator` decorator: `validate_start_time = field_validator("start_time", mode="before")(_ts_validator)`
- Complex validation in model validators with `mode="after"`

## Module Design

**Exports:**
- Public API defined implicitly (no `__all__` typically)
- Private internals prefixed with underscore: `_PROVIDERS`, `_Parser`, `_resolve_dotted_path`
- Modules in packages: Import from specific submodules, not package root (use `from rsf.context.model import ContextObject`, not `from rsf.context import ContextObject`)

**Package structure patterns:**
- Models/types: `models.py`, `types.py`
- Core logic: `engine.py`, `generator.py`
- Registries: `registry.py`
- Utilities: `utils.py` or `<domain>.py` (e.g., `jsonpath.py`, `encoding.py`)
- External interfaces: `client.py`, `router.py`, `server.py`

## Async Patterns

**Usage:**
- Used in inspector/client layer: `rsf/inspect/client.py`, `rsf/inspect/router.py`
- Pattern: `async def` methods with `await` for concurrent operations
- Rate limiting with async: `TokenBucketRateLimiter` with `async def acquire()` and `await asyncio.sleep()`
- Thread-to-async bridging: `await asyncio.to_thread(self._client.method, **kwargs)` for sync boto3 calls

## Testing Conventions

**Test organization:**
- Located in `tests/` parallel to `src/rsf/`
- Subdirectory mirroring source: `tests/test_cdk/`, `tests/test_inspect/`, `tests/test_context/`

**Function signatures:**
- Test methods start with `test_`: `test_create_factory`, `test_set_and_get`
- Async tests: `@pytest.mark.asyncio async def test_...():`
- Parametrized tests: `@pytest.mark.parametrize("arg", [value1, value2])`

**Fixtures:**
- Decorated with `@pytest.fixture`
- Scope: `session`, `function` (default), or `module`
- Example: `def minimal_config():` returns test data object

**Assertions:**
- Direct assertions: `assert result == expected`
- Exception testing: `with pytest.raises(ValueError, match="pattern"):`
- No assertion framework beyond pytest's built-in

---

*Convention analysis: 2026-03-11*
