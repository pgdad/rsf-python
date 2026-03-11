"""Unit tests for S3 event pipeline handlers — mocks boto3 S3 and SNS calls."""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock, patch


@patch("handlers.validate_file.s3")
def test_validate_file_valid_csv(mock_s3: MagicMock) -> None:
    """ValidateFile returns valid=True for a small CSV file."""
    mock_s3.head_object.return_value = {"ContentLength": 1024}
    from handlers.validate_file import validate_file

    event = {"detail": {"object": {"key": "data/report.csv"}}}
    result = validate_file(event, {})

    assert result["valid"] is True
    assert result["key"] == "data/report.csv"
    assert result["size"] == 1024


@patch("handlers.validate_file.s3")
def test_validate_file_oversized_rejected(mock_s3: MagicMock) -> None:
    """ValidateFile returns valid=False for files exceeding MAX_SIZE."""
    mock_s3.head_object.return_value = {"ContentLength": 100_000_000}  # 100MB
    from handlers.validate_file import validate_file

    event = {"detail": {"object": {"key": "data/huge.csv"}}}
    result = validate_file(event, {})

    assert result["valid"] is False


@patch("handlers.validate_file.s3")
def test_validate_file_wrong_extension_rejected(mock_s3: MagicMock) -> None:
    """ValidateFile returns valid=False for disallowed file extensions."""
    mock_s3.head_object.return_value = {"ContentLength": 100}
    from handlers.validate_file import validate_file

    event = {"detail": {"object": {"key": "data/script.exe"}}}
    result = validate_file(event, {})

    assert result["valid"] is False


@patch("handlers.transform_data.s3")
def test_transform_csv_to_jsonl(mock_s3: MagicMock) -> None:
    """TransformData converts CSV to JSON lines format."""
    csv_content = "name,age\nAlice,30\nBob,25"
    mock_s3.get_object.return_value = {"Body": BytesIO(csv_content.encode())}
    from handlers.transform_data import transform_data

    event = {"key": "data/people.csv", "bucket": "uploads", "valid": True, "size": 100}
    result = transform_data(event, {})

    assert result["transformed"] is True
    assert result["output_key"] == "processed/data/people.jsonl"
    mock_s3.put_object.assert_called_once()
    put_call = mock_s3.put_object.call_args
    body = put_call[1]["Body"].decode()
    lines = body.strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"name": "Alice", "age": "30"}


@patch("handlers.process_upload.s3")
def test_process_upload_archives_file(mock_s3: MagicMock) -> None:
    """ProcessUpload moves original file to archived/ prefix."""
    from handlers.process_upload import process_upload

    event = {"key": "data/report.csv", "bucket": "uploads", "valid": True, "size": 100}
    result = process_upload(event, {})

    assert result["archived"] is True
    assert result["archive_key"] == "archived/data/report.csv"
    mock_s3.copy_object.assert_called_once()
    mock_s3.delete_object.assert_called_once_with(Bucket="uploads", Key="data/report.csv")


@patch("handlers.notify_complete.sns")
def test_notify_complete_sends_success(mock_sns: MagicMock) -> None:
    """NotifyComplete publishes success notification to SNS."""
    from handlers.notify_complete import notify_complete

    with patch("handlers.notify_complete.TOPIC_ARN", "arn:aws:sns:us-east-2:123:topic"):
        event = {
            "key": "data/report.csv",
            "valid": True,
            "output_key": "processed/data/report.jsonl",
            "archive_key": "archived/data/report.csv",
            "size": 1024,
        }
        result = notify_complete(event, {})

    assert result["notified"] is True
    assert result["notification_status"] == "sent"
    mock_sns.publish.assert_called_once()
    publish_call = mock_sns.publish.call_args
    message = json.loads(publish_call[1]["Message"])
    assert message["status"] == "success"


@patch("handlers.notify_complete.sns")
def test_notify_complete_skips_without_topic(mock_sns: MagicMock) -> None:
    """NotifyComplete skips SNS publish when TOPIC_ARN is empty."""
    from handlers.notify_complete import notify_complete

    with patch("handlers.notify_complete.TOPIC_ARN", ""):
        event = {"key": "data/report.csv", "valid": True, "size": 100}
        result = notify_complete(event, {})

    assert result["notification_status"] == "skipped"
    mock_sns.publish.assert_not_called()
