"""Handler registry for RSF workflow state handlers.

Provides @state and @startup decorators for registering handler functions
and auto-discovery of handler modules.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable


_handlers: dict[str, Callable] = {}
_startup_hooks: list[Callable] = []


def state(name: str) -> Callable:
    """Decorator to register a function as a handler for a named state.

    Args:
        name: The state name this handler maps to. Must be non-empty.

    Raises:
        ValueError: If name is empty or a handler is already registered for this name.
    """
    if not name or not name.strip():
        raise ValueError("State name must be a non-empty string")

    def decorator(func: Callable) -> Callable:
        if name in _handlers:
            raise ValueError(f"Duplicate handler for state '{name}': {_handlers[name].__name__} already registered")
        _handlers[name] = func
        return func

    return decorator


def startup(func: Callable) -> Callable:
    """Decorator to register a cold-start initialization hook.

    Startup hooks run once per Lambda cold start, before any handler.
    """
    _startup_hooks.append(func)
    return func


def get_handler(name: str) -> Callable:
    """Retrieve the handler function for a named state.

    Args:
        name: The state name to look up.

    Raises:
        KeyError: If no handler is registered for this name.
    """
    if name not in _handlers:
        registered = sorted(_handlers.keys())
        raise KeyError(f"No handler registered for state '{name}'. Registered states: {registered}")
    return _handlers[name]


def get_startup_hooks() -> list[Callable]:
    """Return the list of registered startup hooks."""
    return list(_startup_hooks)


def registered_states() -> frozenset[str]:
    """Return the set of all registered state names."""
    return frozenset(_handlers.keys())


def clear() -> None:
    """Remove all registered handlers. Used for test isolation."""
    _handlers.clear()


def clear_startup_hooks() -> None:
    """Remove all registered startup hooks. Used for test isolation."""
    _startup_hooks.clear()


def discover_handlers(directory: str | Path) -> None:
    """Import all .py files in directory to trigger @state registration.

    Args:
        directory: Path to the handlers directory.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return

    for py_file in sorted(directory.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        module_name = f"handlers.{py_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
