"""Tests for the approval-workflow example.

Covers:
  1. Workflow YAML parsing via rsf.dsl.parser.load_definition
  2. Individual handler testing
  3. Workflow simulation — escalation, approved, and denied flows
"""

from pathlib import Path

from rsf.dsl.parser import load_definition
from rsf.registry import discover_handlers, get_handler, registered_states

from mock_sdk import MockDurableContext, Duration

WORKFLOW_PATH = Path(__file__).parent.parent / "workflow.yaml"
HANDLERS_DIR = Path(__file__).parent.parent / "handlers"


# ---------------------------------------------------------------------------
# 1. Workflow YAML parsing
# ---------------------------------------------------------------------------


class TestWorkflowParsing:
    """Verify the workflow.yaml parses correctly through the RSF DSL parser."""

    def test_load_definition_succeeds(self):
        defn = load_definition(WORKFLOW_PATH)
        assert defn.start_at == "SubmitRequest"
        assert "SubmitRequest" in defn.states
        assert "WaitForReview" in defn.states
        assert "CheckApprovalStatus" in defn.states
        assert "EvaluateDecision" in defn.states
        assert "ProcessApproval" in defn.states
        assert "EscalateRequest" in defn.states
        assert "RequestApproved" in defn.states
        assert "RequestDenied" in defn.states

    def test_state_count(self):
        defn = load_definition(WORKFLOW_PATH)
        assert len(defn.states) == 8

    def test_state_types(self):
        defn = load_definition(WORKFLOW_PATH)
        assert defn.states["SubmitRequest"].type == "Task"
        assert defn.states["WaitForReview"].type == "Wait"
        assert defn.states["CheckApprovalStatus"].type == "Task"
        assert defn.states["EvaluateDecision"].type == "Choice"
        assert defn.states["ProcessApproval"].type == "Task"
        assert defn.states["EscalateRequest"].type == "Pass"
        assert defn.states["RequestApproved"].type == "Succeed"
        assert defn.states["RequestDenied"].type == "Fail"

    def test_wait_state_seconds(self):
        defn = load_definition(WORKFLOW_PATH)
        assert defn.states["WaitForReview"].seconds == 5

    def test_choice_state_rules(self):
        defn = load_definition(WORKFLOW_PATH)
        choice = defn.states["EvaluateDecision"]
        assert len(choice.choices) == 3
        assert choice.default == "WaitForReview"

    def test_fail_state_error(self):
        defn = load_definition(WORKFLOW_PATH)
        fail = defn.states["RequestDenied"]
        assert fail.error == "RequestDenied"
        assert fail.cause == "The approval request was denied"

    def test_rsf_version(self):
        defn = load_definition(WORKFLOW_PATH)
        assert defn.rsf_version == "1.0"

    def test_comment(self):
        defn = load_definition(WORKFLOW_PATH)
        assert "Approval workflow" in defn.comment

    def test_result_paths(self):
        defn = load_definition(WORKFLOW_PATH)
        assert defn.states["SubmitRequest"].result_path == "$.submission"
        assert defn.states["CheckApprovalStatus"].result_path == "$.approvalCheck"
        assert defn.states["ProcessApproval"].result_path == "$.result"


# ---------------------------------------------------------------------------
# 2. Individual handler tests
# ---------------------------------------------------------------------------


class TestSubmitRequestHandler:
    """Test the SubmitRequest handler in isolation."""

    def test_returns_request_id(self):
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("SubmitRequest")
        result = handler({
            "request": {"item": "laptop", "cost": 1500},
            "userId": "user-42",
        })
        assert "requestId" in result
        assert result["status"] == "pending"
        assert result["submittedBy"] == "user-42"
        assert "attemptCount" in result
        assert result["attemptCount"] == 0

    def test_generates_unique_ids(self):
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("SubmitRequest")
        r1 = handler({"request": {}, "userId": "u1"})
        from rsf.registry.registry import clear
        clear()
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("SubmitRequest")
        r2 = handler({"request": {}, "userId": "u2"})
        assert r1["requestId"] != r2["requestId"]


class TestCheckApprovalStatusHandler:
    """Test the CheckApprovalStatus handler in isolation."""

    def test_approved_decision(self):
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("CheckApprovalStatus")
        result = handler({
            "submission": {"requestId": "approve-123", "attemptCount": 0},
        })
        assert result["decision"] == "approved"
        assert result["approver"] == "manager-01"
        assert result["attemptCount"] == 1

    def test_denied_decision(self):
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("CheckApprovalStatus")
        result = handler({
            "submission": {"requestId": "deny-456", "attemptCount": 0},
        })
        assert result["decision"] == "denied"
        assert "approver" not in result

    def test_pending_decision(self):
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("CheckApprovalStatus")
        result = handler({
            "submission": {"requestId": "unknown-789", "attemptCount": 0},
        })
        assert result["decision"] == "pending"

    def test_increments_attempt_count(self):
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("CheckApprovalStatus")
        # First check
        result1 = handler({
            "submission": {"requestId": "pending-001", "attemptCount": 0},
        })
        assert result1["attemptCount"] == 1
        # Second check (using previous approvalCheck)
        result2 = handler({
            "submission": {"requestId": "pending-001", "attemptCount": 0},
            "approvalCheck": {"attemptCount": 1},
        })
        assert result2["attemptCount"] == 2


class TestProcessApprovalHandler:
    """Test the ProcessApproval handler in isolation."""

    def test_returns_completed(self):
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ProcessApproval")
        result = handler({
            "submission": {"requestId": "req-001"},
            "approvalCheck": {"approver": "manager-01"},
        })
        assert result["status"] == "completed"
        assert "processedAt" in result
        assert result["requestId"] == "req-001"
        assert result["approvedBy"] == "manager-01"


# ---------------------------------------------------------------------------
# 3. Workflow simulation
# ---------------------------------------------------------------------------


class TestEscalationFlowSimulation:
    """Simulate the escalation flow using MockDurableContext."""

    def test_escalation_after_max_attempts(self):
        discover_handlers(HANDLERS_DIR)
        ctx = MockDurableContext()

        # Step 1: SubmitRequest
        submit_handler = get_handler("SubmitRequest")
        submit_result = ctx.step(
            lambda _sc: submit_handler({"request": {"item": "test"}, "userId": "user-30"}),
            "SubmitRequest",
        )
        assert submit_result["attemptCount"] == 0
        _ = submit_result["requestId"]  # verified exists

        # Simulate multiple pending checks (4 rounds)
        check_handler = get_handler("CheckApprovalStatus")
        input_data = {"submission": submit_result}

        for _ in range(4):
            ctx.wait(Duration.seconds(5), "WaitForReview")
            check_result = ctx.step(
                lambda _sc: check_handler(input_data),
                "CheckApprovalStatus",
            )
            assert check_result["decision"] == "pending"
            input_data = {**input_data, "approvalCheck": check_result}

        # After 4 checks, attemptCount should be > 3
        assert input_data["approvalCheck"]["attemptCount"] > 3


class TestApprovedFlowSimulation:
    """Simulate the approved flow using MockDurableContext."""

    def test_approved_flow(self):
        discover_handlers(HANDLERS_DIR)
        ctx = MockDurableContext()

        submit_handler = get_handler("SubmitRequest")
        submit_result = ctx.step(
            lambda _sc: submit_handler({"request": {}, "userId": "user-10"}),
            "SubmitRequest",
        )

        ctx.wait(Duration.seconds(5), "WaitForReview")

        check_handler = get_handler("CheckApprovalStatus")
        # Use an "approve-" prefix requestId for approved decision
        input_data = {"submission": {**submit_result, "requestId": "approve-test"}}
        check_result = ctx.step(
            lambda _sc: check_handler(input_data),
            "CheckApprovalStatus",
        )
        assert check_result["decision"] == "approved"

        process_handler = get_handler("ProcessApproval")
        input_data_with_check = {**input_data, "approvalCheck": check_result}
        process_result = ctx.step(
            lambda _sc: process_handler(input_data_with_check),
            "ProcessApproval",
        )
        assert process_result["status"] == "completed"

        assert len(ctx.calls) == 4  # submit, wait, check, process


class TestHandlerRegistration:
    """Verify handler discovery and registration."""

    def test_discover_all_handlers(self):
        discover_handlers(HANDLERS_DIR)
        states = registered_states()
        assert "SubmitRequest" in states
        assert "CheckApprovalStatus" in states
        assert "ProcessApproval" in states

    def test_handler_count(self):
        discover_handlers(HANDLERS_DIR)
        states = registered_states()
        assert len(states) == 3  # Only Task states have handlers
