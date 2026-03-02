"""List all items from DynamoDB with pagination support."""

from __future__ import annotations

import json
import os

import boto3
from rsf.functions.decorators import state

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "Items")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


@state("ListItems")
def list_items(event: dict, context: dict) -> dict:
    """Scan the DynamoDB table and return all items.

    Supports pagination via the 'next_token' query parameter, which maps to
    DynamoDB's ExclusiveStartKey.

    Args:
        event: API Gateway event, optionally with queryStringParameters.next_token.
        context: Lambda execution context.

    Returns:
        HTTP 200 with items array and optional next_token for pagination.
    """
    query_params = event.get("queryStringParameters") or {}
    scan_kwargs: dict = {}

    next_token = query_params.get("next_token")
    if next_token:
        scan_kwargs["ExclusiveStartKey"] = {"id": next_token}

    result = table.scan(**scan_kwargs)
    items = result.get("Items", [])

    response_body: dict = {"items": items}
    last_key = result.get("LastEvaluatedKey")
    if last_key:
        response_body["next_token"] = last_key["id"]

    return {"statusCode": 200, "body": json.dumps(response_body)}
