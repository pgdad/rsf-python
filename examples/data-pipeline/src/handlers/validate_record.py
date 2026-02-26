"""ValidateRecord handler — validates that a record has required fields."""

import json
import logging

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


REQUIRED_FIELDS = {"id", "value"}


@state("ValidateRecord")
def validate_record(event: dict) -> dict:
    """Validate that a record contains all required fields.

    Expects a dict with at least 'id' and 'value' keys.
    Returns the record with a 'validated' flag set to True.
    Raises ValueError if required fields are missing.
    """
    record_id = event.get("id", "unknown")
    _log("ValidateRecord", "Validating record", recordId=record_id)

    missing = REQUIRED_FIELDS - set(event.keys())
    if missing:
        _log(
            "ValidateRecord",
            "Validation failed",
            recordId=record_id,
            missingFields=sorted(missing),
        )
        raise ValueError(f"Record {record_id} missing required fields: {sorted(missing)}")

    _log("ValidateRecord", "Record valid", recordId=record_id)

    return {**event, "validated": True}
