"""Pure transformation logic — no AWS calls, no decorators."""
from __future__ import annotations
from datetime import datetime, timezone

def transform_record(record: dict) -> dict:
    return {**record, "name": record.get("name", "").upper(), "processed_at": datetime.now(timezone.utc).isoformat()}
