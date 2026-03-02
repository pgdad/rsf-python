"""RSF test subcommand — execute a workflow locally with trace output."""

from __future__ import annotations

import importlib.util
import json
import re
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from rsf.dsl.models import (
    ChoiceState,
    FailState,
    PassState,
    StateMachineDefinition,
    SucceedState,
    TaskState,
    WaitState,
)
from rsf.dsl.parser import load_definition

console = Console()


@dataclass
class TransitionRecord:
    """Record of a single state transition during execution."""

    from_state: str
    to_state: str | None  # None for terminal states
    state_type: str
    duration_ms: float
    handler_result: Any = None
    error: str | None = None
    input_data: Any = None
    output_data: Any = None


@dataclass
class ExecutionResult:
    """Result of a local workflow execution."""

    success: bool
    final_output: Any = None
    error: str | None = None
    transitions: list[TransitionRecord] = field(default_factory=list)
    total_duration_ms: float = 0.0


class _CatchRedirect(Exception):
    """Internal exception to signal a catch redirect."""

    def __init__(self, target: str, data: Any):
        self.target = target
        self.data = data
        super().__init__(f"Redirecting to {target}")


def _to_snake_case(name: str) -> str:
    """Convert PascalCase or camelCase to snake_case."""
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    return s.lower()


def _resolve_path(data: Any, path: str) -> Any:
    """Resolve a simple JSONPath reference like $.field or $.field.nested."""
    if path == "$":
        return data
    if not path.startswith("$."):
        return None
    parts = path[2:].split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _evaluate_choice_rule(rule: Any, data: Any) -> bool:
    """Evaluate a single choice rule against the input data."""
    from rsf.dsl.choice import BooleanAndRule, BooleanNotRule, BooleanOrRule, DataTestRule

    if isinstance(rule, BooleanAndRule):
        return all(_evaluate_choice_rule(r, data) for r in rule.and_)
    if isinstance(rule, BooleanOrRule):
        return any(_evaluate_choice_rule(r, data) for r in rule.or_)
    if isinstance(rule, BooleanNotRule):
        return not _evaluate_choice_rule(rule.not_, data)

    if isinstance(rule, DataTestRule):
        value = _resolve_path(data, rule.variable)

        # String operators
        if rule.string_equals is not None:
            return value == rule.string_equals
        # Numeric operators
        if rule.numeric_equals is not None:
            return value == rule.numeric_equals
        if rule.numeric_greater_than is not None:
            return isinstance(value, (int, float)) and value > rule.numeric_greater_than
        if rule.numeric_less_than is not None:
            return isinstance(value, (int, float)) and value < rule.numeric_less_than
        if rule.numeric_greater_than_equals is not None:
            return isinstance(value, (int, float)) and value >= rule.numeric_greater_than_equals
        if rule.numeric_less_than_equals is not None:
            return isinstance(value, (int, float)) and value <= rule.numeric_less_than_equals
        # Boolean operator
        if rule.boolean_equals is not None:
            return value == rule.boolean_equals
        # Type checking
        if rule.is_present is not None:
            present = value is not None
            return present == rule.is_present
        if rule.is_null is not None:
            is_null = value is None
            return is_null == rule.is_null

    return False


def _load_handler(state_name: str, workflow_dir: Path) -> Any:
    """Dynamically load a handler function for a Task state."""
    module_name = _to_snake_case(state_name)
    handler_path = workflow_dir / "handlers" / f"{module_name}.py"

    if not handler_path.exists():
        raise FileNotFoundError(
            f"Handler file not found: {handler_path}\n"
            f"Run 'rsf generate' to create handler stubs."
        )

    spec = importlib.util.spec_from_file_location(f"handlers.{module_name}", handler_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load handler module: {handler_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    handler_fn = getattr(module, module_name, None)
    if handler_fn is None:
        raise AttributeError(f"Handler function '{module_name}' not found in {handler_path}")

    return handler_fn


def _matches_error(error_equals: list[str], error_type: str) -> bool:
    """Check if an error type matches a Retry/Catch error pattern."""
    for pattern in error_equals:
        if pattern == "States.ALL":
            return True
        if pattern == error_type:
            return True
        if pattern == "States.TaskFailed":
            return True
    return False


class LocalRunner:
    """Executes a workflow definition locally with trace output."""

    def __init__(
        self,
        definition: StateMachineDefinition,
        workflow_dir: Path,
        mock_handlers: bool = False,
        json_output: bool = False,
        verbose: bool = False,
        console: Console | None = None,
    ):
        self.definition = definition
        self.workflow_dir = workflow_dir
        self.mock_handlers = mock_handlers
        self.json_output = json_output
        self.verbose = verbose
        self.console = console or Console()
        self.transitions: list[TransitionRecord] = []

    def run(self, input_data: Any) -> ExecutionResult:
        """Execute the workflow with the given input."""
        start_time = time.monotonic()
        current_state = self.definition.start_at
        current_data = input_data

        while True:
            state = self.definition.states.get(current_state)
            if state is None:
                return ExecutionResult(
                    success=False,
                    error=f"State '{current_state}' not found",
                    transitions=self.transitions,
                    total_duration_ms=(time.monotonic() - start_time) * 1000,
                )

            state_start = time.monotonic()
            state_type = getattr(state, "type", "Unknown")

            try:
                next_state, output_data, error = self._execute_state(current_state, state, current_data)
            except Exception as exc:
                duration_ms = (time.monotonic() - state_start) * 1000
                self.transitions.append(
                    TransitionRecord(
                        from_state=current_state,
                        to_state=None,
                        state_type=state_type,
                        duration_ms=duration_ms,
                        error=str(exc),
                        input_data=current_data if self.verbose else None,
                    )
                )
                self._emit_trace(current_state, None, state_type, duration_ms, error=str(exc))
                return ExecutionResult(
                    success=False,
                    error=f"Unhandled exception in {current_state}: {exc}\n{traceback.format_exc()}",
                    transitions=self.transitions,
                    total_duration_ms=(time.monotonic() - start_time) * 1000,
                )

            duration_ms = (time.monotonic() - state_start) * 1000

            record = TransitionRecord(
                from_state=current_state,
                to_state=next_state,
                state_type=state_type,
                duration_ms=duration_ms,
                handler_result=output_data if state_type == "Task" else None,
                error=error,
                input_data=current_data if self.verbose else None,
                output_data=output_data if self.verbose else None,
            )
            self.transitions.append(record)
            self._emit_trace(current_state, next_state, state_type, duration_ms, error=error)

            if next_state is None:
                # Terminal state
                return ExecutionResult(
                    success=error is None,
                    final_output=output_data,
                    error=error,
                    transitions=self.transitions,
                    total_duration_ms=(time.monotonic() - start_time) * 1000,
                )

            current_data = output_data if output_data is not None else current_data
            current_state = next_state

    def _execute_state(
        self, name: str, state: Any, data: Any
    ) -> tuple[str | None, Any, str | None]:
        """Execute a single state and return (next_state, output, error)."""
        if isinstance(state, TaskState):
            return self._execute_task(name, state, data)
        elif isinstance(state, PassState):
            return self._execute_pass(state, data)
        elif isinstance(state, ChoiceState):
            return self._execute_choice(state, data)
        elif isinstance(state, WaitState):
            return self._execute_wait(state, data)
        elif isinstance(state, SucceedState):
            return None, data, None
        elif isinstance(state, FailState):
            error_msg = state.error or "States.TaskFailed"
            cause = state.cause or "Workflow failed"
            return None, None, f"{error_msg}: {cause}"
        else:
            return None, data, f"Unsupported state type: {type(state).__name__}"

    def _execute_task(
        self, name: str, state: TaskState, data: Any
    ) -> tuple[str | None, Any, str | None]:
        """Execute a Task state, handling mock mode, retry, and catch."""
        if self.mock_handlers or state.sub_workflow:
            # Mock mode or sub-workflow: pass through
            result = data
        else:
            try:
                result = self._call_handler_with_retry(name, state, data)
            except _CatchRedirect as redirect:
                # Route to catch target
                return redirect.target, redirect.data, None

        next_state = state.next if state.next else None
        if state.end:
            next_state = None
        return next_state, result, None

    def _call_handler_with_retry(self, name: str, state: TaskState, data: Any) -> Any:
        """Call a handler with retry logic."""
        handler_fn = _load_handler(name, self.workflow_dir)

        retry_policies = state.retry or []
        max_total_attempts = 1
        for policy in retry_policies:
            max_total_attempts = max(max_total_attempts, policy.max_attempts + 1)

        last_exception = None
        for attempt in range(max_total_attempts):
            try:
                return handler_fn(data)
            except Exception as exc:
                last_exception = exc
                error_type = type(exc).__name__

                # Check retry policies
                should_retry = False
                if attempt < max_total_attempts - 1:
                    for policy in retry_policies:
                        if _matches_error(policy.error_equals, error_type):
                            if attempt < policy.max_attempts:
                                should_retry = True
                                break

                if not should_retry:
                    # Check catch policies
                    if state.catch:
                        for catcher in state.catch:
                            if _matches_error(catcher.error_equals, error_type):
                                error_output = {
                                    "Error": error_type,
                                    "Cause": str(exc),
                                }
                                if catcher.result_path:
                                    catch_data = dict(data) if isinstance(data, dict) else {}
                                    path_key = catcher.result_path.lstrip("$.")
                                    catch_data[path_key] = error_output
                                    raise _CatchRedirect(catcher.next, catch_data)
                                raise _CatchRedirect(catcher.next, error_output)

                    # No retry or catch matched -- re-raise
                    raise

        # Should not reach here, but just in case
        raise last_exception  # type: ignore[misc]

    def _execute_pass(self, state: PassState, data: Any) -> tuple[str | None, Any, str | None]:
        """Execute a Pass state."""
        output = state.result if state.result is not None else data
        next_state = state.next if state.next else None
        if state.end:
            next_state = None
        return next_state, output, None

    def _execute_choice(self, state: ChoiceState, data: Any) -> tuple[str | None, Any, str | None]:
        """Execute a Choice state by evaluating rules."""
        for rule in state.choices:
            if _evaluate_choice_rule(rule, data):
                return rule.next, data, None

        if state.default:
            return state.default, data, None

        return None, None, "No choice rule matched and no Default specified"

    def _execute_wait(self, state: WaitState, data: Any) -> tuple[str | None, Any, str | None]:
        """Execute a Wait state (skip actual delay in local mode)."""
        next_state = state.next if state.next else None
        if state.end:
            next_state = None
        return next_state, data, None

    def _emit_trace(
        self,
        from_state: str,
        to_state: str | None,
        state_type: str,
        duration_ms: float,
        error: str | None = None,
    ) -> None:
        """Emit a trace line for a state transition."""
        if self.json_output:
            record: dict[str, Any] = {
                "from": from_state,
                "to": to_state,
                "type": state_type,
                "duration_ms": round(duration_ms, 2),
            }
            if error:
                record["error"] = error
            self.console.print_json(json.dumps(record))
        else:
            arrow = f" -> {to_state}" if to_state else " [END]"
            timing = f"({state_type}: {duration_ms:.0f}ms)"
            if error:
                self.console.print(f"  [red]{from_state}{arrow} {timing} ERROR: {error}[/red]")
            else:
                self.console.print(f"  {from_state}{arrow} {timing}")

            if self.verbose and self.transitions:
                latest = self.transitions[-1]
                if latest.input_data is not None:
                    self.console.print(
                        f"    [dim]Input:  {json.dumps(latest.input_data, default=str)}[/dim]"
                    )
                if latest.output_data is not None:
                    self.console.print(
                        f"    [dim]Output: {json.dumps(latest.output_data, default=str)}[/dim]"
                    )


def _render_summary(result: ExecutionResult) -> Table:
    """Render the execution summary table."""
    table = Table(title="Execution Summary")
    table.add_column("State", style="bold")
    table.add_column("Type")
    table.add_column("Duration")
    table.add_column("Result")

    for tr in result.transitions:
        status = "[green]OK[/green]" if tr.error is None else f"[red]{tr.error}[/red]"
        table.add_row(
            tr.from_state,
            tr.state_type,
            f"{tr.duration_ms:.0f}ms",
            status,
        )

    return table


def test_workflow(
    workflow: Path = typer.Argument("workflow.yaml", help="Path to workflow YAML file"),
    input_data: str = typer.Option("{}", "--input", "-i", help="JSON input payload"),
    mock_handlers: bool = typer.Option(False, "--mock-handlers", help="Skip real handler execution"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON lines for each transition"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show input/output at each state"),
) -> None:
    """Execute a workflow locally with trace output.

    Calls real Python handler functions and follows state transitions.
    Shows streaming trace output and a summary table.
    """
    # Check workflow file exists
    if not workflow.exists():
        console.print(f"[red]Error:[/red] Workflow file not found: [bold]{workflow}[/bold]")
        raise typer.Exit(code=1)

    # Parse input JSON
    try:
        parsed_input = json.loads(input_data)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Error:[/red] Invalid JSON input: {exc}")
        raise typer.Exit(code=1)

    # Load workflow
    try:
        definition = load_definition(workflow)
    except Exception as exc:
        console.print(f"[red]Error:[/red] Invalid workflow: {exc}")
        raise typer.Exit(code=1)

    workflow_dir = workflow.parent

    if not json_output:
        console.print(f"\n[bold]Testing workflow:[/bold] {workflow}")
        console.print(f"[bold]Input:[/bold] {input_data}\n")

    # Execute
    runner = LocalRunner(
        definition=definition,
        workflow_dir=workflow_dir,
        mock_handlers=mock_handlers,
        json_output=json_output,
        verbose=verbose,
    )
    result = runner.run(parsed_input)

    # Summary
    if not json_output:
        console.print()
        summary = _render_summary(result)
        console.print(summary)

        console.print(f"\n[bold]Total duration:[/bold] {result.total_duration_ms:.0f}ms")

        if result.success:
            console.print(f"[bold]Final output:[/bold] {json.dumps(result.final_output, default=str)}")
            console.print("[green]Workflow completed successfully.[/green]")
        else:
            console.print(f"[red]Workflow failed:[/red] {result.error}")
            raise typer.Exit(code=1)
