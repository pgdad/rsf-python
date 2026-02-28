"""Local tests for the retry-and-recovery example (EXAM-04).

Validates workflow parsing, retry policies (JitterStrategy, BackoffRate,
MaxDelaySeconds), multi-Catch chains, individual handler behaviour, and
end-to-end happy/fallback paths using MockDurableContext.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rsf.dsl.parser import load_definition
from rsf.dsl.types import JitterStrategy
from mock_sdk import MockDurableContext

WORKFLOW = Path(__file__).parent.parent / "workflow.yaml"


# ---------------------------------------------------------------------------
# 1. Workflow parsing
# ---------------------------------------------------------------------------

class TestWorkflowParsing:
    """Verify workflow.yaml loads and parses without errors."""

    def test_loads_successfully(self):
        sm = load_definition(WORKFLOW)
        assert sm.start_at == "CallPrimaryService"

    def test_all_states_present(self):
        sm = load_definition(WORKFLOW)
        expected = {
            "CallPrimaryService",
            "TryFallbackService",
            "HandleThrottle",
            "RetryAfterThrottle",
            "HandleBadData",
            "VerifyResult",
            "ServiceComplete",
            "CriticalFailure",
        }
        assert set(sm.states.keys()) == expected

    def test_state_types(self):
        sm = load_definition(WORKFLOW)
        assert sm.states["CallPrimaryService"].type == "Task"
        assert sm.states["TryFallbackService"].type == "Task"
        assert sm.states["HandleThrottle"].type == "Pass"
        assert sm.states["RetryAfterThrottle"].type == "Task"
        assert sm.states["HandleBadData"].type == "Task"
        assert sm.states["VerifyResult"].type == "Task"
        assert sm.states["ServiceComplete"].type == "Succeed"
        assert sm.states["CriticalFailure"].type == "Fail"


# ---------------------------------------------------------------------------
# 2. Retry policies
# ---------------------------------------------------------------------------

class TestRetryPolicies:
    """Check JitterStrategy FULL/NONE, BackoffRate values, and MaxDelaySeconds."""

    @pytest.fixture
    def sm(self):
        return load_definition(WORKFLOW)

    def test_primary_has_three_retry_rules(self, sm):
        retries = sm.states["CallPrimaryService"].retry
        assert len(retries) == 3

    def test_jitter_strategy_full_present(self, sm):
        retries = sm.states["CallPrimaryService"].retry
        full_jitter = [r for r in retries if r.jitter_strategy == JitterStrategy.FULL]
        assert len(full_jitter) >= 1, "Expected at least one retry with FULL jitter"

    def test_jitter_strategy_none_present(self, sm):
        retries = sm.states["CallPrimaryService"].retry
        none_jitter = [r for r in retries if r.jitter_strategy == JitterStrategy.NONE]
        assert len(none_jitter) >= 1, "Expected at least one retry with NONE jitter"

    def test_transient_error_retry_config(self, sm):
        retries = sm.states["CallPrimaryService"].retry
        transient = [r for r in retries if "TransientError" in r.error_equals][0]
        assert transient.interval_seconds == 1
        assert transient.max_attempts == 3
        assert transient.backoff_rate == 2.0
        assert transient.jitter_strategy == JitterStrategy.FULL

    def test_rate_limit_retry_config(self, sm):
        retries = sm.states["CallPrimaryService"].retry
        rate = [r for r in retries if "RateLimitError" in r.error_equals][0]
        assert rate.interval_seconds == 5
        assert rate.max_attempts == 5
        assert rate.backoff_rate == 1.5
        assert rate.max_delay_seconds == 30
        assert rate.jitter_strategy == JitterStrategy.NONE

    def test_timeout_error_retry_config(self, sm):
        retries = sm.states["CallPrimaryService"].retry
        timeout = [r for r in retries if "TimeoutError" in r.error_equals][0]
        assert timeout.interval_seconds == 10
        assert timeout.max_attempts == 2
        assert timeout.backoff_rate == 3.0
        assert timeout.max_delay_seconds == 60

    def test_max_delay_seconds_present(self, sm):
        """At least two retry rules should specify MaxDelaySeconds."""
        retries = sm.states["CallPrimaryService"].retry
        with_max_delay = [r for r in retries if r.max_delay_seconds is not None]
        assert len(with_max_delay) >= 2

    def test_backoff_rates(self, sm):
        retries = sm.states["CallPrimaryService"].retry
        rates = {r.backoff_rate for r in retries}
        assert 2.0 in rates
        assert 1.5 in rates
        assert 3.0 in rates

    def test_fallback_retry_config(self, sm):
        retries = sm.states["TryFallbackService"].retry
        assert len(retries) == 2
        transient = [r for r in retries if "TransientError" in r.error_equals][0]
        assert transient.jitter_strategy == JitterStrategy.FULL
        assert transient.backoff_rate == 1.5

    def test_retry_after_throttle_config(self, sm):
        retries = sm.states["RetryAfterThrottle"].retry
        assert len(retries) == 1
        rule = retries[0]
        assert "RateLimitError" in rule.error_equals
        assert rule.interval_seconds == 30
        assert rule.max_delay_seconds == 120
        assert rule.jitter_strategy == JitterStrategy.FULL


# ---------------------------------------------------------------------------
# 3. Multi-Catch chains
# ---------------------------------------------------------------------------

class TestMultiCatchChains:
    """Verify Catch configuration on states with multiple catchers."""

    @pytest.fixture
    def sm(self):
        return load_definition(WORKFLOW)

    def test_primary_has_four_catch_entries(self, sm):
        catchers = sm.states["CallPrimaryService"].catch
        assert len(catchers) == 4

    def test_primary_catch_order(self, sm):
        catchers = sm.states["CallPrimaryService"].catch
        assert catchers[0].error_equals == ["ServiceDownError"]
        assert catchers[0].next == "TryFallbackService"
        assert catchers[0].result_path == "$.primaryError"

        assert catchers[1].error_equals == ["RateLimitError"]
        assert catchers[1].next == "HandleThrottle"
        assert catchers[1].result_path == "$.throttleError"

        assert catchers[2].error_equals == ["DataValidationError"]
        assert catchers[2].next == "HandleBadData"
        assert catchers[2].result_path == "$.validationError"

        assert catchers[3].error_equals == ["States.ALL"]
        assert catchers[3].next == "CriticalFailure"
        assert catchers[3].result_path == "$.error"

    def test_fallback_has_catch_all(self, sm):
        catchers = sm.states["TryFallbackService"].catch
        assert len(catchers) == 1
        assert catchers[0].error_equals == ["States.ALL"]
        assert catchers[0].next == "CriticalFailure"

    def test_retry_after_throttle_catch(self, sm):
        catchers = sm.states["RetryAfterThrottle"].catch
        assert len(catchers) == 1
        assert catchers[0].error_equals == ["States.ALL"]

    def test_handle_bad_data_catch(self, sm):
        catchers = sm.states["HandleBadData"].catch
        assert len(catchers) == 1
        assert catchers[0].next == "CriticalFailure"


# ---------------------------------------------------------------------------
# 4. Individual handler tests
# ---------------------------------------------------------------------------

class TestCallPrimaryServiceHandler:
    """Test the CallPrimaryService handler in isolation."""

    def test_success(self):
        from handlers.call_primary_service import call_primary_service

        result = call_primary_service({
            "requestId": "req-1",
            "payload": {"item": "widget"},
        })
        assert result["source"] == "primary"
        assert result["status"] == "ok"
        assert result["requestId"] == "req-1"

    def test_transient_error(self):
        from handlers.call_primary_service import call_primary_service

        with pytest.raises(RuntimeError, match="TransientError"):
            call_primary_service({"simulate_error": "TransientError"})

    def test_rate_limit_error(self):
        from handlers.call_primary_service import call_primary_service

        with pytest.raises(RuntimeError, match="RateLimitError"):
            call_primary_service({"simulate_error": "RateLimitError"})

    def test_service_down_error(self):
        from handlers.call_primary_service import call_primary_service

        with pytest.raises(RuntimeError, match="ServiceDownError"):
            call_primary_service({"simulate_error": "ServiceDownError"})

    def test_data_validation_error(self):
        from handlers.call_primary_service import call_primary_service

        with pytest.raises(RuntimeError, match="DataValidationError"):
            call_primary_service({"simulate_error": "DataValidationError"})

    def test_timeout_error(self):
        from handlers.call_primary_service import call_primary_service

        with pytest.raises(RuntimeError, match="TimeoutError"):
            call_primary_service({"simulate_error": "TimeoutError"})


class TestTryFallbackServiceHandler:
    """Test the TryFallbackService handler in isolation."""

    def test_success(self):
        from handlers.try_fallback_service import try_fallback_service

        result = try_fallback_service({
            "requestId": "req-2",
            "primaryError": {"msg": "down"},
        })
        assert result["source"] == "fallback"
        assert result["status"] == "ok"

    def test_transient_error(self):
        from handlers.try_fallback_service import try_fallback_service

        with pytest.raises(RuntimeError, match="TransientError"):
            try_fallback_service({"simulate_error": "TransientError"})

    def test_generic_error(self):
        from handlers.try_fallback_service import try_fallback_service

        with pytest.raises(RuntimeError, match="SomeError"):
            try_fallback_service({"simulate_error": "SomeError"})


class TestRetryAfterThrottleHandler:
    """Test the RetryAfterThrottle handler in isolation."""

    def test_success(self):
        from handlers.retry_after_throttle import retry_after_throttle

        result = retry_after_throttle({
            "requestId": "req-3",
            "recovery": {"retryAfter": 30},
        })
        assert result["source"] == "primary-retry"
        assert result["status"] == "ok"
        assert result["throttleRecovery"] is True

    def test_still_throttled(self):
        from handlers.retry_after_throttle import retry_after_throttle

        with pytest.raises(RuntimeError, match="RateLimitError"):
            retry_after_throttle({"simulate_error": "RateLimitError"})


class TestHandleBadDataHandler:
    """Test the HandleBadData handler in isolation."""

    def test_success(self):
        from handlers.handle_bad_data import handle_bad_data

        result = handle_bad_data({
            "payload": {"field": "value"},
            "validationError": {"msg": "schema mismatch"},
        })
        assert result["cleaned"] is True
        assert "malformed_field" in result["removedFields"]

    def test_sanitization_failure(self):
        from handlers.handle_bad_data import handle_bad_data

        with pytest.raises(RuntimeError, match="CriticalError"):
            handle_bad_data({"simulate_error": "CriticalError"})


class TestVerifyResultHandler:
    """Test the VerifyResult handler in isolation."""

    def test_success(self):
        from handlers.verify_result import verify_result

        result = verify_result({"status": "ok", "source": "primary"})
        assert result["verified"] is True
        assert result["source"] == "primary"
        assert "status_check" in result["checksPerformed"]

    def test_bad_status(self):
        from handlers.verify_result import verify_result

        with pytest.raises(RuntimeError, match="VerificationError"):
            verify_result({"status": "error", "source": "primary"})

    def test_missing_status(self):
        from handlers.verify_result import verify_result

        with pytest.raises(RuntimeError, match="VerificationError"):
            verify_result({"source": "primary"})


# ---------------------------------------------------------------------------
# 5. Happy path integration
# ---------------------------------------------------------------------------

class TestHappyPath:
    """CallPrimaryService -> VerifyResult -> ServiceComplete."""

    def test_happy_path_via_mock_context(self):
        ctx = MockDurableContext()

        # Simulate CallPrimaryService succeeding
        primary_result = {
            "source": "primary",
            "status": "ok",
            "requestId": "req-hp",
            "payload": {"item": "widget"},
        }
        result_after_primary = ctx.step(
            "CallPrimaryService",
            lambda d: primary_result,
            {"requestId": "req-hp", "payload": {"item": "widget"}},
        )
        assert result_after_primary["source"] == "primary"
        assert result_after_primary["status"] == "ok"

        # Simulate VerifyResult
        verification = {
            "verified": True,
            "source": "primary",
            "checksPerformed": ["status_check", "payload_integrity"],
        }
        verify_out = ctx.step(
            "VerifyResult",
            lambda d: verification,
            result_after_primary,
        )
        assert verify_out["verified"] is True

        # Verify the call sequence
        assert len(ctx.calls) == 2
        assert ctx.calls[0].name == "CallPrimaryService"
        assert ctx.calls[1].name == "VerifyResult"

    def test_happy_path_with_real_handlers(self):
        """Import real handlers and run the happy path."""
        from handlers.call_primary_service import call_primary_service
        from handlers.verify_result import verify_result

        ctx = MockDurableContext()

        primary_out = ctx.step(
            "CallPrimaryService",
            call_primary_service,
            {"requestId": "req-real", "payload": {"x": 1}},
        )
        assert primary_out["status"] == "ok"

        verify_out = ctx.step(
            "VerifyResult",
            verify_result,
            primary_out,
        )
        assert verify_out["verified"] is True
        assert verify_out["source"] == "primary"

        assert [c.name for c in ctx.calls] == [
            "CallPrimaryService",
            "VerifyResult",
        ]


# ---------------------------------------------------------------------------
# 6. Fallback path integration
# ---------------------------------------------------------------------------

class TestFallbackPath:
    """CallPrimaryService catches ServiceDownError -> TryFallbackService -> VerifyResult -> ServiceComplete."""

    def test_fallback_path_via_mock_context(self):
        ctx = MockDurableContext()

        # CallPrimaryService fails with ServiceDownError; the Catch routes
        # to TryFallbackService.  We simulate the error-capture result.
        primary_error = {
            "primaryError": {
                "Error": "ServiceDownError",
                "Cause": "503 Service Unavailable",
            },
            "requestId": "req-fb",
        }

        # TryFallbackService succeeds
        fallback_result = {
            "source": "fallback",
            "status": "ok",
            "requestId": "req-fb",
            "payload": {},
        }
        fallback_out = ctx.step(
            "TryFallbackService",
            lambda d: fallback_result,
            primary_error,
        )
        assert fallback_out["source"] == "fallback"

        # VerifyResult validates the fallback response
        verification = {
            "verified": True,
            "source": "fallback",
            "checksPerformed": ["status_check", "payload_integrity"],
        }
        verify_out = ctx.step(
            "VerifyResult",
            lambda d: verification,
            fallback_out,
        )
        assert verify_out["verified"] is True
        assert verify_out["source"] == "fallback"

        assert len(ctx.calls) == 2
        assert ctx.calls[0].name == "TryFallbackService"
        assert ctx.calls[1].name == "VerifyResult"

    def test_fallback_path_with_real_handlers(self):
        """Import real handlers and run the fallback path."""
        from handlers.try_fallback_service import try_fallback_service
        from handlers.verify_result import verify_result

        ctx = MockDurableContext()

        fallback_out = ctx.step(
            "TryFallbackService",
            try_fallback_service,
            {
                "requestId": "req-fb-real",
                "primaryError": {"Error": "ServiceDownError"},
            },
        )
        assert fallback_out["source"] == "fallback"
        assert fallback_out["status"] == "ok"

        verify_out = ctx.step(
            "VerifyResult",
            verify_result,
            fallback_out,
        )
        assert verify_out["verified"] is True
        assert verify_out["source"] == "fallback"

        assert [c.name for c in ctx.calls] == [
            "TryFallbackService",
            "VerifyResult",
        ]
