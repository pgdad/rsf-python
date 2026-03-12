"""StringOperations handler -- performs string operations on prepared data."""

import base64
import hashlib
import json
import logging

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("StringOperations")
def string_operations(event: dict) -> dict:
    """Perform string operations on the prepared data.

    Reads event["prepared"]["userName"] and computes:
      - decoded: base64-encode then decode the user name (demonstrates encode/decode)
      - hash: SHA-256 hash of the user name
      - serialized: JSON-serialized name parts array
      - formatted: human-readable summary string

    Returns a dict with all four computed fields.
    """
    prepared = event.get("prepared", {})
    user_name = prepared.get("userName", "")
    name_parts = user_name.split(" ") if user_name else []

    # Simulate intrinsic functions: Base64Encode + Base64Decode
    encoded = base64.b64encode(user_name.encode()).decode()
    decoded = base64.b64decode(encoded).decode()

    # Simulate States.Hash
    hash_val = hashlib.sha256(f"Welcome, {user_name}!".encode()).hexdigest()[:16]

    # Simulate States.JsonToString
    serialized = json.dumps(name_parts)

    # Simulate States.Format
    formatted = f"{user_name} has {len(name_parts)} name parts"

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
