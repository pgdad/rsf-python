"""Unit tests for API Gateway CRUD handlers — mocks boto3 DynamoDB calls."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


@patch("handlers.create_item.table")
@patch("handlers.create_item.uuid.uuid4", return_value="test-uuid-1234")
def test_create_item_returns_201(mock_uuid: MagicMock, mock_table: MagicMock) -> None:
    """CreateItem handler returns 201 with generated ID."""
    from handlers.create_item import create_item

    event = {"body": json.dumps({"name": "Widget", "price": 9.99})}
    result = create_item(event, {})

    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["id"] == "test-uuid-1234"
    assert body["name"] == "Widget"
    assert body["price"] == 9.99
    mock_table.put_item.assert_called_once()


@patch("handlers.get_item.table")
def test_get_item_returns_200(mock_table: MagicMock) -> None:
    """GetItem handler returns 200 with item data."""
    mock_table.get_item.return_value = {"Item": {"id": "abc-123", "name": "Widget"}}
    from handlers.get_item import get_item

    event = {"pathParameters": {"id": "abc-123"}}
    result = get_item(event, {})

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["id"] == "abc-123"
    assert body["name"] == "Widget"


@patch("handlers.get_item.table")
def test_get_item_returns_404_when_not_found(mock_table: MagicMock) -> None:
    """GetItem handler returns 404 when item does not exist."""
    mock_table.get_item.return_value = {}
    from handlers.get_item import get_item

    event = {"pathParameters": {"id": "nonexistent"}}
    result = get_item(event, {})

    assert result["statusCode"] == 404
    body = json.loads(result["body"])
    assert "error" in body


@patch("handlers.update_item.table")
def test_update_item_returns_200(mock_table: MagicMock) -> None:
    """UpdateItem handler returns 200 with updated attributes."""
    mock_table.update_item.return_value = {"Attributes": {"id": "abc-123", "name": "Updated Widget", "price": 19.99}}
    from handlers.update_item import update_item

    event = {
        "pathParameters": {"id": "abc-123"},
        "body": json.dumps({"name": "Updated Widget", "price": 19.99}),
    }
    result = update_item(event, {})

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["name"] == "Updated Widget"


@patch("handlers.delete_item.table")
def test_delete_item_returns_204(mock_table: MagicMock) -> None:
    """DeleteItem handler returns 204 on successful deletion."""
    from handlers.delete_item import delete_item

    event = {"pathParameters": {"id": "abc-123"}}
    result = delete_item(event, {})

    assert result["statusCode"] == 204
    mock_table.delete_item.assert_called_once_with(Key={"id": "abc-123"})


@patch("handlers.list_items.table")
def test_list_items_returns_200_with_items(mock_table: MagicMock) -> None:
    """ListItems handler returns 200 with items array."""
    mock_table.scan.return_value = {
        "Items": [
            {"id": "1", "name": "Widget A"},
            {"id": "2", "name": "Widget B"},
        ]
    }
    from handlers.list_items import list_items

    result = list_items({}, {})

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body["items"]) == 2
    assert "next_token" not in body


@patch("handlers.list_items.table")
def test_list_items_returns_pagination_token(mock_table: MagicMock) -> None:
    """ListItems handler includes next_token when more pages exist."""
    mock_table.scan.return_value = {
        "Items": [{"id": "1", "name": "Widget A"}],
        "LastEvaluatedKey": {"id": "1"},
    }
    from handlers.list_items import list_items

    result = list_items({}, {})

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["next_token"] == "1"
