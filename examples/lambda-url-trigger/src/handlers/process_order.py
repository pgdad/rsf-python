"""ProcessOrder handler — processes a validated order and returns completion status."""

import json
import logging

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("ProcessOrder")
def process_order(input_data: dict) -> dict:
    """Process a validated order.

    Args:
        input_data: Order data (including validation result from previous state).

    Returns:
        dict with processed, orderId, and status fields.
    """
    order_id = input_data.get("orderId", "unknown")
    _log("ProcessOrder", "Processing order", order_id=order_id)

    total = input_data.get("total", 0)
    item_count = input_data.get("itemCount", 0)

    _log(
        "ProcessOrder",
        "Order processed successfully",
        order_id=order_id,
        total=total,
        item_count=item_count,
    )

    return {
        "processed": True,
        "orderId": order_id,
        "status": "completed",
        "total": total,
        "itemCount": item_count,
    }
