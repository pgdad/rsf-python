"""CheckApprovalStatus handler — simulates checking an approval decision."""

import json
import logging

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("CheckApprovalStatus")
def check_approval_status(event: dict) -> dict:
    """Simulate checking the approval status of a request.

    Reads requestId from event["submission"]["requestId"] and
    attemptCount from event["submission"]["attemptCount"] (or
    event["approvalCheck"]["attemptCount"] from previous check).

    Decision logic:
      - If requestId starts with "approve": decision is "approved" on attempt >= 1.
      - If requestId starts with "deny": decision is always "denied".
      - Otherwise: decision is "pending" (will retry via the Choice default).

    Returns:
        dict with decision, approver (if approved), and incremented attemptCount.
    """
    submission = event.get("submission", {})
    previous_check = event.get("approvalCheck", {})

    request_id = submission.get("requestId", "")
    # Use previous check's attemptCount if available, else use submission's
    attempt_count = previous_check.get("attemptCount", submission.get("attemptCount", 0))
    new_attempt_count = attempt_count + 1

    _log(
        "CheckApprovalStatus",
        "Checking approval status",
        requestId=request_id,
        checkNumber=new_attempt_count,
    )

    if request_id.startswith("approve"):
        decision = "approved"
        approver = "manager-01"
    elif request_id.startswith("deny"):
        decision = "denied"
        approver = None
    else:
        decision = "pending"
        approver = None

    result = {
        "decision": decision,
        "attemptCount": new_attempt_count,
        "requestId": request_id,
    }
    if approver:
        result["approver"] = approver

    _log(
        "CheckApprovalStatus",
        f"Approval check result: {decision}",
        requestId=request_id,
        decision=decision,
        attemptCount=new_attempt_count,
    )

    return result
