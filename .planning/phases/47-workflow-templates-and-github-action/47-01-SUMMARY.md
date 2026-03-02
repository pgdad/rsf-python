---
phase: 47-workflow-templates-and-github-action
plan: 01
status: complete
started: 2026-03-02
completed: 2026-03-02
---

# Plan 47-01 Summary: Template Infrastructure + API Gateway CRUD

## What Was Built

Added `--template` flag to `rsf init` command with template discovery, listing, and scaffolding support. Shipped the `api-gateway-crud` template as the first named template.

## Key Changes

### init_cmd.py Enhancements
- Added `--template` / `-t` option to the `init` command
- `--template list` shows available templates with descriptions
- `--template <name>` scaffolds from a named template subdirectory
- Template discovery scans for subdirectories with workflow.yaml
- Jinja2 rendering for `.j2` files, gitignore rename to `.gitignore`
- Default project name falls back to template name when not provided
- Invalid template shows error with available template list
- Backward compatible: `rsf init <name>` still creates HelloWorld scaffold

### api-gateway-crud Template
- Complete DynamoDB-backed CRUD workflow with API Gateway routing
- 5 real boto3 handlers: create, get, update, delete, list
- Unit tests mocking DynamoDB operations
- Terraform template for DynamoDB table (Jinja2, project name substituted)
- pyproject.toml with boto3 dependency
- README with architecture diagram, customization guide, deployment steps

## Key Files

### Created
- `src/rsf/cli/templates/api-gateway-crud/` (13 files)
  - workflow.yaml, 5 handlers, tests, pyproject.toml.j2, terraform.tf.j2, README.md

### Modified
- `src/rsf/cli/init_cmd.py` — Template-aware init with --template flag

## Verification
- All 4 existing init tests pass (backward compatibility confirmed)
- Template directory structure verified
- action.yml valid YAML, entrypoint.sh executable

## Deviations
None.
