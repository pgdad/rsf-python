"""SF Lambda handlers for SQS collector.

All Task states use Lambda handlers (no SDK integrations) so the SF
and RSF versions exercise identical handler code.
"""
from __future__ import annotations

import json
import os

import boto3

_sqs = boto3.client("sqs")
_s3 = boto3.client("s3")


def poll_handler(event: dict, context) -> dict:
    """Poll SQS for one message."""
    queue_url = os.environ["PARITY_SQS_QUEUE_URL"]
    response = _sqs.receive_message(
        QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=5,
    )
    messages = response.get("Messages", [])
    if messages:
        msg = messages[0]
        body = msg["Body"]
        try:
            body = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            pass
        return {
            **event,
            "received": True,
            "message": body,
            "receipt_handle": msg["ReceiptHandle"],
        }
    return {**event, "received": False}


def append_handler(event: dict, context) -> dict:
    """Append received message to the accumulated messages list."""
    messages = event.get("messages", [])
    receipt_handles = event.get("receipt_handles", [])
    poll_result = event.get("poll_result", {})
    new_message = poll_result.get("message")
    new_receipt_handle = poll_result.get("receipt_handle")

    if new_message is not None:
        messages.append(new_message)
    if new_receipt_handle is not None:
        receipt_handles.append(new_receipt_handle)

    return {
        **event,
        "messages": messages,
        "receipt_handles": receipt_handles,
        "count": len(messages),
    }


def write_handler(event: dict, context) -> dict:
    """Write collected messages to S3."""
    bucket = os.environ["PARITY_S3_BUCKET"]
    output_key = event["output_key"]
    _s3.put_object(
        Bucket=bucket,
        Key=output_key,
        Body=json.dumps(event["messages"], default=str).encode("utf-8"),
        ContentType="application/json",
    )
    return {**event, "written": True}


def delete_handler(event: dict, context) -> dict:
    """Batch delete messages from SQS."""
    queue_url = os.environ["PARITY_SQS_QUEUE_URL"]
    receipt_handles = event.get("receipt_handles", [])
    if not receipt_handles:
        return {**event, "deleted": 0}
    entries = [
        {"Id": str(i), "ReceiptHandle": rh}
        for i, rh in enumerate(receipt_handles)
    ]
    _sqs.delete_message_batch(QueueUrl=queue_url, Entries=entries)
    return {**event, "deleted": len(receipt_handles)}
