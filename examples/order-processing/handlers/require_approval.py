"""RequireApproval handler — simulates manager approval for high-value orders."""

import json
import logging

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


class ApprovalDenied(Exception):
    """Raised when the manager denies the order."""


@state("RequireApproval")
def require_approval(input_data: dict) -> dict:
    """Simulate manager approval for high-value orders.

    In a real workflow this would wait for an external callback.
    For demonstration purposes, orders with total > 10000 are denied.

    Args:
        input_data: Order data including validation results.

    Returns:
        dict with approved status and approver information.

    Raises:
        ApprovalDenied: If the order total exceeds the auto-denial threshold.
    """
    total = input_data.get("validation", {}).get("total", 0)
    order_id = input_data.get("orderId", "unknown")

    _log(
        "RequireApproval",
        "High-value order requires manager approval",
        order_id=order_id,
        total=total,
    )

    # Simulate denial for extremely high-value orders
    if total > 10000:
        _log("RequireApproval", "Order denied — exceeds auto-approval limit", total=total)
        raise ApprovalDenied(f"Order total {total} exceeds auto-approval limit")

    _log("RequireApproval", "Order approved by manager", order_id=order_id)

    return {
        "approved": True,
        "approver": "manager@example.com",
        "approvedAt": "2026-02-26T12:00:00Z",
    }
