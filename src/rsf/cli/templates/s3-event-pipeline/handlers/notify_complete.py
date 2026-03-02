"""Send SNS notification with pipeline processing summary."""

from __future__ import annotations

import json
import os

import boto3
from rsf.functions.decorators import state

TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")

sns = boto3.client("sns")


@state("NotifyComplete")
def notify_complete(event: dict, context: dict) -> dict:
    """Publish a notification to SNS with the pipeline processing summary.

    Sends different messages for successful completions vs. validation failures.

    Args:
        event: Pipeline state with processing results.
        context: Lambda execution context.

    Returns:
        Pipeline state with notification status.
    """
    key = event.get("key", "unknown")
    valid = event.get("valid", True)

    if valid:
        subject = f"Pipeline Complete: {key}"
        message = {
            "status": "success",
            "file": key,
            "output_key": event.get("output_key", ""),
            "archive_key": event.get("archive_key", ""),
            "size": event.get("size", 0),
        }
    else:
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
            Subject=subject[:100],  # SNS subject max 100 chars
            Message=json.dumps(message, indent=2),
        )

    return {
        **event,
        "notified": True,
        "notification_status": "sent" if TOPIC_ARN else "skipped",
    }
