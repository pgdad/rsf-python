"""Local tests for the lambda-url-trigger example.

Tests cover:
1. Workflow YAML parsing via rsf.dsl.parser.load_definition
2. Lambda URL feature validation (enabled, auth_type)
3. Individual handler unit tests (valid and invalid inputs)
4. Full workflow simulation using MockDurableContext:
   ValidateOrder -> ProcessOrder -> OrderComplete
"""

from pathlib import Path

import pytest

from rsf.dsl.parser import load_definition
from rsf.dsl.models import (
    SucceedState,
    TaskState,
)
from rsf.dsl.types import LambdaUrlAuthType
from rsf.registry import discover_handlers, get_handler

from mock_sdk import MockDurableContext


WORKFLOW_PATH = Path(__file__).parent.parent / "workflow.yaml"
HANDLERS_DIR = Path(__file__).parent.parent / "handlers"


# ---------------------------------------------------------------------------
# 1. Workflow YAML Parsing Tests
# ---------------------------------------------------------------------------


class TestWorkflowParsing:
    """Verify that workflow.yaml is valid and parses into the expected model."""

    def test_load_definition_succeeds(self):
        """workflow.yaml should parse without errors."""
        defn = load_definition(WORKFLOW_PATH)
        assert defn is not None

    def test_start_at(self):
        """StartAt should be ValidateOrder."""
        defn = load_definition(WORKFLOW_PATH)
        assert defn.start_at == "ValidateOrder"

    def test_rsf_version(self):
        """rsf_version should be 1.0."""
        defn = load_definition(WORKFLOW_PATH)
        assert defn.rsf_version == "1.0"

    def test_all_states_present(self):
        """All three states should be present in the definition."""
        defn = load_definition(WORKFLOW_PATH)
        expected_states = {
            "ValidateOrder",
            "ProcessOrder",
            "OrderComplete",
        }
        assert set(defn.states.keys()) == expected_states

    def test_state_types(self):
        """Verify each state has the correct type."""
        defn = load_definition(WORKFLOW_PATH)
        assert isinstance(defn.states["ValidateOrder"], TaskState)
        assert isinstance(defn.states["ProcessOrder"], TaskState)
        assert isinstance(defn.states["OrderComplete"], SucceedState)

    def test_state_transitions(self):
        """Verify state transition chain: ValidateOrder -> ProcessOrder -> OrderComplete."""
        defn = load_definition(WORKFLOW_PATH)
        assert defn.states["ValidateOrder"].next == "ProcessOrder"
        assert defn.states["ProcessOrder"].next == "OrderComplete"


# ---------------------------------------------------------------------------
# 2. Lambda URL Feature Tests
# ---------------------------------------------------------------------------


class TestLambdaUrlFeature:
    """Verify that the workflow includes correct lambda_url configuration."""

    def test_lambda_url_present(self):
        """lambda_url configuration should be present in the definition."""
        defn = load_definition(WORKFLOW_PATH)
        assert defn.lambda_url is not None

    def test_lambda_url_enabled(self):
        """lambda_url should be enabled."""
        defn = load_definition(WORKFLOW_PATH)
        assert defn.lambda_url.enabled is True

    def test_lambda_url_auth_type(self):
        """lambda_url auth_type should be NONE."""
        defn = load_definition(WORKFLOW_PATH)
        assert defn.lambda_url.auth_type == LambdaUrlAuthType.NONE


# ---------------------------------------------------------------------------
# 3. Handler Unit Tests
# ---------------------------------------------------------------------------


class TestValidateOrderHandler:
    """Unit tests for the ValidateOrder handler."""

    def test_valid_order(self):
        """Valid order should return validation result with correct fields."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ValidateOrder")

        result = handler({
            "orderId": "test-001",
            "items": [{"name": "Widget", "price": 29.99, "quantity": 2}],
            "total": 59.98,
        })

        assert result["valid"] is True
        assert result["orderId"] == "test-001"
        assert result["itemCount"] == 1
        assert result["total"] == 59.98

    def test_multiple_items(self):
        """Order with multiple items should report correct item count."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ValidateOrder")

        result = handler({
            "orderId": "test-002",
            "items": [
                {"name": "Widget A", "price": 10.00, "quantity": 1},
                {"name": "Widget B", "price": 20.00, "quantity": 3},
            ],
            "total": 70.00,
        })

        assert result["valid"] is True
        assert result["itemCount"] == 2

    def test_empty_items_raises(self):
        """Order with empty items list should raise an error."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ValidateOrder")

        with pytest.raises(Exception, match="at least one item"):
            handler({
                "orderId": "test-003",
                "items": [],
                "total": 0,
            })

    def test_negative_total_raises(self):
        """Order with negative total should raise an error."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ValidateOrder")

        with pytest.raises(Exception, match="not be negative"):
            handler({
                "orderId": "test-004",
                "items": [{"name": "Widget", "price": 10.00, "quantity": 1}],
                "total": -5.00,
            })

    def test_non_list_items_raises(self):
        """Order with non-list items should raise an error."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ValidateOrder")

        with pytest.raises(Exception, match="must be a list"):
            handler({
                "orderId": "test-005",
                "items": "not a list",
                "total": 10.00,
            })

    def test_non_numeric_total_raises(self):
        """Order with non-numeric total should raise an error."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ValidateOrder")

        with pytest.raises(Exception, match="must be a number"):
            handler({
                "orderId": "test-006",
                "items": [{"name": "Widget", "price": 10.00, "quantity": 1}],
                "total": "not a number",
            })


class TestProcessOrderHandler:
    """Unit tests for the ProcessOrder handler."""

    def test_process_valid_order(self):
        """ProcessOrder should return processed result with correct fields."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ProcessOrder")

        result = handler({
            "orderId": "test-001",
            "total": 59.98,
            "itemCount": 1,
        })

        assert result["processed"] is True
        assert result["orderId"] == "test-001"
        assert result["status"] == "completed"
        assert result["total"] == 59.98
        assert result["itemCount"] == 1

    def test_process_defaults(self):
        """ProcessOrder should handle missing fields gracefully with defaults."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ProcessOrder")

        result = handler({})

        assert result["processed"] is True
        assert result["orderId"] == "unknown"
        assert result["status"] == "completed"


# ---------------------------------------------------------------------------
# 4. Full Workflow Simulation
# ---------------------------------------------------------------------------


class TestWorkflowSimulation:
    """Simulate the full workflow using MockDurableContext.

    Expected path:
    ValidateOrder -> ProcessOrder -> OrderComplete (Succeed)
    """

    def test_happy_path(self):
        """Full workflow should validate, process, and complete an order."""
        discover_handlers(HANDLERS_DIR)
        ctx = MockDurableContext()

        order_input = {
            "orderId": "order-sim-001",
            "items": [
                {"name": "Widget", "price": 29.99, "quantity": 2},
            ],
            "total": 59.98,
        }

        # Step 1: ValidateOrder
        validate_handler = get_handler("ValidateOrder")
        validation_result = ctx.step("ValidateOrder", validate_handler, order_input)
        assert validation_result["valid"] is True
        assert validation_result["orderId"] == "order-sim-001"
        assert validation_result["itemCount"] == 1
        assert validation_result["total"] == 59.98

        # Merge validation into state (simulating ResultPath behavior)
        state_data = {**order_input, "validation": validation_result}

        # Step 2: ProcessOrder
        process_handler = get_handler("ProcessOrder")
        process_result = ctx.step("ProcessOrder", process_handler, state_data)
        assert process_result["processed"] is True
        assert process_result["orderId"] == "order-sim-001"
        assert process_result["status"] == "completed"

        # Step 3: OrderComplete (Succeed state — no handler, terminal)
        # Verify the workflow recorded the expected SDK calls
        assert len(ctx.calls) == 2  # ValidateOrder, ProcessOrder
        assert ctx.calls[0].name == "ValidateOrder"
        assert ctx.calls[0].operation == "step"
        assert ctx.calls[1].name == "ProcessOrder"
        assert ctx.calls[1].operation == "step"

    def test_simulation_records_input_data(self):
        """MockDurableContext should record input data for each step."""
        discover_handlers(HANDLERS_DIR)
        ctx = MockDurableContext()

        order_input = {
            "orderId": "order-sim-002",
            "items": [{"name": "Gadget", "price": 15.00, "quantity": 1}],
            "total": 15.00,
        }

        validate_handler = get_handler("ValidateOrder")
        ctx.step("ValidateOrder", validate_handler, order_input)

        # Verify input was recorded
        assert ctx.calls[0].input_data["orderId"] == "order-sim-002"
        assert ctx.calls[0].input_data["total"] == 15.00
