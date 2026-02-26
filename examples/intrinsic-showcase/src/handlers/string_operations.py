"""StringOperations handler -- processes string-related intrinsic function results."""

import json
import logging

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("StringOperations")
def string_operations(event: dict) -> dict:
    """Process string operations from intrinsic function evaluation.

    Receives the effective input after I/O pipeline processing (Parameters
    have already been resolved by the runtime). Returns the computed results
    for downstream states.

    Expected keys in *event* (after Parameters resolution):
        decoded   -- base64-decoded user name
        hash      -- SHA-256 hash of the greeting
        serialized -- JSON-serialized name-parts array
        formatted  -- human-readable summary string
    """
    decoded = event.get("decoded", "")
    hash_val = event.get("hash", "")
    serialized = event.get("serialized", "")
    formatted = event.get("formatted", "")

    _log(
        "StringOperations",
        "Processing string operations",
        decoded=decoded,
        hash_length=len(hash_val),
        serialized_length=len(serialized),
        formatted=formatted,
    )

    result = {
        "decoded": decoded,
        "hash": hash_val,
        "serialized": serialized,
        "formatted": formatted,
    }

    _log("StringOperations", "String operations complete", result_keys=list(result.keys()))

    return result
