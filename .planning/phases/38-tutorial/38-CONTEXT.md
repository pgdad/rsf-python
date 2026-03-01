# Phase 38: Tutorial - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Add Lambda URL tutorial content to the existing documentation. Users who have completed the main tutorial can continue with steps that add a Lambda Function URL trigger, re-deploy, and invoke via curl POST.

</domain>

<decisions>
## Implementation Decisions

### Tutorial location
- Add new steps to the existing `docs/tutorial.md` as a continuation (Steps 12-14)
- Flows naturally after the existing deploy step — user already has a deployed workflow
- Keeps all tutorial content in one place, no separate document to maintain

### Content depth
- Focused 3-step addition building on the existing tutorial:
  - Step 12: Add `lambda_url` configuration to workflow YAML
  - Step 13: Re-deploy with `rsf deploy` (Terraform provisions the Lambda URL resource)
  - Step 14: Invoke via curl POST and see the durable execution trigger
- Concise, not a standalone walkthrough — assumes user completed steps 1-11

### Auth type mention
- Walkthrough uses `auth_type: NONE` (public endpoint) for simplicity
- Include a brief tip/note box mentioning `AWS_IAM` exists for production use
- Don't show the full AWS_IAM flow — users can discover it in the DSL reference

### Claude's Discretion
- Exact MkDocs admonition/tip box styling (follow existing tutorial patterns)
- Whether to show `rsf validate` output confirming lambda_url is accepted
- Exact curl command flags and formatting
- Whether to cross-reference the `examples/lambda-url-trigger/` example

</decisions>

<specifics>
## Specific Ideas

- The curl command must be copy-pasteable with a placeholder for the actual Lambda URL endpoint
- Follow the numbered step pattern established in the existing tutorial (Step 1 through Step 11)
- Use the same MkDocs admonition syntax (`!!! tip`, `!!! note`, `!!! warning`) as the existing tutorial

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/tutorial.md`: Existing 11-step tutorial to extend (Steps 1-11 cover install through inspect)
- `examples/lambda-url-trigger/`: Working example with YAML, handlers, Terraform, and tests — can reference as "see the complete example"
- MkDocs configuration already set up for docs/ directory

### Established Patterns
- Tutorial uses numbered steps: "## Step N: Action"
- Code blocks with language annotations (```yaml, ```bash, ```python)
- MkDocs admonitions for tips (`!!! tip`), notes (`!!! note`), warnings (`!!! warning`)
- Tabbed code blocks (`=== "filename"`) for showing multiple files
- Each step has a brief explanation followed by a command and expected output

### Integration Points
- `docs/tutorial.md`: New steps appended after existing Step 11
- `docs/reference/dsl.md`: May need a lambda_url section update (out of scope — note for later)
- Cross-reference to `examples/lambda-url-trigger/` README

</code_context>

<deferred>
## Deferred Ideas

- DSL reference documentation update for `lambda_url` field — separate docs phase
- Tutorial for AWS_IAM auth type with SigV4 signing — future advanced tutorial

</deferred>

---

*Phase: 38-tutorial*
*Context gathered: 2026-03-01*
