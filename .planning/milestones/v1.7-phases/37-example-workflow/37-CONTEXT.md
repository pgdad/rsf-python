# Phase 37: Example Workflow - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Create a working example in `examples/lambda-url-trigger/` that demonstrates triggering a durable execution via HTTP POST to a Lambda Function URL. Includes DSL YAML, Python handlers, Terraform, local tests, and a real-AWS integration test.

</domain>

<decisions>
## Implementation Decisions

### Workflow scenario
- Webhook receiver pattern: receive an order event via HTTP POST, process it through a multi-step workflow
- Order event payload: `{orderId, items, total}` — familiar business domain, easy to understand
- 3 states: ValidateOrder (Task) -> ProcessOrder (Task) -> OrderComplete (Pass)
- Focused enough to highlight the Lambda URL trigger feature without overshadowing it

### Auth type
- Use `auth_type: NONE` (public endpoint) for simplicity
- No need to demonstrate AWS_IAM in this example — users can see that option in the DSL validation tests from Phase 36

### Integration test design
- POST to the Lambda Function URL, then poll Step Functions until execution completes
- Verify final output matches expected processed order result
- Mark integration test with `@pytest.mark.integration` so it's excluded from `pytest -m "not integration"`

### Claude's Discretion
- Exact handler implementation details (validation logic, processing logic)
- README structure and depth (follow existing example READMEs as template)
- Terraform resource naming conventions (follow existing example patterns)
- conftest.py and test fixture design

</decisions>

<specifics>
## Specific Ideas

- Follow the established example directory structure: workflow.yaml, handlers/, terraform/, tests/test_local.py, README.md
- Local tests should use `MockDurableContext` from `mock_sdk` consistent with other examples
- The `workflow.yaml` must include `lambda_url: {enabled: true, auth_type: NONE}` to exercise the Phase 36 DSL feature
- Integration test should use `requests` library for the HTTP POST

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MockDurableContext` from `mock_sdk`: Used by all existing examples for local testing simulation
- `rsf.dsl.parser.load_definition`: Standard way to parse workflow YAML in tests
- `LambdaUrlConfig` and `LambdaUrlAuthType` from `rsf.dsl`: Phase 36 DSL models for lambda_url configuration
- `lambda_url.tf.j2`, `iam.tf.j2`, `outputs.tf.j2`: Phase 36 Terraform templates that handle lambda_url generation

### Established Patterns
- All examples use the same directory structure: workflow.yaml, handlers/, terraform/, tests/, README.md
- Test files follow a 4-section pattern: 1) Workflow parsing, 2) Handler unit tests, 3) Feature-specific tests, 4) Full simulation with MockDurableContext
- Handlers are simple Python functions that take a dict and return a dict
- Terraform directories contain standalone configs (backend.tf, main.tf, variables.tf, outputs.tf, versions.tf)

### Integration Points
- `examples/` directory: New `lambda-url-trigger/` alongside existing examples
- `rsf generate` + `rsf deploy` pipeline: Example Terraform should be producible from the workflow YAML
- pytest configuration: Integration tests use `@pytest.mark.integration` marker

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 37-example-workflow*
*Context gathered: 2026-03-01*
