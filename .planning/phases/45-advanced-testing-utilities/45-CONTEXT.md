# Phase 45: Advanced Testing Utilities - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Add property-based tests (Hypothesis) for I/O pipeline invariants, chaos injection utilities for simulating state failures during local test runs, and snapshot tests that compare generated orchestrator code against committed golden files. This phase covers TEST-01, TEST-02, and TEST-03.

</domain>

<decisions>
## Implementation Decisions

### Chaos injection API
- Pytest fixture pattern: tests receive a `chaos` fixture, call `chaos.inject_failure('StateName', 'timeout')`
- Four failure types: timeout, exception, throttle, plus custom callback (callable)
- Mock SDK only — inject failures during local test runs, not real infra
- Multiple failures per test supported — e.g., `chaos.inject_failure('StateA', 'timeout'); chaos.inject_failure('StateB', 'exception')`
- Exposed as public API: `rsf.testing.chaos` or `rsf.testing` — users can import for their own workflow tests

### Snapshot golden files
- Centralized storage in `tests/snapshots/` or `fixtures/snapshots/` directory
- Plain file comparison — generate orchestrator, compare against committed .py golden file with text diff. No snapshot library dependency
- Update via `--update-snapshots` pytest flag — custom conftest plugin regenerates all golden files
- All 6 example workflows covered: order-processing, data-pipeline, intrinsic-showcase, lambda-url-trigger, approval-workflow, retry-and-recovery

### Property test invariants
- Key invariants to verify:
  - ResultPath always merges into RAW input (not effective input after InputPath/Parameters)
  - Pipeline never mutates raw_input or task_result in-place
  - OutputPath output is always a valid subset of the merged result
- Custom Hypothesis strategy for generating valid JSONPath expressions ($.field, $.a.b, $.arr[0], $['key'])
- Both random data structures and realistic workflow-like data (nested dicts with order/items/status patterns)
- 200 examples per property test — balance of coverage and speed
- Additional invariants at Claude's discretion based on pipeline analysis

### Test organization
- Extend existing test directories: property tests in `tests/test_io/test_pipeline_properties.py`, snapshot tests in `tests/test_codegen/test_snapshots.py`, chaos utilities in `src/rsf/testing/`
- Always run in standard pytest suite — no markers needed (tests are fast)
- Hypothesis added as optional `testing` extra: `pip install rsf[testing]`

### Claude's Discretion
- Additional property test invariants beyond the three specified
- Internal structure of the chaos fixture (how it hooks into mock SDK)
- Exact golden file naming convention
- Hypothesis strategy details (shrinking, profiles)
- Error messages and diff formatting for snapshot failures

</decisions>

<specifics>
## Specific Ideas

- Chaos injection should feel like a natural pytest fixture — minimal ceremony to use
- Snapshot diffs should be readable in CI output — clear indication of what changed
- Property tests should catch the subtle ResultPath-merges-into-raw invariant that's easy to break

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/rsf/io/pipeline.py`: 5-stage JSONPath pipeline — the target for property testing. Clean function signature with 9 parameters.
- `tests/test_io/test_pipeline.py`: Existing handwritten unit tests — property tests complement these, don't replace them.
- `tests/test_codegen/test_generator.py`: Tests code generation logic — snapshot tests add regression protection on top.
- `tests/mock_sdk.py` + `tests/test_mock_sdk/`: Mock SDK infrastructure — chaos injection hooks into this.
- `fixtures/`: Existing directory for test fixtures (ASL files, YAML) — natural home for snapshot golden files.

### Established Patterns
- pytest with class-based test organization (TestJSONPath, TestPipeline, etc.)
- pyproject.toml uses optional dependency groups (dev, watch, tracing) — `testing` extra follows this pattern
- Examples each have workflow.yaml + handlers/ + tests/ structure

### Integration Points
- `rsf.codegen.generator.render_orchestrator()` — generates the code that snapshots will capture
- `rsf.io.pipeline.process_jsonpath_pipeline()` — the function property tests exercise
- Mock SDK execution — chaos injection modifies state behavior during mock runs
- pyproject.toml `[project.optional-dependencies]` — new `testing` extra
- CI pipeline — snapshot comparison and property tests run in standard pytest

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 45-advanced-testing-utilities*
*Context gathered: 2026-03-02*
