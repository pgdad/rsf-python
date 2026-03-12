"""Handler for RetryAfterThrottle state.

Retries the primary service call after a throttle-recovery pass state
has injected recovery context into the payload.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra: Any) -> None:
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("RetryAfterThrottle")
def retry_after_throttle(data: dict[str, Any]) -> dict[str, Any]:
    """Retry the service call after being throttled.

    Expects ``data["recovery"]`` to contain throttle metadata injected
    by the HandleThrottle pass state.  Raises ``RateLimitError`` when
    ``data["simulate_error"]`` is set for retry testing.
    """
    step = "RetryAfterThrottle"
    recovery = data.get("recovery", {})
    _log(step, "Retrying after throttle", retry_after=recovery.get("retryAfter"))

    error_type = data.get("simulate_error")
    if error_type == "RateLimitError":
        _log(step, "Still being throttled", error=error_type)
        raise RuntimeError("RateLimitError: still throttled")

    result = {
        "source": "primary-retry",
        "status": "ok",
        "requestId": data.get("requestId", "unknown"),
        "throttleRecovery": True,
    }
    _log(step, "Retry after throttle succeeded", result=result)
    return result
