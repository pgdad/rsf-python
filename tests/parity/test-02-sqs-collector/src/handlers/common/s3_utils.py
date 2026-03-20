"""S3 read/write utilities shared by RSF handlers and SF Lambda handlers."""
from __future__ import annotations
import json
import os
import boto3

_s3 = boto3.client("s3")

def get_bucket() -> str:
    return os.environ["PARITY_S3_BUCKET"]

def read_json_from_s3(key: str, bucket: str | None = None) -> dict | list:
    bucket = bucket or get_bucket()
    response = _s3.get_object(Bucket=bucket, Key=key)
    return json.loads(response["Body"].read().decode("utf-8"))

def write_json_to_s3(key: str, data: dict | list, bucket: str | None = None) -> None:
    bucket = bucket or get_bucket()
    _s3.put_object(
        Bucket=bucket, Key=key,
        Body=json.dumps(data, default=str).encode("utf-8"),
        ContentType="application/json",
    )
