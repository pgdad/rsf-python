"""Validate uploaded S3 file metadata — checks extension and size limits."""

from __future__ import annotations

import os

import boto3
from rsf.functions.decorators import state

BUCKET = os.environ.get("S3_BUCKET", "uploads")
MAX_SIZE = int(os.environ.get("MAX_FILE_SIZE", str(50 * 1024 * 1024)))  # 50MB
ALLOWED_EXTENSIONS = os.environ.get("ALLOWED_EXTENSIONS", ".csv,.json,.parquet").split(",")

s3 = boto3.client("s3")


@state("ValidateFile")
def validate_file(event: dict, context: dict) -> dict:
    """Validate an uploaded S3 file by checking its size and extension.

    Args:
        event: S3 event notification with detail.object.key.
        context: Lambda execution context.

    Returns:
        Dict with key, size, valid flag, and bucket name.
    """
    key = event.get("detail", {}).get("object", {}).get("key", "")
    head = s3.head_object(Bucket=BUCKET, Key=key)
    size = head["ContentLength"]
    ext = ""
    if "." in key:
        ext = "." + key.rsplit(".", 1)[-1].lower()
    valid = size <= MAX_SIZE and ext in ALLOWED_EXTENSIONS
    return {"key": key, "size": size, "valid": valid, "bucket": BUCKET}
