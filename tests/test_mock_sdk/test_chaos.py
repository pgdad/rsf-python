"""Tests for chaos injection testing utilities.

API matches real SDK: context.step(func, name=None)
"""

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
            ctx.step(lambda _sc: {"input": 1}, "ValidateOrder")

    def test_inject_exception_raises(self):
        chaos = ChaosFixture()
        chaos.inject_failure("ProcessPayment", "exception")
        ctx = chaos.patch(MockDurableContext())

        with pytest.raises(RuntimeError, match="ProcessPayment"):
            ctx.step(lambda _sc: {"input": 1}, "ProcessPayment")

    def test_inject_throttle_raises(self):
        chaos = ChaosFixture()
        chaos.inject_failure("SendEmail", "throttle")
        ctx = chaos.patch(MockDurableContext())

        with pytest.raises(ChaosThrottleError, match="TooManyRequests"):
            ctx.step(lambda _sc: {"input": 1}, "SendEmail")

    def test_inject_callable_returns_value(self):
        chaos = ChaosFixture()
        chaos.inject_failure(
            "Transform",
            lambda name, data: {"overridden": True},
        )
        ctx = chaos.patch(MockDurableContext())

        result = ctx.step(lambda _sc: {"normal": True}, "Transform")
        assert result == {"overridden": True}

    def test_inject_callable_raises(self):
        def fail_fn(name, data):
            raise ValueError(f"Custom error in {name}")

        chaos = ChaosFixture()
        chaos.inject_failure("Compute", fail_fn)
        ctx = chaos.patch(MockDurableContext())

        with pytest.raises(ValueError, match="Custom error in Compute"):
            ctx.step(lambda _sc: {"x": 1}, "Compute")

    def test_multiple_failures_independent(self):
        chaos = ChaosFixture()
        chaos.inject_failure("StateA", "timeout")
        chaos.inject_failure("StateB", "exception")
        ctx = chaos.patch(MockDurableContext())

        with pytest.raises(ChaosTimeoutError):
            ctx.step(lambda _sc: None, "StateA")

        with pytest.raises(RuntimeError):
            ctx.step(lambda _sc: None, "StateB")

    def test_non_injected_state_calls_handler(self):
        chaos = ChaosFixture()
        chaos.inject_failure("FailState", "timeout")
        ctx = chaos.patch(MockDurableContext())

        result = ctx.step(lambda _sc: {"ok": True}, "NormalState")
        assert result == {"ok": True}

    def test_reset_clears_failures(self):
        chaos = ChaosFixture()
        chaos.inject_failure("State", "timeout")
        chaos.reset()
        ctx = chaos.patch(MockDurableContext())

        # Should not raise -- failure was cleared
        result = ctx.step(lambda _sc: {"ok": True}, "State")
        assert result == {"ok": True}

    def test_count_one_shot(self):
        chaos = ChaosFixture()
        chaos.inject_failure("RetryState", "timeout", count=1)
        ctx = chaos.patch(MockDurableContext())

        # First call fails
        with pytest.raises(ChaosTimeoutError):
            ctx.step(lambda _sc: None, "RetryState")

        # Second call succeeds
        result = ctx.step(lambda _sc: {"ok": True}, "RetryState")
        assert result == {"ok": True}

    def test_persistent_failure_triggers_every_time(self):
        chaos = ChaosFixture()
        chaos.inject_failure("AlwaysFail", "exception")
        ctx = chaos.patch(MockDurableContext())

        for _ in range(5):
            with pytest.raises(RuntimeError):
                ctx.step(lambda _sc: None, "AlwaysFail")

    def test_invalid_failure_type_raises(self):
        chaos = ChaosFixture()
        with pytest.raises(ValueError, match="Invalid failure_type"):
            chaos.inject_failure("State", "invalid_type")
