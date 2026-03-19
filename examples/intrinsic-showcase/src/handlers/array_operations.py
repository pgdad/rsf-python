"""ArrayOperations handler -- performs array operations on prepared data."""

import json
import logging

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("ArrayOperations")
def array_operations(event: dict) -> dict:
    """Perform array operations on the prepared data.

    Reads event["prepared"]["tagArray"] and computes:
      - range: list [1, 3, 5, 7, 9] (simulates States.ArrayRange)
      - partitioned: tag array split into chunks of 2
      - contains: does tag array contain 'demo'?
      - firstTag: first element of tag array
      - tagCount: length of tag array
      - uniqueTags: deduplicated array

    Returns a dict with all six computed fields.
    """
    prepared = event.get("prepared", {})
    tag_array = prepared.get("tagArray", [])

    # Simulate States.ArrayRange(1, 10, 2)
    range_val = list(range(1, 10, 2))

    # Simulate States.ArrayPartition(tagArray, 2)
    partitioned = [tag_array[i : i + 2] for i in range(0, len(tag_array), 2)]

    # Simulate States.ArrayContains(tagArray, 'demo')
    contains = "demo" in tag_array

    # Simulate States.ArrayGetItem(tagArray, 0)
    first_tag = tag_array[0] if tag_array else ""

    # Simulate States.ArrayLength(tagArray)
    tag_count = len(tag_array)

    # Simulate States.ArrayUnique(['a', 'b', 'a', 'c', 'b'])
    sample = ["a", "b", "a", "c", "b"]
    unique_tags = list(dict.fromkeys(sample))

    _log(
        "ArrayOperations",
        "Processing array operations",
        range_length=len(range_val),
        partitioned_chunks=len(partitioned),
        contains=contains,
        firstTag=first_tag,
        tagCount=tag_count,
        uniqueTagCount=len(unique_tags),
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
