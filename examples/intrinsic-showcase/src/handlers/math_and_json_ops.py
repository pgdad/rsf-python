"""MathAndJsonOps handler -- performs math and JSON operations on accumulated data."""

import json
import logging
import random

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("MathAndJsonOps")
def math_and_json_ops(event: dict) -> dict:
    """Perform math and JSON operations on the accumulated workflow state.

    Reads from event["arrays"]["tagCount"] and event["strings"]["serialized"].
    Computes:
      - sum: tagCount + 10 (simulates States.MathAdd)
      - randomVal: random integer between 1 and 100 (simulates States.MathRandom)
      - parsed: parsed JSON object from serialized string (simulates States.StringToJson)

    Returns a dict with all three computed fields.
    """
    arrays = event.get("arrays", {})
    strings = event.get("strings", {})

    tag_count = arrays.get("tagCount", 0)
    serialized = strings.get("serialized", "[]")

    # Simulate States.MathAdd(tagCount, 10)
    sum_val = tag_count + 10

    # Simulate States.MathRandom(1, 100)
    random_val = random.randint(1, 100)

    # Simulate States.StringToJson(serialized)
    try:
        parsed = json.loads(serialized)
    except (json.JSONDecodeError, TypeError):
        parsed = None

    _log(
        "MathAndJsonOps",
        "Processing math and JSON operations",
        sum=sum_val,
        randomVal=random_val,
        parsed_type=type(parsed).__name__,
    )

    result = {
        "sum": sum_val,
        "randomVal": random_val,
        "parsed": parsed,
    }

    _log("MathAndJsonOps", "Math and JSON operations complete", result_keys=list(result.keys()))

    return result
