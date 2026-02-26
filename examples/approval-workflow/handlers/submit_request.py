"""SubmitRequest handler — creates an approval request record."""

import json
import logging
import uuid

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("SubmitRequest")
def submit_request(event: dict) -> dict:
    """Create a new approval request and return its ID.

    Expects:
        event.requestData: The request payload to be approved.
        event.submittedBy: User ID of the submitter.
        event.executionId: Context Object execution ID ($$).
        event.stateMachine: Context Object state machine name ($$).

    Returns:
        dict with requestId and status="pending".
    """
    request_id = str(uuid.uuid4())[:8]
    submitter = event.get("submittedBy", "unknown")

    _log(
        "SubmitRequest",
        "Creating approval request",
        requestId=request_id,
        submittedBy=submitter,
        executionId=event.get("executionId"),
        stateMachine=event.get("stateMachine"),
    )

    return {
        "requestId": request_id,
        "status": "pending",
        "submittedBy": submitter,
        "userId": submitter,
    }
