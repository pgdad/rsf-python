"""Tests for observability features in the order-processing example.

Validates:
- CloudWatch custom metrics code patterns in the orchestrator
- Grafana dashboard JSON structure and content
- README observability documentation
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

EXAMPLE_ROOT = Path(__file__).parent.parent.parent / "examples" / "order-processing"
ORCHESTRATOR_PATH = EXAMPLE_ROOT / "src" / "generated" / "orchestrator.py"
DASHBOARD_PATH = EXAMPLE_ROOT / "dashboards" / "grafana.json"
README_PATH = EXAMPLE_ROOT / "README.md"


@pytest.fixture
def orchestrator_src() -> str:
    """Read the orchestrator source code."""
    return ORCHESTRATOR_PATH.read_text()


@pytest.fixture
def dashboard() -> dict:
    """Load and parse the Grafana dashboard JSON."""
    return json.loads(DASHBOARD_PATH.read_text())


@pytest.fixture
def readme() -> str:
    """Read the README content."""
    return README_PATH.read_text()


# ---------------------------------------------------------------------------
# Metrics in orchestrator
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="CloudWatch metrics codegen not yet implemented — only OpenTelemetry tracing is generated")
class TestMetricsImports:
    """Test that the orchestrator has proper metrics imports and setup."""

    def test_boto3_cloudwatch_client(self, orchestrator_src: str):
        """Orchestrator imports boto3 and creates a CloudWatch client."""
        assert "boto3" in orchestrator_src
        assert 'client("cloudwatch")' in orchestrator_src

    def test_emit_metric_helper(self, orchestrator_src: str):
        """Orchestrator has an _emit_metric helper function."""
        assert "def _emit_metric(" in orchestrator_src

    def test_cw_namespace(self, orchestrator_src: str):
        """Orchestrator uses RSF/Workflows as the CloudWatch namespace."""
        assert 'CW_NAMESPACE = "RSF/Workflows"' in orchestrator_src

    def test_workflow_name_dimension(self, orchestrator_src: str):
        """Metrics are dimensioned by WorkflowName."""
        assert '"WorkflowName"' in orchestrator_src
        assert '"order-processing"' in orchestrator_src

    def test_emit_metric_swallows_exceptions(self, orchestrator_src: str):
        """_emit_metric swallows exceptions to avoid breaking workflow."""
        # The helper has a try/except with pass
        assert "pass  # Never break workflow execution for metrics" in orchestrator_src


@pytest.mark.skip(reason="CloudWatch metrics codegen not yet implemented — only OpenTelemetry tracing is generated")
class TestMetricsEmission:
    """Test that the three core metrics are emitted."""

    def test_workflow_executions_metric(self, orchestrator_src: str):
        """WorkflowExecutions metric is emitted at workflow start."""
        assert '"WorkflowExecutions"' in orchestrator_src

    def test_workflow_duration_metric(self, orchestrator_src: str):
        """WorkflowDuration metric is emitted at workflow end."""
        assert '"WorkflowDuration"' in orchestrator_src
        assert '"Milliseconds"' in orchestrator_src

    def test_workflow_errors_metric(self, orchestrator_src: str):
        """WorkflowErrors metric is emitted on exception."""
        assert '"WorkflowErrors"' in orchestrator_src

    def test_execution_count_at_start(self, orchestrator_src: str):
        """WorkflowExecutions is emitted with count=1 at the start."""
        assert '_emit_metric("WorkflowExecutions", 1, "Count")' in orchestrator_src

    def test_duration_uses_monotonic_timer(self, orchestrator_src: str):
        """Duration metric uses time.monotonic() for accurate timing."""
        assert "_metrics_time.monotonic()" in orchestrator_src

    def test_error_metric_in_except_block(self, orchestrator_src: str):
        """WorkflowErrors is emitted inside an except block."""
        # Find the line with WorkflowErrors and verify it's in an except context
        lines = orchestrator_src.split("\n")
        for i, line in enumerate(lines):
            if '"WorkflowErrors"' in line:
                # Look backward for the except statement
                found_except = False
                for j in range(i - 1, max(0, i - 5), -1):
                    if "except" in lines[j]:
                        found_except = True
                        break
                assert found_except, "WorkflowErrors should be inside an except block"


# ---------------------------------------------------------------------------
# Grafana dashboard
# ---------------------------------------------------------------------------


class TestDashboardStructure:
    """Test Grafana dashboard JSON structure."""

    def test_valid_json(self):
        """grafana.json is valid JSON."""
        content = DASHBOARD_PATH.read_text()
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    def test_dashboard_title(self, dashboard: dict):
        """Dashboard has a title containing RSF or Workflow."""
        title = dashboard.get("title", "")
        assert "RSF" in title or "Workflow" in title

    def test_has_four_panels(self, dashboard: dict):
        """Dashboard has exactly 4 panels."""
        panels = dashboard.get("panels", [])
        assert len(panels) == 4

    def test_tags_include_rsf(self, dashboard: dict):
        """Dashboard tags include 'rsf'."""
        tags = dashboard.get("tags", [])
        assert "rsf" in tags

    def test_refresh_interval(self, dashboard: dict):
        """Dashboard has a refresh interval set."""
        assert dashboard.get("refresh") is not None


class TestDashboardTemplateVariables:
    """Test that dashboard has required template variables."""

    def test_has_workflow_name_variable(self, dashboard: dict):
        """Dashboard has a workflow_name template variable."""
        var_names = [v["name"] for v in dashboard["templating"]["list"]]
        assert "workflow_name" in var_names

    def test_has_region_variable(self, dashboard: dict):
        """Dashboard has a region template variable."""
        var_names = [v["name"] for v in dashboard["templating"]["list"]]
        assert "region" in var_names

    def test_workflow_name_default(self, dashboard: dict):
        """workflow_name defaults to order-processing."""
        for var in dashboard["templating"]["list"]:
            if var["name"] == "workflow_name":
                assert var["current"]["text"] == "order-processing"
                break

    def test_time_range(self, dashboard: dict):
        """Dashboard has a default time range."""
        assert "time" in dashboard
        assert "from" in dashboard["time"]
        assert "to" in dashboard["time"]


class TestDashboardPanels:
    """Test individual dashboard panels."""

    def _get_panel_by_title(self, dashboard: dict, keyword: str) -> dict | None:
        """Find a panel whose title contains the keyword."""
        for panel in dashboard.get("panels", []):
            if keyword.lower() in panel.get("title", "").lower():
                return panel
        return None

    def test_executions_panel_exists(self, dashboard: dict):
        """Dashboard has a panel for WorkflowExecutions."""
        panel = self._get_panel_by_title(dashboard, "Execution")
        assert panel is not None
        assert panel["type"] == "timeseries"

    def test_duration_panel_exists(self, dashboard: dict):
        """Dashboard has a panel for WorkflowDuration with percentiles."""
        panel = self._get_panel_by_title(dashboard, "Duration")
        assert panel is not None
        assert panel["type"] == "timeseries"
        # Should have p50, p95, p99 targets
        stats = [t.get("statistics", [None])[0] for t in panel.get("targets", []) if "statistics" in t]
        assert "p50" in stats
        assert "p95" in stats
        assert "p99" in stats

    def test_error_rate_panel_exists(self, dashboard: dict):
        """Dashboard has an error rate panel."""
        panel = self._get_panel_by_title(dashboard, "Error Rate")
        assert panel is not None
        assert panel["type"] == "stat"

    def test_recent_errors_panel_exists(self, dashboard: dict):
        """Dashboard has a recent errors table panel."""
        panel = self._get_panel_by_title(dashboard, "Recent Errors")
        assert panel is not None
        assert panel["type"] == "table"

    def test_panels_use_rsf_namespace(self, dashboard: dict):
        """All metric panels reference the RSF/Workflows namespace."""
        for panel in dashboard.get("panels", []):
            for target in panel.get("targets", []):
                ns = target.get("namespace")
                if ns is not None:
                    assert ns == "RSF/Workflows"

    def test_panels_use_workflow_name_dimension(self, dashboard: dict):
        """Metric panels use the WorkflowName dimension."""
        found_dimension = False
        for panel in dashboard.get("panels", []):
            for target in panel.get("targets", []):
                dims = target.get("dimensions", {})
                if "WorkflowName" in dims:
                    found_dimension = True
                    break
        assert found_dimension, "At least one panel should use WorkflowName dimension"


# ---------------------------------------------------------------------------
# README documentation
# ---------------------------------------------------------------------------


class TestReadmeObservability:
    """Test that README documents observability features."""

    def test_observability_section(self, readme: str):
        """README has an Observability section."""
        assert "## Observability" in readme

    def test_mentions_tracing(self, readme: str):
        """README mentions OpenTelemetry tracing."""
        assert "tracing" in readme.lower() or "Tracing" in readme

    def test_mentions_metrics(self, readme: str):
        """README mentions CloudWatch metrics."""
        assert "metrics" in readme.lower() or "Metrics" in readme

    def test_mentions_cost(self, readme: str):
        """README mentions cost estimation."""
        assert "cost" in readme.lower() or "Cost" in readme

    def test_mentions_grafana(self, readme: str):
        """README mentions the Grafana dashboard."""
        assert "Grafana" in readme or "grafana" in readme

    def test_shows_rsf_cost_usage(self, readme: str):
        """README shows example rsf cost output."""
        assert "rsf cost" in readme
