"""Intrinsic function registry with @intrinsic decorator."""

from __future__ import annotations

from typing import Any, Callable

# Global registry: function_name → callable
_REGISTRY: dict[str, Callable[..., Any]] = {}


def intrinsic(name: str) -> Callable:
    """Decorator to register an intrinsic function.

    Usage:
        @intrinsic("States.Format")
        def states_format(template: str, *args: Any) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        if name in _REGISTRY:
            raise ValueError(f"Intrinsic function '{name}' already registered")
        _REGISTRY[name] = func
        return func
    return decorator


def get_intrinsic(name: str) -> Callable[..., Any]:
    """Get a registered intrinsic function by name."""
    if name not in _REGISTRY:
        raise KeyError(
            f"Unknown intrinsic function '{name}'. "
            f"Registered: {', '.join(sorted(_REGISTRY.keys()))}"
        )
    return _REGISTRY[name]


def registered_intrinsics() -> frozenset[str]:
    """Return the set of registered intrinsic function names."""
    return frozenset(_REGISTRY.keys())


def call_intrinsic(name: str, args: list[Any]) -> Any:
    """Call a registered intrinsic function with the given arguments."""
    func = get_intrinsic(name)
    return func(*args)


def clear() -> None:
    """Clear all registered intrinsic functions (for testing)."""
    _REGISTRY.clear()
