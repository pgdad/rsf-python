"""RSF @state handlers for the SQS message collector."""
from __future__ import annotations
from rsf.registry import state
from handlers.common.s3_utils import write_json_to_s3
from handlers.common.sqs_utils import poll_sqs, delete_messages

@state("PollSQS")
def poll_sqs_handler(event: dict) -> dict:
    messages = poll_sqs(max_messages=1)
    if messages:
        msg = messages[0]
        return {**event, "received": True, "message": msg["body"], "receipt_handle": msg["receipt_handle"]}
    return {**event, "received": False}

@state("AppendMessage")
def append_message_handler(event: dict) -> dict:
    import json
    messages = event.get("messages", [])
    receipt_handles = event.get("receipt_handles", [])
    poll_result = event.get("poll_result", {})
    new_message = poll_result.get("message")
    new_receipt_handle = poll_result.get("receipt_handle")
    if isinstance(new_message, str):
        try:
            new_message = json.loads(new_message)
        except json.JSONDecodeError:
            pass
    if new_message is not None:
        messages.append(new_message)
    if new_receipt_handle is not None:
        receipt_handles.append(new_receipt_handle)
    return {**event, "messages": messages, "receipt_handles": receipt_handles, "count": len(messages)}

@state("WriteCollected")
def write_collected_handler(event: dict) -> dict:
    output_key = event["output_key"]
    write_json_to_s3(output_key, event["messages"])
    return {**event, "written": True}

@state("DeleteMessages")
def delete_messages_handler(event: dict) -> dict:
    receipt_handles = event.get("receipt_handles", [])
    delete_messages(receipt_handles)
    return {**event, "deleted": len(receipt_handles)}
