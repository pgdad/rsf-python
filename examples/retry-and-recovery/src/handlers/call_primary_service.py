"""Handler for CallPrimaryService state.

Simulates calling an unreliable external API that may raise
TransientError, RateLimitError, TimeoutError, ServiceDownError,
or DataValidationError depending on the input payload.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra: Any) -> None:
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("CallPrimaryService")
def call_primary_service(data: dict[str, Any]) -> dict[str, Any]:
    """Call the primary external service.

    Inspects ``data["simulate_error"]`` to decide whether to raise an
    error (for retry/catch testing) or return a successful response.
    """
    step = "CallPrimaryService"
    _log(step, "Invoking primary service", request_id=data.get("requestId"))

    error_type = data.get("simulate_error")
    if error_type == "TransientError":
        _log(step, "Transient failure encountered", error=error_type)
        raise RuntimeError("TransientError: connection reset")
    if error_type == "RateLimitError":
        _log(step, "Rate limit exceeded", error=error_type)
        raise RuntimeError("RateLimitError: 429 Too Many Requests")
    if error_type == "TimeoutError":
        _log(step, "Request timed out", error=error_type)
        raise RuntimeError("TimeoutError: upstream took too long")
    if error_type == "ServiceDownError":
        _log(step, "Primary service is down", error=error_type)
        raise RuntimeError("ServiceDownError: 503 Service Unavailable")
    if error_type == "DataValidationError":
        _log(step, "Invalid data received from upstream", error=error_type)
        raise RuntimeError("DataValidationError: schema mismatch")

    result = {
        "source": "primary",
        "status": "ok",
        "requestId": data.get("requestId", "unknown"),
        "payload": data.get("payload", {}),
    }
    _log(step, "Primary service responded successfully", result=result)
    return result
