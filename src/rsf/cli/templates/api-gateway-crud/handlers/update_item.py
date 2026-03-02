"""Update an existing item in DynamoDB."""

from __future__ import annotations

import json
import os

import boto3
from rsf.functions.decorators import state

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "Items")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


@state("UpdateItem")
def update_item(event: dict, context: dict) -> dict:
    """Update an item identified by path parameter ID with the request body fields.

    Args:
        event: API Gateway event with pathParameters.id and body with update fields.
        context: Lambda execution context.

    Returns:
        HTTP 200 with the updated item attributes.
    """
    item_id = event.get("pathParameters", {}).get("id", "")
    body = json.loads(event.get("body", "{}"))

    # Build update expression dynamically from body keys
    update_parts = []
    attr_names = {}
    attr_values = {}
    for idx, (key, value) in enumerate(body.items()):
        if key == "id":
            continue  # Skip primary key
        placeholder = f"#k{idx}"
        value_placeholder = f":v{idx}"
        update_parts.append(f"{placeholder} = {value_placeholder}")
        attr_names[placeholder] = key
        attr_values[value_placeholder] = value

    if not update_parts:
        return {"statusCode": 400, "body": json.dumps({"error": "No fields to update"})}

    update_expr = "SET " + ", ".join(update_parts)
    result = table.update_item(
        Key={"id": item_id},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=attr_names,
        ExpressionAttributeValues=attr_values,
        ReturnValues="ALL_NEW",
    )
    return {"statusCode": 200, "body": json.dumps(result.get("Attributes", {}))}
