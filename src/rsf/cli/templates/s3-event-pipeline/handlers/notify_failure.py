"""Send SNS notification for pipeline validation failure."""

from __future__ import annotations

import json
import os

import boto3
from rsf.functions.decorators import state

TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")

sns = boto3.client("sns")


@state("NotifyFailure")
def notify_failure(event: dict, context: dict) -> dict:
    """Publish a failure notification to SNS when file validation fails.

    Args:
        event: Pipeline state with validation failure details.
        context: Lambda execution context.

    Returns:
        Pipeline state with notification status.
    """
    key = event.get("key", "unknown")
    subject = f"Pipeline Failed: {key}"
    message = {
        "status": "validation_failed",
        "file": key,
        "size": event.get("size", 0),
        "reason": "File did not pass validation checks",
    }

    if TOPIC_ARN:
        sns.publish(
            TopicArn=TOPIC_ARN,
            Subject=subject[:100],
            Message=json.dumps(message, indent=2),
        )

    return {
        **event,
        "notified": True,
        "notification_status": "sent" if TOPIC_ARN else "skipped",
    }
