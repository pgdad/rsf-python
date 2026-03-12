"""FetchRecords handler — simulates fetching records from an S3 bucket."""

import json
import logging

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("FetchRecords")
def fetch_records(event: dict) -> dict:
    """Simulate fetching records from S3.

    Receives the full pipeline state. Reads bucket and prefix from
    event["source"] if present, otherwise uses defaults.
    Returns a dict with 'records' (list of records) and 'count'.
    """
    source = event.get("source", {})
    bucket = source.get("bucket", "default-bucket")
    prefix = source.get("prefix", "data/")
    max_items = source.get("maxItems", 100)

    _log(
        "FetchRecords",
        "Fetching records from S3",
        bucket=bucket,
        prefix=prefix,
        maxItems=max_items,
    )

    # Simulate fetched records
    records = [
        {"id": f"rec-{i}", "value": i * 10, "source": f"s3://{bucket}/{prefix}{i}.json"}
        for i in range(1, min(max_items, 6) + 1)
    ]

    _log("FetchRecords", "Fetch complete", totalCount=len(records))

    return {"records": records, "count": len(records)}
