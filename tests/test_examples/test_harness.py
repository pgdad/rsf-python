"""Unit tests for the integration test harness components.

Tests harness helpers with mocked boto3 clients — no AWS credentials needed.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from tests.test_examples.conftest import (
    TERMINAL_STATUSES,
    make_execution_id,
    poll_execution,
    query_logs,
    terraform_teardown,
)


# ---------------------------------------------------------------------------
# make_execution_id tests (HARN-06)
# ---------------------------------------------------------------------------


class TestMakeExecutionId:
    """UUID-suffixed execution IDs: format and uniqueness."""

    def test_format_matches_spec(self):
        """ID matches: test-{name}-{YYYYMMDD}T{HHMMSS}-{hex8}."""
        eid = make_execution_id("order-processing")
        pattern = r"^test-order-processing-\d{8}T\d{6}-[0-9a-f]{8}$"
        assert re.match(pattern, eid), f"ID {eid!r} doesn't match pattern"

    def test_uniqueness(self):
        """Two calls with the same name produce different IDs."""
        id1 = make_execution_id("foo")
        id2 = make_execution_id("foo")
        assert id1 != id2

    def test_contains_name(self):
        """The name segment is embedded in the ID."""
        eid = make_execution_id("data-pipeline")
        assert "test-data-pipeline-" in eid

    def test_uuid_suffix_is_8_hex_chars(self):
        """UUID suffix is exactly 8 hex characters."""
        eid = make_execution_id("test")
        suffix = eid.rsplit("-", 1)[-1]
        assert len(suffix) == 8
        assert all(c in "0123456789abcdef" for c in suffix)


# ---------------------------------------------------------------------------
# poll_execution tests (HARN-01)
# ---------------------------------------------------------------------------


class TestPollExecution:
    """poll_execution waits for terminal state with backoff on throttle."""

    def _mock_client(self, responses):
        """Create a mock Lambda client that returns responses in order."""
        client = MagicMock()
        client.list_durable_executions_by_function = MagicMock(side_effect=responses)
        return client

    def test_returns_on_succeeded(self):
        """Returns immediately when execution is SUCCEEDED."""
        execution = {
            "DurableExecutionArn": "arn:test",
            "DurableExecutionName": "test-exec",
            "Status": "SUCCEEDED",
        }
        client = self._mock_client([{"DurableExecutions": [execution]}])

        result = poll_execution(client, "fn", "test-exec", timeout=10)
        assert result["Status"] == "SUCCEEDED"

    def test_returns_on_failed(self):
        """Returns when execution reaches FAILED."""
        execution = {
            "DurableExecutionName": "test-exec",
            "Status": "FAILED",
        }
        client = self._mock_client([{"DurableExecutions": [execution]}])

        result = poll_execution(client, "fn", "test-exec", timeout=10)
        assert result["Status"] == "FAILED"

    def test_polls_until_terminal(self):
        """Keeps polling RUNNING until terminal state is reached."""
        running = {"DurableExecutions": [{"Status": "RUNNING", "DurableExecutionName": "x"}]}
        succeeded = {"DurableExecutions": [{"Status": "SUCCEEDED", "DurableExecutionName": "x"}]}

        client = self._mock_client([running, running, succeeded])

        with patch("tests.test_examples.conftest.time.sleep"):
            result = poll_execution(client, "fn", "x", timeout=60, poll_interval=0.01)
        assert result["Status"] == "SUCCEEDED"
        assert client.list_durable_executions_by_function.call_count == 3

    def test_timeout_raises(self):
        """Raises TimeoutError if terminal state not reached in time."""
        running = {"DurableExecutions": [{"Status": "RUNNING", "DurableExecutionName": "x"}]}
        client = self._mock_client([running] * 100)

        with patch("tests.test_examples.conftest.time.sleep"):
            with patch("tests.test_examples.conftest.time.monotonic") as mock_mono:
                # Simulate time passing beyond deadline
                mock_mono.side_effect = [0, 0, 100, 100]
                with pytest.raises(TimeoutError, match="did not reach terminal state"):
                    poll_execution(client, "fn", "x", timeout=5, poll_interval=0.01)

    def test_backoff_on_throttle(self):
        """Applies exponential backoff on TooManyRequestsException."""
        from botocore.exceptions import ClientError

        throttle_error = ClientError(
            {"Error": {"Code": "TooManyRequestsException", "Message": "Rate exceeded"}},
            "ListDurableExecutionsByFunction",
        )
        succeeded = {"DurableExecutions": [{"Status": "SUCCEEDED", "DurableExecutionName": "x"}]}

        client = self._mock_client([throttle_error, succeeded])

        with patch("tests.test_examples.conftest.time.sleep"):
            result = poll_execution(client, "fn", "x", timeout=60, poll_interval=0.01)
        assert result["Status"] == "SUCCEEDED"

    def test_non_throttle_error_raises(self):
        """Non-throttle ClientError is re-raised."""
        from botocore.exceptions import ClientError

        access_error = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Forbidden"}},
            "ListDurableExecutionsByFunction",
        )
        client = self._mock_client([access_error])

        with pytest.raises(ClientError, match="AccessDeniedException"):
            poll_execution(client, "fn", "x", timeout=10, poll_interval=0.01)

    def test_empty_executions_keeps_polling(self):
        """Continues polling when execution list is empty (not yet started)."""
        empty = {"DurableExecutions": []}
        succeeded = {"DurableExecutions": [{"Status": "SUCCEEDED", "DurableExecutionName": "x"}]}

        client = self._mock_client([empty, empty, succeeded])

        with patch("tests.test_examples.conftest.time.sleep"):
            result = poll_execution(client, "fn", "x", timeout=60, poll_interval=0.01)
        assert result["Status"] == "SUCCEEDED"

    def test_all_terminal_statuses(self):
        """All 4 terminal statuses are recognized."""
        for status in TERMINAL_STATUSES:
            execution = {"DurableExecutionName": "x", "Status": status}
            client = self._mock_client([{"DurableExecutions": [execution]}])
            result = poll_execution(client, "fn", "x", timeout=10)
            assert result["Status"] == status


# ---------------------------------------------------------------------------
# query_logs tests (HARN-02)
# ---------------------------------------------------------------------------


class TestQueryLogs:
    """query_logs applies propagation buffer and retries until non-empty."""

    def _mock_logs_client(self, query_results_sequence):
        """Create a mock Logs client.

        Args:
            query_results_sequence: List of results to return on successive
                get_query_results calls.
        """
        client = MagicMock()
        client.start_query = MagicMock(return_value={"queryId": "qid-1"})
        client.get_query_results = MagicMock(
            side_effect=[{"status": "Complete", "results": r} for r in query_results_sequence]
        )
        return client

    def test_returns_results_on_first_try(self):
        """Returns results when first query succeeds."""
        results = [[{"field": "@message", "value": "hello"}]]
        client = self._mock_logs_client([results])
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)

        with patch("tests.test_examples.conftest.time.sleep"):
            got = query_logs(client, "/aws/lambda/fn", "fields @message", start)

        assert got == results

    def test_retries_on_empty_results(self):
        """Retries when initial queries return empty results."""
        results = [[{"field": "@message", "value": "ok"}]]
        client = self._mock_logs_client([[], [], results])
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)

        with patch("tests.test_examples.conftest.time.sleep"):
            got = query_logs(
                client,
                "/aws/lambda/fn",
                "fields @message",
                start,
                max_retries=5,
            )

        assert got == results
        assert client.start_query.call_count == 3

    def test_returns_empty_after_max_retries(self):
        """Returns empty list after exhausting retries."""
        client = self._mock_logs_client([[], [], []])
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)

        with patch("tests.test_examples.conftest.time.sleep"):
            got = query_logs(
                client,
                "/aws/lambda/fn",
                "fields @message",
                start,
                max_retries=3,
            )

        assert got == []

    def test_propagation_wait_called(self):
        """Propagation wait is applied before first query."""
        results = [[{"field": "@message", "value": "ok"}]]
        client = self._mock_logs_client([results])
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)

        with patch("tests.test_examples.conftest.time.sleep") as mock_sleep:
            query_logs(
                client,
                "/aws/lambda/fn",
                "fields @message",
                start,
                propagation_wait=15.0,
            )

        # First sleep call should be the 15s propagation wait
        assert mock_sleep.call_args_list[0][0][0] == 15.0


# ---------------------------------------------------------------------------
# terraform_teardown tests (HARN-03)
# ---------------------------------------------------------------------------


class TestTerraformTeardown:
    """Teardown runs terraform destroy and deletes orphaned log groups."""

    def test_deletes_orphaned_log_group(self, tmp_path):
        """Calls delete_log_group after terraform destroy."""
        tf_dir = tmp_path / "terraform"
        tf_dir.mkdir()

        logs_client = MagicMock()

        with patch("tests.test_examples.conftest.subprocess.run"):
            terraform_teardown(
                tmp_path,
                logs_client=logs_client,
                log_group_name="/aws/lambda/test-fn",
            )

        logs_client.delete_log_group.assert_called_once_with(logGroupName="/aws/lambda/test-fn")

    def test_swallows_resource_not_found(self, tmp_path):
        """Swallows ResourceNotFoundException when log group already deleted."""
        from botocore.exceptions import ClientError

        tf_dir = tmp_path / "terraform"
        tf_dir.mkdir()

        logs_client = MagicMock()
        logs_client.delete_log_group.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Not found"}},
            "DeleteLogGroup",
        )

        with patch("tests.test_examples.conftest.subprocess.run"):
            # Should not raise
            terraform_teardown(
                tmp_path,
                logs_client=logs_client,
                log_group_name="/aws/lambda/test-fn",
            )

    def test_reraises_non_resource_not_found(self, tmp_path):
        """Re-raises non-ResourceNotFoundException errors."""
        from botocore.exceptions import ClientError

        tf_dir = tmp_path / "terraform"
        tf_dir.mkdir()

        logs_client = MagicMock()
        logs_client.delete_log_group.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Forbidden"}},
            "DeleteLogGroup",
        )

        with patch("tests.test_examples.conftest.subprocess.run"):
            with pytest.raises(ClientError, match="AccessDeniedException"):
                terraform_teardown(
                    tmp_path,
                    logs_client=logs_client,
                    log_group_name="/aws/lambda/test-fn",
                )

    def test_skips_log_group_delete_when_no_client(self, tmp_path):
        """No log group deletion when logs_client is None."""
        tf_dir = tmp_path / "terraform"
        tf_dir.mkdir()

        with patch("tests.test_examples.conftest.subprocess.run"):
            # Should not raise
            terraform_teardown(tmp_path)
