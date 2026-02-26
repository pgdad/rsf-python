"""ReserveInventory handler — simulates inventory reservation."""

import json
import logging
import uuid

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


class InventoryLockError(Exception):
    """Raised when inventory cannot be locked (concurrent access)."""


@state("ReserveInventory")
def reserve_inventory(input_data: dict) -> dict:
    """Simulate inventory reservation for order items.

    Args:
        input_data: Order data including items list.

    Returns:
        dict with reservation details for each item.
    """
    items = input_data.get("items", [])
    order_id = input_data.get("orderId", "unknown")

    _log(
        "ReserveInventory",
        "Reserving inventory",
        order_id=order_id,
        item_count=len(items),
    )

    reservation_id = str(uuid.uuid4())
    reserved_items = []

    for item in items:
        item_id = item.get("itemId", "unknown")
        quantity = item.get("quantity", 1)
        reserved_items.append({
            "itemId": item_id,
            "quantity": quantity,
            "reserved": True,
        })
        _log(
            "ReserveInventory",
            "Item reserved",
            item_id=item_id,
            quantity=quantity,
        )

    _log(
        "ReserveInventory",
        "Inventory reservation complete",
        reservation_id=reservation_id,
    )

    return {
        "reservationId": reservation_id,
        "items": reserved_items,
        "status": "reserved",
    }
