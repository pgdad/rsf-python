"""Transform uploaded data — downloads from S3, processes, and uploads result."""

from __future__ import annotations

import json
import os

import boto3
from rsf.functions.decorators import state

BUCKET = os.environ.get("S3_BUCKET", "uploads")
OUTPUT_PREFIX = os.environ.get("OUTPUT_PREFIX", "processed/")

s3 = boto3.client("s3")


@state("TransformData")
def transform_data(event: dict, context: dict) -> dict:
    """Download a file from S3, apply transformation, and upload the result.

    For CSV files: converts to JSON lines format.
    For JSON files: passes through with metadata enrichment.
    For other files: copies as-is to the processed prefix.

    Args:
        event: Pipeline state with key, bucket, size, and valid fields.
        context: Lambda execution context.

    Returns:
        Updated pipeline state with output_key pointing to the processed file.
    """
    key = event["key"]
    bucket = event.get("bucket", BUCKET)

    # Download original file
    response = s3.get_object(Bucket=bucket, Key=key)
    content = response["Body"].read().decode("utf-8")

    # Determine transformation based on file extension
    ext = ""
    if "." in key:
        ext = "." + key.rsplit(".", 1)[-1].lower()

    if ext == ".csv":
        # CSV to JSON lines: split rows, first row is header
        lines = content.strip().split("\n")
        if len(lines) > 1:
            headers = [h.strip() for h in lines[0].split(",")]
            records = []
            for line in lines[1:]:
                values = [v.strip() for v in line.split(",")]
                record = dict(zip(headers, values))
                records.append(record)
            output_content = "\n".join(json.dumps(r) for r in records)
        else:
            output_content = content
        output_key = OUTPUT_PREFIX + key.rsplit(".", 1)[0] + ".jsonl"
    elif ext == ".json":
        # Enrich JSON with processing metadata
        data = json.loads(content)
        if isinstance(data, dict):
            data["_processed"] = True
            data["_source_key"] = key
        output_content = json.dumps(data)
        output_key = OUTPUT_PREFIX + key
    else:
        # Pass through
        output_content = content
        output_key = OUTPUT_PREFIX + key

    # Upload processed file
    s3.put_object(
        Bucket=bucket,
        Key=output_key,
        Body=output_content.encode("utf-8"),
        ContentType="application/json",
    )

    return {
        **event,
        "output_key": output_key,
        "transformed": True,
    }
