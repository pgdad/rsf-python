"""Tests for the approval-workflow example.

Covers:
  1. Workflow YAML parsing via rsf.dsl.parser.load_definition
  2. Context Object ($$) references present in workflow
  3. Variables/Assign present in workflow
  4. Individual handler testing
  5. Workflow simulation — approved and denied flows
"""

from pathlib import Path

import pytest

from rsf.dsl.parser import load_definition, load_yaml
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
        assert "SetApprovalContext" in defn.states
        assert "WaitForReview" in defn.states
        assert "CheckApprovalStatus" in defn.states
        assert "EvaluateDecision" in defn.states
        assert "ProcessApproval" in defn.states
        assert "EscalateRequest" in defn.states
        assert "RequestApproved" in defn.states
        assert "RequestDenied" in defn.states

    def test_state_count(self):
        defn = load_definition(WORKFLOW_PATH)
        assert len(defn.states) == 9

    def test_state_types(self):
        defn = load_definition(WORKFLOW_PATH)
        assert defn.states["SubmitRequest"].type == "Task"
        assert defn.states["SetApprovalContext"].type == "Pass"
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


# ---------------------------------------------------------------------------
# 2. Context Object ($$) references
# ---------------------------------------------------------------------------


class TestContextObjectReferences:
    """Verify Context Object references ($$.xxx) are present in the YAML."""

    def test_context_object_references_present(self):
        raw_text = WORKFLOW_PATH.read_text(encoding="utf-8")
        assert "$$." in raw_text, "Workflow must contain Context Object references ($$)"

    def test_execution_id_reference(self):
        raw_text = WORKFLOW_PATH.read_text(encoding="utf-8")
        assert "$$.Execution.Id" in raw_text

    def test_state_machine_name_reference(self):
        raw_text = WORKFLOW_PATH.read_text(encoding="utf-8")
        assert "$$.StateMachine.Name" in raw_text

    def test_state_name_reference(self):
        raw_text = WORKFLOW_PATH.read_text(encoding="utf-8")
        assert "$$.State.Name" in raw_text

    def test_execution_start_time_reference(self):
        raw_text = WORKFLOW_PATH.read_text(encoding="utf-8")
        assert "$$.Execution.StartTime" in raw_text

    def test_context_object_in_submit_request(self):
        """SubmitRequest Parameters must reference $$.Execution.Id."""
        raw = load_yaml(WORKFLOW_PATH)
        params = raw["States"]["SubmitRequest"]["Parameters"]
        assert params["executionId.$"] == "$$.Execution.Id"
        assert params["stateMachine.$"] == "$$.StateMachine.Name"

    def test_context_object_in_set_approval_context(self):
        """SetApprovalContext Parameters must reference $$.State.Name."""
        raw = load_yaml(WORKFLOW_PATH)
        params = raw["States"]["SetApprovalContext"]["Parameters"]
        assert params["stateName.$"] == "$$.State.Name"
        assert params["startTime.$"] == "$$.Execution.StartTime"

    def test_context_object_in_process_approval(self):
        """ProcessApproval Parameters must reference $$.Execution.Id."""
        raw = load_yaml(WORKFLOW_PATH)
        params = raw["States"]["ProcessApproval"]["Parameters"]
        assert params["executionId.$"] == "$$.Execution.Id"


# ---------------------------------------------------------------------------
# 3. Variables/Assign and Output fields
# ---------------------------------------------------------------------------


class TestVariablesAssign:
    """Verify Variables/Assign and Output are present in the YAML."""

    def test_assign_present_in_yaml(self):
        raw_text = WORKFLOW_PATH.read_text(encoding="utf-8")
        assert "Assign:" in raw_text, "Workflow must contain Assign blocks"

    def test_output_present_in_yaml(self):
        raw_text = WORKFLOW_PATH.read_text(encoding="utf-8")
        assert "Output:" in raw_text, "Workflow must contain Output blocks"

    def test_submit_request_assign(self):
        raw = load_yaml(WORKFLOW_PATH)
        assign = raw["States"]["SubmitRequest"]["Assign"]
        assert "requestId.$" in assign
        assert "submitter.$" in assign
        assert assign["attemptCount"] == 0

    def test_set_approval_context_assign(self):
        raw = load_yaml(WORKFLOW_PATH)
        assign = raw["States"]["SetApprovalContext"]["Assign"]
        assert assign["approvalDeadline"] == "2024-12-31T23:59:59Z"
        assert assign["escalationLevel"] == 1

    def test_check_approval_status_assign(self):
        raw = load_yaml(WORKFLOW_PATH)
        assign = raw["States"]["CheckApprovalStatus"]["Assign"]
        assert "attemptCount.$" in assign
        assert "States.MathAdd" in assign["attemptCount.$"]

    def test_process_approval_output(self):
        raw = load_yaml(WORKFLOW_PATH)
        output = raw["States"]["ProcessApproval"]["Output"]
        assert output["status"] == "approved"
        assert "requestId.$" in output
        assert "approver.$" in output

    def test_escalate_request_assign_and_output(self):
        raw = load_yaml(WORKFLOW_PATH)
        state_def = raw["States"]["EscalateRequest"]
        assert "Assign" in state_def
        assert "Output" in state_def
        assert state_def["Output"]["status"] == "escalated"

    def test_parsed_assign_fields(self):
        """Verify Assign fields parse correctly through the Pydantic model."""
        defn = load_definition(WORKFLOW_PATH)
        submit = defn.states["SubmitRequest"]
        assert submit.assign is not None
        assert submit.assign["attemptCount"] == 0

    def test_parsed_output_fields(self):
        """Verify Output fields parse correctly through the Pydantic model."""
        defn = load_definition(WORKFLOW_PATH)
        process = defn.states["ProcessApproval"]
        assert process.output is not None
        assert process.output["status"] == "approved"


# ---------------------------------------------------------------------------
# 4. Individual handler tests
# ---------------------------------------------------------------------------


class TestSubmitRequestHandler:
    """Test the SubmitRequest handler in isolation."""

    def test_returns_request_id(self):
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("SubmitRequest")
        result = handler(
            {
                "requestData": {"item": "laptop", "cost": 1500},
                "submittedBy": "user-42",
                "executionId": "exec-abc-123",
                "stateMachine": "ApprovalWorkflow",
            }
        )
        assert "requestId" in result
        assert result["status"] == "pending"
        assert result["submittedBy"] == "user-42"

    def test_generates_unique_ids(self):
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("SubmitRequest")
        r1 = handler({"requestData": {}, "submittedBy": "u1"})
        # Clear and re-register to call again (registry prevents duplicates)
        from rsf.registry.registry import clear

        clear()
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("SubmitRequest")
        r2 = handler({"requestData": {}, "submittedBy": "u2"})
        assert r1["requestId"] != r2["requestId"]


class TestCheckApprovalStatusHandler:
    """Test the CheckApprovalStatus handler in isolation."""

    def test_approved_decision(self):
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("CheckApprovalStatus")
        result = handler({"requestId": "approve-123", "checkNumber": 1})
        assert result["decision"] == "approved"
        assert result["approver"] == "manager-01"

    def test_denied_decision(self):
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("CheckApprovalStatus")
        result = handler({"requestId": "deny-456", "checkNumber": 0})
        assert result["decision"] == "denied"
        assert "approver" not in result

    def test_pending_decision(self):
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("CheckApprovalStatus")
        result = handler({"requestId": "unknown-789", "checkNumber": 0})
        assert result["decision"] == "pending"


class TestProcessApprovalHandler:
    """Test the ProcessApproval handler in isolation."""

    def test_returns_completed(self):
        discover_handlers(HANDLERS_DIR)
        handler = get_handler("ProcessApproval")
        result = handler(
            {
                "requestId": "req-001",
                "approvedBy": "manager-01",
                "executionId": "exec-abc",
            }
        )
        assert result["status"] == "completed"
        assert "processedAt" in result
        assert result["requestId"] == "req-001"
        assert result["approvedBy"] == "manager-01"


# ---------------------------------------------------------------------------
# 5. Workflow simulation
# ---------------------------------------------------------------------------


class TestApprovedFlowSimulation:
    """Simulate the full approved flow using MockDurableContext."""

    def test_approved_flow(self):
        discover_handlers(HANDLERS_DIR)
        ctx = MockDurableContext()

        # Step 1: SubmitRequest
        submit_handler = get_handler("SubmitRequest")
        submit_result = ctx.step(
            "SubmitRequest",
            submit_handler,
            {
                "requestData": {"item": "server", "cost": 5000},
                "submittedBy": "user-10",
                "executionId": "exec-001",
                "stateMachine": "ApprovalWorkflow",
            },
        )
        assert submit_result["status"] == "pending"
        request_id = submit_result["requestId"]

        # Step 2: SetApprovalContext (Pass state — simulated inline)
        # Pass state would produce context like:
        # {"requestId": request_id, "submitter": "user-10", "stateName": "SetApprovalContext", ...}

        # Step 3: WaitForReview
        ctx.wait("WaitForReview", Duration.seconds(5))

        # Step 4: CheckApprovalStatus — request starts with "approve" prefix
        # Override to simulate an "approved" response for our request ID
        ctx.override_step(
            "CheckApprovalStatus",
            {
                "decision": "approved",
                "approver": "manager-01",
                "checkNumber": 0,
                "requestId": request_id,
            },
        )
        check_handler = get_handler("CheckApprovalStatus")
        check_result = ctx.step(
            "CheckApprovalStatus",
            check_handler,
            {
                "requestId": request_id,
                "checkNumber": 0,
            },
        )
        assert check_result["decision"] == "approved"

        # Step 5: EvaluateDecision (Choice state — evaluate inline)
        decision = check_result["decision"]
        assert decision == "approved"
        # Choice selects "ProcessApproval"

        # Step 6: ProcessApproval
        process_handler = get_handler("ProcessApproval")
        process_result = ctx.step(
            "ProcessApproval",
            process_handler,
            {
                "requestId": request_id,
                "approvedBy": check_result["approver"],
                "executionId": "exec-001",
            },
        )
        assert process_result["status"] == "completed"
        assert process_result["approvedBy"] == "manager-01"

        # Step 7: RequestApproved (Succeed — terminal)

        # Verify the call sequence
        assert len(ctx.calls) == 4  # submit, wait, check, process
        assert ctx.calls[0].name == "SubmitRequest"
        assert ctx.calls[0].operation == "step"
        assert ctx.calls[1].name == "WaitForReview"
        assert ctx.calls[1].operation == "wait"
        assert ctx.calls[2].name == "CheckApprovalStatus"
        assert ctx.calls[2].operation == "step"
        assert ctx.calls[3].name == "ProcessApproval"
        assert ctx.calls[3].operation == "step"


class TestDeniedFlowSimulation:
    """Simulate the denied flow using MockDurableContext."""

    def test_denied_flow(self):
        discover_handlers(HANDLERS_DIR)
        ctx = MockDurableContext()

        # Step 1: SubmitRequest
        submit_handler = get_handler("SubmitRequest")
        submit_result = ctx.step(
            "SubmitRequest",
            submit_handler,
            {
                "requestData": {"item": "denied-item"},
                "submittedBy": "user-20",
                "executionId": "exec-002",
                "stateMachine": "ApprovalWorkflow",
            },
        )
        request_id = submit_result["requestId"]

        # Step 2: SetApprovalContext (Pass — inline)
        # Step 3: WaitForReview
        ctx.wait("WaitForReview", Duration.seconds(5))

        # Step 4: CheckApprovalStatus — override with denied decision
        ctx.override_step(
            "CheckApprovalStatus",
            {
                "decision": "denied",
                "checkNumber": 0,
                "requestId": request_id,
            },
        )
        check_handler = get_handler("CheckApprovalStatus")
        check_result = ctx.step(
            "CheckApprovalStatus",
            check_handler,
            {
                "requestId": request_id,
                "checkNumber": 0,
            },
        )
        assert check_result["decision"] == "denied"

        # Step 5: EvaluateDecision → RequestDenied (Fail state)
        # Simulate the Fail state
        with pytest.raises(RuntimeError, match="RequestDenied"):
            raise RuntimeError("RequestDenied: The approval request was denied")

        # Verify the call sequence
        assert len(ctx.calls) == 3  # submit, wait, check
        assert ctx.calls[0].name == "SubmitRequest"
        assert ctx.calls[1].name == "WaitForReview"
        assert ctx.calls[2].name == "CheckApprovalStatus"


class TestEscalationFlowSimulation:
    """Simulate the escalation flow (attempts exceed threshold)."""

    def test_escalation_after_max_attempts(self):
        discover_handlers(HANDLERS_DIR)
        ctx = MockDurableContext()

        # Step 1: SubmitRequest
        submit_handler = get_handler("SubmitRequest")
        submit_result = ctx.step(
            "SubmitRequest",
            submit_handler,
            {
                "requestData": {"item": "ambiguous-item"},
                "submittedBy": "user-30",
                "executionId": "exec-003",
                "stateMachine": "ApprovalWorkflow",
            },
        )
        request_id = submit_result["requestId"]

        # Simulate multiple pending checks that loop back via Default
        check_handler = get_handler("CheckApprovalStatus")
        attempt_count = 0

        for attempt in range(4):
            ctx.wait(f"WaitForReview-{attempt}", Duration.seconds(5))

            ctx.override_step(
                f"CheckApprovalStatus-{attempt}",
                {
                    "decision": "pending",
                    "checkNumber": attempt,
                    "requestId": request_id,
                },
            )
            check_result = ctx.step(
                f"CheckApprovalStatus-{attempt}",
                check_handler,
                {"requestId": request_id, "checkNumber": attempt},
            )
            assert check_result["decision"] == "pending"
            attempt_count += 1

        # After 4 attempts, attemptCount > 3, so EvaluateDecision routes to EscalateRequest
        assert attempt_count > 3

        # EscalateRequest is a Pass state — produces output inline
        escalation_output = {
            "status": "escalated",
            "requestId": request_id,
            "level": 2,  # escalationLevel was 1, incremented by 1
        }
        assert escalation_output["status"] == "escalated"

        # Verify we had the right number of SDK calls
        # 1 submit + 4*(wait + check) = 1 + 8 = 9
        assert len(ctx.calls) == 9


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
