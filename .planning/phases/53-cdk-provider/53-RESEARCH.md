# Phase 53: CDK Provider - Research

**Researched:** 2026-03-02
**Domain:** AWS CDK Python provider for RSF infrastructure deployment
**Confidence:** HIGH

## Summary

Phase 53 implements a CDKProvider class that plugs into RSF's existing InfrastructureProvider ABC (from Phase 51/52). The provider generates a Python CDK app from Jinja2 templates, invokes `cdk deploy` via `npx aws-cdk@latest` as a subprocess with real-time output streaming, and integrates with `rsf doctor` for prerequisite checks. The CDK bootstrap detection uses boto3's CloudFormation API to check for the `CDKToolkit` stack before deployment.

The existing TerraformProvider serves as a reference implementation. CDKProvider follows the same lifecycle (validate_config -> check_prerequisites -> generate -> deploy) and reuses the same ProviderContext, WorkflowMetadata, and registration patterns. The main new concerns are: (1) Jinja2 templates that produce Python CDK code instead of HCL, (2) streaming subprocess output instead of capturing it, and (3) prerequisite checks for Node.js/npx availability plus CDK bootstrap status.

**Primary recommendation:** Mirror TerraformProvider's structure exactly, adding CDK-specific Jinja2 templates under `src/rsf/cdk/templates/`, a streaming subprocess helper, and bootstrap detection via boto3.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use L2 constructs (aws_lambda.Function, aws_iam.Role, etc.) -- idiomatic CDK, less boilerplate
- Generation Gap pattern with GENERATED_MARKER comment -- don't overwrite files the user has edited (matches existing Terraform and codegen patterns)
- Standalone CDK app with its own `requirements.txt` and virtual env -- isolated from user's project dependencies
- Jinja2 templates live in `src/rsf/cdk/templates/` -- separate directory mirroring `src/rsf/terraform/templates/`
- Use `npx aws-cdk@latest` to run CDK commands -- no global install needed, auto-downloads latest version
- Always use latest CDK version (no pinning)
- Node.js/npx missing -> FAIL in doctor and deploy (nothing CDK-related works without it)
- cdk binary absent -> WARN in doctor (per success criteria #4) with npm install instructions
- Default CDK app output directory: `cdk/` (parallel to `terraform/`), uses existing `--output-dir` flag
- Stream CDK stdout/stderr in real-time to terminal
- CDK approval: pass through `--require-approval` flag; RSF's `--auto-approve` maps to `--require-approval never`; default CDK behavior prompts for security-sensitive changes
- Stage support via CDK context values: `-c stage=prod`; CDK stack reads via `self.node.try_get_context('stage')`
- Pre-check before deploy starts -- fail fast with clear message before any CDK commands run
- Use boto3 `cloudformation.describe_stacks(StackName='CDKToolkit')` -- no AWS CLI dependency, minimal permissions
- Warn only on missing bootstrap -- show the exact `cdk bootstrap aws://ACCOUNT/REGION` command; don't auto-run (security implications)

### Claude's Discretion
- CDK stack naming conventions
- Exact Jinja2 template structure and variable passing
- Virtual env creation and pip install strategy
- Error message formatting and Rich console output styling
- Teardown (`cdk destroy`) flag handling

### Deferred Ideas (OUT OF SCOPE)
- None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CDKP-01 | CDKProvider generates a Python CDK app (app.py, stack.py, cdk.json) via Jinja2 with Generation Gap pattern | Jinja2 template engine, CDK app structure patterns, GENERATED_MARKER reuse |
| CDKP-02 | User can deploy infrastructure via `cdk deploy` invoked by RSF | Subprocess streaming pattern, npx invocation, auto-approve mapping |
| CDKP-03 | RSF detects missing CDK bootstrap and warns user before deploy | boto3 CloudFormation describe_stacks API, CDKToolkit stack detection |
| CDKP-04 | CDK CLI (npm package `aws-cdk`) is installed/updated to latest on local machine | npx aws-cdk@latest auto-downloads, no explicit install step needed |
| CDKP-05 | `rsf doctor` checks for CDK CLI binary when CDK provider is configured | PrerequisiteCheck pattern, shutil.which for node/npx, provider-aware doctor checks |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aws-cdk-lib | latest (via npx) | CDK construct library for generated app | Standard CDK library for Python apps |
| constructs | >=10.0.0 | CDK construct base (peer dep of aws-cdk-lib) | Required peer dependency |
| Jinja2 | already in RSF deps | Template engine for CDK code generation | Same engine used by Terraform templates |
| boto3 | already in RSF deps | CloudFormation API for bootstrap detection | Already an RSF dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| npx | via Node.js | CDK CLI runner without global install | Every CDK operation (synth, deploy, destroy) |
| subprocess (stdlib) | N/A | Streaming process execution | CDK deploy with real-time output |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| npx aws-cdk@latest | Global cdk install | Requires user to manage CDK version; npx always uses latest |
| boto3 for bootstrap check | aws cloudformation describe-stacks CLI | Adds AWS CLI dependency; boto3 already available |
| L2 constructs | L1 Cfn* constructs | L1 is more verbose, maps 1:1 to CloudFormation; L2 is idiomatic |

**Installation:**
CDK dependencies go in the generated app's `requirements.txt`, NOT in RSF's `pyproject.toml`:
```
aws-cdk-lib>=2.0.0
constructs>=10.0.0,<11.0.0
```

## Architecture Patterns

### Recommended Project Structure
```
src/rsf/
├── cdk/
│   ├── __init__.py          # Module init
│   ├── engine.py            # Jinja2 template rendering (standard delimiters)
│   └── templates/
│       ├── app.py.j2        # CDK app entry point
│       ├── stack.py.j2      # Main stack with L2 constructs
│       ├── cdk.json.j2      # CDK config
│       └── requirements.txt.j2  # CDK app dependencies
├── providers/
│   ├── cdk.py               # CDKProvider class
│   └── ...existing files...
```

### Pattern 1: CDK App Generation (Jinja2 Templates)
**What:** Generate complete CDK Python app from Jinja2 templates using WorkflowMetadata
**When to use:** `rsf generate` or `rsf deploy` with CDK provider
**Key insight:** CDK templates use standard Jinja2 delimiters ({{ }}, {% %}) since Python CDK code doesn't conflict with Jinja2 syntax (unlike HCL which uses ${}).

Template variables mirror TerraformConfig but map to CDK constructs:
```python
# Generated app.py (from app.py.j2)
#!/usr/bin/env python3
# DO NOT EDIT - Generated by RSF
import aws_cdk as cdk
from stack import {{ stack_class_name }}

app = cdk.App()
{{ stack_class_name }}(app, "{{ stack_id }}")
app.synth()
```

### Pattern 2: Streaming Subprocess for CDK Deploy
**What:** Real-time stdout/stderr piping for CDK deploy (not capture_output=True)
**When to use:** `cdk deploy` which produces ongoing stack event output
**Key insight:** The existing `run_provider_command()` uses `capture_output=True` which buffers all output. CDK deploy needs a streaming variant that pipes stdout/stderr directly to the terminal.

```python
def run_provider_command_streaming(
    self,
    cmd: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command with real-time stdout/stderr output."""
    merged_env = {**os.environ, **(env or {})}
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=merged_env,
        check=True,
        text=True,
        shell=False,
        # No capture_output -- inherits parent's stdout/stderr
    )
    return proc
```

### Pattern 3: Bootstrap Detection via boto3
**What:** Check for CDKToolkit CloudFormation stack before deploy
**When to use:** Pre-deploy validation step
```python
import boto3
from botocore.exceptions import ClientError

def _check_bootstrap(self) -> bool:
    """Return True if CDK bootstrap stack exists in current region."""
    cf = boto3.client("cloudformation")
    try:
        cf.describe_stacks(StackName="CDKToolkit")
        return True
    except ClientError as e:
        if "does not exist" in str(e):
            return False
        raise  # Re-raise unexpected errors
```

### Pattern 4: npx CDK Invocation
**What:** Use `npx aws-cdk@latest` for all CDK CLI operations
**When to use:** synth, deploy, destroy
```python
# Base CDK command via npx
cdk_cmd = ["npx", "aws-cdk@latest"]

# Deploy
deploy_cmd = cdk_cmd + ["deploy", "--app", "python3 app.py"]
if auto_approve:
    deploy_cmd.extend(["--require-approval", "never"])
if stage:
    deploy_cmd.extend(["-c", f"stage={stage}"])

# Destroy
destroy_cmd = cdk_cmd + ["destroy", "--app", "python3 app.py", "--force"]
```

### Anti-Patterns to Avoid
- **Global CDK install:** Don't rely on `npm install -g aws-cdk`. Use `npx aws-cdk@latest` which auto-downloads.
- **Capturing CDK deploy output:** Don't use `capture_output=True` for deploy. Users need to see stack events in real-time.
- **Auto-running cdk bootstrap:** Never auto-run bootstrap. It creates IAM roles and S3 buckets. Warn and show the command.
- **Putting aws-cdk-lib in RSF's pyproject.toml:** aws-cdk-lib is ~200MB. It goes in the generated app's requirements.txt only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CDK CLI execution | Custom Node.js wrapper | npx aws-cdk@latest | npx handles download, caching, version resolution |
| Template rendering | String concatenation | Jinja2 Environment + FileSystemLoader | Already proven in Terraform generator |
| Bootstrap detection | Parsing CLI output | boto3 describe_stacks | Programmatic, no shell parsing, already a dep |
| Process streaming | Custom async I/O | subprocess.run without capture_output | Inherits parent stdout/stderr automatically |

**Key insight:** Nearly all infrastructure for this phase exists already. The CDK provider is a thin adapter that maps existing patterns (Jinja2 templates, provider lifecycle, prerequisite checks) to CDK-specific commands and templates.

## Common Pitfalls

### Pitfall 1: CDK Jinja2 Template Delimiter Confusion
**What goes wrong:** Using HCL-safe custom delimiters (<< >>, <% %>) in CDK templates when they're not needed
**Why it happens:** Copy-pasting from Terraform engine.py which uses custom delimiters to avoid ${} conflicts
**How to avoid:** CDK templates generate Python code. Standard Jinja2 delimiters ({{ }}, {% %}) work fine since Python doesn't use ${}
**Warning signs:** Templates with << >> in CDK code generation

### Pitfall 2: npx Not Found on PATH
**What goes wrong:** `npx` command not found because Node.js isn't installed
**Why it happens:** npx ships with Node.js (via npm), but many Python developers don't have Node.js installed
**How to avoid:** Check for npx in check_prerequisites() and produce a clear FAIL with install instructions
**Warning signs:** FileNotFoundError when running subprocess with npx

### Pitfall 3: CDK Bootstrap Missing
**What goes wrong:** `cdk deploy` fails with obscure error about S3 bucket or IAM role
**Why it happens:** CDK needs a one-time bootstrap per account+region to create its staging resources
**How to avoid:** Pre-check with boto3 before running cdk deploy; show exact bootstrap command
**Warning signs:** ClientError mentioning CDKToolkit or staging bucket

### Pitfall 4: Streaming vs Capture for Different CDK Commands
**What goes wrong:** Using streaming for `cdk synth` which should be captured, or capturing for `cdk deploy` which should stream
**Why it happens:** Not distinguishing between commands that produce output for users vs output for validation
**How to avoid:** `cdk synth` -> capture (for validation); `cdk deploy` -> stream (for user feedback); `cdk destroy` -> stream
**Warning signs:** No output during long deploy, or synth validation output cluttering terminal

### Pitfall 5: CDK App Virtual Environment Conflicts
**What goes wrong:** CDK app's dependencies conflict with the user's project or RSF's own deps
**Why it happens:** Running `pip install` in the wrong virtual environment
**How to avoid:** CDK app has its own `requirements.txt`. Document that the generated CDK app should use its own venv.
**Warning signs:** Import errors for aws_cdk when running synth

## Code Examples

### CDKProvider Class Structure
```python
# src/rsf/providers/cdk.py
class CDKProvider(InfrastructureProvider):
    """Infrastructure provider for AWS CDK."""

    CDK_CMD = ["npx", "aws-cdk@latest"]

    def generate(self, ctx: ProviderContext) -> None:
        """Generate CDK Python app from Jinja2 templates."""
        config = self._build_config(ctx)
        generate_cdk(config=config, output_dir=ctx.output_dir)

    def deploy(self, ctx: ProviderContext) -> None:
        """Run cdk deploy with streaming output."""
        self._check_bootstrap_or_warn(ctx)
        cmd = self.CDK_CMD + ["deploy", "--app", "python3 app.py"]
        if ctx.auto_approve:
            cmd.extend(["--require-approval", "never"])
        if ctx.stage:
            cmd.extend(["-c", f"stage={ctx.stage}"])
        self.run_provider_command_streaming(cmd, cwd=ctx.output_dir)

    def teardown(self, ctx: ProviderContext) -> None:
        """Run cdk destroy."""
        cmd = self.CDK_CMD + ["destroy", "--app", "python3 app.py", "--force"]
        if ctx.stage:
            cmd.extend(["-c", f"stage={ctx.stage}"])
        self.run_provider_command_streaming(cmd, cwd=ctx.output_dir)

    def check_prerequisites(self, ctx: ProviderContext) -> list[PrerequisiteCheck]:
        """Check for Node.js/npx and optionally CDK CLI."""
        checks = []
        if shutil.which("npx"):
            checks.append(PrerequisiteCheck("node/npx", "pass", "npx found"))
        else:
            checks.append(PrerequisiteCheck(
                "node/npx", "fail",
                "npx not found. Install Node.js: https://nodejs.org/"
            ))
        if shutil.which("cdk"):
            checks.append(PrerequisiteCheck("cdk", "pass", "cdk binary found"))
        else:
            checks.append(PrerequisiteCheck(
                "cdk", "warn",
                "cdk binary not found. Install: npm install -g aws-cdk"
            ))
        return checks

    def validate_config(self, ctx: ProviderContext) -> None:
        """Validate CDK provider configuration (no-op: Pydantic handles it)."""
        pass
```

### CDK Template: app.py.j2
```python
#!/usr/bin/env python3
# DO NOT EDIT - Generated by RSF
import aws_cdk as cdk
from stack import {{ stack_class_name }}

app = cdk.App()
{{ stack_class_name }}(app, "{{ stack_id }}")
app.synth()
```

### CDK Template: cdk.json.j2
```json
{
  "app": "python3 app.py",
  "watch": {
    "include": ["**"],
    "exclude": ["cdk.out"]
  }
}
```

### Provider Registration
```python
# In src/rsf/providers/__init__.py
from rsf.providers.cdk import CDKProvider
register_provider("cdk", CDKProvider)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Global `npm install -g aws-cdk` | `npx aws-cdk@latest` | CDK v2 (2021) | No global install needed, always latest |
| Separate `cdk init` required | RSF generates complete app | This phase | Users don't need to learn CDK init workflow |
| L1 CfnResource constructs | L2 higher-level constructs | CDK v2 stable | Less boilerplate, better defaults |

**Deprecated/outdated:**
- CDK v1 (aws-cdk package per service): Replaced by CDK v2 (single aws-cdk-lib package). All templates must use CDK v2 imports.

## Open Questions

1. **CDK app virtual environment management**
   - What we know: CDK app needs `aws-cdk-lib` and `constructs` installed to run `cdk synth`
   - What's unclear: Should RSF auto-create a venv in the CDK output directory, or just document that users should?
   - Recommendation: Generate `requirements.txt` but don't auto-create venv. Add a comment in the generated app explaining how to set up. The `cdk synth` step via npx handles the CDK CLI itself; the Python deps are only needed if the user wants to customize the stack.

2. **Stack naming convention**
   - What we know: CDK needs a stack ID and optionally a stack name
   - What's unclear: How to derive from workflow_name
   - Recommendation: Stack ID = `RsfStack` (simple default), stack name = `rsf-{workflow_name}` (matches Terraform resource naming). Stack class name = `RsfStack`.

## Sources

### Primary (HIGH confidence)
- RSF codebase: `src/rsf/providers/base.py`, `terraform.py`, `registry.py`, `__init__.py` -- provider interface and reference implementation
- RSF codebase: `src/rsf/terraform/generator.py`, `engine.py` -- Jinja2 template generation pattern
- RSF codebase: `src/rsf/cli/deploy_cmd.py` -- deploy routing through provider interface
- RSF codebase: `src/rsf/cli/doctor_cmd.py` -- prerequisite check display pattern

### Secondary (MEDIUM confidence)
- AWS CDK v2 documentation -- L2 construct patterns, cdk.json format, bootstrap requirements
- npx documentation -- auto-download and caching behavior

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- CDK v2 is well-established, patterns are stable
- Architecture: HIGH -- follows existing TerraformProvider pattern exactly
- Pitfalls: HIGH -- based on direct codebase analysis and CDK best practices

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (30 days -- CDK is stable)
