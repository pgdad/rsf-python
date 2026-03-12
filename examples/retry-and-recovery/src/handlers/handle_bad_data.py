"""Handler for HandleBadData state.

Sanitizes or repairs invalid data so the workflow can retry
CallPrimaryService with a clean payload.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra: Any) -> None:
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("HandleBadData")
def handle_bad_data(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize invalid data before retrying the primary service.

    Strips or replaces problematic fields and clears the
    ``simulate_error`` flag so the next CallPrimaryService invocation
    succeeds.
    """
    step = "HandleBadData"
    validation_error = data.get("validationError", {})
    _log(step, "Sanitizing bad data", validation_error=str(validation_error))

    error_type = data.get("simulate_error")
    if error_type:
        _log(step, "Sanitization failed", error=error_type)
        raise RuntimeError(f"{error_type}: unable to sanitize data")

    sanitized = {
        "cleaned": True,
        "originalPayload": data.get("payload", {}),
        "removedFields": ["malformed_field"],
    }
    _log(step, "Data sanitized successfully", sanitized=sanitized)
    return sanitized
