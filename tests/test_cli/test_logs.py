"""Tests for rsf logs CLI command."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch


from rsf.cli.logs_cmd import (
    _discover_log_groups,
    _extract_function_name,
    _extract_level,
    _filter_by_level,
    _format_log_line,
    _parse_since,
)


# --- Log group discovery tests ---


class TestDiscoverLogGroups:
    """Tests for _discover_log_groups."""

    def test_reads_tfstate_and_extracts_lambda_function_names(self, tmp_path: Path) -> None:
        """Test 1: Reads terraform.tfstate and extracts Lambda function names."""
        tfstate = {
            "resources": [
                {
                    "type": "aws_lambda_function",
                    "name": "orchestrator",
                    "instances": [
                        {"attributes": {"function_name": "my-workflow-orchestrator"}}
                    ],
                },
                {
                    "type": "aws_lambda_function",
                    "name": "handler",
                    "instances": [
                        {"attributes": {"function_name": "my-workflow-handler"}}
                    ],
                },
            ]
        }
        (tmp_path / "terraform.tfstate").write_text(json.dumps(tfstate))

        result = _discover_log_groups(tmp_path)
        assert result == [
            "/aws/lambda/my-workflow-handler",
            "/aws/lambda/my-workflow-orchestrator",
        ]

    def test_no_tfstate_returns_empty(self, tmp_path: Path) -> None:
        """Test 2: No tfstate file returns empty list."""
        result = _discover_log_groups(tmp_path)
        assert result == []

    def test_empty_resources_returns_empty(self, tmp_path: Path) -> None:
        """Test 3: Empty resources returns empty list."""
        tfstate = {"resources": []}
        (tmp_path / "terraform.tfstate").write_text(json.dumps(tfstate))
        result = _discover_log_groups(tmp_path)
        assert result == []

    def test_skips_non_lambda_resources(self, tmp_path: Path) -> None:
        """Non-Lambda resources are ignored."""
        tfstate = {
            "resources": [
                {
                    "type": "aws_iam_role",
                    "name": "role",
                    "instances": [{"attributes": {"name": "my-role"}}],
                },
                {
                    "type": "aws_lambda_function",
                    "name": "fn",
                    "instances": [
                        {"attributes": {"function_name": "my-function"}}
                    ],
                },
            ]
        }
        (tmp_path / "terraform.tfstate").write_text(json.dumps(tfstate))
        result = _discover_log_groups(tmp_path)
        assert result == ["/aws/lambda/my-function"]


# --- Format log line tests ---


class TestFormatLogLine:
    """Tests for _format_log_line."""

    def test_standard_format(self) -> None:
        """Test 4: Produces [timestamp] [function-name] [level] message format."""
        ts_ms = int(datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
        result = _format_log_line(ts_ms, "my-fn", "Hello world", no_color=True)
        assert "[2026-01-15 12:00:00]" in result
        assert "[my-fn]" in result
        assert "[INFO]" in result
        assert "Hello world" in result

    def test_info_green_warn_yellow_error_red(self) -> None:
        """Test 5: Colors INFO green, WARN yellow, ERROR red."""
        ts_ms = int(datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)

        info_line = _format_log_line(ts_ms, "fn", "INFO message")
        assert "[green]INFO[/green]" in info_line

        warn_line = _format_log_line(ts_ms, "fn", "WARNING: something")
        assert "[yellow]WARN[/yellow]" in warn_line

        error_line = _format_log_line(ts_ms, "fn", "ERROR: failed")
        assert "[red]ERROR[/red]" in error_line

    def test_json_format(self) -> None:
        """Test 6: --json flag produces JSONL dict with expected keys."""
        ts_ms = int(datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
        result = _format_log_line(ts_ms, "my-fn", "Hello world", use_json=True)
        parsed = json.loads(result)
        assert "timestamp" in parsed
        assert parsed["function"] == "my-fn"
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Hello world"


# --- Parse since tests ---


class TestParseSince:
    """Tests for _parse_since."""

    def test_1h_returns_epoch_for_1_hour_ago(self) -> None:
        """Test 7: '1h' returns epoch_ms for ~1 hour ago."""
        result = _parse_since("1h")
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        one_hour_ms = 3600 * 1000
        # Allow 5 second tolerance
        assert abs(result - (now_ms - one_hour_ms)) < 5000

    def test_30m_returns_epoch_for_30_minutes_ago(self) -> None:
        """Test 8: '30m' returns epoch_ms for ~30 minutes ago."""
        result = _parse_since("30m")
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        thirty_min_ms = 1800 * 1000
        assert abs(result - (now_ms - thirty_min_ms)) < 5000

    def test_iso_date_returns_correct_epoch(self) -> None:
        """Test 9: ISO date returns correct epoch_ms."""
        result = _parse_since("2026-01-01T00:00:00Z")
        expected = int(
            datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp() * 1000
        )
        assert result == expected


# --- Extract level tests ---


class TestExtractLevel:
    """Tests for _extract_level."""

    def test_detects_error_warn_info(self) -> None:
        """Test 10: Detects ERROR, WARN, INFO from message content."""
        assert _extract_level("ERROR: something failed") == "ERROR"
        assert _extract_level("EXCEPTION in handler") == "ERROR"
        assert _extract_level("Traceback (most recent call)") == "ERROR"
        assert _extract_level("WARNING: deprecated") == "WARN"
        assert _extract_level("Just a normal log line") == "INFO"


# --- Extract function name tests ---


class TestExtractFunctionName:
    """Tests for _extract_function_name."""

    def test_extracts_from_log_group_path(self) -> None:
        """Test 11: Extracts function name from /aws/lambda/{name}."""
        assert _extract_function_name("/aws/lambda/my-function") == "my-function"
        assert _extract_function_name("/aws/lambda/rsf-orchestrator") == "rsf-orchestrator"
        assert _extract_function_name("custom-group") == "custom-group"


# --- Filter by level tests ---


class TestFilterByLevel:
    """Tests for _filter_by_level."""

    def test_filters_by_minimum_level(self) -> None:
        """Test 12: Filters events to matching level and above."""
        events = [
            {"message": "INFO: normal"},
            {"message": "WARNING: attention"},
            {"message": "ERROR: critical"},
        ]
        error_only = _filter_by_level(events, "ERROR")
        assert len(error_only) == 1
        assert "ERROR" in error_only[0]["message"]

        warn_and_above = _filter_by_level(events, "WARN")
        assert len(warn_and_above) == 2

        all_levels = _filter_by_level(events, "INFO")
        assert len(all_levels) == 3


# --- CLI command tests ---


class TestLogsCommand:
    """Tests for the logs CLI command integration."""

    def test_no_log_groups_prints_error(self, tmp_path: Path) -> None:
        """Test 13: No log groups discovered prints error and exits 1."""
        from typer.testing import CliRunner
        from rsf.cli.main import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["logs", str(tmp_path / "workflow.yaml"), "--tf-dir", str(tmp_path)],
        )
        assert result.exit_code == 1
        assert "No Lambda functions found" in result.output

    def test_execution_id_passes_filter_pattern(self, tmp_path: Path) -> None:
        """Test 14: --execution-id passes filter pattern to CloudWatch API."""
        # Create tfstate
        tfstate = {
            "resources": [
                {
                    "type": "aws_lambda_function",
                    "name": "fn",
                    "instances": [
                        {"attributes": {"function_name": "my-fn"}}
                    ],
                }
            ]
        }
        (tmp_path / "terraform.tfstate").write_text(json.dumps(tfstate))

        mock_client = MagicMock()
        mock_client.filter_log_events.return_value = {
            "events": [],
            "nextToken": None,
        }

        with patch("boto3.client", return_value=mock_client):
            from typer.testing import CliRunner
            from rsf.cli.main import app

            runner = CliRunner()
            runner.invoke(
                app,
                [
                    "logs",
                    str(tmp_path / "workflow.yaml"),
                    "--tf-dir",
                    str(tmp_path),
                    "--execution-id",
                    "exec-123",
                ],
            )

            # Verify filter pattern was passed
            call_kwargs = mock_client.filter_log_events.call_args[1]
            assert call_kwargs["filterPattern"] == '"exec-123"'

    def test_since_passes_start_time(self, tmp_path: Path) -> None:
        """Test 15: --since passes correct startTime to CloudWatch API."""
        tfstate = {
            "resources": [
                {
                    "type": "aws_lambda_function",
                    "name": "fn",
                    "instances": [
                        {"attributes": {"function_name": "my-fn"}}
                    ],
                }
            ]
        }
        (tmp_path / "terraform.tfstate").write_text(json.dumps(tfstate))

        mock_client = MagicMock()
        mock_client.filter_log_events.return_value = {
            "events": [],
            "nextToken": None,
        }

        with patch("boto3.client", return_value=mock_client):

            from typer.testing import CliRunner
            from rsf.cli.main import app

            runner = CliRunner()
            runner.invoke(
                app,
                [
                    "logs",
                    str(tmp_path / "workflow.yaml"),
                    "--tf-dir",
                    str(tmp_path),
                    "--since",
                    "1h",
                ],
            )

            call_kwargs = mock_client.filter_log_events.call_args[1]
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            one_hour_ms = 3600 * 1000
            assert abs(call_kwargs["startTime"] - (now_ms - one_hour_ms)) < 5000

    def test_level_filter(self, tmp_path: Path) -> None:
        """Test 16: --level ERROR filters output to ERROR only."""
        tfstate = {
            "resources": [
                {
                    "type": "aws_lambda_function",
                    "name": "fn",
                    "instances": [
                        {"attributes": {"function_name": "my-fn"}}
                    ],
                }
            ]
        }
        (tmp_path / "terraform.tfstate").write_text(json.dumps(tfstate))

        mock_client = MagicMock()
        mock_client.filter_log_events.return_value = {
            "events": [
                {
                    "logGroupName": "/aws/lambda/my-fn",
                    "timestamp": int(
                        datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp()
                        * 1000
                    ),
                    "message": "INFO: normal log",
                },
                {
                    "logGroupName": "/aws/lambda/my-fn",
                    "timestamp": int(
                        datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc).timestamp()
                        * 1000
                    ),
                    "message": "ERROR: something broke",
                },
            ],
            "nextToken": None,
        }

        with patch("boto3.client", return_value=mock_client):

            from typer.testing import CliRunner
            from rsf.cli.main import app

            runner = CliRunner()
            result = runner.invoke(
                app,
                [
                    "logs",
                    str(tmp_path / "workflow.yaml"),
                    "--tf-dir",
                    str(tmp_path),
                    "--level",
                    "ERROR",
                    "--no-color",
                ],
            )

            assert "ERROR" in result.output
            # INFO line should be filtered out
            assert "normal log" not in result.output

    def test_json_output(self, tmp_path: Path) -> None:
        """Test 17: --json outputs JSONL lines."""
        tfstate = {
            "resources": [
                {
                    "type": "aws_lambda_function",
                    "name": "fn",
                    "instances": [
                        {"attributes": {"function_name": "my-fn"}}
                    ],
                }
            ]
        }
        (tmp_path / "terraform.tfstate").write_text(json.dumps(tfstate))

        mock_client = MagicMock()
        mock_client.filter_log_events.return_value = {
            "events": [
                {
                    "logGroupName": "/aws/lambda/my-fn",
                    "timestamp": int(
                        datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp()
                        * 1000
                    ),
                    "message": "Hello from Lambda",
                },
            ],
            "nextToken": None,
        }

        with patch("boto3.client", return_value=mock_client):

            from typer.testing import CliRunner
            from rsf.cli.main import app

            runner = CliRunner()
            result = runner.invoke(
                app,
                [
                    "logs",
                    str(tmp_path / "workflow.yaml"),
                    "--tf-dir",
                    str(tmp_path),
                    "--json",
                ],
            )

            # Parse JSONL output
            lines = [line for line in result.output.strip().split("\n") if line.startswith("{")]
            assert len(lines) >= 1
            parsed = json.loads(lines[-1])
            assert parsed["function"] == "my-fn"
            assert parsed["message"] == "Hello from Lambda"

    def test_no_color_plain_text(self, tmp_path: Path) -> None:
        """Test 18: --no-color outputs plain text without Rich markup."""
        tfstate = {
            "resources": [
                {
                    "type": "aws_lambda_function",
                    "name": "fn",
                    "instances": [
                        {"attributes": {"function_name": "my-fn"}}
                    ],
                }
            ]
        }
        (tmp_path / "terraform.tfstate").write_text(json.dumps(tfstate))

        mock_client = MagicMock()
        mock_client.filter_log_events.return_value = {
            "events": [
                {
                    "logGroupName": "/aws/lambda/my-fn",
                    "timestamp": int(
                        datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp()
                        * 1000
                    ),
                    "message": "Test message",
                },
            ],
            "nextToken": None,
        }

        with patch("boto3.client", return_value=mock_client):

            from typer.testing import CliRunner
            from rsf.cli.main import app

            runner = CliRunner()
            result = runner.invoke(
                app,
                [
                    "logs",
                    str(tmp_path / "workflow.yaml"),
                    "--tf-dir",
                    str(tmp_path),
                    "--no-color",
                ],
            )

            # Should not contain Rich markup
            output_lines = [line for line in result.output.split("\n") if "Test message" in line]
            assert len(output_lines) >= 1
            assert "[dim]" not in output_lines[0]
            assert "[bold]" not in output_lines[0]

    def test_formatted_output(self, tmp_path: Path) -> None:
        """Test 20: Prints formatted log lines to console."""
        tfstate = {
            "resources": [
                {
                    "type": "aws_lambda_function",
                    "name": "fn",
                    "instances": [
                        {"attributes": {"function_name": "my-fn"}}
                    ],
                }
            ]
        }
        (tmp_path / "terraform.tfstate").write_text(json.dumps(tfstate))

        mock_client = MagicMock()
        mock_client.filter_log_events.return_value = {
            "events": [
                {
                    "logGroupName": "/aws/lambda/my-fn",
                    "timestamp": int(
                        datetime(2026, 1, 1, 12, 30, 0, tzinfo=timezone.utc).timestamp()
                        * 1000
                    ),
                    "message": "Processing request",
                },
            ],
            "nextToken": None,
        }

        with patch("boto3.client", return_value=mock_client):

            from typer.testing import CliRunner
            from rsf.cli.main import app

            runner = CliRunner()
            result = runner.invoke(
                app,
                [
                    "logs",
                    str(tmp_path / "workflow.yaml"),
                    "--tf-dir",
                    str(tmp_path),
                    "--no-color",
                ],
            )

            assert "Processing request" in result.output
            assert "my-fn" in result.output
