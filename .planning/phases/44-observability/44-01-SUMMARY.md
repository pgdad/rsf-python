# Plan 44-01 Summary: OpenTelemetry Tracing Injection

## Status: COMPLETE

## What was built
Conditional OpenTelemetry tracing injection in generated orchestrator code. When `tracing=True` (the default), the orchestrator template includes a try/except import for OpenTelemetry, creates parent and child spans for workflow execution and state transitions, and optionally propagates trace context for sub-workflow invocations. When OTel is not installed, the code is a no-op. Added `[tracing]` optional dependency group to pyproject.toml.

## Key files
- `src/rsf/codegen/templates/orchestrator.py.j2` -- Conditional OTel tracing blocks via Jinja2 `{% if tracing %}` tags
- `src/rsf/codegen/generator.py` -- Passes `tracing=True` and `workflow_name` to template
- `pyproject.toml` -- Added `[tracing]` optional dependency (opentelemetry-api, opentelemetry-sdk)
- `tests/test_codegen/test_otel_tracing.py` -- 22 tests covering imports, spans, propagation, and pyproject

## Test results
22/22 tests passed

## Self-Check: PASSED
- [x] All tasks executed
- [x] Tests pass
- [x] Conditional import with graceful fallback
- [x] Parent span wraps workflow, child spans per state
- [x] Sub-workflow trace context propagation
- [x] pyproject.toml has tracing extras
