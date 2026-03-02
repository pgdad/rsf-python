# Phase 44: Observability - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Generated orchestrators carry OpenTelemetry trace context for distributed tracing, users can estimate workflow costs before deploying via `rsf cost`, and an example workflow demonstrates CloudWatch custom metrics with an importable Grafana dashboard JSON. Scope is limited to these three observability features — alerting, log aggregation, and APM integrations are separate concerns.

</domain>

<decisions>
## Implementation Decisions

### Tracing injection
- Always-on: every generated orchestrator includes OpenTelemetry context injection — no DSL toggle needed
- If no OTel collector is configured at runtime, tracing is a no-op (graceful degradation)
- State-level spans: each state transition creates a child span (ValidateOrder, CheckOrderValue, etc.) under one parent span for the full execution
- Gives flamegraph-style visibility into workflow execution
- OpenTelemetry packaged as optional extra: `pip install rsf[tracing]` — conditional imports in generated code, graceful no-op if not installed
- Trace context propagates across sub-workflow invocations (Lambda-to-Lambda) — parent injects context into invoke payload, child extracts and continues the trace

### Cost estimation (`rsf cost`)
- Estimates Lambda invocations, DynamoDB reads/writes, and data transfer costs
- Hardcoded pricing defaults (us-east-1 base), user can override region via `--region`
- Static DSL analysis: parses workflow.yaml to count states, handler tasks, parallel branches, map iterations — combined with `--invocations N` flag — no deployment needed
- Output: Rich table with per-service breakdown and total by default, `--json` flag for machine-readable output
- Follows existing CLI pattern (Typer + Rich console, like logs and doctor commands)

### Metrics & dashboard
- Three core CloudWatch custom metrics: WorkflowExecutions (count), WorkflowDuration (milliseconds), WorkflowErrors (count) — dimensioned by workflow name
- Metrics emission embedded directly in generated orchestrator code (put_metric_data at workflow start/end) — not via startup hooks
- Example-only pattern: the example workflow shows how to add metrics manually; the orchestrator template does NOT include metrics by default — users copy the pattern into their own workflows
- Single Grafana overview dashboard: panels for executions over time, p50/p95/p99 duration, error rate %, table of recent errors — template variables for workflow name and time range
- Grafana only — no separate CloudWatch dashboard definition needed

### Example workflow
- Extend existing order-processing example rather than creating a new standalone example
- Demonstrates all three observability features together (tracing + metrics + cost) as a complete reference
- Dashboard JSON lives in `examples/order-processing/dashboards/grafana.json`
- Example README shows `rsf cost` output for the order-processing workflow

### Claude's Discretion
- Exact OTel span attributes and naming conventions
- CloudWatch namespace naming
- Grafana dashboard panel sizing and layout
- Cost estimation formula details and rounding
- How conditional OTel imports are structured in generated code
- Error handling in metrics emission (should not break workflow execution)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `orchestrator.py.j2` (Jinja2 template): injection point for OTel spans and metrics — extends existing template with conditional blocks
- `generator.py` / `render_orchestrator()`: pipeline for code generation, passes template variables
- `emitter.py`: per-state code emission — state-level spans could wrap each emitted block
- Existing CLI commands (`logs_cmd.py`, `doctor_cmd.py`, `export_cmd.py`): follow Typer + Rich console pattern for `rsf cost`
- `main.py`: CLI entry point — register new `cost` command following existing pattern

### Established Patterns
- CLI subcommands: `*_cmd.py` file with function registered in `main.py` via `app.command()`
- DSL parsing: `load_definition()` from `rsf.dsl.parser` returns `StateMachineDefinition`
- Code generation: Jinja2 templates in `src/rsf/codegen/templates/`, rendered via `render_template()` from `engine.py`
- Terraform state reading: `logs_cmd.py` reads `terraform.tfstate` to discover deployed resources

### Integration Points
- `orchestrator.py.j2` template: add OTel imports, span creation around state machine loop and individual states
- `generator.py` / `render_orchestrator()`: may need new template variables for tracing configuration
- `main.py`: register `cost` command
- `examples/order-processing/`: add metrics code, dashboard JSON, update README
- `pyproject.toml`: add `[tracing]` optional dependency group for opentelemetry packages

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 44-observability*
*Context gathered: 2026-03-02*
