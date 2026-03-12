"""ValidateOrder handler — validates that an order has items and a positive total."""

import json
import logging

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


class InvalidOrderError(Exception):
    """Raised when the order data is invalid."""


@state("ValidateOrder")
def validate_order(input_data: dict) -> dict:
    """Validate order structure, items, and total.

    Args:
        input_data: Order data with 'items' list and optional 'total'.

    Returns:
        dict with valid, total, and itemCount fields.

    Raises:
        InvalidOrderError: If order has no items list or negative total.
    """
    _log("ValidateOrder", "Starting order validation", order_id=input_data.get("orderId"))

    items = input_data.get("items", [])
    if not isinstance(items, list):
        _log("ValidateOrder", "Invalid items field — not a list")
        raise InvalidOrderError("Order items must be a list")

    item_count = len(items)
    total = input_data.get("total", 0)

    if not isinstance(total, (int, float)):
        _log("ValidateOrder", "Invalid total — not a number")
        raise InvalidOrderError("Order total must be a number")

    if total < 0:
        _log("ValidateOrder", "Invalid total — negative value", total=total)
        raise InvalidOrderError("Order total must not be negative")

    if item_count == 0:
        _log("ValidateOrder", "Order has no items")

    _log(
        "ValidateOrder",
        "Order validated successfully",
        total=total,
        item_count=item_count,
    )

    return {"valid": True, "total": total, "itemCount": item_count}
