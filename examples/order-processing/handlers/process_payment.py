"""ProcessPayment handler — simulates payment processing."""

import json
import logging
import uuid

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


class PaymentGatewayError(Exception):
    """Raised when the payment gateway is temporarily unavailable."""


@state("ProcessPayment")
def process_payment(input_data: dict) -> dict:
    """Simulate payment processing for an order.

    Args:
        input_data: Order data including total and payment method.

    Returns:
        dict with payment transaction details.
    """
    total = input_data.get("validation", {}).get("total", 0)
    order_id = input_data.get("orderId", "unknown")
    payment_method = input_data.get("paymentMethod", "credit_card")

    _log(
        "ProcessPayment",
        "Processing payment",
        order_id=order_id,
        total=total,
        payment_method=payment_method,
    )

    transaction_id = str(uuid.uuid4())

    _log(
        "ProcessPayment",
        "Payment processed successfully",
        transaction_id=transaction_id,
        total=total,
    )

    return {
        "transactionId": transaction_id,
        "amount": total,
        "status": "completed",
        "paymentMethod": payment_method,
    }
