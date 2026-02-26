"""EnrichRecord handler — adds computed fields to a validated record."""

import hashlib
import json
import logging
from datetime import datetime, timezone

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("EnrichRecord")
def enrich_record(event: dict) -> dict:
    """Enrich a record by adding a timestamp and a content hash.

    Expects a validated record dict with at least 'id' and 'value'.
    Returns the record with 'enrichedAt' (ISO timestamp) and 'hash' fields added.
    """
    record_id = event.get("id", "unknown")
    _log("EnrichRecord", "Enriching record", recordId=record_id)

    # Compute a deterministic hash of the record content
    content_str = json.dumps(event, sort_keys=True)
    content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]

    enriched = {
        **event,
        "enrichedAt": datetime.now(timezone.utc).isoformat(),
        "hash": content_hash,
    }

    _log("EnrichRecord", "Enrichment complete", recordId=record_id, hash=content_hash)

    return enriched
