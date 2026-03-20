"""RSF @state handlers for the ETL pipeline."""

from __future__ import annotations
from rsf.registry import state
from handlers.common.s3_utils import read_json_from_s3, write_json_to_s3
from handlers.etl.transform import transform_record


@state("ReadFromS3")
def read_from_s3(event: dict) -> dict:
    key = event["source_key"]
    data = read_json_from_s3(key)
    return {**event, "records": data}


@state("TransformOne")
def transform_one_handler(event: dict) -> dict:
    return transform_record(event)


@state("WriteETLResult")
def write_etl_result(event: dict) -> dict:
    output_key = event["output_key"]
    write_json_to_s3(output_key, event["records"])
    return {**event, "written": True, "output_key": output_key}
