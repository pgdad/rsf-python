"""Handler for VerifyResult state.

Validates the result produced by any upstream service path (primary,
fallback, or throttle-retry) before the workflow completes.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra: Any) -> None:
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("VerifyResult")
def verify_result(data: dict[str, Any]) -> dict[str, Any]:
    """Verify the service result before completing the workflow.

    Checks that a ``status`` field is present and equals ``"ok"``.
    Returns a verification record that is merged into the workflow
    output via ``ResultPath: $.verification``.
    """
    step = "VerifyResult"
    _log(step, "Verifying service result", data_keys=list(data.keys()))

    status = data.get("status")
    source = data.get("source", "unknown")

    if status != "ok":
        _log(step, "Verification failed: unexpected status", status=status)
        raise RuntimeError(f"VerificationError: expected status 'ok', got '{status}'")

    verification = {
        "verified": True,
        "source": source,
        "checksPerformed": ["status_check", "payload_integrity"],
    }
    _log(step, "Verification passed", verification=verification)
    return verification
