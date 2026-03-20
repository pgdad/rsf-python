"""Pure JSON processing logic — no AWS calls."""

from __future__ import annotations


def process_json(records: list[dict]) -> list[dict]:
    return [{k.lower(): v for k, v in record.items()} | {"validated": True} for record in records]
