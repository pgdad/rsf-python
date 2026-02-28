"""Variable resolver — detects and resolves $varName references."""

from __future__ import annotations

import re
from typing import Any

from rsf.variables.store import VariableStore

# Pattern to detect variable references: $varName (not $ alone, not $.path, not $$)
VARIABLE_PATTERN = re.compile(r"^\$([a-zA-Z_][a-zA-Z0-9_]*)$")


def is_variable_reference(value: str) -> bool:
    """Check if a string is a $varName variable reference."""
    return bool(VARIABLE_PATTERN.match(value))


def extract_variable_name(value: str) -> str | None:
    """Extract the variable name from a $varName reference, or None."""
    match = VARIABLE_PATTERN.match(value)
    return match.group(1) if match else None


def apply_assign(store: VariableStore, assign: dict[str, Any] | None, data: Any) -> None:
    """Apply Assign field — set variables from state output.

    Each key in the assign dict becomes a variable name, with the value
    being either a literal or a reference to resolve from data.
    """
    if assign is None:
        return
    for name, value in assign.items():
        store.set(name, value)
