# Phase 26: CI/CD Pipeline - Research

**Researched:** 2026-02-28
**Domain:** GitHub Actions, PyPI OIDC Trusted Publishing, Python CI, React/npm build integration
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CICD-01 | GitHub Actions runs lint and tests on every pull request | CI workflow with ruff + pytest; PR status check via `on: pull_request` trigger |
| CICD-02 | GitHub Actions builds wheel and publishes to PyPI on git tag push | Tag-triggered release workflow; `python -m build` + `pypa/gh-action-pypi-publish@release/v1` |
| CICD-03 | CI builds React UIs as part of the wheel build process | `actions/setup-node@v6` + `npm ci && npm run build` in `ui/` before `python -m build` |
| CICD-04 | PyPI publishing uses OIDC trusted publisher authentication — no API tokens | `permissions: id-token: write` + PyPI pending publisher configuration; no secrets stored |
</phase_requirements>

## Summary

Phase 26 adds two GitHub Actions workflows to the repository. The first is a CI workflow triggered on every pull request that runs Python lint (ruff) and the full pytest suite. The second is a release workflow triggered on `v*` tag pushes that compiles the React UI, builds the Python wheel, and publishes to PyPI using OIDC trusted publisher authentication with no stored API tokens.

The project already has Phase 25 complete: `pyproject.toml` uses hatchling + hatch-vcs for git-tag-derived versioning. The static assets from `npm run build` (run from `ui/`) output directly into `src/rsf/editor/static/`, which is already git-tracked and included in the wheel via the standard `packages = ["src/rsf"]` hatchling configuration. This means the build sequence in CI is: `npm ci && npm run build` (in `ui/`), then `python -m build`. The React assets must be built before `python -m build` so they exist on disk when hatchling packages `src/rsf`.

PyPI trusted publisher (OIDC) requires one manual step on PyPI.org before the first release: configure a pending trusted publisher with the GitHub repo owner, repo name, and workflow filename. After that, no API tokens are ever stored in GitHub secrets — GitHub's OIDC identity provider exchanges a short-lived token at publish time.

**Primary recommendation:** Two separate workflow files — `.github/workflows/ci.yml` (PR checks) and `.github/workflows/release.yml` (tag-triggered publish). Keep jobs minimal and cache npm dependencies via `setup-node`'s built-in cache.

## Standard Stack

### Core
| Tool/Action | Version | Purpose | Why Standard |
|-------------|---------|---------|--------------|
| `actions/checkout` | v6 | Checkout repo code | Latest major version (v6.0.2, Jan 2025) |
| `actions/setup-python` | v6 | Install Python with caching | Latest major version (v6.2.0, Jan 2025) |
| `actions/setup-node` | v6 | Install Node.js with npm cache | Latest major version; built-in `npm` cache support |
| `actions/upload-artifact` | v4 | Pass dist/ between jobs | v4 is current; used in 3-job publish pattern |
| `actions/download-artifact` | v4 | Retrieve dist/ in publish job | Paired with upload-artifact v4 |
| `pypa/gh-action-pypi-publish` | `release/v1` | Publish wheel to PyPI | Official PyPA action; supports OIDC natively |
| `astral-sh/ruff-action` | v3 | Run ruff lint in CI | Official ruff action; zero-config, fast |
| `python -m build` | latest (via pip install build) | Build sdist + wheel | PEP 517 standard; works with hatchling |
| `npm ci` | (npm built-in) | Reproducible dependency install | Uses package-lock.json; correct for CI |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `ruff check` | latest | Lint Python code | In CI lint step |
| `ruff format --check` | latest | Enforce formatting | In CI lint step |
| `pytest` | >=7.0 (from pyproject.toml) | Run test suite | In CI test step |
| GitHub environment (`pypi`) | N/A | Scope OIDC token to PyPI | Required for trusted publishing |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `astral-sh/ruff-action` | `pip install ruff && ruff check` | ruff-action is simpler; manual install gives version control |
| `pypa/gh-action-pypi-publish` | `twine upload` with API token | OIDC is more secure; no stored secrets; pypa action is the standard |
| `release/v1` (floating) | pinned SHA | Floating tag is recommended by PyPA for security patches; SHA pinning is stricter |
| `python -m build` | `hatch build` | `python -m build` is the PEP 517 standard tool; both work with hatchling |

## Architecture Patterns

### Recommended Project Structure
```
.github/
└── workflows/
    ├── ci.yml          # PR checks: lint + test
    └── release.yml     # Tag push: build UI + wheel + publish to PyPI
```

### Pattern 1: Two-Workflow Separation (CI vs Release)

**What:** Separate workflow files for CI (PR checks) and release (publish). Never combine into one workflow.
**When to use:** Always — separation of concerns, different triggers, different permissions.

CI workflow trigger:
```yaml
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
```

Release workflow trigger:
```yaml
on:
  push:
    tags:
      - 'v*'
```

### Pattern 2: Three-Job Release Workflow (Build → Publish)

**What:** Separate jobs for building the wheel and publishing it. The build job has no special permissions; the publish job gets `id-token: write` scoped to the minimum required job.
**When to use:** Any OIDC trusted publishing workflow — the PyPA docs and `pypa/gh-action-pypi-publish` README mandate this pattern.

```yaml
# Source: https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0   # CRITICAL: hatch-vcs needs full history to derive version
      - uses: actions/setup-node@v6
        with:
          node-version: '22'
          cache: 'npm'
          cache-dependency-path: ui/package-lock.json
      - name: Build React UI
        run: npm ci && npm run build
        working-directory: ui
      - uses: actions/setup-python@v6
        with:
          python-version: '3.12'
      - run: pip install build hatch-vcs
      - run: python -m build
      - uses: actions/upload-artifact@v4
        with:
          name: python-package-distributions
          path: dist/

  publish-to-pypi:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/rsf
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: python-package-distributions
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
```

### Pattern 3: CI Workflow with Lint + Test

```yaml
# Source: https://docs.astral.sh/ruff/integrations/ + GitHub Actions Python docs
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: astral-sh/ruff-action@v3
      - uses: astral-sh/ruff-action@v3
        with:
          args: "format --check"

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.12', '3.13']
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
      - run: pip install -e ".[dev]"
      - run: pytest -m "not integration"
```

### Pattern 4: fetch-depth: 0 for hatch-vcs

**What:** `actions/checkout` by default only fetches the latest commit (shallow clone). hatch-vcs uses `git describe` to compute the version from git tags — this requires the full tag history.
**When to use:** Any workflow that calls `python -m build` or `hatch build` with hatch-vcs.

```yaml
- uses: actions/checkout@v6
  with:
    fetch-depth: 0   # Required for hatch-vcs git-tag-based versioning
```

Without `fetch-depth: 0`, hatch-vcs cannot find the nearest tag and will produce a fallback version or fail.

### Anti-Patterns to Avoid

- **Storing PyPI API tokens in GitHub secrets:** Unnecessary with OIDC trusted publisher; creates a secret rotation burden and security risk.
- **Single workflow file for CI + release:** Makes permissions too broad; OIDC token should be scoped to the publish job only.
- **Shallow checkout for hatch-vcs builds:** `fetch-depth: 0` is mandatory; without it the version derived by hatch-vcs is wrong.
- **Running `npm install` instead of `npm ci` in CI:** `npm install` can update package-lock.json; `npm ci` is deterministic and faster.
- **Not setting `working-directory: ui`:** The React build must run from `ui/` where `package.json` lives.
- **Publishing in the same job as building:** Violates principle of least privilege for OIDC token.
- **Using `on: release: types: [published]` instead of `on: push: tags`:** Tag push is simpler; avoids needing to create a GitHub Release manually before publishing to PyPI.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PyPI authentication | Custom token scripts or env vars | `pypa/gh-action-pypi-publish@release/v1` + OIDC | Handles token exchange, attestation signing automatically |
| Ruff invocation | Bash `pip install ruff && ruff check .` | `astral-sh/ruff-action@v3` | Zero config; handles installation and GitHub annotations |
| Artifact passing between jobs | Custom upload scripts | `actions/upload-artifact@v4` + `actions/download-artifact@v4` | Standard approach; atomic, versioned |
| Python version matrix | Multiple duplicate jobs | `strategy.matrix.python-version` | DRY; parallel execution |
| npm caching | Custom `~/.npm` cache steps | `actions/setup-node@v6` with `cache: 'npm'` | Built-in; uses package-lock.json hash automatically |

**Key insight:** GitHub Actions has first-party or officially-blessed actions for every required step. Custom shell scripts should only fill gaps where no action exists.

## Common Pitfalls

### Pitfall 1: Shallow Clone Breaks hatch-vcs Versioning
**What goes wrong:** `python -m build` succeeds but produces a wheel with version `0.0.0` or `0.1.dev0+unknown` because hatch-vcs cannot find any tags in the shallow history.
**Why it happens:** `actions/checkout@v6` defaults to `fetch-depth: 1` (one commit only). Git tags are not fetched unless explicitly requested.
**How to avoid:** Always add `fetch-depth: 0` to checkout in any job that builds the wheel.
**Warning signs:** Wheel filename in dist/ shows unexpected version; `pip show rsf` after install shows wrong version.

### Pitfall 2: OIDC Trusted Publisher Not Configured on PyPI Before First Tag Push
**What goes wrong:** The publish job gets a 403 error from PyPI: "Forbidden — the token could not be verified."
**Why it happens:** The pending trusted publisher on PyPI.org must be created before the first publish attempt. PyPI validates the OIDC token against the configured publisher entry.
**How to avoid:** Before pushing the first `v*` tag, create a pending trusted publisher on PyPI.org at https://pypi.org/manage/account/publishing/ with: PyPI project name (`rsf`), GitHub owner (`pgdad`), repo name (`rsf-python`), workflow file name (`release.yml`), and environment name (`pypi`).
**Warning signs:** Publish job fails immediately after the upload step with a 403 or 422 error.

### Pitfall 3: React Static Assets Not Present at Wheel Build Time
**What goes wrong:** The wheel is built successfully but `src/rsf/editor/static/` is empty (or contains stale files). The published package serves no UI.
**Why it happens:** The React build step is skipped, runs after `python -m build`, or fails silently.
**How to avoid:** In the release workflow, the `npm run build` step must complete successfully before `python -m build` runs. Both steps must be in the same job (not separate jobs) because static assets must be on the filesystem when hatchling packages `src/rsf`.
**Warning signs:** Built wheel contains no `.js` or `.css` files under `rsf/editor/static/assets/`; `rsf ui` after install shows blank page.

### Pitfall 4: `id-token: write` Permission Set at Wrong Scope
**What goes wrong:** OIDC token exchange fails; trusted publisher authentication rejected.
**Why it happens:** If the permission is set at the workflow level instead of the job level, all jobs get the elevated permission (security risk). If omitted from the publish job, the OIDC exchange cannot happen.
**How to avoid:** Set `permissions: id-token: write` only on the `publish-to-pypi` job, not at the top-level `permissions:` block.
**Warning signs:** CI job gets permission errors on unrelated steps; or publish job gets OIDC token failure.

### Pitfall 5: Integration Tests Running in CI Without AWS Credentials
**What goes wrong:** `pytest` fails on tests marked `integration` because they require real AWS credentials and deployed Terraform infrastructure.
**Why it happens:** The full test suite includes integration tests that make real AWS API calls.
**How to avoid:** Always exclude integration tests in CI: `pytest -m "not integration"`.
**Warning signs:** Tests hang waiting for network, or fail with `NoCredentialsError`.

### Pitfall 6: npm ci Fails Because package-lock.json Is Outdated
**What goes wrong:** `npm ci` exits non-zero because `package-lock.json` is not in sync with `package.json`.
**Why it happens:** A developer ran `npm install` locally and updated `package.json` but did not commit the regenerated `package-lock.json`.
**How to avoid:** Enforce in team workflow: always commit `package-lock.json` after changing dependencies. The CI failure itself is the correct signal.
**Warning signs:** `npm ci` error: "npm ci can only install packages when your package.json and package-lock.json are in sync."

## Code Examples

### Complete CI Workflow (`.github/workflows/ci.yml`)
```yaml
# Source: https://docs.astral.sh/ruff/integrations/ + https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: astral-sh/ruff-action@v3
      - uses: astral-sh/ruff-action@v3
        with:
          args: "format --check"

  test:
    name: Test (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.12', '3.13']
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run tests
        run: pytest -m "not integration" -v
```

### Complete Release Workflow (`.github/workflows/release.yml`)
```yaml
# Source: https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    name: Build wheel
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0  # Required: hatch-vcs reads git tags for version

      - uses: actions/setup-node@v6
        with:
          node-version: '22'
          cache: 'npm'
          cache-dependency-path: ui/package-lock.json

      - name: Build React UI
        working-directory: ui
        run: |
          npm ci
          npm run build

      - uses: actions/setup-python@v6
        with:
          python-version: '3.12'

      - name: Install build tools
        run: pip install build hatch-vcs

      - name: Build wheel and sdist
        run: python -m build

      - uses: actions/upload-artifact@v4
        with:
          name: python-package-distributions
          path: dist/

  publish-to-pypi:
    name: Publish to PyPI
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/rsf
    permissions:
      id-token: write  # Required for OIDC trusted publishing
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: python-package-distributions
          path: dist/

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

### PyPI Pending Trusted Publisher Configuration
Before first release, navigate to https://pypi.org/manage/account/publishing/ and fill:
- **PyPI Project Name:** `rsf`
- **Owner:** `pgdad` (GitHub owner from `git remote -v`)
- **Repository name:** `rsf-python`
- **Workflow filename:** `release.yml`
- **Environment name:** `pypi` (optional but strongly recommended)

### Verifying Wheel Contains React Assets
```bash
# After python -m build completes locally:
unzip -l dist/rsf-*.whl | grep "editor/static"
# Should show: rsf/editor/static/index.html, rsf/editor/static/assets/*.js, rsf/editor/static/assets/*.css
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PyPI API tokens in secrets | OIDC trusted publisher (no stored token) | 2023, mature by 2024 | No secret rotation; auto-expiring tokens |
| `actions/checkout@v3` | `actions/checkout@v6` | Jan 2025 | Node.js 24 runtime |
| `actions/setup-python@v4` | `actions/setup-python@v6` | Sep 2025 | Node.js 24 runtime |
| `flake8` + `black` | `ruff` (unified linter+formatter) | 2023, standard by 2024 | Single tool, 10-100x faster |
| `python setup.py bdist_wheel` | `python -m build` (PEP 517) | 2021, universal by 2023 | Backend-agnostic; works with hatchling |
| Storing PyPI token as `PYPI_API_TOKEN` secret | No stored secrets + OIDC | 2023 | Digital attestations auto-generated with Sigstore |

**Deprecated/outdated:**
- `actions/create-release`: superseded by GitHub's built-in release creation from tags; not needed for PyPI publishing
- PyPI username/password auth: disabled
- `twine upload` with `--username __token__ --password $PYPI_TOKEN`: still works but unnecessary with OIDC action

## Open Questions

1. **Does the `rsf` project name already exist on PyPI?**
   - What we know: pyproject.toml has `name = "rsf"`. Phase 25 is marked complete.
   - What's unclear: Whether `rsf` was ever published to PyPI. If it already exists and is owned by another user, the name cannot be used.
   - Recommendation: Check https://pypi.org/project/rsf/ before configuring the trusted publisher. If taken, a name change is required.

2. **Should the release workflow also create a GitHub Release?**
   - What we know: CICD-02 only requires publishing to PyPI. The requirements do not mention GitHub Releases.
   - What's unclear: Whether the team wants release notes auto-generated on GitHub alongside the PyPI publish.
   - Recommendation: Keep it out of scope for this phase. A GitHub Release can be created manually or added to the workflow later.

3. **Node.js version to use in CI**
   - What we know: `package.json` in `ui/` uses Vite 7 and TypeScript ~5.9. No `.nvmrc` or `engines` field in `package.json`.
   - What's unclear: Whether Node 22 LTS or 20 LTS is more appropriate.
   - Recommendation: Use Node 22 (current LTS as of 2025). If build fails, fall back to 20.

## Sources

### Primary (HIGH confidence)
- https://docs.pypi.org/trusted-publishers/using-a-publisher/ — OIDC permission requirements, mandatory fields
- https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/ — Pending publisher setup for new projects
- https://github.com/pypa/gh-action-pypi-publish — Current version (release/v1, v1.13.0 Sep 2025), exact YAML syntax
- https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/ — Official 3-job workflow pattern
- https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python — Matrix builds, caching patterns
- https://hatch.pypa.io/1.13/plugins/build-hook/reference/ — Build hook API (artifacts, force_include)
- https://hatch.pypa.io/latest/config/build/ — Static file inclusion in wheels

### Secondary (MEDIUM confidence)
- https://docs.astral.sh/ruff/integrations/ — ruff GitHub Actions integration (verified against official ruff docs)
- https://github.com/actions/setup-node releases — v6 confirmed current major version
- https://github.com/actions/setup-python releases — v6 confirmed current major version (v6.2.0 Jan 2025)
- https://github.com/actions/checkout releases — v6 confirmed current major version

### Tertiary (LOW confidence)
- None — all key claims are verified against primary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Actions versions verified from official GitHub release pages; pypa action version from official repo (v1.13.0)
- Architecture: HIGH — 3-job publish pattern is the official PyPA recommendation; triggers documented in GitHub Actions docs
- Pitfalls: HIGH — fetch-depth and integration test exclusion are well-known gotchas; OIDC configuration verified against PyPI docs

**Research date:** 2026-02-28
**Valid until:** 2026-05-28 (stable domain; GitHub Actions major versions release infrequently)
