# Architecture Research

**Domain:** Pluggable Infrastructure Provider System for RSF CLI tool
**Researched:** 2026-03-02
**Confidence:** HIGH — based on direct source code analysis of the existing RSF codebase

---

## Standard Architecture

### System Overview: Current State (v2.0)

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Layer                               │
│  ┌────────────┐  ┌──────────────┐  ┌───────────┐  ┌─────────┐  │
│  │ deploy_cmd │  │ generate_cmd │  │  diff_cmd │  │ doctor  │  │
│  │  279 LOC   │  │  --no-infra  │  │  tf_dir   │  │ _check_ │  │
│  └─────┬──────┘  └──────────────┘  └─────┬─────┘  │terraform│  │
│        │                                  │        └─────────┘  │
├────────┼──────────────────────────────────┼─────────────────────┤
│        │         Terraform Layer          │                     │
│  ┌─────▼──────────────────────┐          │                     │
│  │  TerraformConfig dataclass │          │                     │
│  │  generate_terraform()      │          │                     │
│  │  Jinja2 HCL engine         │          │                     │
│  │  11 .j2 templates          │          │                     │
│  └────────────────────────────┘          │                     │
│                                           │                     │
│  deploy_cmd.py extracts infra fields ─────┘                     │
│  from StateMachineDefinition manually                           │
│  (~80 LOC of hasattr/dict-building)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────┐
│                         DSL Layer                             │
│  StateMachineDefinition (Pydantic v2)                         │
│    triggers, dynamodb_tables, alarms,                         │
│    dead_letter_queue, lambda_url, sub_workflows               │
└───────────────────────────────────────────────────────────────┘
```

### System Overview: Target State (v3.0)

```
┌──────────────────────────────────────────────────────────────────┐
│                          CLI Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌─────────┐  │
│  │  deploy_cmd  │  │ generate_cmd │  │ diff_cmd │  │ doctor  │  │
│  │  (slimmed)   │  │  --provider  │  │(provider │  │(provider│  │
│  └──────┬───────┘  └──────────────┘  │ aware)   │  │ checks) │  │
│         │                            └──────────┘  └─────────┘  │
├─────────┼────────────────────────────────────────────────────────┤
│         │         Provider Abstraction Layer (NEW)               │
│  ┌──────▼──────────────────────────────────────────────────┐    │
│  │              InfraProvider Protocol / ABC               │    │
│  │   generate(definition, output_dir, config) -> Result    │    │
│  │   deploy(output_dir, options) -> None                   │    │
│  │   code_only(output_dir, options) -> None                │    │
│  └──────┬──────────────┬───────────────────┬──────────────┘    │
│         │              │                   │                    │
│  ┌──────▼─────┐  ┌─────▼──────┐  ┌────────▼──────────┐        │
│  │ Terraform  │  │  CDK (new) │  │  Custom (new)     │        │
│  │  Provider  │  │  Provider  │  │  Provider         │        │
│  │(refactored)│  │            │  │  (exec arbitrary  │        │
│  └────────────┘  └────────────┘  │   program)        │        │
│                                   └───────────────────┘        │
└──────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────────────┐
│                          DSL Layer                             │
│   StateMachineDefinition — unchanged                           │
│   + optional: infrastructure.provider config field             │
└────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

### Current Components

| Component | Responsibility | Status |
|-----------|----------------|--------|
| `deploy_cmd.py` | Load DSL → extract infra fields → call TerraformConfig → run terraform CLI | Modified |
| `terraform/generator.py` | TerraformConfig dataclass + generate_terraform() → write HCL files | Modified |
| `terraform/engine.py` | Jinja2 environment with custom HCL delimiters | Unchanged |
| `terraform/templates/*.j2` | 11 HCL template files | Unchanged (moved to provider) |
| `dsl/models.py` | StateMachineDefinition with all infra fields | Unchanged |
| `generate_cmd.py` | `--no-infra` flag (currently a no-op aside from a print) | Minor change |
| `doctor_cmd.py` | Hardcoded Terraform check (`_check_terraform()`) | Modified |
| `diff_cmd.py` | Hardcoded `--tf-dir` option | Modified |
| `export_cmd.py` | Duplicates infra extraction logic from deploy_cmd | Unchanged |

### New Components

| Component | Responsibility | Notes |
|-----------|----------------|-------|
| `providers/__init__.py` | Provider registry + `get_provider()` factory | New module |
| `providers/base.py` | `InfraProvider` abstract base class or Protocol | New |
| `providers/terraform.py` | Terraform provider (wraps existing generator + CLI) | New, extracts from deploy_cmd |
| `providers/cdk.py` | CDK provider (ships CDK template, invokes cdk CLI) | New |
| `providers/custom.py` | Custom provider (exec user-specified program) | New |
| `providers/metadata.py` | Workflow metadata serializer (JSON file, env vars, CLI args) | New |

---

## What Changes vs. What Stays

### Unchanged

- `src/rsf/dsl/` — All DSL models, parser, validator. The `StateMachineDefinition` with its infra fields is the input contract to providers. Zero changes needed.
- `src/rsf/codegen/` — Orchestrator + handler code generation is completely independent of infrastructure. Unchanged.
- `src/rsf/terraform/engine.py` — The Jinja2 HCL engine stays. The TerraformProvider will use it.
- `src/rsf/terraform/templates/` — The 11 .j2 templates stay. Owned by TerraformProvider.
- `src/rsf/testing/`, `src/rsf/io/`, `src/rsf/functions/` — Not infrastructure related.
- `src/rsf/inspect/`, `src/rsf/editor/` — Not infrastructure related.
- `src/rsf/cli/export_cmd.py` — CloudFormation export is a distinct code path; not part of provider system.

### Modified

**`src/rsf/cli/deploy_cmd.py`** — The primary change site. The ~80 LOC block that manually extracts infra fields from `StateMachineDefinition` and builds a `TerraformConfig` dict is replaced by:

```python
provider = get_provider(definition, project_config)
provider.generate(definition, output_dir=tf_dir, stage=stage)
provider.deploy(output_dir=tf_dir, auto_approve=auto_approve, stage=stage)
```

The `--tf-dir` option becomes `--infra-dir` (or stays as `--tf-dir` for backward compat with a deprecation warning). The `--code-only` path becomes `provider.code_only(...)`.

**`src/rsf/cli/doctor_cmd.py`** — `_check_terraform()` becomes `_check_provider_binary(provider_name)` that dispatches based on the configured provider. Terraform remains the default.

**`src/rsf/cli/diff_cmd.py`** — The `--tf-dir` flag can stay; diff is about workflow definitions, not provider output. Low impact.

**`src/rsf/cli/generate_cmd.py`** — Adds `--provider` option that wires into `provider.generate()`. Currently `--no-infra` is a print-only no-op here; stays as is.

**`src/rsf/terraform/generator.py`** — `TerraformConfig` and `generate_terraform()` move into the TerraformProvider class or are wrapped by it. The public API of `generator.py` may be preserved for backward compatibility.

### New

**`src/rsf/providers/`** — New package. Build order:

```
providers/base.py       ← define the protocol/ABC first
providers/metadata.py   ← workflow metadata serialization (shared utility)
providers/terraform.py  ← wraps existing generator.py + CLI invocation
providers/cdk.py        ← CDK template + cdk CLI invocation
providers/custom.py     ← arbitrary program execution
providers/__init__.py   ← registry + get_provider() factory
```

---

## Architectural Patterns

### Pattern 1: Protocol-Based Provider Interface

**What:** Define `InfraProvider` as a Python `Protocol` (structural subtyping) rather than an ABC. Providers are duck-typed — any object with the right methods satisfies the interface.

**When to use:** When the provider implementations live in different files and you want to avoid mandatory inheritance. Protocol is more Pythonic and allows external providers without depending on RSF internals.

**Trade-offs:** Protocol gives flexibility and no inheritance coupling. ABC (`abstractmethod`) gives clearer errors at class definition time (fails at instantiation if a method is missing). Given RSF is a closed tool with 3 known providers, either works — Protocol is the leaner choice.

**Example:**

```python
# src/rsf/providers/base.py
from typing import Protocol, runtime_checkable
from pathlib import Path
from dataclasses import dataclass

@dataclass
class ProviderResult:
    """Result returned from provider.generate()."""
    generated_files: list[Path]
    skipped_files: list[Path]
    output_dir: Path

@runtime_checkable
class InfraProvider(Protocol):
    """Contract all infrastructure providers must satisfy."""

    def generate(
        self,
        definition: "StateMachineDefinition",
        output_dir: Path,
        stage: str | None = None,
    ) -> ProviderResult:
        """Generate infrastructure artifacts (HCL, CDK app, config file, etc.)."""
        ...

    def deploy(
        self,
        output_dir: Path,
        auto_approve: bool = False,
        stage: str | None = None,
        stage_var_file: Path | None = None,
    ) -> None:
        """Invoke the provider's deployment tool."""
        ...

    def code_only(
        self,
        output_dir: Path,
        stage: str | None = None,
        stage_var_file: Path | None = None,
    ) -> None:
        """Update Lambda code without full infrastructure re-deploy."""
        ...

    def check_binary(self) -> tuple[bool, str]:
        """Return (available, version_or_error) for doctor checks."""
        ...
```

### Pattern 2: Provider Configuration via Project Config File

**What:** Provider selection lives in a project-level config file (`rsf.toml` or `rsf.yaml`), not in the workflow YAML. The workflow YAML stays provider-agnostic and describes what infrastructure is needed (triggers, tables, alarms), not how to provision it.

**When to use:** Always. Conflating provisioning tool choice with workflow definition creates coupling — a team switching from Terraform to CDK would need to edit every workflow file.

**Trade-offs:** Requires a separate config file lookup on CLI invocation. The tradeoff is clean separation of concerns: workflow YAML = "what", project config = "how and with what tool".

**Example:**

```toml
# rsf.toml (project root)
[infrastructure]
provider = "terraform"        # terraform | cdk | custom
output_dir = "terraform"      # default infra output directory

[infrastructure.terraform]
# Terraform-specific options (passed through to existing TerraformConfig)
aws_region = "us-east-1"
name_prefix = "rsf"

[infrastructure.cdk]
app_dir = "cdk"

[infrastructure.custom]
program = "./scripts/deploy-infra.sh"
args = ["--workflow", "{workflow_path}", "--stage", "{stage}"]
metadata_format = "json_file"  # json_file | env_vars | cli_args
metadata_file = ".rsf-metadata.json"
```

Alternatively, the workflow YAML can carry an optional top-level `infrastructure` key:

```yaml
# workflow.yaml (optional override)
infrastructure:
  provider: terraform
```

Both approaches are valid. The project config file is preferred for multi-workflow projects. The workflow YAML field is an escape hatch for per-workflow overrides.

### Pattern 3: Metadata Passing to External Programs

**What:** When a custom provider is invoked, RSF serializes workflow metadata (workflow name, stage, infra fields, output dir) in the format the external program expects: a JSON file, environment variables, or extra CLI args.

**When to use:** Custom provider only. Terraform and CDK providers handle this internally via their own config formats.

**Trade-offs:** Adds a serialization step before exec. The payoff is that arbitrary programs (shell scripts, Pulumi, Ansible, custom Python) can integrate without knowing RSF internals.

**Example:**

```python
# src/rsf/providers/metadata.py
import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict

@dataclass
class WorkflowMetadata:
    workflow_name: str
    workflow_path: str
    output_dir: str
    stage: str | None
    triggers: list[dict]
    dynamodb_tables: list[dict]
    alarms: list[dict]
    dlq_enabled: bool
    lambda_url_enabled: bool

def write_json_file(metadata: WorkflowMetadata, path: Path) -> None:
    path.write_text(json.dumps(asdict(metadata), indent=2))

def to_env_vars(metadata: WorkflowMetadata) -> dict[str, str]:
    return {
        "RSF_WORKFLOW_NAME": metadata.workflow_name,
        "RSF_WORKFLOW_PATH": metadata.workflow_path,
        "RSF_OUTPUT_DIR": metadata.output_dir,
        "RSF_STAGE": metadata.stage or "",
        "RSF_METADATA_JSON": json.dumps(asdict(metadata)),
    }
```

### Pattern 4: Infra Extraction as Shared Utility

**What:** The `~80 LOC` block in `deploy_cmd.py` that extracts `StateMachineDefinition` fields into dicts (triggers, DynamoDB, alarms, DLQ, lambda_url) is currently duplicated in `export_cmd.py` (`_extract_infrastructure_from_definition()`). This extraction logic should move to a single shared utility used by all providers.

**When to use:** All providers need the same normalized dict representation of the DSL's infrastructure fields. Centralizing avoids the existing duplication.

**Do this:**

```python
# src/rsf/providers/metadata.py (or providers/extractor.py)

def extract_infra_config(definition: StateMachineDefinition) -> InfraConfig:
    """Single source of truth for extracting infra fields from DSL definition."""
    # ... consolidate the logic currently in deploy_cmd._deploy_full()
    # ... and export_cmd._extract_infrastructure_from_definition()
```

This eliminates the drift between deploy and export paths.

---

## Data Flow

### Deploy Flow — Current (v2.0)

```
rsf deploy workflow.yaml
    │
    ▼
load_definition(workflow.yaml) → StateMachineDefinition
    │
    ▼
codegen_generate(definition) → orchestrator.py + handlers/
    │
    ▼
[Manual extraction loop in deploy_cmd.py ~80 LOC]
    │
    ├─ triggers → list[dict]
    ├─ dynamodb_tables → list[dict]
    ├─ alarms → list[dict]
    ├─ dlq → dlq_enabled, dlq_max_receive_count, dlq_queue_name
    └─ lambda_url → lambda_url_enabled, lambda_url_auth_type
    │
    ▼
TerraformConfig(workflow_name, ...) → generate_terraform() → HCL files
    │
    ▼
subprocess.run(["terraform", "init"]) → subprocess.run(["terraform", "apply"])
```

### Deploy Flow — Target (v3.0)

```
rsf deploy workflow.yaml [--provider terraform|cdk|custom]
    │
    ▼
load_definition(workflow.yaml) → StateMachineDefinition
    │
    ▼
load_project_config("rsf.toml") → provider_name, provider_options
    │
    ▼
get_provider(provider_name, provider_options) → InfraProvider instance
    │
    ▼
codegen_generate(definition) → orchestrator.py + handlers/
    │
    ▼
provider.generate(definition, output_dir, stage) → ProviderResult
    │  [internal: extract_infra_config(definition) → normalized InfraConfig]
    │  [TerraformProvider: InfraConfig → TerraformConfig → generate_terraform()]
    │  [CDKProvider: InfraConfig → CDK app synthesis]
    │  [CustomProvider: InfraConfig → JSON/env/args → exec program]
    │
    ▼
provider.deploy(output_dir, auto_approve, stage) → None
    │  [TerraformProvider: subprocess terraform init + apply]
    │  [CDKProvider: subprocess cdk deploy]
    │  [CustomProvider: subprocess user_program with metadata]
```

### Provider Selection Flow

```
CLI flag --provider (highest priority)
    │
    ▼ (if not set)
workflow.yaml infrastructure.provider field
    │
    ▼ (if not set)
rsf.toml [infrastructure] provider
    │
    ▼ (if not set)
Default: "terraform"
```

### Metadata Passing Flow (Custom Provider)

```
StateMachineDefinition
    │
    ▼
extract_infra_config() → InfraConfig
    │
    ▼
WorkflowMetadata(workflow_name, output_dir, stage, infra_config)
    │
    ├─ metadata_format = "json_file"  → write .rsf-metadata.json
    ├─ metadata_format = "env_vars"   → os.environ update before exec
    └─ metadata_format = "cli_args"   → append --rsf-metadata=... to args
    │
    ▼
subprocess.run([user_program, ...args])
```

---

## Recommended Project Structure

```
src/rsf/
├── providers/                    # NEW — provider abstraction layer
│   ├── __init__.py               # get_provider() factory + registry
│   ├── base.py                   # InfraProvider Protocol + ProviderResult
│   ├── metadata.py               # extract_infra_config() + WorkflowMetadata
│   ├── config.py                 # load_project_config() → rsf.toml parsing
│   ├── terraform.py              # TerraformProvider (wraps existing generator)
│   ├── cdk.py                    # CDKProvider (new)
│   └── custom.py                 # CustomProvider (new)
│
├── terraform/                    # KEPT — owned by TerraformProvider
│   ├── engine.py                 # unchanged
│   ├── generator.py              # unchanged (called by TerraformProvider)
│   └── templates/                # unchanged (11 .j2 files)
│
├── cli/
│   ├── deploy_cmd.py             # MODIFIED — slimmed, delegates to provider
│   ├── generate_cmd.py           # MINOR — --provider flag wiring
│   ├── doctor_cmd.py             # MODIFIED — provider-aware binary check
│   ├── diff_cmd.py               # MINOR — --infra-dir replaces --tf-dir
│   └── [all others unchanged]
│
├── dsl/                          # UNCHANGED
├── codegen/                      # UNCHANGED
└── [all other packages]          # UNCHANGED
```

### Structure Rationale

- **`providers/` as a peer to `terraform/`:** The Terraform implementation is just one provider. The `terraform/` package stays because it contains the HCL engine and templates; the new `providers/terraform.py` wraps it.
- **`providers/metadata.py` for extraction:** Consolidates the infra extraction logic currently duplicated between `deploy_cmd.py` and `export_cmd.py`.
- **`providers/config.py` for project config:** Isolates `rsf.toml` parsing. Keeps deploy_cmd from growing more config-reading logic.
- **`terraform/` package unchanged:** No need to move or rename the existing HCL generation infrastructure.

---

## Integration Points

### deploy_cmd.py — Primary Integration Point

`deploy_cmd.py` is the heart of the change. The `_deploy_full()` function's infra extraction block (~lines 114-195) becomes:

```python
from rsf.providers import get_provider

provider = get_provider(definition, project_config)

with Status("[bold]Generating infrastructure...[/bold]", console=console):
    infra_result = provider.generate(definition, output_dir=infra_dir, stage=stage)

console.print(
    f"[green]Infrastructure generated:[/green] {len(infra_result.generated_files)} file(s)"
)

provider.deploy(infra_dir, auto_approve=auto_approve, stage=stage, stage_var_file=stage_var_file)
```

The `_deploy_code_only()` function similarly becomes `provider.code_only(...)`.

### doctor_cmd.py — Provider Binary Check

Currently hardcoded:

```python
results.append(_check_terraform())
```

Target:

```python
provider_name = load_project_config().infrastructure.provider  # default: "terraform"
provider = get_provider_instance(provider_name)
results.append(_check_provider_binary(provider))
```

The `_check_terraform()` function becomes `TerraformProvider.check_binary()` — returning `(available: bool, version: str)`. Each provider implements `check_binary()`.

### generate_cmd.py — Optional Provider Hook

`generate_cmd.py` currently prints a message when `--no-infra` is set and generates nothing. With providers, it can optionally call `provider.generate()` (without `provider.deploy()`):

```python
if not no_infra:
    provider = get_provider(definition, project_config)
    provider.generate(definition, output_dir=infra_dir, stage=stage)
```

The `--no-infra` flag remains as the way to skip this step.

### export_cmd.py — Infra Extraction Unification

`export_cmd._extract_infrastructure_from_definition()` and the extraction block in `deploy_cmd._deploy_full()` both do the same work. After this milestone, both call `providers.metadata.extract_infra_config(definition)` instead. The export command itself is unchanged in behavior.

### DSL (dsl/models.py) — Optional Provider Field

`StateMachineDefinition` can gain an optional `infrastructure` field for per-workflow provider overrides:

```python
class InfrastructureConfig(BaseModel):
    model_config = {"extra": "forbid"}
    provider: Literal["terraform", "cdk", "custom"] | None = None

class StateMachineDefinition(BaseModel):
    # ... existing fields ...
    infrastructure: InfrastructureConfig | None = Field(default=None, alias="infrastructure")
```

This is optional — if absent, the project config or CLI flag governs.

---

## Build Order (Phase Dependencies)

The dependency graph is straightforward — the protocol must exist before any provider implements it:

```
1. providers/base.py
   └── InfraProvider Protocol + ProviderResult + ProviderOptions
       (no dependencies on other RSF modules)

2. providers/metadata.py
   └── extract_infra_config() + WorkflowMetadata
       (depends on: dsl/models.py — already exists)

3. providers/config.py
   └── load_project_config() + ProjectConfig
       (depends on: nothing RSF-specific, just TOML parsing)

4. providers/terraform.py
   └── TerraformProvider implementing InfraProvider
       (depends on: base.py, metadata.py, terraform/generator.py — all exist)

5. providers/cdk.py
   └── CDKProvider implementing InfraProvider
       (depends on: base.py, metadata.py)

6. providers/custom.py
   └── CustomProvider implementing InfraProvider
       (depends on: base.py, metadata.py)

7. providers/__init__.py
   └── get_provider() factory + registration
       (depends on: terraform.py, cdk.py, custom.py)

8. deploy_cmd.py refactor
   └── replace extraction block with provider.generate() + provider.deploy()
       (depends on: providers/__init__.py)

9. generate_cmd.py, doctor_cmd.py, diff_cmd.py updates
   └── provider-aware options
       (depends on: providers/__init__.py, providers/config.py)

10. dsl/models.py — optional InfrastructureConfig field
    └── (depends on: nothing new, but must happen before deploy_cmd tests)

11. Tests for all providers
    └── mock provider, terraform provider, custom provider test
        (depends on: all above)
```

---

## Anti-Patterns

### Anti-Pattern 1: Provider Config in the Workflow YAML as the Primary Location

**What people do:** Put `provider: terraform` at the top of `workflow.yaml`.

**Why it's wrong:** A team of 5 engineers has 20 workflow files. They decide to switch from Terraform to CDK. They must edit all 20 workflow files. The workflow YAML describes the business process; the provisioning tool is an operational concern.

**Do this instead:** Provider selection in `rsf.toml` (project-level) with optional per-workflow override in workflow.yaml.

### Anti-Pattern 2: Making deploy_cmd.py Grow to Handle Provider Logic

**What people do:** Add `if provider == "cdk":` branches directly in `deploy_cmd.py`.

**Why it's wrong:** `deploy_cmd.py` is already 279 LOC with the single Terraform path. Adding CDK and custom provider paths inline will make it unreadable and untestable.

**Do this instead:** deploy_cmd.py calls `provider.generate()` and `provider.deploy()`. The provider object encapsulates all tool-specific logic.

### Anti-Pattern 3: Duplicating the Infra Extraction Logic Again

**What people do:** Each new provider (CDK, custom) re-implements the logic that reads `definition.triggers`, `definition.dynamodb_tables`, etc.

**Why it's wrong:** This logic is already duplicated between `deploy_cmd.py` and `export_cmd.py`. Adding a third and fourth copy creates three places to update when a new DSL field is added.

**Do this instead:** `providers/metadata.py` owns a single `extract_infra_config()` function. All providers call it. `export_cmd.py` switches to it too.

### Anti-Pattern 4: Hard-Coding the Terraform Binary Check in doctor_cmd

**What people do:** Leave `_check_terraform()` as-is and add separate `_check_cdk()`, `_check_custom()` as new if-branches.

**Why it's wrong:** The doctor command would always check all tools, even ones not used by this project.

**Do this instead:** Doctor reads project config, calls `provider.check_binary()` for the configured provider only. Falls back to Terraform check when no config is present.

### Anti-Pattern 5: Blocking on Missing CDK App Before Terraform Provider Works

**What people do:** Try to implement CDK provider and Terraform provider in the same phase.

**Why it's wrong:** The CDK provider requires writing a CDK app template, testing CDK CLI integration, and understanding the CDK synthesis/deployment lifecycle — all of which are independent of the abstraction layer. Blocking Terraform working-behind-a-provider on CDK completion delays value.

**Do this instead:** Phase 1 = base + metadata + terraform provider (existing Terraform behavior now behind the interface). Phase 2 = CDK provider. Phase 3 = custom provider. Each phase is independently shippable.

---

## Scaling Considerations

This is a local CLI tool, not a server. "Scale" here means code complexity as the number of providers grows.

| Number of Providers | Architecture Adjustments |
|---------------------|--------------------------|
| 2-3 (Terraform, CDK, Custom) | Simple factory function with if-elif or dict dispatch is sufficient |
| 4-6 (adding Pulumi, CloudFormation native, etc.) | Plugin-style registration: dict of `{name: ProviderClass}` initialized at module load |
| 7+ | Entry point-based plugin system (`importlib.metadata` entry_points); external packages can register providers |

For v3.0 with 3 providers, a dict dispatch factory is the right level of complexity:

```python
# providers/__init__.py
_PROVIDERS: dict[str, type[InfraProvider]] = {
    "terraform": TerraformProvider,
    "cdk": CDKProvider,
    "custom": CustomProvider,
}

def get_provider(name: str, options: dict) -> InfraProvider:
    if name not in _PROVIDERS:
        raise ValueError(f"Unknown provider: {name!r}. Available: {list(_PROVIDERS)}")
    return _PROVIDERS[name](options)
```

Entry-point-based plugins are out of scope for v3.0 but the dict-dispatch pattern makes migration to entry points trivial later.

---

## Sources

- Direct source code analysis: `src/rsf/cli/deploy_cmd.py` (279 LOC)
- Direct source code analysis: `src/rsf/terraform/generator.py` (217 LOC)
- Direct source code analysis: `src/rsf/terraform/engine.py`
- Direct source code analysis: `src/rsf/dsl/models.py` (404 LOC)
- Direct source code analysis: `src/rsf/cli/export_cmd.py` — reveals duplication of infra extraction
- Direct source code analysis: `src/rsf/cli/doctor_cmd.py` — reveals hardcoded terraform check
- Direct source code analysis: `src/rsf/cli/diff_cmd.py` — reveals tf_dir coupling
- `.planning/PROJECT.md` — v3.0 milestone requirements
- Python `typing.Protocol` — standard library, Python 3.8+, no external dependency
- Python `tomllib` — standard library, Python 3.11+; `tomli` backport for 3.10

---

*Architecture research for: RSF v3.0 Pluggable Infrastructure Providers*
*Researched: 2026-03-02*
