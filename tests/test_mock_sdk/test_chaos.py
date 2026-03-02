"""Tests for chaos injection testing utilities."""

import pytest

from rsf.testing.chaos import (
    ChaosFixture,
    ChaosThrottleError,
    ChaosTimeoutError,
)
from tests.mock_sdk import MockDurableContext


class TestChaosInjection:
    """Test ChaosFixture failure injection."""

    def test_inject_timeout_raises(self):
        chaos = ChaosFixture()
        chaos.inject_failure("ValidateOrder", "timeout")
        ctx = chaos.patch(MockDurableContext())

        with pytest.raises(ChaosTimeoutError, match="ValidateOrder"):
            ctx.step("ValidateOrder", lambda d: d, {"input": 1})

    def test_inject_exception_raises(self):
        chaos = ChaosFixture()
        chaos.inject_failure("ProcessPayment", "exception")
        ctx = chaos.patch(MockDurableContext())

        with pytest.raises(RuntimeError, match="ProcessPayment"):
            ctx.step("ProcessPayment", lambda d: d, {"input": 1})

    def test_inject_throttle_raises(self):
        chaos = ChaosFixture()
        chaos.inject_failure("SendEmail", "throttle")
        ctx = chaos.patch(MockDurableContext())

        with pytest.raises(ChaosThrottleError, match="TooManyRequests"):
            ctx.step("SendEmail", lambda d: d, {"input": 1})

    def test_inject_callable_returns_value(self):
        chaos = ChaosFixture()
        chaos.inject_failure(
            "Transform",
            lambda name, data: {"overridden": True},
        )
        ctx = chaos.patch(MockDurableContext())

        result = ctx.step("Transform", lambda d: {"normal": True}, {"x": 1})
        assert result == {"overridden": True}

    def test_inject_callable_raises(self):
        def fail_fn(name, data):
            raise ValueError(f"Custom error in {name}")

        chaos = ChaosFixture()
        chaos.inject_failure("Compute", fail_fn)
        ctx = chaos.patch(MockDurableContext())

        with pytest.raises(ValueError, match="Custom error in Compute"):
            ctx.step("Compute", lambda d: d, {"x": 1})

    def test_multiple_failures_independent(self):
        chaos = ChaosFixture()
        chaos.inject_failure("StateA", "timeout")
        chaos.inject_failure("StateB", "exception")
        ctx = chaos.patch(MockDurableContext())

        with pytest.raises(ChaosTimeoutError):
            ctx.step("StateA", lambda d: d, {})

        with pytest.raises(RuntimeError):
            ctx.step("StateB", lambda d: d, {})

    def test_non_injected_state_calls_handler(self):
        chaos = ChaosFixture()
        chaos.inject_failure("FailState", "timeout")
        ctx = chaos.patch(MockDurableContext())

        result = ctx.step("NormalState", lambda d: {"ok": True}, {"x": 1})
        assert result == {"ok": True}

    def test_reset_clears_failures(self):
        chaos = ChaosFixture()
        chaos.inject_failure("State", "timeout")
        chaos.reset()
        ctx = chaos.patch(MockDurableContext())

        # Should not raise -- failure was cleared
        result = ctx.step("State", lambda d: {"ok": True}, {})
        assert result == {"ok": True}

    def test_count_one_shot(self):
        chaos = ChaosFixture()
        chaos.inject_failure("RetryState", "timeout", count=1)
        ctx = chaos.patch(MockDurableContext())

        # First call fails
        with pytest.raises(ChaosTimeoutError):
            ctx.step("RetryState", lambda d: d, {})

        # Second call succeeds
        result = ctx.step("RetryState", lambda d: {"ok": True}, {})
        assert result == {"ok": True}

    def test_persistent_failure_triggers_every_time(self):
        chaos = ChaosFixture()
        chaos.inject_failure("AlwaysFail", "exception")
        ctx = chaos.patch(MockDurableContext())

        for _ in range(5):
            with pytest.raises(RuntimeError):
                ctx.step("AlwaysFail", lambda d: d, {})

    def test_invalid_failure_type_raises(self):
        chaos = ChaosFixture()
        with pytest.raises(ValueError, match="Invalid failure_type"):
            chaos.inject_failure("State", "invalid_type")
