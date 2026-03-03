"""Tests for rsf test subcommand (local workflow execution)."""

from __future__ import annotations

import textwrap
from io import StringIO

from rich.console import Console

from rsf.cli.test_cmd import ExecutionResult, LocalRunner, TransitionRecord, _render_summary
from rsf.dsl.parser import parse_definition


def _make_definition(states_yaml: dict, start_at: str = "Start", **kwargs):
    """Helper to create a StateMachineDefinition from a dict."""
    data = {
        "StartAt": start_at,
        "States": states_yaml,
        **kwargs,
    }
    return parse_definition(data)


class TestLocalRunner:
    """Tests for the LocalRunner execution engine."""

    def test_simple_two_state_workflow_executes(self, tmp_path):
        """Simple Task -> End workflow executes and returns final output."""
        defn = _make_definition({
            "Start": {"Type": "Task", "End": True},
        })

        # Create a simple handler
        handlers_dir = tmp_path / "handlers"
        handlers_dir.mkdir()
        (handlers_dir / "start.py").write_text(
            "def start(event):\n    return {'result': 'done'}\n"
        )

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            console=Console(file=StringIO()),
        )
        result = runner.run({"input": "test"})

        assert result.success is True
        assert result.final_output == {"result": "done"}
        assert len(result.transitions) == 1

    def test_trace_includes_state_names_and_transitions(self, tmp_path):
        """Trace output includes state names and transition arrows."""
        defn = _make_definition({
            "Start": {"Type": "Task", "Next": "End"},
            "End": {"Type": "Succeed"},
        })

        handlers_dir = tmp_path / "handlers"
        handlers_dir.mkdir()
        (handlers_dir / "start.py").write_text(
            "def start(event):\n    return event\n"
        )

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            console=Console(file=StringIO()),
        )
        result = runner.run({"key": "value"})

        assert result.success is True
        assert len(result.transitions) == 2
        assert result.transitions[0].from_state == "Start"
        assert result.transitions[0].to_state == "End"
        assert result.transitions[1].from_state == "End"
        assert result.transitions[1].to_state is None

    def test_pass_state_injects_result(self, tmp_path):
        """Pass state injects Result into output correctly."""
        defn = _make_definition({
            "Start": {"Type": "Pass", "Result": {"injected": True}, "End": True},
        })

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            console=Console(file=StringIO()),
        )
        result = runner.run({})

        assert result.success is True
        assert result.final_output == {"injected": True}

    def test_choice_state_routes_correctly(self, tmp_path):
        """Choice state routes to correct branch based on input data."""
        defn = _make_definition(
            {
                "Start": {
                    "Type": "Choice",
                    "Choices": [
                        {
                            "Variable": "$.status",
                            "StringEquals": "approved",
                            "Next": "Approved",
                        },
                    ],
                    "Default": "Rejected",
                },
                "Approved": {"Type": "Pass", "Result": {"approved": True}, "End": True},
                "Rejected": {"Type": "Pass", "Result": {"rejected": True}, "End": True},
            },
        )

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            console=Console(file=StringIO()),
        )

        # Test approved path
        result = runner.run({"status": "approved"})
        assert result.success is True
        assert result.final_output == {"approved": True}
        assert result.transitions[0].to_state == "Approved"

    def test_choice_state_falls_to_default(self, tmp_path):
        """Choice state falls to Default when no rule matches."""
        defn = _make_definition(
            {
                "Start": {
                    "Type": "Choice",
                    "Choices": [
                        {
                            "Variable": "$.status",
                            "StringEquals": "approved",
                            "Next": "Approved",
                        },
                    ],
                    "Default": "Rejected",
                },
                "Approved": {"Type": "Pass", "Result": {"approved": True}, "End": True},
                "Rejected": {"Type": "Pass", "Result": {"rejected": True}, "End": True},
            },
        )

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            console=Console(file=StringIO()),
        )

        result = runner.run({"status": "pending"})
        assert result.success is True
        assert result.final_output == {"rejected": True}
        assert result.transitions[0].to_state == "Rejected"

    def test_wait_state_skipped_in_local_mode(self, tmp_path):
        """Wait state is skipped (no delay) but appears in trace."""
        defn = _make_definition({
            "Start": {"Type": "Wait", "Seconds": 30, "Next": "Done"},
            "Done": {"Type": "Succeed"},
        })

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            console=Console(file=StringIO()),
        )
        result = runner.run({})

        assert result.success is True
        assert len(result.transitions) == 2
        assert result.transitions[0].state_type == "Wait"
        # Should complete nearly instantly (no real 30s delay)
        assert result.total_duration_ms < 1000

    def test_succeed_state_terminates_with_success(self, tmp_path):
        """Succeed state terminates execution with success."""
        defn = _make_definition({
            "Start": {"Type": "Succeed"},
        })

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            console=Console(file=StringIO()),
        )
        result = runner.run({"data": "test"})

        assert result.success is True
        assert result.final_output == {"data": "test"}

    def test_fail_state_terminates_with_error(self, tmp_path):
        """Fail state terminates execution with error message."""
        defn = _make_definition({
            "Start": {
                "Type": "Fail",
                "Error": "CustomError",
                "Cause": "Something went wrong",
            },
        })

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            console=Console(file=StringIO()),
        )
        result = runner.run({})

        assert result.success is False
        assert "CustomError" in result.error
        assert "Something went wrong" in result.error

    def test_mock_handlers_passes_input_through(self, tmp_path):
        """--mock-handlers passes input through without calling real handler functions."""
        defn = _make_definition({
            "Start": {"Type": "Task", "Next": "Process"},
            "Process": {"Type": "Task", "End": True},
        })

        # Don't create any handler files -- mock mode shouldn't need them
        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            mock_handlers=True,
            console=Console(file=StringIO()),
        )
        result = runner.run({"key": "value"})

        assert result.success is True
        assert result.final_output == {"key": "value"}
        assert len(result.transitions) == 2

    def test_handler_exception_with_catch_routes_to_target(self, tmp_path):
        """Handler exception with Catch routes to the catch target state."""
        defn = _make_definition({
            "Start": {
                "Type": "Task",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "Next": "HandleError",
                    },
                ],
                "End": True,
            },
            "HandleError": {
                "Type": "Pass",
                "Result": {"handled": True},
                "End": True,
            },
        })

        handlers_dir = tmp_path / "handlers"
        handlers_dir.mkdir()
        (handlers_dir / "start.py").write_text(
            "def start(event):\n    raise ValueError('test error')\n"
        )

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            console=Console(file=StringIO()),
        )
        result = runner.run({"key": "value"})

        assert result.success is True
        assert result.final_output == {"handled": True}
        # Should have transitions: Start (caught) -> HandleError
        assert any(t.to_state == "HandleError" for t in result.transitions)

    def test_handler_exception_with_retry(self, tmp_path):
        """Handler exception with Retry retries the configured number of times."""
        defn = _make_definition({
            "Start": {
                "Type": "Task",
                "Retry": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "MaxAttempts": 2,
                        "IntervalSeconds": 0,
                    },
                ],
                "End": True,
            },
        })

        handlers_dir = tmp_path / "handlers"
        handlers_dir.mkdir()
        # Handler that fails first 2 times, succeeds on 3rd
        (handlers_dir / "start.py").write_text(textwrap.dedent("""\
            _call_count = 0
            def start(event):
                global _call_count
                _call_count += 1
                if _call_count < 3:
                    raise ValueError(f'attempt {_call_count}')
                return {'attempt': _call_count}
        """))

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            console=Console(file=StringIO()),
        )
        result = runner.run({})

        assert result.success is True
        assert result.final_output == {"attempt": 3}

    def test_handler_exception_without_error_handling_stops(self, tmp_path):
        """Handler exception without error handling stops execution with traceback."""
        defn = _make_definition({
            "Start": {"Type": "Task", "End": True},
        })

        handlers_dir = tmp_path / "handlers"
        handlers_dir.mkdir()
        (handlers_dir / "start.py").write_text(
            "def start(event):\n    raise RuntimeError('fatal error')\n"
        )

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            console=Console(file=StringIO()),
        )
        result = runner.run({})

        assert result.success is False
        assert "RuntimeError" in result.error or "fatal error" in result.error

    def test_json_output_produces_json_lines(self, tmp_path):
        """--json flag produces JSON lines output (one dict per transition)."""
        defn = _make_definition({
            "Start": {"Type": "Pass", "Result": {"ok": True}, "End": True},
        })

        output = StringIO()
        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            json_output=True,
            console=Console(file=output),
        )
        result = runner.run({})

        assert result.success is True
        # The output should contain valid JSON
        raw_output = output.getvalue()
        assert "from" in raw_output
        assert "Start" in raw_output

    def test_summary_table_shows_all_visited_states(self, tmp_path):
        """Summary table shows all visited states with durations."""
        result = ExecutionResult(
            success=True,
            final_output={"done": True},
            transitions=[
                TransitionRecord(
                    from_state="Start",
                    to_state="Process",
                    state_type="Task",
                    duration_ms=42.0,
                ),
                TransitionRecord(
                    from_state="Process",
                    to_state=None,
                    state_type="Succeed",
                    duration_ms=1.0,
                ),
            ],
            total_duration_ms=43.0,
        )

        table = _render_summary(result)
        assert table.row_count == 2

    def test_verbose_mode_records_input_output(self, tmp_path):
        """Verbose mode (-v) records input/output payloads at each state."""
        defn = _make_definition({
            "Start": {"Type": "Pass", "Result": {"transformed": True}, "End": True},
        })

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            verbose=True,
            console=Console(file=StringIO()),
        )
        result = runner.run({"original": "data"})

        assert result.success is True
        # Verbose mode should record input/output in transitions
        assert result.transitions[0].input_data == {"original": "data"}
        assert result.transitions[0].output_data == {"transformed": True}


class TestChaosIntegration:
    """Tests for --chaos flag integration with LocalRunner."""

    def test_chaos_timeout_injection_fails_state(self, tmp_path):
        """--chaos StateName:timeout causes the state to fail with ChaosTimeoutError."""
        from rsf.testing.chaos import ChaosFixture

        defn = _make_definition({
            "Start": {"Type": "Task", "End": True},
        })

        handlers_dir = tmp_path / "handlers"
        handlers_dir.mkdir()
        (handlers_dir / "start.py").write_text(
            "def start(event):\n    return {'result': 'done'}\n"
        )

        chaos = ChaosFixture()
        chaos.inject_failure("Start", "timeout")

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            chaos_fixture=chaos,
            console=Console(file=StringIO()),
        )
        result = runner.run({"input": "test"})

        assert result.success is False
        assert "timeout" in result.error.lower() or "Timeout" in result.error

    def test_chaos_exception_injection_fails_state(self, tmp_path):
        """--chaos StateName:exception causes RuntimeError."""
        from rsf.testing.chaos import ChaosFixture

        defn = _make_definition({
            "Start": {"Type": "Task", "End": True},
        })

        handlers_dir = tmp_path / "handlers"
        handlers_dir.mkdir()
        (handlers_dir / "start.py").write_text(
            "def start(event):\n    return {'result': 'done'}\n"
        )

        chaos = ChaosFixture()
        chaos.inject_failure("Start", "exception")

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            chaos_fixture=chaos,
            console=Console(file=StringIO()),
        )
        result = runner.run({})

        assert result.success is False
        assert "Exception injected" in result.error or "RuntimeError" in result.error

    def test_chaos_throttle_injection_fails_state(self, tmp_path):
        """--chaos StateName:throttle causes ChaosThrottleError."""
        from rsf.testing.chaos import ChaosFixture

        defn = _make_definition({
            "Start": {"Type": "Task", "End": True},
        })

        handlers_dir = tmp_path / "handlers"
        handlers_dir.mkdir()
        (handlers_dir / "start.py").write_text(
            "def start(event):\n    return {'ok': True}\n"
        )

        chaos = ChaosFixture()
        chaos.inject_failure("Start", "throttle")

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            chaos_fixture=chaos,
            console=Console(file=StringIO()),
        )
        result = runner.run({})

        assert result.success is False
        assert "TooManyRequests" in result.error or "throttle" in result.error.lower()

    def test_chaos_with_catch_routes_to_error_handler(self, tmp_path):
        """Chaos-injected failure interacts with Catch to route to error handler."""
        from rsf.testing.chaos import ChaosFixture

        defn = _make_definition({
            "Start": {
                "Type": "Task",
                "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "HandleError"}],
                "End": True,
            },
            "HandleError": {
                "Type": "Pass",
                "Result": {"caught": True},
                "End": True,
            },
        })

        handlers_dir = tmp_path / "handlers"
        handlers_dir.mkdir()
        (handlers_dir / "start.py").write_text(
            "def start(event):\n    return {'ok': True}\n"
        )

        chaos = ChaosFixture()
        chaos.inject_failure("Start", "exception")

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            chaos_fixture=chaos,
            console=Console(file=StringIO()),
        )
        result = runner.run({})

        assert result.success is True
        assert result.final_output == {"caught": True}

    def test_chaos_with_retry_and_count(self, tmp_path):
        """Chaos-injected failure with count=1 interacts with Retry -- first call fails, retry succeeds."""
        from rsf.testing.chaos import ChaosFixture

        defn = _make_definition({
            "Start": {
                "Type": "Task",
                "Retry": [{"ErrorEquals": ["States.ALL"], "MaxAttempts": 2, "IntervalSeconds": 0}],
                "End": True,
            },
        })

        handlers_dir = tmp_path / "handlers"
        handlers_dir.mkdir()
        (handlers_dir / "start.py").write_text(
            "def start(event):\n    return {'result': 'ok'}\n"
        )

        chaos = ChaosFixture()
        chaos.inject_failure("Start", "timeout", count=1)

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            chaos_fixture=chaos,
            console=Console(file=StringIO()),
        )
        result = runner.run({})

        # First attempt hits chaos (timeout), retry calls real handler which succeeds
        assert result.success is True
        assert result.final_output == {"result": "ok"}

    def test_chaos_non_injected_state_runs_normally(self, tmp_path):
        """States without chaos injection execute normally."""
        from rsf.testing.chaos import ChaosFixture

        defn = _make_definition({
            "Start": {"Type": "Task", "Next": "Process"},
            "Process": {"Type": "Task", "End": True},
        })

        handlers_dir = tmp_path / "handlers"
        handlers_dir.mkdir()
        (handlers_dir / "start.py").write_text(
            "def start(event):\n    return {'step': 1}\n"
        )
        (handlers_dir / "process.py").write_text(
            "def process(event):\n    return {'step': 2}\n"
        )

        chaos = ChaosFixture()
        chaos.inject_failure("Process", "timeout")  # Only Process fails

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            chaos_fixture=chaos,
            console=Console(file=StringIO()),
        )
        result = runner.run({})

        # Start runs fine, Process fails
        assert result.success is False
        assert result.transitions[0].from_state == "Start"
        assert result.transitions[0].error is None  # Start succeeded

    def test_no_chaos_fixture_runs_normally(self, tmp_path):
        """When chaos_fixture is None (default), behavior is unchanged."""
        defn = _make_definition({
            "Start": {"Type": "Task", "End": True},
        })

        handlers_dir = tmp_path / "handlers"
        handlers_dir.mkdir()
        (handlers_dir / "start.py").write_text(
            "def start(event):\n    return {'result': 'done'}\n"
        )

        runner = LocalRunner(
            definition=defn,
            workflow_dir=tmp_path,
            chaos_fixture=None,
            console=Console(file=StringIO()),
        )
        result = runner.run({"input": "test"})

        assert result.success is True
        assert result.final_output == {"result": "done"}
