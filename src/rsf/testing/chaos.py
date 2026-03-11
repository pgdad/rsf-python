"""Chaos injection for RSF workflow testing.

Provides ChaosFixture to inject failures (timeout, exception, throttle, custom)
into specific workflow states during local mock SDK test runs.

Usage as pytest fixture:
    def test_retry_logic():
        chaos = ChaosFixture()
        chaos.inject_failure("ValidateOrder", "timeout")
        ctx = chaos.patch(MockDurableContext())
        # ... run workflow -- ValidateOrder will raise ChaosTimeoutError

Usage as standalone:
    from rsf.testing.chaos import ChaosFixture
    chaos = ChaosFixture()
    chaos.inject_failure("StateName", "exception")
    ctx = chaos.patch(mock_context)
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import Any, Callable


class ChaosTimeoutError(TimeoutError):
    """Raised when a chaos-injected timeout failure triggers."""


class ChaosThrottleError(Exception):
    """Raised when a chaos-injected throttle failure triggers.

    Simulates AWS TooManyRequestsException.
    """

    def __init__(self, state_name: str):
        super().__init__(f"TooManyRequestsException: Rate exceeded for state '{state_name}'")
        self.state_name = state_name


@dataclass
class _InjectedFailure:
    """Internal record of an injected failure."""

    state_name: str
    failure_type: str | Callable
    remaining: int | None = None  # None = persistent, int = countdown


class ChaosFixture:
    """Inject failures into workflow states during mock SDK test runs.

    Supports four failure types:
    - "timeout": raises ChaosTimeoutError
    - "exception": raises RuntimeError
    - "throttle": raises ChaosThrottleError (simulates TooManyRequestsException)
    - callable: called with (state_name, input_data), return value or exception propagates
    """

    def __init__(self) -> None:
        self._failures: dict[str, _InjectedFailure] = {}

    def inject_failure(
        self,
        state_name: str,
        failure_type: str | Callable,
        *,
        count: int | None = None,
    ) -> None:
        """Register a failure for a specific state.

        Args:
            state_name: The state name to inject failure into.
            failure_type: One of "timeout", "exception", "throttle",
                or a callable(state_name, input_data).
            count: Number of times to trigger (None = every time).
        """
        valid_types = ("timeout", "exception", "throttle")
        if isinstance(failure_type, str) and failure_type not in valid_types:
            raise ValueError(f"Invalid failure_type '{failure_type}'. Must be one of {valid_types} or a callable.")
        self._failures[state_name] = _InjectedFailure(
            state_name=state_name,
            failure_type=failure_type,
            remaining=count,
        )

    def reset(self) -> None:
        """Clear all injected failures."""
        self._failures.clear()

    def _should_trigger(self, state_name: str) -> _InjectedFailure | None:
        """Check if a failure should trigger for this state."""
        failure = self._failures.get(state_name)
        if failure is None:
            return None

        if failure.remaining is not None:
            if failure.remaining <= 0:
                return None
            failure.remaining -= 1

        return failure

    def _trigger_failure(self, failure: _InjectedFailure, input_data: Any) -> Any:
        """Execute the failure. Returns a value (for callables) or raises."""
        ft = failure.failure_type
        name = failure.state_name

        if ft == "timeout":
            raise ChaosTimeoutError(f"Timeout injected for state '{name}'")
        elif ft == "exception":
            raise RuntimeError(f"Exception injected for state '{name}'")
        elif ft == "throttle":
            raise ChaosThrottleError(name)
        elif callable(ft):
            return ft(name, input_data)
        else:
            raise ValueError(f"Unknown failure type: {ft}")

    def patch(self, context: Any) -> Any:
        """Patch a MockDurableContext to check for injected failures.

        Wraps the context's step() method. When a state has an injected
        failure, the failure triggers instead of calling the handler.

        Args:
            context: A MockDurableContext instance.

        Returns:
            The same context (mutated with patched step method).
        """
        original_step = context.step

        @functools.wraps(original_step)
        def patched_step(name: str, handler: Callable, input_data: Any) -> Any:
            failure = self._should_trigger(name)
            if failure is not None:
                return self._trigger_failure(failure, input_data)
            return original_step(name, handler, input_data)

        context.step = patched_step
        return context
