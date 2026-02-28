# Phase 27: README as Landing Page - Research

**Researched:** 2026-02-28
**Domain:** Markdown README authoring, PyPI rendering, GitHub badges
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| README-01 | README includes install instructions (`pip install rsf`) | Existing README already has this; needs badge row added above it |
| README-02 | README includes quick start showing init -> generate -> deploy workflow | Existing README has Quickstart section; needs condensed "command + expected output" version for landing-page clarity |
| README-03 | README includes PyPI badge, CI status badge, and license badge | Exact badge URL formulas documented in Code Examples section |
| README-04 | README renders correctly on both GitHub and PyPI | Image absolute-URL rule and `twine check` validation documented in Pitfalls section |
</phase_requirements>

---

## Summary

Phase 27 is a focused documentation polish task: update the existing `README.md` to function as a polished landing page on both GitHub and PyPI. The README already contains install instructions and a Quickstart section from earlier phases. What is missing is (1) a badge row at the top, (2) a tighter quick-start that shows expected terminal output for each command, and (3) validation that the file renders cleanly on PyPI.

The dominant technical risk is the PyPI image rendering constraint: PyPI does not resolve relative paths. Any screenshot images embedded in the README must use absolute `raw.githubusercontent.com` URLs or they will appear broken on the PyPI project page. The existing `docs/images/` screenshots were created in Phase 24 and are available to embed — but only via absolute URLs.

Badge syntax is well-established. shields.io provides the PyPI version badge; the GitHub Actions workflow badge URL is provided by GitHub itself and requires only the workflow filename (`ci.yml`). The license badge is a static shields.io URL. All three badge types are trivially composed in Markdown as clickable image links. No new libraries or tools need to be installed.

**Primary recommendation:** Add the three-badge row immediately after the `# RSF` title, tighten the Quickstart to show one-line expected outputs per command, ensure all images use `raw.githubusercontent.com` absolute URLs, then validate with `pip install twine && twine check dist/*` before closing the phase.

---

## Standard Stack

### Core

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| shields.io | (service, no version) | Generates SVG badges for PyPI version, license | De-facto standard badge CDN; used by virtually all Python OSS projects |
| GitHub Actions badge | (built-in) | CI status badge via `badge.svg` URL | First-party; no third-party service needed |
| twine | >=3.0 | Validates README rendering before PyPI upload | Official PyPA tool; `twine check dist/*` catches render failures before publish |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| readme-renderer | (auto via twine) | Renders and validates Markdown/RST | Used internally by `twine check`; do not invoke directly |
| `pip install build` | >=0.10 | Builds wheel/sdist for twine check | Need a dist artifact to validate against |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| shields.io PyPI badge | badge.fury.io | badge.fury.io is simpler URL but shields.io is more customizable and widely used |
| shields.io license badge | Static image | shields.io reads from PyPI metadata; static image is always correct but less "live" |

**No installation required** — this phase edits `README.md` only. Validation uses twine, which should already be available or can be installed with:

```bash
pip install twine
```

---

## Architecture Patterns

### README Structure (Recommended Order)

```
README.md
├── # Title + one-line tagline
├── Badge row (PyPI version · CI · License)
├── ## What is RSF?           ← keep existing prose
├── YAML DSL code block       ← keep existing
├── ## Features               ← keep existing feature list
├── ## Quickstart             ← TIGHTEN: add expected output per command
│   ├── ### Install           ← pip install rsf (README-01)
│   ├── ### init              ← rsf init + expected output (README-02)
│   ├── ### generate          ← rsf generate + expected output
│   └── ### deploy            ← rsf deploy + expected output
├── ## Architecture           ← keep existing ASCII diagram
├── ## Documentation          ← keep existing
├── ## Technical Stack        ← keep existing table
├── ## Requirements           ← keep existing
├── ## Development            ← keep existing
└── ## License                ← keep existing
```

### Pattern 1: Badge Row

**What:** Three inline clickable badges placed between the title and the tagline (or immediately after the title).
**When to use:** Always — this is the first visible content after the project name.

```markdown
[![PyPI version](https://img.shields.io/pypi/v/rsf)](https://pypi.org/project/rsf/)
[![CI](https://github.com/pgdad/rsf-python/actions/workflows/ci.yml/badge.svg)](https://github.com/pgdad/rsf-python/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
```

- PyPI badge links to `https://pypi.org/project/rsf/`
- CI badge uses the GitHub-native badge URL: `https://github.com/pgdad/rsf-python/actions/workflows/ci.yml/badge.svg`
- License badge is a static shields.io badge (no live data lookup needed)

**Source:** GitHub Actions docs — https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/monitoring-workflows/adding-a-workflow-status-badge

### Pattern 2: Quick-Start with Expected Output

**What:** Each command block immediately followed by a fenced block showing expected terminal output.
**When to use:** For all CLI commands in the Quickstart section. Users need to know what "success looks like."

```markdown
### Create a project

```bash
rsf init my-workflow
cd my-workflow
```

```
Created project scaffold in my-workflow/
  workflow.yaml       — edit this to define your workflow
  handlers/           — handler stubs go here
```

### Generate code

```bash
rsf generate
```

```
Generated orchestrator.py
Created handlers/process_order.py
```
```

The expected output blocks use plain (unlabeled) fenced code so they render as preformatted text on both GitHub and PyPI without a syntax-highlighting language specifier.

### Pattern 3: Images with Absolute URLs

**What:** All `![alt](path)` image references must use absolute `raw.githubusercontent.com` URLs.
**When to use:** Any time a screenshot or diagram from `docs/images/` is embedded in README.

```markdown
![RSF Graph Editor](https://raw.githubusercontent.com/pgdad/rsf-python/main/docs/images/order-processing-graph.png)
```

**Note:** The README currently has no embedded images. If screenshots are added to the landing page (optional enhancement), they MUST use this absolute URL pattern.

### Anti-Patterns to Avoid

- **Relative image paths:** `![alt](docs/images/foo.png)` renders on GitHub but NOT on PyPI.
- **Relative doc links:** `[Tutorial](docs/tutorial.md)` — works on GitHub, broken on PyPI. Use full GitHub URLs: `https://github.com/pgdad/rsf-python/blob/main/docs/tutorial.md`.
- **Badge row without links:** `![badge](url)` with no wrapping link — badges should be clickable.
- **Using branch-specific commit SHA in badge URL:** The workflow badge URL uses the branch name, not a SHA. SHA-pinning breaks the badge.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Version badge | Scrape PyPI JSON and embed a version number as text | `https://img.shields.io/pypi/v/rsf` | shields.io updates in real time; hand-rolled version would require a CI step to update README on every release |
| CI status badge | Parse GitHub API for workflow run status | GitHub's native `badge.svg` URL | First-party, always current, zero maintenance |
| README rendering validation | Manually eyeball the PyPI preview | `twine check dist/*` | Automated; catches RST/Markdown errors and reports them |

**Key insight:** Shields.io and GitHub's own badge endpoint handle live data fetching. The README is static Markdown; only the badge image URL endpoints are dynamic.

---

## Common Pitfalls

### Pitfall 1: Relative Image Paths Break on PyPI

**What goes wrong:** `![Graph](docs/images/order-processing-graph.png)` renders fine on GitHub (which resolves relative paths from the repo root) but shows a broken image on the PyPI project page.
**Why it happens:** PyPI renders only the Markdown text you upload; it has no repo filesystem to resolve relative paths against.
**How to avoid:** Use `https://raw.githubusercontent.com/pgdad/rsf-python/main/docs/images/<file>.png` for every image.
**Warning signs:** After running `twine check`, image rendering issues won't be caught — twine only validates Markdown syntax, not image URL reachability. Must visually verify on PyPI after first publish.

### Pitfall 2: Relative Documentation Links Break on PyPI

**What goes wrong:** `[Tutorial](docs/tutorial.md)` appears as a dead link on the PyPI page.
**Why it happens:** Same as images — PyPI cannot resolve repo-relative paths.
**How to avoid:** Use absolute GitHub URLs: `https://github.com/pgdad/rsf-python/blob/main/docs/tutorial.md`
**Warning signs:** The existing README already has `[Tutorial](docs/tutorial.md)` — this MUST be updated.

### Pitfall 3: CI Badge Points to Wrong Workflow File

**What goes wrong:** The badge URL uses `main.yml` but the actual workflow is `ci.yml`, so the badge shows "no status."
**Why it happens:** Copy-paste from docs/examples that use different workflow filenames.
**How to avoid:** The CI workflow is at `.github/workflows/ci.yml` and the workflow `name:` is `CI`. The badge URL must be `ci.yml` (the filename), not the workflow display name.
**Badge URL:** `https://github.com/pgdad/rsf-python/actions/workflows/ci.yml/badge.svg`

### Pitfall 4: PyPI Version Badge Before First Publish

**What goes wrong:** `https://img.shields.io/pypi/v/rsf` shows "package not found" if the package has never been published.
**Why it happens:** The badge is live and queries PyPI in real time.
**How to avoid:** The badge will show correctly after the first `v*` tag triggers the release workflow. This is expected behavior — add the badge now, it will show correctly post-publish.

### Pitfall 5: README Markdown Content-Type Not Declared

**What goes wrong:** PyPI renders raw Markdown text instead of formatted HTML.
**Why it happens:** PyPI infers `text/markdown` from `.md` extension — but only if the build tool declares it correctly.
**How to avoid:** The existing `pyproject.toml` already has `readme = "README.md"`. Hatchling infers `text/markdown` from the `.md` extension automatically. No action needed.

### Pitfall 6: twine check Not Run Before Phase Close

**What goes wrong:** README has invalid Markdown that silently passes on GitHub but fails to render on PyPI (shows raw text).
**Why it happens:** GitHub's Markdown renderer is more lenient than PyPI's readme-renderer.
**How to avoid:** Run `twine check dist/*` after building to catch rendering failures. The wheel in `dist/` can be used for this without rebuilding.

---

## Code Examples

Verified patterns from official sources:

### Badge Row (place immediately after `# RSF` title line)

```markdown
<!-- Source: GitHub Actions docs + shields.io -->
[![PyPI version](https://img.shields.io/pypi/v/rsf)](https://pypi.org/project/rsf/)
[![CI](https://github.com/pgdad/rsf-python/actions/workflows/ci.yml/badge.svg)](https://github.com/pgdad/rsf-python/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
```

### Converting Relative Doc Links to Absolute

```markdown
<!-- BEFORE (broken on PyPI): -->
[Tutorial](docs/tutorial.md)
[DSL Reference](docs/reference/dsl.md)
[Migration Guide](docs/migration-guide.md)

<!-- AFTER (works on both GitHub and PyPI): -->
[Tutorial](https://github.com/pgdad/rsf-python/blob/main/docs/tutorial.md)
[DSL Reference](https://github.com/pgdad/rsf-python/blob/main/docs/reference/dsl.md)
[Migration Guide](https://github.com/pgdad/rsf-python/blob/main/docs/migration-guide.md)
```

### Embedding Screenshots (Absolute URL Pattern)

```markdown
<!-- Source: packaging.python.org + glasnt.com/blog/new-images -->
![RSF Graph Editor](https://raw.githubusercontent.com/pgdad/rsf-python/main/docs/images/order-processing-graph.png)
![RSF Execution Inspector](https://raw.githubusercontent.com/pgdad/rsf-python/main/docs/images/order-processing-inspector.png)
```

### Validating README Rendering

```bash
# Source: packaging.python.org/en/latest/guides/making-a-pypi-friendly-readme/
pip install twine
twine check dist/rsf-*.whl
# Expected output: PASSED
```

### Quick-Start Command + Output Pattern

```markdown
### Install

```bash
pip install rsf
```

### Create your first workflow

```bash
rsf init my-workflow
cd my-workflow
```

```
Initialized new RSF project in my-workflow/
  workflow.yaml — define your states here
```

### Generate Python code

```bash
rsf generate
```

```
Generated orchestrator.py from workflow.yaml
Created handlers/start.py — add your business logic here
```

### Deploy to AWS

```bash
rsf deploy
```

```
Applying Terraform... done
Lambda function deployed: my-workflow-orchestrator
```
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Manual version in README (`v1.5.0`) | Live shields.io PyPI badge | Always been available; now standard | Version auto-updates on publish; no manual README edits per release |
| Travis CI badge | GitHub Actions native badge | ~2019 when GHA launched | First-party badge, no third-party service |
| `setup.py` long_description | `pyproject.toml` `readme = "README.md"` | PEP 621, ~2021 | No code changes needed; hatchling auto-infers content-type |

**Deprecated/outdated:**
- Travis CI badges (`travis-ci.org/...`): Use GitHub Actions badge instead
- `setup.py` `long_description_content_type='text/markdown'`: Handled by `pyproject.toml` `readme = "README.md"` with hatchling

---

## Open Questions

1. **Should screenshots from docs/images/ be embedded in the README?**
   - What we know: 15 high-quality screenshots exist in `docs/images/`, created in Phase 24
   - What's unclear: Whether the README should show 1-2 hero shots or stay text-only to keep the landing page fast-loading
   - Recommendation: Add one graph editor and one inspector screenshot as "hero images" to make the landing page visual; use absolute raw.githubusercontent.com URLs

2. **Will the PyPI version badge show before first publish?**
   - What we know: The badge queries PyPI live; `rsf` package has not been published yet (no `rsf` found on pypi.org)
   - What's unclear: Whether to use a "build passing" placeholder until first publish
   - Recommendation: Add the badge as-is; it will show "not found" until first publish but that is acceptable — the badge will activate automatically when the release workflow runs

3. **Are there GitHub repository visibility considerations?**
   - What we know: Remote is `git@github.com:pgdad/rsf-python.git` (private vs public unknown)
   - What's unclear: If the repo is private, CI badges will not be visible to unauthenticated users on PyPI
   - Recommendation: Assume public; if private, the CI badge must be omitted from PyPI README (it will show nothing)

---

## Sources

### Primary (HIGH confidence)

- GitHub Docs — https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/monitoring-workflows/adding-a-workflow-status-badge — Exact badge URL format for GitHub Actions
- Python Packaging User Guide — https://packaging.python.org/en/latest/guides/making-a-pypi-friendly-readme/ — PyPI README requirements, twine check validation
- shields.io — https://shields.io/badges/py-pi-version — PyPI version badge URL format

### Secondary (MEDIUM confidence)

- glasnt.com/blog/new-images — PyPI image rendering with absolute raw.githubusercontent.com URLs (verified against known-correct pattern in pypi/warehouse issues)
- pypi/warehouse GitHub Issue #5246 — Confirms markdown images are not rendered from relative paths on PyPI

### Tertiary (LOW confidence)

- Various community blog posts about badge best practices — general guidance verified against official shields.io docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — badge URLs from official GitHub docs and shields.io directly
- Architecture: HIGH — README structure is direct editing of existing file; no new tooling
- Pitfalls: HIGH — PyPI image rendering limitation is documented in official packaging guide and confirmed in multiple sources

**Research date:** 2026-02-28
**Valid until:** 2026-04-01 (stable domain — badge URL formats change rarely)
