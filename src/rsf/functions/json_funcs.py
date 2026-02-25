"""JSON intrinsic functions: States.StringToJson, States.JsonToString."""

from __future__ import annotations

import json
from typing import Any

from rsf.functions.registry import intrinsic


@intrinsic("States.StringToJson")
def states_string_to_json(string: str) -> Any:
    """Parse a JSON string into a Python object."""
    if not isinstance(string, str):
        raise TypeError("States.StringToJson: argument must be a string")
    return json.loads(string)


@intrinsic("States.JsonToString")
def states_json_to_string(obj: Any) -> str:
    """Serialize a Python object to a JSON string."""
    return json.dumps(obj, separators=(",", ":"))
