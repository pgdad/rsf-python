# Stack Research

**Domain:** Pluggable infrastructure providers for Python CLI tool
**Researched:** 2026-03-02
**Confidence:** HIGH

---

## Context: What Already Exists (Do Not Change)

The existing validated stack for v2.0:

| Technology | Version | Role |
|------------|---------|------|
| Python | 3.13+ | Runtime (SDK requirement) |
| Pydantic v2 | >=2.0 | DSL models, validation |
| Typer | >=0.9 | CLI framework |
| Jinja2 | >=3.1 | HCL template rendering |
| PyYAML | >=6.0 | Workflow file parsing |
| Rich | >=13.0 | Console output |
| subprocess (stdlib) | stdlib | Terraform CLI invocation |
| shutil (stdlib) | stdlib | Binary detection (`shutil.which`) |
| dataclasses (stdlib) | stdlib | TerraformConfig, TerraformResult |

The `deploy_cmd.py` uses `subprocess.run()` with list-style args (no `shell=True`), `shutil.which()` for binary detection, and `dataclasses.dataclass` for configuration objects. These patterns must be extended — not replaced.

---

## New Stack Requirements

Three new capabilities are needed:

1. **Provider abstraction** — A typed interface so Terraform, CDK, and custom providers are interchangeable
2. **AWS CDK provider** — Ships a CDK app template, invokes the `cdk` CLI via subprocess
3. **Metadata passing** — Workflow data sent to external programs as JSON file, env vars, or CLI args

---

## Recommended Stack — New Additions

### Core: Provider Abstraction

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `abc` (stdlib) | stdlib | `InfrastructureProvider` abstract base class | Nominal subtyping: providers must explicitly implement the interface. Cleaner than Protocol for this case because providers are internal code we control, not third-party duck-typed objects. Forces `deploy()` and `teardown()` to be implemented. No external dependencies. |
| `dataclasses` (stdlib) | stdlib | `ProviderConfig` and `ProviderResult` data types | Already used for `TerraformConfig`/`TerraformResult`. Consistent pattern. Zero dependencies. `dataclasses.asdict()` gives free JSON serialisation for metadata passing. |
| `json` (stdlib) | stdlib | Workflow metadata serialisation | `json.dumps()` produces the JSON file or env var payload that external programs consume. Already available. |
| `os` (stdlib) | stdlib | Environment variable construction for subprocess | `{**os.environ, "RSF_METADATA": json_str}` — merge pattern for subprocess `env` argument. |

**Why ABC over Protocol here:** The provider interface is defined and consumed by RSF itself. ABCs enforce implementation at instantiation time (raises `TypeError` on missing methods), not just at type-check time. This gives runtime safety when users register custom providers via config. Protocol requires `@runtime_checkable` and `isinstance()` checks are shallow (no signature validation). ABC is the right tool when you own both the interface and the implementations.

**Why not pluggy:** Pluggy is designed for hook-based plugin systems where many plugins may all respond to the same hook (pytest-style). RSF needs a single selected provider per deploy invocation — a "driver" pattern, not a "broadcast" pattern. Pluggy adds indirection without benefit here. One ABC with a factory function is sufficient.

### AWS CDK Provider

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `aws-cdk-lib` | >=2.241.0 | CDK constructs for Lambda, IAM, DynamoDB in the shipped CDK app template | CDK v2 consolidated all constructs into one package. 2.241.0 is current (released 2026-03-02). Required only in the generated CDK app's `requirements.txt`, NOT in RSF's own `pyproject.toml`. |
| `constructs` | >=10.0.0 | Base class for all CDK constructs | Required companion to `aws-cdk-lib`. Same scoping: goes into the generated CDK app's dependencies, not RSF itself. |
| `aws-cdk` CLI | installed globally via npm | `cdk synth`, `cdk deploy`, `cdk bootstrap` invocation | The CDK CLI is a Node.js tool installed separately (`npm install --global aws-cdk`). RSF invokes it via `subprocess.run(["cdk", "deploy", ...])` with `shutil.which("cdk")` pre-check. RSF does not depend on it at install time — it is a user prerequisite like `terraform`. |

**Critical CDK bootstrap requirement:** CDK requires a one-time `cdk bootstrap` per AWS account/region before any `cdk deploy` can succeed. This creates the `CDKToolkit` CloudFormation stack (S3 bucket for assets, ECR repo, IAM roles). The CDK provider's `deploy()` must either run `cdk bootstrap` automatically or document it as a prerequisite. Recommendation: detect whether bootstrap has been run (check for `CDKToolkit` stack), warn if missing, and offer `--bootstrap` flag.

**CDK app template approach:** RSF generates a complete CDK Python app directory (with `app.py`, `cdk.json`, `requirements.txt`) via Jinja2, then invokes `cdk deploy`. This is the same template-then-invoke pattern as the Terraform provider. The CDK app receives workflow metadata via CDK context values (`--context key=value`) or via a JSON file written to the app directory before synthesis.

### Metadata Passing

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `json` (stdlib) | stdlib | Serialize workflow metadata dict to JSON string/file | `json.dumps(metadata, indent=2)` for file, `json.dumps(metadata)` for compact env var value. Already in stdlib, no dependency. |
| `tempfile` (stdlib) | stdlib | Write ephemeral metadata JSON file to temp location | `tempfile.NamedTemporaryFile` or `Path(tempdir) / "rsf-metadata.json"` — ephemeral file that custom programs read. Avoids polluting the workflow directory. |
| `os.environ` (stdlib) | stdlib | Construct merged env dict for subprocess | `{**os.environ, "RSF_WORKFLOW_NAME": name, "RSF_METADATA_FILE": path}` — standard subprocess env merging pattern. |

**Three metadata transport modes (all needed):**

1. **JSON file** (`--metadata-file`): RSF writes `rsf-metadata.json` with full workflow dict, passes path via `RSF_METADATA_FILE` env var. Best for rich data (nested DynamoDB tables, alarm configs).
2. **Environment variables** (`--metadata-env`): RSF sets `RSF_WORKFLOW_NAME`, `RSF_STAGE`, `RSF_METADATA` (full JSON as single env var). Best for simple values and shell scripts.
3. **CLI args** (`--metadata-args`): RSF passes `--rsf-workflow-name NAME --rsf-stage STAGE` as extra CLI arguments. Best for programs that only accept CLI flags.

All three are implemented with stdlib only. No new dependencies.

---

## Supporting Libraries — No New Additions Needed

| Considered | Decision | Reason |
|------------|----------|--------|
| `pluggy` >=1.6.0 | **DO NOT ADD** | Hook-broadcast model is wrong for single-provider-per-deploy. ABC is simpler and correct. |
| `stevedore` | **DO NOT ADD** | Entry-point-based plugin discovery for third-party packages. RSF providers are first-party code configured by name string, not pip-installed packages. |
| `aws-cdk-lib` in RSF deps | **DO NOT ADD to RSF** | CDK constructs belong in the generated CDK app's `requirements.txt`, not in RSF's own `pyproject.toml`. Installing CDK in RSF would pull in ~200MB of dependencies for all users, including those who never use CDK. |
| `dataclasses-json` | **DO NOT ADD** | `dataclasses.asdict()` + `json.dumps()` is sufficient. No marshmallow overhead needed. |
| `orjson` | **DO NOT ADD** | Serialisation speed is not a bottleneck for metadata objects. |
| `invoke` / `fabric` | **DO NOT ADD** | subprocess.run() with list args is adequate. Adding `invoke` adds indirection with no benefit for 3-5 CLI invocations. |

---

## Installation

No new RSF runtime dependencies are required. All new capabilities use stdlib modules (`abc`, `json`, `os`, `tempfile`, `dataclasses`, `subprocess`, `shutil`).

The CDK app template ships its own `requirements.txt`:

```bash
# Inside generated CDK app directory (not RSF itself)
pip install aws-cdk-lib>=2.241.0 constructs>=10.0.0
```

Users who want the CDK provider also need the CDK CLI (Node.js prerequisite, identical to how Terraform users need the `terraform` binary):

```bash
npm install --global aws-cdk
cdk --version  # verify: 2.x
```

The `rsf doctor` command should check for both `cdk` and `terraform` binaries and report their presence.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `abc.ABC` for provider interface | `typing.Protocol` | Use Protocol when accepting third-party objects you don't control. For RSF's internal providers (Terraform, CDK), ABC's runtime TypeError on missing methods is the better safety guarantee. |
| Subprocess invocation of `cdk` CLI | `aws-cdk-lib` Python constructs directly in RSF | Never: importing CDK constructs in RSF means CDK is always installed. The CLI invocation keeps CDK optional and user-installed, matching the Terraform provider model exactly. |
| JSON file for rich metadata | Only env vars | Use JSON file when metadata contains nested structures (DynamoDB configs, alarm configs). Env vars work for scalar values only. Support both modes. |
| Jinja2 for CDK app template | Cookiecutter / copier | Jinja2 is already in the stack for HCL generation. Same rendering engine, same custom delimiter skill set. No new templating dependency. |
| `tempfile.mkdtemp()` for metadata JSON | Write to `./rsf-metadata.json` | Use temp dir when metadata is ephemeral and shouldn't appear in VCS. Write to workflow dir only if user requests a persistent artifact. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pluggy` | Hook-broadcast semantics don't match single-provider-per-invocation model. Adds plugin manager indirection and hook specification boilerplate for no benefit. | `abc.ABC` with a `get_provider(name)` factory function |
| `aws-cdk-lib` in RSF `pyproject.toml` | Adds ~200MB of transitive dependencies (jsii, typing-extensions pins, etc.) for all RSF users, including those who only use Terraform | Generate CDK app with its own `requirements.txt`; invoke via subprocess |
| `shell=True` in subprocess | Shell injection risk; also breaks on Windows. The existing codebase correctly uses list args. | `subprocess.run(["cdk", "deploy", "--context", f"key={val}"], ...)` |
| Hardcoded provider selection in `deploy_cmd.py` | The current Terraform-only code is the anti-pattern being replaced | `ProviderRegistry.get(config.provider)` dispatching to the ABC implementation |
| Modifying `TerraformConfig` | It is the Terraform provider's private config. The new `ProviderConfig` base dataclass should be separate. | New `ProviderConfig` dataclass with `provider: str` field; `TerraformConfig` inherits from it or sits alongside it |

---

## Stack Patterns by Variant

**If provider is Terraform (default, existing behaviour):**
- Use existing `TerraformConfig` / `generate_terraform()` / `subprocess.run(["terraform", ...])`
- No change to existing code path
- `TerraformProvider(InfrastructureProvider)` wraps the existing logic

**If provider is CDK:**
- Generate CDK app directory via Jinja2 templates (same pattern as HCL generation)
- Write `rsf-metadata.json` to the CDK app dir (CDK app reads it in `app.py`)
- Check `shutil.which("cdk")` — fail with install instructions if missing
- Run `cdk bootstrap` check / warn
- `subprocess.run(["cdk", "deploy", "--require-approval=never", "--context", f"stage={stage}"])`
- CDK app's own `requirements.txt` lists `aws-cdk-lib>=2.241.0`

**If provider is custom (user-specified program):**
- Config provides: `program: "/path/to/my-provisioner"` and `metadata_transport: file|env|args`
- RSF serialises workflow metadata via chosen transport
- `subprocess.run([program, ...extra_args], env={**os.environ, ...metadata_env})`
- Provider invokes program, captures exit code, propagates failure

**If metadata transport is `file`:**
- `json.dumps(metadata_dict, indent=2)` → write to temp file
- Pass `RSF_METADATA_FILE=/tmp/rsf-abc123/metadata.json` as env var
- Clean up after subprocess exits

**If metadata transport is `env`:**
- Flatten scalar fields to `RSF_WORKFLOW_NAME`, `RSF_STAGE`, `RSF_AWS_REGION`
- Full JSON blob in `RSF_METADATA` (compact, no indent)
- Nested structures available only via `RSF_METADATA`

**If metadata transport is `args`:**
- Append `["--rsf-workflow-name", name, "--rsf-stage", stage]` to subprocess command list
- Only scalar values; nested structures require `file` or `env` transport

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `aws-cdk-lib>=2.241.0` | `constructs>=10.0.0,<11.0.0` | CDK v2 requires constructs ^10. Never use CDK v1 (`aws-cdk.core`) — deprecated and unmaintained. |
| `aws-cdk-lib>=2.241.0` | Python `~=3.9` | CDK supports Python 3.9+. RSF requires 3.13+, which is a superset — no conflict. |
| `cdk` CLI (Node.js) | `aws-cdk-lib` same major version | CLI major version must match library major version. Both v2. |
| `abc.ABC` | Python 3.3+ | stdlib, always available in Python 3.13+ |
| `dataclasses` | Python 3.7+ | stdlib, always available |

---

## Provider Interface Design (Concrete Recommendation)

```python
# src/rsf/providers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProviderContext:
    """Workflow metadata passed to every provider."""
    workflow_name: str
    workflow_path: Path
    stage: str | None
    aws_region: str
    metadata: dict  # full workflow definition as dict


@dataclass
class ProviderResult:
    """Result returned by every provider."""
    success: bool
    message: str
    outputs: dict  # provider-specific key-value outputs


class InfrastructureProvider(ABC):
    """Abstract base for all infrastructure providers."""

    @abstractmethod
    def deploy(self, context: ProviderContext) -> ProviderResult:
        """Provision or update infrastructure for a workflow."""
        ...

    @abstractmethod
    def teardown(self, context: ProviderContext) -> ProviderResult:
        """Destroy infrastructure for a workflow."""
        ...

    @abstractmethod
    def check_prerequisites(self) -> list[str]:
        """Return list of error strings if prerequisites are missing."""
        ...
```

This interface requires no external dependencies. The `check_prerequisites()` method uses `shutil.which()` internally. `ProviderContext.metadata` is serialised by the provider using `json.dumps()` when needed.

---

## Sources

- [aws-cdk-lib on PyPI](https://pypi.org/project/aws-cdk-lib/) — version 2.241.0 current as of 2026-03-02 (HIGH confidence)
- [AWS CDK CLI reference](https://docs.aws.amazon.com/cdk/v2/guide/cli.html) — cdk deploy flags, --context, --require-approval (HIGH confidence)
- [AWS CDK bootstrapping](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping-env.html) — bootstrap required before first deploy (HIGH confidence)
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html) — env merging pattern, list-style args (HIGH confidence)
- [Python abc module documentation](https://docs.python.org/3/library/abc.html) — ABC vs Protocol tradeoffs (HIGH confidence)
- [Python typing Protocol spec](https://typing.python.org/en/latest/spec/protocol.html) — structural subtyping limitations (HIGH confidence)
- [pluggy on PyPI](https://pypi.org/project/pluggy/) — version 1.6.0, hook-broadcast semantics (MEDIUM confidence — version via local pip show)
- [WebSearch: ABC vs Protocol 2025-2026](https://jellis18.github.io/post/2022-01-11-abc-vs-protocol/) — recommendation for internal plugin systems (MEDIUM confidence)
- [WebSearch: Python plugin architecture patterns 2026](https://oneuptime.com/blog/post/2026-01-30-python-plugin-systems/view) — driver vs dispatcher vs iterator patterns (MEDIUM confidence)

---

*Stack research for: Pluggable infrastructure providers (RSF v3.0)*
*Researched: 2026-03-02*
