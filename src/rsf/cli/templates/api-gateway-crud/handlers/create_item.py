"""Create a new item in DynamoDB."""

from __future__ import annotations

import json
import os
import uuid

import boto3
from rsf.functions.decorators import state

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "Items")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


@state("CreateItem")
def create_item(event: dict, context: dict) -> dict:
    """Create a new item from the request body.

    Expects a JSON body with item attributes. Generates a UUID for the item ID.

    Args:
        event: API Gateway event with body containing item data.
        context: Lambda execution context.

    Returns:
        HTTP 201 response with the created item including its generated ID.
    """
    body = json.loads(event.get("body", "{}"))
    item_id = str(uuid.uuid4())
    item = {"id": item_id, **body}
    table.put_item(Item=item)
    return {"statusCode": 201, "body": json.dumps(item)}
