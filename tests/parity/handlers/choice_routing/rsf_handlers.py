"""RSF @state handlers for choice-based format routing."""

from __future__ import annotations
import json
from rsf.registry import state
from handlers.common.s3_utils import read_json_from_s3, write_json_to_s3
from handlers.choice_routing.process_csv import process_csv
from handlers.choice_routing.process_json import process_json


@state("ReadConfig")
def read_config(event: dict) -> dict:
    config = read_json_from_s3(event["config_key"])
    return {**event, **config}


@state("ProcessCSV")
def process_csv_handler(event: dict) -> dict:
    csv_data = read_json_from_s3(event["source_key"])
    records = process_csv(csv_data if isinstance(csv_data, str) else json.dumps(csv_data))
    return {**event, "records": records, "record_count": len(records)}


@state("ProcessJSON")
def process_json_handler(event: dict) -> dict:
    raw_records = read_json_from_s3(event["source_key"])
    records = process_json(raw_records)
    return {**event, "records": records, "record_count": len(records)}


@state("WriteResult")
def write_result(event: dict) -> dict:
    fmt = event["format"]
    output_key = f"{event['output_prefix']}/{fmt}/result.json"
    write_json_to_s3(output_key, event["records"])
    return {**event, "output_key": output_key, "written": True}
