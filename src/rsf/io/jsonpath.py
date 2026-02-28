"""ASL-subset JSONPath evaluator.

Supports:
- Root: $
- Dot notation: $.field.subfield
- Bracket notation: $['field name']
- Array indexing: $.array[0]
- Variable references: $varName, $varName.field

Does NOT support: filters, wildcards, recursive descent, functions.
"""

from __future__ import annotations

import re
from typing import Any

from rsf.io.types import VariableStoreProtocol


class JSONPathError(Exception):
    """Raised when a JSONPath expression is invalid or cannot be evaluated."""


def evaluate_jsonpath(
    data: Any,
    path: str,
    variables: VariableStoreProtocol | None = None,
    context: Any | None = None,
) -> Any:
    """Evaluate an ASL-subset JSONPath expression against data.

    Args:
        data: The input data to query.
        path: A JSONPath expression starting with '$'.
        variables: Optional variable store for $varName references.
        context: Optional context object for $$ references.

    Returns:
        The value at the specified path.
    """
    if path is None:
        return data

    path = path.strip()

    # Context object reference: $$
    if path.startswith("$$"):
        if context is None:
            raise JSONPathError("Context object ($$) not available")
        if path == "$$":
            return context
        # $$. notation
        remainder = path[2:]
        if remainder.startswith("."):
            remainder = remainder[1:]
        return _resolve_dotted_path(context, remainder)

    # Variable reference: $varName (not $ alone, not $.something)
    if path.startswith("$") and len(path) > 1 and path[1] not in (".", "["):
        if variables is None:
            raise JSONPathError(f"Variable store not available for '{path}'")
        # Extract variable name and optional path
        match = re.match(r"^\$([a-zA-Z_][a-zA-Z0-9_]*)(.*)", path)
        if not match:
            raise JSONPathError(f"Invalid variable reference: '{path}'")
        var_name = match.group(1)
        remainder = match.group(2)
        value = variables.get(var_name)
        if remainder:
            if remainder.startswith("."):
                remainder = remainder[1:]
            return _resolve_dotted_path(value, remainder)
        return value

    # Root reference: $
    if path == "$":
        return data

    # $. notation
    if not path.startswith("$.") and not path.startswith("$["):
        raise JSONPathError(f"Invalid JSONPath: '{path}' (must start with '$')")

    remainder = path[1:]  # Strip the leading $
    if remainder.startswith("."):
        remainder = remainder[1:]

    if not remainder:
        return data

    return _resolve_path(data, remainder)


def _resolve_path(data: Any, path: str) -> Any:
    """Resolve a path (after stripping $.) against data."""
    tokens = _tokenize(path)
    current = data
    for token in tokens:
        current = _access(current, token)
    return current


def _resolve_dotted_path(data: Any, path: str) -> Any:
    """Resolve a dotted path against an object (dict or object with attrs)."""
    if not path:
        return data
    return _resolve_path(data, path)


def _tokenize(path: str) -> list[str | int]:
    """Tokenize a JSONPath remainder into field names and array indices."""
    tokens: list[str | int] = []
    i = 0
    while i < len(path):
        if path[i] == "[":
            # Bracket notation
            end = path.index("]", i)
            inner = path[i + 1 : end]
            if inner.startswith("'") and inner.endswith("'"):
                # String key: ['field name']
                tokens.append(inner[1:-1])
            elif inner.startswith('"') and inner.endswith('"'):
                tokens.append(inner[1:-1])
            else:
                # Numeric index
                tokens.append(int(inner))
            i = end + 1
            if i < len(path) and path[i] == ".":
                i += 1  # Skip dot after bracket
        elif path[i] == ".":
            i += 1
        else:
            # Dot notation field
            match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)", path[i:])
            if match:
                tokens.append(match.group(1))
                i += len(match.group(1))
            else:
                raise JSONPathError(f"Invalid path segment at position {i}: '{path[i:]}'")
    return tokens


def _access(data: Any, key: str | int) -> Any:
    """Access a single key/index on data."""
    if isinstance(key, int):
        if not isinstance(data, (list, tuple)):
            raise JSONPathError(f"Cannot index non-array with [{key}]")
        try:
            return data[key]
        except IndexError:
            raise JSONPathError(f"Array index {key} out of range")

    # String key — try dict first, then attribute
    if isinstance(data, dict):
        if key not in data:
            raise JSONPathError(f"Key '{key}' not found in object")
        return data[key]

    # Try attribute access for context objects
    if hasattr(data, key):
        return getattr(data, key)

    raise JSONPathError(f"Cannot access '{key}' on {type(data).__name__}")
