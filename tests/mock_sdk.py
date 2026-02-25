"""Mock AWS Lambda Durable Functions SDK for testing generated orchestrator code.

Provides MockDurableContext that simulates the SDK's step, wait, parallel,
and map primitives without requiring actual Lambda infrastructure.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Callable


class Duration:
    """Mock Duration class matching SDK API."""

    def __init__(self, kind: str, value: Any):
        self.kind = kind
        self.value = value

    @staticmethod
    def seconds(n: int | float) -> Duration:
        return Duration("seconds", n)

    @staticmethod
    def timestamp(ts: str) -> Duration:
        return Duration("timestamp", ts)

    def __repr__(self) -> str:
        return f"Duration.{self.kind}({self.value!r})"


@dataclass
class StepRecord:
    """Records a single SDK call for introspection."""

    operation: str  # "step", "wait", "parallel", "map"
    name: str
    input_data: Any = None
    result: Any = None
    duration: Duration | None = None


@dataclass
class BranchResult:
    """Result container for parallel/map operations."""

    _results: list[Any] = field(default_factory=list)

    def get_results(self) -> list[Any]:
        return self._results


class MockDurableContext:
    """Mock implementation of the Lambda Durable Functions SDK context.

    Records all SDK calls and executes handlers synchronously for testing.
    Supports step, wait, parallel, and map primitives.
    """

    def __init__(self) -> None:
        self.calls: list[StepRecord] = []
        self._step_overrides: dict[str, Any] = {}

    def override_step(self, name: str, result: Any) -> None:
        """Pre-configure the return value for a named step.

        Use this to mock handler results without actual handler functions.
        """
        self._step_overrides[name] = result

    def step(self, name: str, handler: Callable, input_data: Any) -> Any:
        """Execute a Task state handler and record the call.

        If an override is set for this step name, return that instead
        of calling the handler.
        """
        record = StepRecord(operation="step", name=name, input_data=copy.deepcopy(input_data))

        if name in self._step_overrides:
            result = self._step_overrides[name]
        else:
            result = handler(input_data)

        record.result = result
        self.calls.append(record)
        return result

    def wait(self, name: str, duration: Duration) -> None:
        """Record a Wait state without actually waiting."""
        record = StepRecord(operation="wait", name=name, duration=duration)
        self.calls.append(record)

    def parallel(
        self,
        name: str,
        branches: list[Callable],
        input_data: Any,
    ) -> BranchResult:
        """Execute parallel branches synchronously and return combined results."""
        record = StepRecord(
            operation="parallel",
            name=name,
            input_data=copy.deepcopy(input_data),
        )

        results = []
        for branch_fn in branches:
            branch_result = branch_fn(copy.deepcopy(input_data))
            results.append(branch_result)

        record.result = results
        self.calls.append(record)
        return BranchResult(_results=results)

    def map(
        self,
        name: str,
        item_fn: Callable,
        items: list[Any],
        max_concurrency: int | None = None,
    ) -> BranchResult:
        """Execute map operation synchronously over items."""
        record = StepRecord(
            operation="map",
            name=name,
            input_data=copy.deepcopy(items),
        )

        results = []
        for item in items:
            result = item_fn(copy.deepcopy(item))
            results.append(result)

        record.result = results
        self.calls.append(record)
        return BranchResult(_results=results)
