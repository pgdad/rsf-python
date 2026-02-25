"""ResultPath merge logic.

ResultPath determines how task results are merged into the raw input:
- "$" → result replaces entire output
- "$.field" → deep merge result at path into copy of raw input
- null → discard result, return copy of raw input

Critical: ResultPath merges into the RAW input (before InputPath), not effective input.
Always deep-copies to prevent mutation.
"""

from __future__ import annotations

import copy
from typing import Any

from rsf.io.jsonpath import JSONPathError


def apply_result_path(
    raw_input: Any,
    result: Any,
    result_path: str | None,
) -> Any:
    """Merge task result into raw input according to ResultPath.

    Args:
        raw_input: The original raw input (before InputPath filtering).
        result: The task result (possibly filtered by ResultSelector).
        result_path: The ResultPath specification.

    Returns:
        The merged output.
    """
    # null → discard result
    if result_path is None:
        return copy.deepcopy(raw_input)

    # "$" → replace entirely
    if result_path == "$":
        return copy.deepcopy(result)

    # "$.field" → merge at path
    if result_path.startswith("$."):
        output = copy.deepcopy(raw_input)
        if not isinstance(output, dict):
            output = {}
        path_parts = result_path[2:].split(".")
        _set_nested(output, path_parts, result)
        return output

    raise JSONPathError(f"Invalid ResultPath: '{result_path}'")


def _set_nested(data: dict, path_parts: list[str], value: Any) -> None:
    """Set a value at a nested path in a dict, creating intermediate dicts."""
    current = data
    for part in path_parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[path_parts[-1]] = copy.deepcopy(value)
