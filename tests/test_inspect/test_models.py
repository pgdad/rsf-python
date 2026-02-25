"""Tests for inspector data models and timestamp normalization."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from rsf.inspect.models import (
    TERMINAL_STATUSES,
    ExecutionDetail,
    ExecutionError,
    ExecutionListResponse,
    ExecutionStatus,
    ExecutionSummary,
    HistoryEvent,
    normalize_timestamp,
)


# -----------------------------------------------------------------------
# ExecutionStatus
# -----------------------------------------------------------------------


class TestExecutionStatus:
    def test_all_values(self):
        assert set(ExecutionStatus) == {
            ExecutionStatus.RUNNING,
            ExecutionStatus.SUCCEEDED,
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMED_OUT,
            ExecutionStatus.STOPPED,
        }

    def test_terminal_statuses_exclude_running(self):
        assert ExecutionStatus.RUNNING not in TERMINAL_STATUSES

    def test_terminal_statuses_include_all_terminal(self):
        for status in (
            ExecutionStatus.SUCCEEDED,
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMED_OUT,
            ExecutionStatus.STOPPED,
        ):
            assert status in TERMINAL_STATUSES

    def test_string_value(self):
        assert ExecutionStatus.RUNNING.value == "RUNNING"
        assert ExecutionStatus.SUCCEEDED == "SUCCEEDED"


# -----------------------------------------------------------------------
# normalize_timestamp
# -----------------------------------------------------------------------


class TestNormalizeTimestamp:
    def test_epoch_seconds_int(self):
        dt = normalize_timestamp(0)
        assert dt == datetime(1970, 1, 1, tzinfo=timezone.utc)

    def test_epoch_seconds_float(self):
        dt = normalize_timestamp(1700000000.5)
        assert dt.tzinfo == timezone.utc
        assert dt.year == 2023

    def test_naive_datetime(self):
        naive = datetime(2025, 6, 15, 12, 0, 0)
        dt = normalize_timestamp(naive)
        assert dt.tzinfo == timezone.utc
        assert dt.hour == 12

    def test_aware_datetime_preserved(self):
        aware = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        dt = normalize_timestamp(aware)
        assert dt == aware

    def test_iso_string(self):
        dt = normalize_timestamp("2025-06-15T12:00:00+00:00")
        assert dt.tzinfo == timezone.utc
        assert dt.year == 2025

    def test_iso_string_naive(self):
        dt = normalize_timestamp("2025-06-15T12:00:00")
        assert dt.tzinfo == timezone.utc

    def test_invalid_type_raises(self):
        with pytest.raises(TypeError, match="Cannot normalize"):
            normalize_timestamp([1, 2, 3])


# -----------------------------------------------------------------------
# ExecutionSummary
# -----------------------------------------------------------------------


class TestExecutionSummary:
    def test_basic_construction(self):
        summary = ExecutionSummary(
            execution_id="exec-123",
            name="my-execution",
            status=ExecutionStatus.RUNNING,
            function_name="my-func",
            start_time=1700000000,
        )
        assert summary.execution_id == "exec-123"
        assert summary.status == ExecutionStatus.RUNNING
        assert summary.start_time.tzinfo == timezone.utc
        assert summary.end_time is None

    def test_timestamp_normalization_from_epoch(self):
        summary = ExecutionSummary(
            execution_id="e1",
            status="SUCCEEDED",
            function_name="fn",
            start_time=1700000000,
            end_time=1700000060,
        )
        assert summary.start_time.tzinfo == timezone.utc
        assert summary.end_time is not None
        assert summary.end_time.tzinfo == timezone.utc

    def test_timestamp_normalization_from_string(self):
        summary = ExecutionSummary(
            execution_id="e1",
            status="RUNNING",
            function_name="fn",
            start_time="2025-06-15T12:00:00+00:00",
        )
        assert summary.start_time.year == 2025

    def test_json_roundtrip(self):
        summary = ExecutionSummary(
            execution_id="e1",
            name="test",
            status=ExecutionStatus.FAILED,
            function_name="fn",
            start_time=1700000000,
        )
        data = summary.model_dump(mode="json")
        assert data["execution_id"] == "e1"
        assert data["status"] == "FAILED"
        restored = ExecutionSummary.model_validate(data)
        assert restored.execution_id == summary.execution_id


# -----------------------------------------------------------------------
# ExecutionDetail
# -----------------------------------------------------------------------


class TestExecutionDetail:
    def test_inherits_summary_fields(self):
        detail = ExecutionDetail(
            execution_id="e1",
            status=ExecutionStatus.SUCCEEDED,
            function_name="fn",
            start_time=1700000000,
            input_payload={"key": "value"},
            result={"output": 42},
        )
        assert detail.execution_id == "e1"
        assert detail.input_payload == {"key": "value"}
        assert detail.result == {"output": 42}

    def test_with_error(self):
        detail = ExecutionDetail(
            execution_id="e1",
            status=ExecutionStatus.FAILED,
            function_name="fn",
            start_time=1700000000,
            error=ExecutionError(error="States.TaskFailed", cause="timeout"),
        )
        assert detail.error is not None
        assert detail.error.error == "States.TaskFailed"

    def test_with_history_events(self):
        detail = ExecutionDetail(
            execution_id="e1",
            status=ExecutionStatus.RUNNING,
            function_name="fn",
            start_time=1700000000,
            history=[
                HistoryEvent(
                    event_id=1,
                    timestamp=1700000001,
                    event_type="StepStarted",
                    details={"state": "S1"},
                ),
                HistoryEvent(
                    event_id=2,
                    timestamp=1700000002,
                    event_type="StepSucceeded",
                    details={"state": "S1"},
                ),
            ],
        )
        assert len(detail.history) == 2
        assert detail.history[0].event_type == "StepStarted"

    def test_json_roundtrip(self):
        detail = ExecutionDetail(
            execution_id="e1",
            status=ExecutionStatus.RUNNING,
            function_name="fn",
            start_time=1700000000,
            history=[
                HistoryEvent(
                    event_id=1, timestamp=1700000001, event_type="StepStarted"
                )
            ],
        )
        data = detail.model_dump(mode="json")
        assert len(data["history"]) == 1
        restored = ExecutionDetail.model_validate(data)
        assert restored.history[0].event_id == 1


# -----------------------------------------------------------------------
# HistoryEvent
# -----------------------------------------------------------------------


class TestHistoryEvent:
    def test_basic_construction(self):
        evt = HistoryEvent(
            event_id=1, timestamp=1700000000, event_type="StepStarted"
        )
        assert evt.event_id == 1
        assert evt.event_type == "StepStarted"
        assert evt.sub_type is None
        assert evt.details == {}

    def test_with_sub_type_and_details(self):
        evt = HistoryEvent(
            event_id=5,
            timestamp=1700000005,
            event_type="StepFailed",
            sub_type="TaskFailed",
            details={"error": "timeout", "state": "S3"},
        )
        assert evt.sub_type == "TaskFailed"
        assert evt.details["error"] == "timeout"

    def test_timestamp_normalized(self):
        evt = HistoryEvent(
            event_id=1, timestamp=1700000000, event_type="StepStarted"
        )
        assert evt.timestamp.tzinfo == timezone.utc


# -----------------------------------------------------------------------
# ExecutionListResponse
# -----------------------------------------------------------------------


class TestExecutionListResponse:
    def test_empty_list(self):
        resp = ExecutionListResponse(executions=[])
        assert resp.executions == []
        assert resp.next_token is None

    def test_with_pagination(self):
        resp = ExecutionListResponse(
            executions=[
                ExecutionSummary(
                    execution_id="e1",
                    status=ExecutionStatus.RUNNING,
                    function_name="fn",
                    start_time=1700000000,
                )
            ],
            next_token="abc123",
        )
        assert len(resp.executions) == 1
        assert resp.next_token == "abc123"
