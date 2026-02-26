"""ArrayOperations handler -- processes array-related intrinsic function results."""

import json
import logging

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("ArrayOperations")
def array_operations(event: dict) -> dict:
    """Process array operations from intrinsic function evaluation.

    Receives the effective input after I/O pipeline processing (Parameters
    have already been resolved by the runtime). Returns the computed results
    for downstream states.

    Expected keys in *event* (after Parameters resolution):
        range       -- number range [1, 3, 5, 7, 9]
        partitioned -- tag array split into chunks of 2
        contains    -- boolean: does tag array contain 'demo'?
        firstTag    -- first element of tag array
        tagCount    -- length of tag array
        uniqueTags  -- deduplicated array
    """
    range_val = event.get("range", [])
    partitioned = event.get("partitioned", [])
    contains = event.get("contains", False)
    first_tag = event.get("firstTag", "")
    tag_count = event.get("tagCount", 0)
    unique_tags = event.get("uniqueTags", [])

    _log(
        "ArrayOperations",
        "Processing array operations",
        range_length=len(range_val) if isinstance(range_val, list) else 0,
        partitioned_chunks=len(partitioned) if isinstance(partitioned, list) else 0,
        contains=contains,
        firstTag=first_tag,
        tagCount=tag_count,
        uniqueTagCount=len(unique_tags) if isinstance(unique_tags, list) else 0,
    )

    result = {
        "range": range_val,
        "partitioned": partitioned,
        "contains": contains,
        "firstTag": first_tag,
        "tagCount": tag_count,
        "uniqueTags": unique_tags,
    }

    _log("ArrayOperations", "Array operations complete", result_keys=list(result.keys()))

    return result
