"""Delete an item from DynamoDB by ID."""

from __future__ import annotations

import json
import os

import boto3
from rsf.functions.decorators import state

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "Items")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


@state("DeleteItem")
def delete_item(event: dict, context: dict) -> dict:
    """Delete an item identified by its path parameter ID.

    Args:
        event: API Gateway event with pathParameters.id.
        context: Lambda execution context.

    Returns:
        HTTP 204 (no content) on successful deletion.
    """
    item_id = event.get("pathParameters", {}).get("id", "")
    table.delete_item(Key={"id": item_id})
    return {"statusCode": 204, "body": json.dumps({"message": "Item deleted"})}
