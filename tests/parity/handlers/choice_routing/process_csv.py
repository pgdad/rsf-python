"""Pure CSV processing logic — no AWS calls."""
from __future__ import annotations
import csv
import io

def process_csv(csv_text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(csv_text))
    return [dict(row) for row in reader]
