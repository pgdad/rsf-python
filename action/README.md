# RSF Workflow Action

A reusable GitHub Action that validates, generates, and optionally deploys RSF workflows. Posts a plan summary as a PR comment with validation results and generated changes.

## Quick Start

Add to your GitHub workflow (`.github/workflows/rsf.yml`):

```yaml
name: RSF Workflow
on:
  pull_request:
    paths:
      - 'workflow.yaml'
      - 'handlers/**'

jobs:
  rsf:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: your-org/rsf-python/action@main
        with:
          workflow-file: 'workflow.yaml'
```

This will:
1. Install the latest RSF from PyPI
2. Run `rsf validate` on your workflow
3. Run `rsf generate` to produce orchestrator code
4. Post a summary comment on the PR

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `rsf-version` | `latest` | RSF version to install (e.g., `0.5.0`). Set to pin a specific version. |
| `rsf-install-source` | _(empty)_ | Override install source (e.g., `git+https://github.com/...`). If set, `rsf-version` is ignored. |
| `workflow-file` | `workflow.yaml` | Path to workflow YAML file. |
| `deploy` | `false` | Enable deployment after validate+generate. Set to `true` to enable. |
| `stage` | _(empty)_ | Deployment stage (e.g., `dev`, `staging`, `prod`). Only used when `deploy` is `true`. |
| `auto-approve` | `false` | Auto-approve Terraform changes during deploy. |
| `post-comment` | `true` | Post plan summary as PR comment. Set to `false` to disable. |
| `python-version` | `3.12` | Python version to use. |
| `github-token` | `${{ github.token }}` | GitHub token for posting PR comments. |

## Outputs

| Output | Description |
|--------|-------------|
| `validate-result` | `pass` or `fail` |
| `generate-result` | `pass`, `fail`, or `skipped` |
| `deploy-result` | `pass`, `fail`, or `skipped` |

## Examples

### Basic Validation (PRs Only)

```yaml
- uses: your-org/rsf-python/action@main
  with:
    workflow-file: 'workflow.yaml'
```

### Deploy to Staging on Merge

```yaml
- uses: your-org/rsf-python/action@main
  with:
    deploy: 'true'
    stage: 'staging'
    auto-approve: 'true'
    post-comment: 'false'
```

### Pin RSF Version

```yaml
- uses: your-org/rsf-python/action@main
  with:
    rsf-version: '0.5.0'
```

### Deploy to Production with Review

```yaml
- uses: your-org/rsf-python/action@main
  with:
    deploy: 'true'
    stage: 'prod'
    # auto-approve defaults to false -- shows Terraform plan in PR comment
```

### Install from Git

```yaml
- uses: your-org/rsf-python/action@main
  with:
    rsf-install-source: 'git+https://github.com/your-org/rsf-python.git@feature-branch'
```

## PR Comment Format

The action posts a comment with this structure:

| Step | Status |
|------|--------|
| Validate | :white_check_mark: Pass |
| Generate | :white_check_mark: Pass |
| Deploy   | :fast_forward: Skipped |

With expandable sections for validation output, generated changes, and deploy output (when enabled).

On subsequent pushes, the same comment is updated in-place (no duplicate comments).

## How It Works

1. **Setup**: Installs Python and RSF (from PyPI or custom source)
2. **Validate**: Runs `rsf validate` on the workflow file
3. **Generate**: Runs `rsf generate` to produce orchestrator code (skipped if validation fails)
4. **Deploy** (opt-in): Runs `rsf deploy` with optional stage and auto-approve (skipped if generation fails)
5. **Comment**: Posts results as a PR comment (updates existing comment if found)

## Troubleshooting

### Action fails to install RSF

- Check that `rsf-version` is a valid version on PyPI
- If using `rsf-install-source`, ensure the URL is accessible

### PR comment not appearing

- Verify `GITHUB_TOKEN` has `pull-requests: write` permission
- Check that the workflow trigger is `pull_request` (not `push`)
- Ensure `post-comment` is not set to `false`

### Deploy fails

- Ensure AWS credentials are configured in the workflow (e.g., via `aws-actions/configure-aws-credentials`)
- Check that Terraform is available if infrastructure generation is enabled
- Review the deploy output in the PR comment for specific errors
