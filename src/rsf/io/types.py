"""I/O processing type definitions."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class VariableStoreProtocol(Protocol):
    """Protocol for variable stores used in I/O processing."""

    def get(self, name: str) -> Any: ...
    def set(self, name: str, value: Any) -> None: ...
