"""SF Lambda handler for the ETL pipeline. Only used for Map's TransformOne."""
from __future__ import annotations
from etl.transform import transform_record

def handler(event: dict, context) -> dict:
    return transform_record(event)
