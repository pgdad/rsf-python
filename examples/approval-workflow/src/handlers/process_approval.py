"""ProcessApproval handler — finalizes an approved request."""

import json
import logging
from datetime import datetime, timezone

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("ProcessApproval")
def process_approval(event: dict) -> dict:
    """Finalize processing of an approved request.

    Reads from event["submission"]["requestId"] and
    event["approvalCheck"]["approver"].

    Returns:
        dict with processedAt timestamp and status="completed".
    """
    submission = event.get("submission", {})
    approval_check = event.get("approvalCheck", {})

    request_id = submission.get("requestId", "unknown")
    approved_by = approval_check.get("approver", "unknown")

    _log(
        "ProcessApproval",
        "Processing approved request",
        requestId=request_id,
        approvedBy=approved_by,
    )

    processed_at = datetime.now(timezone.utc).isoformat()

    _log(
        "ProcessApproval",
        "Request processing complete",
        requestId=request_id,
        processedAt=processed_at,
    )

    return {
        "processedAt": processed_at,
        "status": "completed",
        "requestId": request_id,
        "approvedBy": approved_by,
    }
