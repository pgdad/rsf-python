"""Tests for OpenTelemetry tracing injection in generated orchestrator code."""

from __future__ import annotations

import tomllib
from pathlib import Path

from rsf.codegen.engine import render_template


def _render_with_tracing(**overrides):
    """Helper to render orchestrator template with tracing enabled."""
    defaults = {
        "rsf_version": "test",
        "timestamp": "2026-03-02T00:00:00Z",
        "dsl_file": "workflow.yaml",
        "dsl_hash": "abc123",
        "start_at": "StartState",
        "state_blocks": [],
        "handler_imports": [],
        "mappings": [],
        "timeout_seconds": None,
        "has_sub_workflows": False,
        "sub_workflow_names": [],
        "tracing": True,
        "workflow_name": "test-workflow",
    }
    defaults.update(overrides)
    return render_template("orchestrator.py.j2", **defaults)


def _render_without_tracing(**overrides):
    """Helper to render orchestrator template with tracing disabled."""
    defaults = {
        "rsf_version": "test",
        "timestamp": "2026-03-02T00:00:00Z",
        "dsl_file": "workflow.yaml",
        "dsl_hash": "abc123",
        "start_at": "StartState",
        "state_blocks": [],
        "handler_imports": [],
        "mappings": [],
        "timeout_seconds": None,
        "has_sub_workflows": False,
        "sub_workflow_names": [],
        "tracing": False,
        "workflow_name": "test-workflow",
    }
    defaults.update(overrides)
    return render_template("orchestrator.py.j2", **defaults)


class TestOtelConditionalImport:
    """Test that OTel imports are conditional and graceful."""

    def test_tracing_enabled_includes_otel_import(self):
        code = _render_with_tracing()
        assert "from opentelemetry import trace as _otel_trace" in code

    def test_tracing_disabled_excludes_otel_import(self):
        code = _render_without_tracing()
        assert "opentelemetry" not in code

    def test_otel_available_flag_set(self):
        code = _render_with_tracing()
        assert "_OTEL_AVAILABLE = True" in code
        assert "_OTEL_AVAILABLE = False" in code  # In except branch

    def test_tracer_created_with_correct_name(self):
        code = _render_with_tracing()
        assert '_tracer = _otel_trace.get_tracer("rsf.workflow")' in code

    def test_import_error_caught(self):
        code = _render_with_tracing()
        assert "except ImportError:" in code


class TestParentSpan:
    """Test that parent span wraps the entire workflow execution."""

    def test_parent_span_created(self):
        code = _render_with_tracing()
        assert 'start_span(\n            "workflow.execute"' in code or 'start_span("workflow.execute"' in code

    def test_parent_span_has_workflow_name_attribute(self):
        code = _render_with_tracing()
        assert '"workflow.name"' in code

    def test_parent_span_has_start_at_attribute(self):
        code = _render_with_tracing()
        assert '"workflow.start_at"' in code

    def test_parent_span_workflow_name_value(self):
        code = _render_with_tracing(workflow_name="order-processing")
        assert "'order-processing'" in code

    def test_parent_span_start_at_value(self):
        code = _render_with_tracing(start_at="ValidateOrder")
        assert "'ValidateOrder'" in code


class TestChildSpans:
    """Test that child spans are created for each state transition."""

    def test_state_span_created(self):
        code = _render_with_tracing()
        assert "_state_span = _tracer.start_span(" in code

    def test_state_span_has_name_attribute(self):
        code = _render_with_tracing()
        assert '"state.name": current_state' in code

    def test_state_span_cleanup_in_finally(self):
        code = _render_with_tracing()
        assert "_state_span.__exit__(None, None, None)" in code


class TestErrorHandling:
    """Test that tracing handles errors correctly."""

    def test_error_status_set_on_exception(self):
        code = _render_with_tracing()
        assert "_OtelStatusCode.ERROR" in code

    def test_parent_span_closed_in_finally(self):
        code = _render_with_tracing()
        assert "_wf_span.__exit__(None, None, None)" in code

    def test_workflow_still_works_without_otel(self):
        """When tracing=False, no OTel code exists — workflow runs normally."""
        code = _render_without_tracing()
        assert "lambda_handler" in code
        assert "current_state" in code
        assert "_OTEL_AVAILABLE" not in code
        assert "_tracer" not in code


class TestSubWorkflowPropagation:
    """Test trace context propagation across sub-workflow invocations."""

    def test_propagate_import_when_sub_workflows(self):
        code = _render_with_tracing(has_sub_workflows=True)
        assert "from opentelemetry import propagate as _otel_propagate" in code

    def test_no_propagate_import_without_sub_workflows(self):
        code = _render_with_tracing(has_sub_workflows=False)
        assert "_otel_propagate" not in code

    def test_trace_context_extraction_from_event(self):
        code = _render_with_tracing(has_sub_workflows=True)
        assert '_otel_propagate.extract(event["_trace_context"])' in code

    def test_no_trace_context_extraction_without_sub_workflows(self):
        code = _render_with_tracing(has_sub_workflows=False)
        assert "_trace_context" not in code


class TestPyprojectTracing:
    """Test that pyproject.toml has the tracing optional dependency."""

    def test_tracing_optional_dependency_exists(self):
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            cfg = tomllib.load(f)
        optional_deps = cfg["project"]["optional-dependencies"]
        assert "tracing" in optional_deps

    def test_tracing_includes_opentelemetry_api(self):
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            cfg = tomllib.load(f)
        tracing_deps = cfg["project"]["optional-dependencies"]["tracing"]
        assert any("opentelemetry-api" in d for d in tracing_deps)

    def test_tracing_includes_opentelemetry_sdk(self):
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            cfg = tomllib.load(f)
        tracing_deps = cfg["project"]["optional-dependencies"]["tracing"]
        assert any("opentelemetry-sdk" in d for d in tracing_deps)
