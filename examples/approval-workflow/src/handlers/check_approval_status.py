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

    For testing purposes, the decision is determined by the requestId
    and the check attempt number:
      - If requestId starts with "approve": decision is "approved" on attempt >= 1.
      - If requestId starts with "deny": decision is always "denied".
      - Otherwise: decision is "pending" (will retry via the Choice default).

    Expects:
        event.requestId: The request identifier.
        event.checkNumber: Current attempt count.

    Returns:
        dict with decision, approver (if approved), and checkNumber.
    """
    request_id = event.get("requestId", "")
    check_number = event.get("checkNumber", 0)

    _log(
        "CheckApprovalStatus",
        "Checking approval status",
        requestId=request_id,
        checkNumber=check_number,
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
        "checkNumber": check_number,
        "requestId": request_id,
    }
    if approver:
        result["approver"] = approver

    _log(
        "CheckApprovalStatus",
        f"Approval check result: {decision}",
        requestId=request_id,
        decision=decision,
    )

    return result
