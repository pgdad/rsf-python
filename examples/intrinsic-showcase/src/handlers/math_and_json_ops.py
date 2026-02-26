"""MathAndJsonOps handler -- processes math and JSON intrinsic function results."""

import json
import logging

from rsf.registry import state

logger = logging.getLogger(__name__)


def _log(step_name: str, message: str, **extra):
    logger.info(json.dumps({"step_name": step_name, "message": message, **extra}))


@state("MathAndJsonOps")
def math_and_json_ops(event: dict) -> dict:
    """Process math and JSON operations from intrinsic function evaluation.

    Receives the effective input after I/O pipeline processing (Parameters
    have already been resolved by the runtime). Returns the computed results
    for downstream states.

    Expected keys in *event* (after Parameters resolution):
        sum       -- result of MathAdd (tagCount + 10)
        randomVal -- random integer between 1 and 100
        parsed    -- parsed JSON object from serialized string
    """
    sum_val = event.get("sum", 0)
    random_val = event.get("randomVal", 0)
    parsed = event.get("parsed", None)

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
