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

    Expects input with 'bucket', 'prefix', and optionally 'maxItems'.
    Returns a dict with 'items' (list of records) and 'totalCount'.
    """
    bucket = event.get("bucket", "default-bucket")
    prefix = event.get("prefix", "data/")
    max_items = event.get("maxItems", 100)

    _log(
        "FetchRecords",
        "Fetching records from S3",
        bucket=bucket,
        prefix=prefix,
        maxItems=max_items,
    )

    # Simulate fetched records
    items = [
        {"id": f"rec-{i}", "value": i * 10, "source": f"s3://{bucket}/{prefix}{i}.json"}
        for i in range(1, min(max_items, 6) + 1)
    ]

    _log("FetchRecords", "Fetch complete", totalCount=len(items))

    return {"items": items, "totalCount": len(items)}
