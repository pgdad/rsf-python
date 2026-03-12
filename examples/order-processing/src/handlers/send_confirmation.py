"""SendConfirmation handler — generates a confirmation number and sends notification."""

import json
import logging
import uuid

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("SendConfirmation")
def send_confirmation(input_data: dict) -> dict:
    """Generate an order confirmation number and simulate sending a notification.

    Args:
        input_data: Order data including processing results.

    Returns:
        dict with confirmation number and notification status.
    """
    order_id = input_data.get("orderId", "unknown")
    customer_email = input_data.get("customerEmail", "customer@example.com")

    confirmation_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"

    _log(
        "SendConfirmation",
        "Generating order confirmation",
        order_id=order_id,
        confirmation_number=confirmation_number,
    )

    _log(
        "SendConfirmation",
        "Confirmation sent to customer",
        customer_email=customer_email,
        confirmation_number=confirmation_number,
    )

    return {
        "confirmationNumber": confirmation_number,
        "emailSent": True,
        "recipientEmail": customer_email,
    }
