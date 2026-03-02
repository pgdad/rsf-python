"""Retrieve a single item from DynamoDB by ID."""

from __future__ import annotations

import json
import os

import boto3
from rsf.functions.decorators import state

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "Items")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


@state("GetItem")
def get_item(event: dict, context: dict) -> dict:
    """Fetch an item by its ID from the path parameters.

    Args:
        event: API Gateway event with pathParameters.id.
        context: Lambda execution context.

    Returns:
        HTTP 200 with item data, or HTTP 404 if not found.
    """
    item_id = event.get("pathParameters", {}).get("id", "")
    result = table.get_item(Key={"id": item_id})
    item = result.get("Item")
    if item is None:
        return {"statusCode": 404, "body": json.dumps({"error": "Item not found"})}
    return {"statusCode": 200, "body": json.dumps(item)}
