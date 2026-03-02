# Phase 47: Workflow Templates and GitHub Action - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can scaffold new projects from curated workflow templates via `rsf init --template <name>`, and CI pipelines can validate, generate, and deploy workflows using a reusable GitHub Action (`rsf-action`) that posts plan summaries as PR comments. Two named templates ship: `api-gateway-crud` and `s3-event-pipeline`.

</domain>

<decisions>
## Implementation Decisions

### Template structure
- Templates bundled inside the RSF package in `src/rsf/cli/templates/` as subdirectories (e.g., `templates/api-gateway-crud/`)
- Each template is a full scaffold: workflow.yaml, handlers with real AWS logic (boto3 calls), tests, pyproject.toml, Terraform pre-configured, .gitignore
- Handlers contain real implementations — templates are deployable as-is, not stubs
- Each template includes a per-template README.md explaining architecture, customization, and deployment

### Template selection UX
- `rsf init <project-name>` keeps current behavior (HelloWorld scaffold) — `--template` is purely additive
- `rsf init --template list` shows all available templates with descriptions (dedicated list flag)
- Template names use kebab-case exactly as specified: `api-gateway-crud`, `s3-event-pipeline`
- When `--template` is given without a project name, default directory name to the template name (e.g., `rsf init --template api-gateway-crud` creates `api-gateway-crud/`)
- Invalid template name shows error with available templates listed

### GitHub Action scope
- Default steps: `rsf validate` + `rsf generate` (safe for PRs)
- Deploy is opt-in via an input flag — no accidental deployments
- Optional `stage` input maps to `rsf deploy --stage` for environment-specific deploys
- PR comment includes: validation results (pass/fail/warnings) + diff summary of generated changes (like terraform plan for RSF)
- When deploy is enabled, PR comment also includes Terraform plan output for full reviewer visibility

### Action distribution
- Composite GitHub Action (action.yml with run steps) — transparent, lightweight, easy to debug
- Lives in this repo (rsf-python), not a separate repo
- RSF install source is configurable: defaults to PyPI (`pip install rsf`), with input to override with git ref or local path for development
- Optional `rsf-version` input: defaults to latest PyPI release, users can pin specific versions for reproducibility

### Claude's Discretion
- Internal template directory structure and naming conventions
- Template test coverage depth
- PR comment formatting and collapsible sections
- Error message wording and help text
- Action input validation approach

</decisions>

<specifics>
## Specific Ideas

- Templates should feel like complete, real-world examples — not toy demos
- PR comment format should resemble a terraform plan: concise summary of what changes, not raw command output
- The action should "just work" — users shouldn't need to install RSF separately in their CI

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `init_cmd.py`: Existing init command with Jinja2 template rendering (`_render_template`), project scaffolding pattern, directory creation, Rich console output
- `src/rsf/cli/templates/`: Existing templates directory with workflow.yaml, handler_example.py, test_example.py, pyproject.toml.j2, gitignore — pattern for adding new template subdirectories
- `deploy_cmd.py`: Full validate → generate → deploy pipeline with `--stage`, `--no-infra`, `--auto-approve` flags — action can invoke these same commands
- `validate_cmd.py`, `generate_cmd.py`: Existing CLI commands the action will call

### Established Patterns
- CLI uses Typer for command registration + Rich for console output
- Jinja2 for template rendering (`.j2` extension convention)
- `main.py` registers all subcommands via `app.command(name=...)(module.function)`
- Project name passed as Typer Argument, flags as Typer Options

### Integration Points
- New template subdirectories under `src/rsf/cli/templates/` (e.g., `templates/api-gateway-crud/`)
- `--template` flag added to existing `init` command in `init_cmd.py`
- `action/` directory at repo root for the GitHub Action (action.yml + scripts)
- Action invokes `rsf validate`, `rsf generate`, `rsf deploy` — same CLI commands users run locally

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 47-workflow-templates-and-github-action*
*Context gathered: 2026-03-02*
