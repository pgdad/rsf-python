---
phase: 47-workflow-templates-and-github-action
plan: 02
status: complete
started: 2026-03-02
completed: 2026-03-02
requirements_completed: [ECO-03]
---

# Plan 47-02 Summary: GitHub Action (rsf-action)

## What Was Built

Created a reusable composite GitHub Action at `action/` that validates, generates, and optionally deploys RSF workflows, posting plan summaries as PR comments.

## Key Changes

### action/action.yml
- Composite GitHub Action with 10 configurable inputs
- Python setup, RSF installation, validate/generate/deploy pipeline, PR comment posting
- Deploy is opt-in (default: false) with stage and auto-approve support
- RSF version pinning and custom install source support
- Three outputs: validate-result, generate-result, deploy-result

### action/entrypoint.sh
- Installs RSF based on version or custom source
- Runs validate -> generate -> deploy (opt-in) pipeline
- Captures all outputs in GITHUB_OUTPUT for downstream steps
- Continues past validation failure to allow comment posting
- Executable shell script

### action/comment.py
- Posts terraform-plan-style PR comment using Python stdlib only
- Status table (Validate/Generate/Deploy with emoji icons)
- Collapsible sections for output details
- Validation failures shown expanded for visibility
- Updates existing comment in-place using COMMENT_MARKER
- No external dependencies (urllib.request, json, os)

### action/README.md
- Quick start example
- Full input/output reference table
- Examples: basic validation, staging deploy, version pinning, production deploy
- PR comment format description
- Troubleshooting section

## Key Files

### Created
- `action/action.yml` — Composite action definition
- `action/entrypoint.sh` — Install + run pipeline
- `action/comment.py` — PR comment formatter
- `action/README.md` — Documentation

## Verification
- action.yml valid YAML
- comment.py valid Python (ast.parse passes)
- entrypoint.sh is executable
- grep confirms key patterns present

## Deviations
None.
