"""Tests for the MockDurableContext — verifies step, wait, parallel, map primitives.

API matches real AWS Lambda Durable Functions SDK (DurableFunction.v9):
  context.step(func, name=None)          — func receives MockStepContext
  context.wait(duration, name=None)
  context.parallel(functions, name=None) — each function receives MockDurableContext
  context.map(inputs, func, name=None)   — func receives (MockDurableContext, item, idx, all)
"""

import pytest

from tests.mock_sdk import BranchResult, Duration, MockDurableContext


class TestDuration:
    def test_seconds(self):
        d = Duration(seconds=30)
        assert d.seconds == 30
        assert d.value == 30

    def test_from_seconds(self):
        d = Duration.from_seconds(30)
        assert d.seconds == 30

    def test_timestamp(self):
        # Duration(seconds=n) is the primary constructor; timestamps are passed raw
        d = Duration(seconds=0)
        assert d.seconds == 0


class TestStep:
    def test_step_calls_func(self):
        """step(func, name) calls func with StepContext and returns result."""
        ctx = MockDurableContext()
        data = {"val": 5}
        result = ctx.step(lambda _sc: {"processed": data["val"] * 2}, "DoWork")
        assert result == {"processed": 10}

    def test_step_records_call(self):
        ctx = MockDurableContext()
        ctx.step(lambda _sc: {"key": "value"}, "DoWork")
        assert len(ctx.calls) == 1
        assert ctx.calls[0].operation == "step"
        assert ctx.calls[0].name == "DoWork"

    def test_step_override(self):
        ctx = MockDurableContext()
        ctx.override_step("DoWork", {"mocked": True})
        result = ctx.step(lambda _sc: {"original": True}, "DoWork")
        assert result == {"mocked": True}

    def test_step_no_name(self):
        """step(func) without name still works."""
        ctx = MockDurableContext()
        result = ctx.step(lambda _sc: {"done": True})
        assert result == {"done": True}

    def test_step_func_exception_propagates(self):
        ctx = MockDurableContext()
        with pytest.raises(ValueError, match="boom"):
            ctx.step(lambda _sc: (_ for _ in ()).throw(ValueError("boom")), "Fail")

    def test_multiple_steps(self):
        ctx = MockDurableContext()
        ctx.step(lambda _sc: {"step": 1}, "Step1")
        ctx.step(lambda _sc: {"step": 2}, "Step2")
        ctx.step(lambda _sc: {"step": 3}, "Step3")
        assert len(ctx.calls) == 3
        assert [c.name for c in ctx.calls] == ["Step1", "Step2", "Step3"]


class TestWait:
    def test_wait_seconds(self):
        """wait(duration, name) matches real SDK signature."""
        ctx = MockDurableContext()
        ctx.wait(Duration(seconds=60), "Delay")
        assert len(ctx.calls) == 1
        assert ctx.calls[0].operation == "wait"
        assert ctx.calls[0].name == "Delay"
        assert ctx.calls[0].duration.seconds == 60
        assert ctx.calls[0].duration.value == 60

    def test_wait_timestamp(self):
        # For timestamp-based waits, a raw string is passed to context.wait
        ctx = MockDurableContext()
        ctx.wait("2026-01-01T00:00:00Z", "WaitUntil")
        assert ctx.calls[0].duration == "2026-01-01T00:00:00Z"

    def test_wait_no_name(self):
        ctx = MockDurableContext()
        ctx.wait(Duration(seconds=30))
        assert ctx.calls[0].duration.seconds == 30


class TestParallel:
    def test_parallel_executes_all_branches(self):
        """parallel(functions, name) — each function receives a DurableContext."""
        ctx = MockDurableContext()
        branches = [
            lambda _ctx: {"branch": "A"},
            lambda _ctx: {"branch": "B"},
        ]
        result = ctx.parallel(branches, "RunBoth")
        assert isinstance(result, BranchResult)
        results = result.get_results()
        assert len(results) == 2
        assert results[0] == {"branch": "A"}
        assert results[1] == {"branch": "B"}

    def test_parallel_records_call(self):
        ctx = MockDurableContext()
        ctx.parallel([lambda _ctx: 1, lambda _ctx: 2], "P")
        # parallel itself plus any inner steps
        parallel_record = [c for c in ctx.calls if c.operation == "parallel"]
        assert len(parallel_record) == 1
        assert parallel_record[0].name == "P"
        assert parallel_record[0].result == [1, 2]

    def test_parallel_branch_uses_branch_context(self):
        """Each branch receives its own MockDurableContext for nested steps."""
        ctx = MockDurableContext()

        def branch_with_step(_ctx):
            return _ctx.step(lambda _sc: {"inner": "result"}, "InnerStep")

        result = ctx.parallel([branch_with_step], "P")
        assert result.get_results() == [{"inner": "result"}]

    def test_parallel_branches_can_close_over_input(self):
        """Branches can close over captured input from outer scope."""
        ctx = MockDurableContext()
        captured = {"x": 10}
        branches = [
            lambda _ctx: {"val": captured["x"] + 1},
            lambda _ctx: {"val": captured["x"] + 2},
        ]
        result = ctx.parallel(branches, "P")
        results = result.get_results()
        assert results[0] == {"val": 11}
        assert results[1] == {"val": 12}


class TestMap:
    def test_map_processes_all_items(self):
        """map(inputs, func, name) — func receives (ctx, item, idx, all_items)."""
        ctx = MockDurableContext()
        result = ctx.map(
            [1, 2, 3],
            lambda _ctx, item, idx, all_items: {"processed": item * 2},
            "ProcessItems",
        )
        assert result.get_results() == [
            {"processed": 2},
            {"processed": 4},
            {"processed": 6},
        ]

    def test_map_records_call(self):
        ctx = MockDurableContext()
        ctx.map([1, 2], lambda _ctx, item, idx, all_items: item, "M")
        map_record = [c for c in ctx.calls if c.operation == "map"]
        assert len(map_record) == 1
        assert map_record[0].name == "M"

    def test_map_empty_items(self):
        ctx = MockDurableContext()
        result = ctx.map([], lambda _ctx, item, idx, all_items: item, "M")
        assert result.get_results() == []

    def test_map_items_get_independent_copies(self):
        """Items are deep-copied before being passed to func."""
        ctx = MockDurableContext()
        items = [{"val": 1}, {"val": 2}]

        def mutating_fn(_ctx, item, idx, all_items):
            item["val"] *= 100
            return item

        result = ctx.map(items, mutating_fn, "M")
        # Original items should not be mutated
        assert items == [{"val": 1}, {"val": 2}]
        assert result.get_results() == [{"val": 100}, {"val": 200}]

    def test_map_func_receives_idx_and_all(self):
        """Map func receives correct index and all_items."""
        ctx = MockDurableContext()
        captured = []

        def capture_fn(_ctx, item, idx, all_items):
            captured.append((item, idx, len(all_items)))
            return item

        ctx.map(["a", "b", "c"], capture_fn, "M")
        assert captured == [("a", 0, 3), ("b", 1, 3), ("c", 2, 3)]

    def test_map_item_uses_item_context(self):
        """Each map item receives its own DurableContext for nested steps."""
        ctx = MockDurableContext()

        def map_with_step(_ctx, item, idx, all_items):
            return _ctx.step(lambda _sc: {"processed": item}, "InnerStep")

        result = ctx.map(["x", "y"], map_with_step, "M")
        assert result.get_results() == [{"processed": "x"}, {"processed": "y"}]


class TestBranchResult:
    def test_get_results(self):
        br = BranchResult(_results=[1, 2, 3])
        assert br.get_results() == [1, 2, 3]

    def test_empty_results(self):
        br = BranchResult()
        assert br.get_results() == []


class TestCallHistory:
    def test_mixed_operations(self):
        ctx = MockDurableContext()
        ctx.step(lambda _sc: None, "S1")
        ctx.wait(Duration(seconds=5), "W1")
        ctx.parallel([lambda _ctx: None], "P1")
        ctx.map([1], lambda _ctx, item, idx, all_items: item, "M1")

        ops = [c.operation for c in ctx.calls if c.name in ("S1", "W1", "P1", "M1")]
        assert "step" in ops
        assert "wait" in ops
        assert "parallel" in ops
        assert "map" in ops
