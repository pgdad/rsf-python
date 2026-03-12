"""Mock AWS Lambda Durable Functions SDK for testing generated orchestrator code.

Provides MockDurableContext that simulates the SDK's step, wait, parallel,
and map primitives without requiring actual Lambda infrastructure.

API matches the real AWS Lambda Durable Functions SDK (DurableFunction.v9):
  context.step(func, name=None, config=None)
  context.wait(duration, name=None)
  context.parallel(functions, name=None, config=None)
  context.map(inputs, func, name=None, config=None)
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
    def seconds(n: int | float) -> "Duration":
        return Duration("seconds", n)

    @staticmethod
    def timestamp(ts: str) -> "Duration":
        return Duration("timestamp", ts)

    def __repr__(self) -> str:
        return f"Duration.{self.kind}({self.value!r})"


class MockStepContext:
    """Mock StepContext passed to step functions — matches real SDK (only has logger)."""

    def __init__(self) -> None:
        self.logger = None


@dataclass
class StepRecord:
    """Records a single SDK call for introspection."""

    operation: str  # "step", "wait", "parallel", "map"
    name: str | None = None
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

    Matches the real AWS Lambda Durable Functions SDK API:
      step(func, name=None, config=None)   — func receives MockStepContext
      wait(duration, name=None)
      parallel(functions, name=None)       — each function receives MockDurableContext
      map(inputs, func, name=None)         — func receives (MockDurableContext, item, idx, all)
    """

    def __init__(self) -> None:
        self.calls: list[StepRecord] = []
        self._step_overrides: dict[str, Any] = {}

    def override_step(self, name: str, result: Any) -> None:
        """Pre-configure the return value for a named step.

        Use this to mock handler results without actual handler functions.
        """
        self._step_overrides[name] = result

    def step(self, func: Callable, name: str | None = None, config: Any = None) -> Any:
        """Execute a step function and record the call.

        Matches real SDK: step(func: Callable[[StepContext], T], name=None, config=None) -> T

        The func receives a MockStepContext (has only .logger).
        If an override is set for this step name, return that instead.
        """
        step_ctx = MockStepContext()
        record = StepRecord(operation="step", name=name)

        if name in self._step_overrides:
            result = self._step_overrides[name]
        else:
            result = func(step_ctx)

        record.result = result
        self.calls.append(record)
        return result

    def wait(self, duration: Duration, name: str | None = None) -> None:
        """Record a Wait state without actually waiting.

        Matches real SDK: wait(duration, name=None) -> None
        """
        record = StepRecord(operation="wait", name=name, duration=duration)
        self.calls.append(record)

    def parallel(
        self,
        functions: list[Callable],
        name: str | None = None,
        config: Any = None,
    ) -> BranchResult:
        """Execute parallel branches synchronously and return combined results.

        Matches real SDK: parallel(functions, name=None, config=None) -> BatchResult
        Each function receives a MockDurableContext (branch context).
        """
        record = StepRecord(operation="parallel", name=name)

        results = []
        for branch_fn in functions:
            branch_ctx = MockDurableContext()
            branch_ctx._step_overrides = self._step_overrides  # share overrides
            branch_result = branch_fn(branch_ctx)
            # Merge branch calls for inspection
            self.calls.extend(branch_ctx.calls)
            results.append(branch_result)

        record.result = results
        self.calls.append(record)
        return BranchResult(_results=results)

    def map(
        self,
        inputs: list[Any],
        func: Callable,
        name: str | None = None,
        config: Any = None,
    ) -> BranchResult:
        """Execute map operation synchronously over items.

        Matches real SDK: map(inputs, func, name=None, config=None) -> BatchResult
        func receives (DurableContext, item, index, all_items).
        """
        record = StepRecord(operation="map", name=name, input_data=copy.deepcopy(inputs))

        results = []
        for idx, item in enumerate(inputs):
            item_ctx = MockDurableContext()
            item_ctx._step_overrides = self._step_overrides  # share overrides
            result = func(item_ctx, copy.deepcopy(item), idx, inputs)
            self.calls.extend(item_ctx.calls)
            results.append(result)

        record.result = results
        self.calls.append(record)
        return BranchResult(_results=results)
