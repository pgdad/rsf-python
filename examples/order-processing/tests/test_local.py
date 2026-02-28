"""Local tests for the order-processing example.

Tests cover:
1. Workflow YAML parsing via rsf.dsl.parser.load_definition
2. Individual handler unit tests (valid and invalid inputs)
3. Full workflow simulation using MockDurableContext:
   - Standard order (total <= 1000):
     ValidateOrder -> CheckOrderValue -> ProcessOrder -> SendConfirmation -> OrderComplete
   - High-value order (total > 1000):
     ValidateOrder -> CheckOrderValue -> RequireApproval -> ProcessOrder ->
     SendConfirmation -> OrderComplete
"""

from pathlib import Path

import pytest

from rsf.dsl.parser import load_definition
from rsf.dsl.models import (
    ChoiceState,
    FailState,
    ParallelState,
    SucceedState,
    TaskState,
)
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
        """All seven states should be present in the definition."""
        defn = load_definition(WORKFLOW_PATH)
        expected_states = {
            "ValidateOrder",
            "CheckOrderValue",
            "RequireApproval",
            "ProcessOrder",
            "SendConfirmation",
            "OrderComplete",
            "OrderRejected",
        }
        assert set(defn.states.keys()) == expected_states

    def test_state_types(self):
        """Verify each state has the correct type."""
        defn = load_definition(WORKFLOW_PATH)
        assert isinstance(defn.states["ValidateOrder"], TaskState)
        assert isinstance(defn.states["CheckOrderValue"], ChoiceState)
        assert isinstance(defn.states["RequireApproval"], TaskState)
        assert isinstance(defn.states["ProcessOrder"], ParallelState)
        assert isinstance(defn.states["SendConfirmation"], TaskState)
        assert isinstance(defn.states["OrderComplete"], SucceedState)
        assert isinstance(defn.states["OrderRejected"], FailState)

    def test_validate_order_retry_config(self):
        """ValidateOrder should have a retry policy for ValidationTimeout."""
        defn = load_definition(WORKFLOW_PATH)
        state = defn.states["ValidateOrder"]
        assert state.retry is not None
        assert len(state.retry) == 1
        retry = state.retry[0]
        assert "ValidationTimeout" in retry.error_equals
        assert retry.interval_seconds == 2
        assert retry.max_attempts == 3
        assert retry.backoff_rate == 2.0

    def test_validate_order_catch_config(self):
        """ValidateOrder should catch InvalidOrderError and route to OrderRejected."""
        defn = load_definition(WORKFLOW_PATH)
        state = defn.states["ValidateOrder"]
        assert state.catch is not None
        assert len(state.catch) == 1
        catcher = state.catch[0]
        assert "InvalidOrderError" in catcher.error_equals
        assert catcher.next == "OrderRejected"

    def test_choice_state_rules(self):
        """CheckOrderValue should have two choice rules and a default."""
        defn = load_definition(WORKFLOW_PATH)
        state = defn.states["CheckOrderValue"]
        assert len(state.choices) == 2
        assert state.default == "ProcessOrder"

    def test_parallel_state_branches(self):
        """ProcessOrder should have two parallel branches."""
        defn = load_definition(WORKFLOW_PATH)
        state = defn.states["ProcessOrder"]
        assert len(state.branches) == 2

    def test_fail_state_error(self):
        """OrderRejected should have error and cause set."""
        defn = load_definition(WORKFLOW_PATH)
        state = defn.states["OrderRejected"]
        assert state.error == "OrderRejected"
        assert state.cause == "Order could not be processed"


# ---------------------------------------------------------------------------
# 2. Individual Handler Unit Tests
# ---------------------------------------------------------------------------


class TestValidateOrderHandler:
    """Unit tests for the ValidateOrder handler."""

    def test_valid_order(self):
        """A valid order should return valid=True with correct total and itemCount."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ValidateOrder")
        result = handler(
            {
                "orderId": "order-001",
                "items": [
                    {"itemId": "item-1", "quantity": 2},
                    {"itemId": "item-2", "quantity": 1},
                ],
                "total": 150.00,
            }
        )
        assert result["valid"] is True
        assert result["total"] == 150.00
        assert result["itemCount"] == 2

    def test_empty_items(self):
        """An order with empty items list should still validate but with itemCount=0."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ValidateOrder")
        result = handler({"orderId": "order-002", "items": [], "total": 0})
        assert result["valid"] is True
        assert result["itemCount"] == 0

    def test_invalid_items_not_list(self):
        """An order with non-list items should raise InvalidOrderError."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ValidateOrder")
        with pytest.raises(Exception, match="items must be a list"):
            handler({"orderId": "order-003", "items": "not-a-list", "total": 10})

    def test_negative_total(self):
        """An order with a negative total should raise InvalidOrderError."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ValidateOrder")
        with pytest.raises(Exception, match="must not be negative"):
            handler({"orderId": "order-004", "items": [{"itemId": "x"}], "total": -5})

    def test_non_numeric_total(self):
        """An order with a non-numeric total should raise InvalidOrderError."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ValidateOrder")
        with pytest.raises(Exception, match="must be a number"):
            handler({"orderId": "order-005", "items": [{"itemId": "x"}], "total": "abc"})

    def test_high_value_order(self):
        """A high-value order (total > 1000) should validate normally."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ValidateOrder")
        result = handler(
            {
                "orderId": "order-006",
                "items": [{"itemId": "expensive", "quantity": 1}],
                "total": 5000.00,
            }
        )
        assert result["valid"] is True
        assert result["total"] == 5000.00


class TestRequireApprovalHandler:
    """Unit tests for the RequireApproval handler."""

    def test_approval_granted(self):
        """An order within limits should be approved."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("RequireApproval")
        result = handler(
            {
                "orderId": "order-010",
                "validation": {"total": 2000, "itemCount": 3},
            }
        )
        assert result["approved"] is True
        assert "approver" in result

    def test_approval_denied_high_value(self):
        """An order exceeding 10000 should be denied."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("RequireApproval")
        with pytest.raises(Exception, match="exceeds auto-approval limit"):
            handler(
                {
                    "orderId": "order-011",
                    "validation": {"total": 15000, "itemCount": 1},
                }
            )


class TestProcessPaymentHandler:
    """Unit tests for the ProcessPayment handler."""

    def test_payment_success(self):
        """Payment processing should return a transaction ID and completed status."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ProcessPayment")
        result = handler(
            {
                "orderId": "order-020",
                "validation": {"total": 200, "itemCount": 2},
                "paymentMethod": "credit_card",
            }
        )
        assert result["status"] == "completed"
        assert "transactionId" in result
        assert result["amount"] == 200
        assert result["paymentMethod"] == "credit_card"


class TestReserveInventoryHandler:
    """Unit tests for the ReserveInventory handler."""

    def test_reservation_success(self):
        """Inventory reservation should reserve all items."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ReserveInventory")
        result = handler(
            {
                "orderId": "order-030",
                "items": [
                    {"itemId": "item-A", "quantity": 3},
                    {"itemId": "item-B", "quantity": 1},
                ],
            }
        )
        assert result["status"] == "reserved"
        assert "reservationId" in result
        assert len(result["items"]) == 2
        assert all(item["reserved"] is True for item in result["items"])

    def test_empty_items_reservation(self):
        """Reserving with no items should still succeed with empty items list."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ReserveInventory")
        result = handler({"orderId": "order-031", "items": []})
        assert result["status"] == "reserved"
        assert len(result["items"]) == 0


class TestSendConfirmationHandler:
    """Unit tests for the SendConfirmation handler."""

    def test_confirmation_generated(self):
        """Confirmation should generate a number and flag email as sent."""
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("SendConfirmation")
        result = handler(
            {
                "orderId": "order-040",
                "customerEmail": "test@example.com",
            }
        )
        assert result["emailSent"] is True
        assert result["confirmationNumber"].startswith("ORD-")
        assert result["recipientEmail"] == "test@example.com"


# ---------------------------------------------------------------------------
# 3. Full Workflow Simulation Tests
# ---------------------------------------------------------------------------


class TestStandardOrderWorkflow:
    """Simulate a standard order (total <= 1000) through the full workflow.

    Expected path:
    ValidateOrder -> CheckOrderValue -> ProcessOrder (Parallel) -> SendConfirmation -> OrderComplete
    """

    def test_standard_order_flow(self):
        """Standard order should skip RequireApproval and reach OrderComplete."""
        discover_handlers(HANDLERS_DIR)
        ctx = MockDurableContext()

        order_input = {
            "orderId": "order-100",
            "items": [
                {"itemId": "widget-A", "quantity": 2},
                {"itemId": "widget-B", "quantity": 1},
            ],
            "total": 250.00,
            "customerEmail": "buyer@example.com",
            "paymentMethod": "credit_card",
        }

        # Step 1: ValidateOrder
        validate_handler = get_handler("ValidateOrder")
        validation_result = ctx.step("ValidateOrder", validate_handler, order_input)
        assert validation_result["valid"] is True
        assert validation_result["total"] == 250.00
        assert validation_result["itemCount"] == 2

        # Merge validation into state
        state_data = {**order_input, "validation": validation_result}

        # Step 2: CheckOrderValue — total is 250, so default -> ProcessOrder
        # (Choice is evaluated by the orchestrator, not a handler; we simulate the decision)
        assert state_data["validation"]["total"] <= 1000
        # Choice selects "ProcessOrder" (default path)

        # Step 3: ProcessOrder (Parallel) — ProcessPayment + ReserveInventory
        payment_handler = get_handler("ProcessPayment")
        inventory_handler = get_handler("ReserveInventory")

        parallel_result = ctx.parallel(
            "ProcessOrder",
            [payment_handler, inventory_handler],
            state_data,
        )
        results = parallel_result.get_results()
        assert len(results) == 2
        assert results[0]["status"] == "completed"  # payment
        assert results[1]["status"] == "reserved"  # inventory

        state_data["processing"] = results

        # Step 4: SendConfirmation
        confirmation_handler = get_handler("SendConfirmation")
        confirmation_result = ctx.step("SendConfirmation", confirmation_handler, state_data)
        assert confirmation_result["emailSent"] is True
        assert confirmation_result["confirmationNumber"].startswith("ORD-")

        state_data["confirmation"] = confirmation_result

        # Step 5: OrderComplete (Succeed state — no handler, just terminal)
        # Verify the workflow recorded the expected SDK calls
        assert len(ctx.calls) == 3  # ValidateOrder, ProcessOrder, SendConfirmation
        assert ctx.calls[0].name == "ValidateOrder"
        assert ctx.calls[0].operation == "step"
        assert ctx.calls[1].name == "ProcessOrder"
        assert ctx.calls[1].operation == "parallel"
        assert ctx.calls[2].name == "SendConfirmation"
        assert ctx.calls[2].operation == "step"


class TestHighValueOrderWorkflow:
    """Simulate a high-value order (total > 1000) through the full workflow.

    Expected path:
    ValidateOrder -> CheckOrderValue -> RequireApproval -> ProcessOrder (Parallel) -> SendConfirmation -> OrderComplete
    """

    def test_high_value_order_flow(self):
        """High-value order should go through RequireApproval before processing."""
        discover_handlers(HANDLERS_DIR)
        ctx = MockDurableContext()

        order_input = {
            "orderId": "order-200",
            "items": [
                {"itemId": "premium-gadget", "quantity": 1},
                {"itemId": "luxury-case", "quantity": 2},
            ],
            "total": 3500.00,
            "customerEmail": "vip@example.com",
            "paymentMethod": "wire_transfer",
        }

        # Step 1: ValidateOrder
        validate_handler = get_handler("ValidateOrder")
        validation_result = ctx.step("ValidateOrder", validate_handler, order_input)
        assert validation_result["valid"] is True
        assert validation_result["total"] == 3500.00

        state_data = {**order_input, "validation": validation_result}

        # Step 2: CheckOrderValue — total is 3500, so -> RequireApproval
        assert state_data["validation"]["total"] > 1000
        # Choice selects "RequireApproval"

        # Step 3: RequireApproval
        approval_handler = get_handler("RequireApproval")
        approval_result = ctx.step("RequireApproval", approval_handler, state_data)
        assert approval_result["approved"] is True

        state_data["approval"] = approval_result

        # Step 4: ProcessOrder (Parallel)
        payment_handler = get_handler("ProcessPayment")
        inventory_handler = get_handler("ReserveInventory")

        parallel_result = ctx.parallel(
            "ProcessOrder",
            [payment_handler, inventory_handler],
            state_data,
        )
        results = parallel_result.get_results()
        assert len(results) == 2
        assert results[0]["status"] == "completed"
        assert results[1]["status"] == "reserved"

        state_data["processing"] = results

        # Step 5: SendConfirmation
        confirmation_handler = get_handler("SendConfirmation")
        confirmation_result = ctx.step("SendConfirmation", confirmation_handler, state_data)
        assert confirmation_result["emailSent"] is True

        state_data["confirmation"] = confirmation_result

        # Step 6: OrderComplete (Succeed state — terminal)
        # Verify the workflow recorded the expected SDK calls
        assert len(ctx.calls) == 4  # ValidateOrder, RequireApproval, ProcessOrder, SendConfirmation
        assert ctx.calls[0].name == "ValidateOrder"
        assert ctx.calls[1].name == "RequireApproval"
        assert ctx.calls[1].operation == "step"
        assert ctx.calls[2].name == "ProcessOrder"
        assert ctx.calls[2].operation == "parallel"
        assert ctx.calls[3].name == "SendConfirmation"


class TestRejectedOrderWorkflow:
    """Simulate an order rejection scenario."""

    def test_empty_order_rejected(self):
        """An order with zero items should result in itemCount=0 (Choice routes to OrderRejected)."""
        discover_handlers(HANDLERS_DIR)
        ctx = MockDurableContext()

        order_input = {
            "orderId": "order-300",
            "items": [],
            "total": 0,
        }

        # Step 1: ValidateOrder
        validate_handler = get_handler("ValidateOrder")
        validation_result = ctx.step("ValidateOrder", validate_handler, order_input)
        assert validation_result["itemCount"] == 0

        state_data = {**order_input, "validation": validation_result}

        # Step 2: CheckOrderValue — itemCount == 0, so -> OrderRejected
        assert state_data["validation"]["itemCount"] == 0
        # OrderRejected is a Fail state — no handler to call, workflow terminates

    def test_invalid_order_caught(self):
        """An order with invalid data should raise an error caught by the Catch clause."""
        discover_handlers(HANDLERS_DIR)

        validate_handler = get_handler("ValidateOrder")

        # Negative total triggers InvalidOrderError
        with pytest.raises(Exception, match="must not be negative"):
            validate_handler(
                {
                    "orderId": "order-301",
                    "items": [{"itemId": "x"}],
                    "total": -100,
                }
            )
