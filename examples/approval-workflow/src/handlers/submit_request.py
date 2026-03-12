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
        event.request: The request payload to be approved.
        event.userId: User ID of the submitter.

    Returns:
        dict with requestId, status, submittedBy, and attemptCount: 0.
    """
    request_id = str(uuid.uuid4())[:8]
    submitter = event.get("userId", "unknown")
    request = event.get("request", {})

    _log(
        "SubmitRequest",
        "Creating approval request",
        requestId=request_id,
        submittedBy=submitter,
        executionId=None,
        stateMachine=None,
    )

    return {
        "requestId": request_id,
        "status": "pending",
        "submittedBy": submitter,
        "attemptCount": 0,
    }
