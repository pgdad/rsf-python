# Phase 53: CDK Provider - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can deploy infrastructure via AWS CDK through RSF. CDKProvider implements the InfrastructureProvider ABC. CDK app is generated from Jinja2 templates. Missing prerequisites (Node.js, CDK bootstrap) are caught before deploy begins. `rsf doctor` reports CDK-specific checks.

</domain>

<decisions>
## Implementation Decisions

### Generated CDK code
- Use L2 constructs (aws_lambda.Function, aws_iam.Role, etc.) — idiomatic CDK, less boilerplate
- Generation Gap pattern with GENERATED_MARKER comment — don't overwrite files the user has edited (matches existing Terraform and codegen patterns)
- Standalone CDK app with its own `requirements.txt` and virtual env — isolated from user's project dependencies
- Jinja2 templates live in `src/rsf/cdk/templates/` — separate directory mirroring `src/rsf/terraform/templates/`

### CDK CLI management
- Use `npx aws-cdk@latest` to run CDK commands — no global install needed, auto-downloads latest version
- Always use latest CDK version (no pinning)
- Node.js/npx missing → FAIL in doctor and deploy (nothing CDK-related works without it)
- cdk binary absent → WARN in doctor (per success criteria #4) with npm install instructions

### Output and deploy UX
- Default CDK app output directory: `cdk/` (parallel to `terraform/`), uses existing `--output-dir` flag
- Stream CDK stdout/stderr in real-time to terminal — user sees stack events and resource creation progress as it happens
- CDK approval: pass through `--require-approval` flag; RSF's `--auto-approve` maps to `--require-approval never`; default CDK behavior prompts for security-sensitive changes
- Stage support via CDK context values: `-c stage=prod`; CDK stack reads via `self.node.try_get_context('stage')`

### Bootstrap detection
- Pre-check before deploy starts — fail fast with clear message before any CDK commands run
- Use boto3 `cloudformation.describe_stacks(StackName='CDKToolkit')` — no AWS CLI dependency, minimal permissions
- Warn only on missing bootstrap — show the exact `cdk bootstrap aws://ACCOUNT/REGION` command; don't auto-run (security implications)

### Claude's Discretion
- CDK stack naming conventions
- Exact Jinja2 template structure and variable passing
- Virtual env creation and pip install strategy
- Error message formatting and Rich console output styling
- Teardown (`cdk destroy`) flag handling

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `InfrastructureProvider` ABC (`providers/base.py`): CDKProvider implements `generate()`, `deploy()`, `teardown()`, `check_prerequisites()`, `validate_config()`
- `run_provider_command()` base class helper: shell=False subprocess runner with env merging — needs streaming variant for CDK deploy
- `ProviderContext` dataclass: carries metadata, output_dir, stage, auto_approve — CDK provider receives this
- `WorkflowMetadata` dataclass: all DSL infrastructure fields — CDK templates consume this
- `TerraformProvider` (`providers/terraform.py`): reference implementation for the provider pattern
- Jinja2 template engine (`terraform/engine.py`): `render_hcl_template()` — CDK needs equivalent `render_cdk_template()`
- Provider registry (`providers/registry.py`): `register_provider("cdk", CDKProvider)` in `__init__.py`
- `GENERATED_MARKER` pattern (`terraform/generator.py`): reuse for CDK Generation Gap

### Established Patterns
- Provider registration: `register_provider("name", ProviderClass)` in `providers/__init__.py`
- Deploy routing: `deploy_cmd.py` → `get_provider()` → `provider.generate()` → `provider.deploy()` — CDK provider auto-routes
- Doctor integration: `check_prerequisites()` returns `list[PrerequisiteCheck]` with pass/warn/fail status
- Config resolution: `resolve_infra_config()` reads provider name from workflow YAML or rsf.toml

### Integration Points
- `providers/__init__.py`: add `register_provider("cdk", CDKProvider)` and export
- `deploy_cmd.py`: already routes through provider interface — CDK "just works" but deploy streaming needs subprocess change from `capture_output=True` to real-time piping
- `doctor_cmd.py`: needs to call CDK provider's `check_prerequisites()` when CDK is configured
- `generate_cmd.py`: may need provider-aware infrastructure generation (currently only does codegen)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 53-cdk-provider*
*Context gathered: 2026-03-02*
