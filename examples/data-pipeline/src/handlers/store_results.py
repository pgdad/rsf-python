"""StoreResults handler — simulates a DynamoDB batch write operation."""

import json
import logging

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("StoreResults")
def store_results(event: dict) -> dict:
    """Simulate writing items to a DynamoDB table via batch write.

    Receives the full pipeline state. Reads table name from
    event["config"]["config"]["tableName"] (set by InitPipeline) and
    items from event["transformed"] (set by TransformRecords).
    Returns a summary with 'itemsWritten' count and 'tableName'.
    """
    config = event.get("config", {})
    table_name = config.get("config", {}).get("tableName", "unknown-table")
    items = event.get("transformed", [])

    _log(
        "StoreResults",
        "Starting DynamoDB batch write",
        tableName=table_name,
        itemCount=len(items),
    )

    # Simulate writing each item
    for i, item in enumerate(items):
        _log(
            "StoreResults",
            "Writing item",
            tableName=table_name,
            itemIndex=i,
            itemId=item.get("id", "unknown"),
        )

    _log(
        "StoreResults",
        "Batch write complete",
        tableName=table_name,
        itemsWritten=len(items),
    )

    return {"itemsWritten": len(items), "tableName": table_name}
