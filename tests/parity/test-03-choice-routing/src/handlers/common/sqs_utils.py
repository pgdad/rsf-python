"""SQS poll/delete utilities shared by RSF handlers and SF Lambda handlers."""
from __future__ import annotations
import json
import os
import boto3

_sqs = boto3.client("sqs")

def get_queue_url() -> str:
    return os.environ["PARITY_SQS_QUEUE_URL"]

def poll_sqs(queue_url: str | None = None, max_messages: int = 1) -> list[dict]:
    queue_url = queue_url or get_queue_url()
    response = _sqs.receive_message(
        QueueUrl=queue_url, MaxNumberOfMessages=max_messages, WaitTimeSeconds=5,
    )
    return [
        {"body": json.loads(m["Body"]), "receipt_handle": m["ReceiptHandle"], "message_id": m["MessageId"]}
        for m in response.get("Messages", [])
    ]

def delete_messages(receipt_handles: list[str], queue_url: str | None = None) -> None:
    queue_url = queue_url or get_queue_url()
    if not receipt_handles:
        return
    entries = [{"Id": str(i), "ReceiptHandle": rh} for i, rh in enumerate(receipt_handles)]
    _sqs.delete_message_batch(QueueUrl=queue_url, Entries=entries)
