"""String intrinsic functions: States.Format, States.StringSplit."""

from __future__ import annotations

import json
from typing import Any

from rsf.functions.registry import intrinsic


@intrinsic("States.Format")
def states_format(template: str, *args: Any) -> str:
    """String interpolation with {} placeholders.

    Each {} is replaced in order with the string representation of the
    corresponding argument. Non-string values are JSON-serialized.
    """
    parts = template.split("{}")
    if len(parts) - 1 != len(args):
        raise ValueError(
            f"States.Format: template has {len(parts) - 1} placeholders but {len(args)} arguments were provided"
        )
    result: list[str] = [parts[0]]
    for i, arg in enumerate(args):
        if isinstance(arg, str):
            result.append(arg)
        else:
            result.append(json.dumps(arg))
        result.append(parts[i + 1])
    return "".join(result)


@intrinsic("States.StringSplit")
def states_string_split(string: str, delimiter: str) -> list[str]:
    """Split a string by a delimiter."""
    if not isinstance(string, str):
        raise TypeError("States.StringSplit: first argument must be a string")
    if not isinstance(delimiter, str):
        raise TypeError("States.StringSplit: second argument must be a string")
    return string.split(delimiter)
