"""SF Lambda handlers for SQS collector. Used for AppendMessage and DeleteMessages."""
from __future__ import annotations
import json
import os
import boto3

_sqs = boto3.client("sqs")

def append_handler(event: dict, context) -> dict:
    messages = event.get("messages", [])
    receipt_handles = event.get("receipt_handles", [])
    new_message = event.get("new_message")
    new_receipt_handle = event.get("new_receipt_handle")
    if isinstance(new_message, str):
        try:
            new_message = json.loads(new_message)
        except json.JSONDecodeError:
            pass
    messages.append(new_message)
    receipt_handles.append(new_receipt_handle)
    return {
        "messages": messages, "receipt_handles": receipt_handles, "count": len(messages),
        "queue_url": event.get("queue_url"), "output_key": event.get("output_key"), "s3_bucket": event.get("s3_bucket"),
    }

def delete_handler(event: dict, context) -> dict:
    queue_url = os.environ["PARITY_SQS_QUEUE_URL"]
    receipt_handles = event.get("receipt_handles", [])
    if not receipt_handles:
        return {"deleted": 0}
    entries = [{"Id": str(i), "ReceiptHandle": rh} for i, rh in enumerate(receipt_handles)]
    _sqs.delete_message_batch(QueueUrl=queue_url, Entries=entries)
    return {"deleted": len(receipt_handles)}
