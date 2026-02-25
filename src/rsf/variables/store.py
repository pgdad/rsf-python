"""Runtime variable store for ASL variables (Assign/Output)."""

from __future__ import annotations

from typing import Any


class VariableStore:
    """Runtime variable store supporting $varName references.

    Variables are set via Assign/Output fields in state definitions
    and accessed via $varName in JSONPath expressions.
    """

    def __init__(self) -> None:
        self._variables: dict[str, Any] = {}

    def get(self, name: str) -> Any:
        """Get a variable by name.

        Raises KeyError if the variable does not exist.
        """
        if name not in self._variables:
            raise KeyError(f"Variable '${name}' is not defined")
        return self._variables[name]

    def set(self, name: str, value: Any) -> None:
        """Set a variable value."""
        self._variables[name] = value

    def has(self, name: str) -> bool:
        """Check if a variable exists."""
        return name in self._variables

    def clear(self) -> None:
        """Clear all variables."""
        self._variables.clear()

    def all(self) -> dict[str, Any]:
        """Return a copy of all variables."""
        return dict(self._variables)

    def __repr__(self) -> str:
        return f"VariableStore({self._variables})"
