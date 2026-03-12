"""Handler for TryFallbackService state.

Simulates a fallback API call used when the primary service is down.
Supports the same error-simulation mechanism via ``simulate_error``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra: Any) -> None:
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("TryFallbackService")
def try_fallback_service(data: dict[str, Any]) -> dict[str, Any]:
    """Call the fallback service after the primary service failed.

    Reads ``data["simulate_error"]`` to optionally raise errors for
    retry/catch testing.  On success returns a response tagged with
    ``"source": "fallback"``.
    """
    step = "TryFallbackService"
    _log(step, "Invoking fallback service", primary_error=data.get("primaryError"))

    error_type = data.get("simulate_error")
    if error_type == "TransientError":
        _log(step, "Transient failure on fallback", error=error_type)
        raise RuntimeError("TransientError: fallback connection reset")
    if error_type:
        _log(step, "Unexpected error on fallback", error=error_type)
        raise RuntimeError(f"{error_type}: fallback service failure")

    result = {
        "source": "fallback",
        "status": "ok",
        "requestId": data.get("requestId", "unknown"),
        "payload": data.get("payload", {}),
    }
    _log(step, "Fallback service responded successfully", result=result)
    return result
