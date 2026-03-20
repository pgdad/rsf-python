"""SF Lambda handlers for choice-based format routing."""

from __future__ import annotations
from choice_routing.process_csv import process_csv
from choice_routing.process_json import process_json


def csv_handler(event: dict, context) -> dict:
    csv_text = event.get("csv_text", "")
    records = process_csv(csv_text)
    return {"records": records, "record_count": len(records)}


def json_handler(event: dict, context) -> dict:
    raw_records = event.get("records", [])
    records = process_json(raw_records)
    return {"records": records, "record_count": len(records)}
