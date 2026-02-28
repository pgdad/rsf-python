"""Tests for the MockDurableContext — verifies step, wait, parallel, map primitives."""

import pytest

from tests.mock_sdk import BranchResult, Duration, MockDurableContext


class TestDuration:
    def test_seconds(self):
        d = Duration.seconds(30)
        assert d.kind == "seconds"
        assert d.value == 30

    def test_timestamp(self):
        d = Duration.timestamp("2025-01-01T00:00:00Z")
        assert d.kind == "timestamp"
        assert d.value == "2025-01-01T00:00:00Z"


class TestStep:
    def test_step_calls_handler(self):
        ctx = MockDurableContext()
        result = ctx.step("DoWork", lambda x: {"processed": x["val"] * 2}, {"val": 5})
        assert result == {"processed": 10}

    def test_step_records_call(self):
        ctx = MockDurableContext()
        ctx.step("DoWork", lambda x: x, {"key": "value"})
        assert len(ctx.calls) == 1
        assert ctx.calls[0].operation == "step"
        assert ctx.calls[0].name == "DoWork"
        assert ctx.calls[0].input_data == {"key": "value"}

    def test_step_override(self):
        ctx = MockDurableContext()
        ctx.override_step("DoWork", {"mocked": True})
        result = ctx.step("DoWork", lambda x: x, {"original": True})
        assert result == {"mocked": True}

    def test_step_does_not_mutate_input(self):
        ctx = MockDurableContext()
        original = {"items": [1, 2, 3]}

        def mutating_handler(data):
            data["items"].append(99)
            return data

        ctx.step("DoWork", mutating_handler, original)
        # The recorded input should be the original (deep copied before mutation)
        assert ctx.calls[0].input_data == {"items": [1, 2, 3]}

    def test_multiple_steps(self):
        ctx = MockDurableContext()
        ctx.step("Step1", lambda x: {"step": 1}, {})
        ctx.step("Step2", lambda x: {"step": 2}, {})
        ctx.step("Step3", lambda x: {"step": 3}, {})
        assert len(ctx.calls) == 3
        assert [c.name for c in ctx.calls] == ["Step1", "Step2", "Step3"]

    def test_step_handler_exception_propagates(self):
        ctx = MockDurableContext()
        with pytest.raises(ValueError, match="boom"):
            ctx.step("Fail", lambda x: (_ for _ in ()).throw(ValueError("boom")), {})


class TestWait:
    def test_wait_seconds(self):
        ctx = MockDurableContext()
        ctx.wait("Delay", Duration.seconds(60))
        assert len(ctx.calls) == 1
        assert ctx.calls[0].operation == "wait"
        assert ctx.calls[0].name == "Delay"
        assert ctx.calls[0].duration.kind == "seconds"
        assert ctx.calls[0].duration.value == 60

    def test_wait_timestamp(self):
        ctx = MockDurableContext()
        ctx.wait("WaitUntil", Duration.timestamp("2026-01-01T00:00:00Z"))
        assert ctx.calls[0].duration.kind == "timestamp"


class TestParallel:
    def test_parallel_executes_all_branches(self):
        ctx = MockDurableContext()
        branches = [
            lambda inp: {"branch": "A", "val": inp.get("x", 0) + 1},
            lambda inp: {"branch": "B", "val": inp.get("x", 0) + 2},
        ]
        result = ctx.parallel("RunBoth", branches, {"x": 10})
        assert isinstance(result, BranchResult)
        results = result.get_results()
        assert len(results) == 2
        assert results[0] == {"branch": "A", "val": 11}
        assert results[1] == {"branch": "B", "val": 12}

    def test_parallel_records_call(self):
        ctx = MockDurableContext()
        ctx.parallel("P", [lambda x: 1, lambda x: 2], {"data": True})
        assert len(ctx.calls) == 1
        assert ctx.calls[0].operation == "parallel"
        assert ctx.calls[0].name == "P"
        assert ctx.calls[0].result == [1, 2]

    def test_parallel_branches_get_independent_copies(self):
        ctx = MockDurableContext()
        shared = {"counter": 0}

        def branch_a(inp):
            inp["counter"] += 1
            return inp

        def branch_b(inp):
            inp["counter"] += 10
            return inp

        result = ctx.parallel("P", [branch_a, branch_b], shared)
        results = result.get_results()
        # Each branch should have gotten its own copy
        assert results[0]["counter"] == 1
        assert results[1]["counter"] == 10


class TestMap:
    def test_map_processes_all_items(self):
        ctx = MockDurableContext()
        result = ctx.map(
            "ProcessItems",
            lambda item: {"processed": item * 2},
            [1, 2, 3],
        )
        assert result.get_results() == [
            {"processed": 2},
            {"processed": 4},
            {"processed": 6},
        ]

    def test_map_records_call(self):
        ctx = MockDurableContext()
        ctx.map("M", lambda x: x, [1, 2])
        assert len(ctx.calls) == 1
        assert ctx.calls[0].operation == "map"
        assert ctx.calls[0].name == "M"

    def test_map_with_max_concurrency(self):
        ctx = MockDurableContext()
        result = ctx.map("M", lambda x: x * 10, [1, 2, 3], max_concurrency=2)
        # max_concurrency doesn't change behavior in mock, but should be accepted
        assert result.get_results() == [10, 20, 30]

    def test_map_empty_items(self):
        ctx = MockDurableContext()
        result = ctx.map("M", lambda x: x, [])
        assert result.get_results() == []

    def test_map_items_get_independent_copies(self):
        ctx = MockDurableContext()
        items = [{"val": 1}, {"val": 2}]

        def mutating_fn(item):
            item["val"] *= 100
            return item

        result = ctx.map("M", mutating_fn, items)
        # Original items should not be mutated
        assert items == [{"val": 1}, {"val": 2}]
        assert result.get_results() == [{"val": 100}, {"val": 200}]


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
        ctx.step("S1", lambda x: x, {})
        ctx.wait("W1", Duration.seconds(5))
        ctx.parallel("P1", [lambda x: x], {})
        ctx.map("M1", lambda x: x, [1])

        assert len(ctx.calls) == 4
        ops = [c.operation for c in ctx.calls]
        assert ops == ["step", "wait", "parallel", "map"]
        names = [c.name for c in ctx.calls]
        assert names == ["S1", "W1", "P1", "M1"]
