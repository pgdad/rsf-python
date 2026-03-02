"""Archive the original uploaded file by moving it to the archived/ prefix."""

from __future__ import annotations

import os

import boto3
from rsf.functions.decorators import state

BUCKET = os.environ.get("S3_BUCKET", "uploads")
ARCHIVE_PREFIX = os.environ.get("ARCHIVE_PREFIX", "archived/")

s3 = boto3.client("s3")


@state("ProcessUpload")
def process_upload(event: dict, context: dict) -> dict:
    """Move the original file to the archived/ prefix after processing.

    Copies the file to the archive location and deletes the original.

    Args:
        event: Pipeline state with key and bucket fields.
        context: Lambda execution context.

    Returns:
        Updated pipeline state with archive_key.
    """
    key = event["key"]
    bucket = event.get("bucket", BUCKET)
    archive_key = ARCHIVE_PREFIX + key

    # Copy to archive
    s3.copy_object(
        Bucket=bucket,
        Key=archive_key,
        CopySource={"Bucket": bucket, "Key": key},
    )

    # Delete original
    s3.delete_object(Bucket=bucket, Key=key)

    return {
        **event,
        "archive_key": archive_key,
        "archived": True,
    }
