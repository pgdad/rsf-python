"""RSF logs subcommand — tail and search CloudWatch logs across workflow Lambdas."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

console = Console()

LEVEL_PRIORITY = {"ERROR": 3, "WARN": 2, "WARNING": 2, "INFO": 1}
LEVEL_COLORS = {"ERROR": "red", "WARN": "yellow", "WARNING": "yellow", "INFO": "green"}


def _discover_log_groups(tf_dir: Path) -> list[str]:
    """Discover CloudWatch log group names from Terraform state.

    Reads terraform.tfstate to find all aws_lambda_function resources
    and derives log group names as /aws/lambda/{function_name}.
    """
    tfstate_path = tf_dir / "terraform.tfstate"
    if not tfstate_path.exists():
        return []

    try:
        state_data = json.loads(tfstate_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    log_groups: list[str] = []
    for resource in state_data.get("resources", []):
        if resource.get("type") == "aws_lambda_function":
            for instance in resource.get("instances", []):
                fn_name = instance.get("attributes", {}).get("function_name")
                if fn_name:
                    log_groups.append(f"/aws/lambda/{fn_name}")

    return sorted(log_groups)


def _extract_function_name(log_group: str) -> str:
    """Extract the function name from a CloudWatch log group path."""
    if log_group.startswith("/aws/lambda/"):
        return log_group[len("/aws/lambda/") :]
    return log_group


def _extract_level(message: str) -> str:
    """Extract log level from a log message. Defaults to INFO."""
    upper = message.upper()
    if "ERROR" in upper or "EXCEPTION" in upper or "TRACEBACK" in upper:
        return "ERROR"
    if "WARN" in upper or "WARNING" in upper:
        return "WARN"
    return "INFO"


def _parse_since(since: str) -> int:
    """Parse a --since value into epoch milliseconds.

    Supports:
    - Duration: "1h", "30m", "2d" (hours, minutes, days)
    - ISO datetime: "2026-01-01T00:00:00Z"
    """
    # Try duration format
    match = re.match(r"^(\d+)([hmd])$", since.strip())
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        now = datetime.now(timezone.utc)
        if unit == "h":
            dt = now - timedelta(hours=value)
        elif unit == "m":
            dt = now - timedelta(minutes=value)
        elif unit == "d":
            dt = now - timedelta(days=value)
        else:
            dt = now - timedelta(hours=1)
        return int(dt.timestamp() * 1000)

    # Try ISO format
    try:
        dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except ValueError:
        pass

    # Default: 1 hour ago
    return int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp() * 1000)


def _filter_by_level(
    events: list[dict[str, Any]], min_level: str
) -> list[dict[str, Any]]:
    """Filter log events to only those at or above the minimum level."""
    min_priority = LEVEL_PRIORITY.get(min_level.upper(), 1)
    return [
        e
        for e in events
        if LEVEL_PRIORITY.get(_extract_level(e.get("message", "")), 1) >= min_priority
    ]


def _format_log_line(
    timestamp_ms: int,
    function_name: str,
    message: str,
    *,
    use_json: bool = False,
    no_color: bool = False,
) -> str:
    """Format a single log line for display.

    Standard format: [timestamp] [function-name] [level] message
    JSON format: {"timestamp": "...", "function": "...", "level": "...", "message": "..."}
    """
    dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    level = _extract_level(message)
    clean_message = message.strip()

    if use_json:
        return json.dumps(
            {
                "timestamp": dt.isoformat(),
                "function": function_name,
                "level": level,
                "message": clean_message,
            }
        )

    if no_color:
        return f"[{ts_str}] [{function_name}] [{level}] {clean_message}"

    color = LEVEL_COLORS.get(level, "white")
    return (
        f"[dim]{ts_str}[/dim] [bold]{function_name}[/bold] "
        f"[{color}]{level}[/{color}] {clean_message}"
    )


def logs(
    workflow: Path = typer.Argument(
        "workflow.yaml", help="Path to workflow YAML file"
    ),
    tf_dir: Path = typer.Option(
        "terraform",
        "--tf-dir",
        help="Terraform directory for log group discovery",
    ),
    execution_id: str | None = typer.Option(
        None, "--execution-id", help="Filter logs by execution ID"
    ),
    tail: bool = typer.Option(
        False, "--tail", "-f", help="Continuously stream new log events"
    ),
    since: str = typer.Option(
        "1h", "--since", help="Show logs since (e.g., 1h, 30m, 2d, or ISO date)"
    ),
    level: str | None = typer.Option(
        None, "--level", help="Minimum log level: INFO, WARN, ERROR"
    ),
    output_json: bool = typer.Option(
        False, "--json", help="Output in JSONL format"
    ),
    no_color: bool = typer.Option(
        False, "--no-color", help="Disable colored output"
    ),
    stage: str | None = typer.Option(
        None, "--stage", help="Deployment stage"
    ),
) -> None:
    """Tail and search CloudWatch logs across all workflow Lambda functions.

    Discovers Lambda functions from Terraform state and streams their logs
    in a unified, color-coded view. Use --execution-id to correlate logs
    from a specific workflow execution. Use --tail for continuous streaming.
    """
    import boto3

    # Stage handling
    effective_tf_dir = tf_dir
    if stage:
        effective_tf_dir = tf_dir / stage

    # Discover log groups
    log_groups = _discover_log_groups(effective_tf_dir)
    if not log_groups:
        console.print(
            "[red]Error:[/red] No Lambda functions found in Terraform state. "
            f"Check --tf-dir ({effective_tf_dir}) or deploy first."
        )
        raise typer.Exit(code=1)

    console.print(
        f"[blue]Streaming logs from {len(log_groups)} function(s)...[/blue]"
    )
    for lg in log_groups:
        console.print(f"  [dim]{lg}[/dim]")
    console.print()

    # Detect non-TTY
    is_tty = console.is_terminal
    effective_no_color = no_color or not is_tty

    # Build CloudWatch filter parameters
    start_time = _parse_since(since)
    filter_kwargs: dict[str, Any] = {
        "logGroupNames": log_groups,
        "startTime": start_time,
        "interleaved": True,
    }

    if execution_id:
        filter_kwargs["filterPattern"] = f'"{execution_id}"'

    client = boto3.client("logs")

    try:
        while True:
            # Fetch log events
            next_token: str | None = None
            all_events: list[dict[str, Any]] = []

            while True:
                if next_token:
                    filter_kwargs["nextToken"] = next_token
                elif "nextToken" in filter_kwargs:
                    del filter_kwargs["nextToken"]

                response = client.filter_log_events(**filter_kwargs)
                events = response.get("events", [])
                all_events.extend(events)

                next_token = response.get("nextToken")
                if not next_token:
                    break

            # Filter by level if specified
            if level:
                all_events = _filter_by_level(all_events, level)

            # Display events
            for event in all_events:
                log_group = event.get("logGroupName", "")
                fn_name = _extract_function_name(log_group)
                ts = event.get("timestamp", 0)
                msg = event.get("message", "")

                line = _format_log_line(
                    ts,
                    fn_name,
                    msg,
                    use_json=output_json,
                    no_color=effective_no_color,
                )

                if output_json or effective_no_color:
                    typer.echo(line)
                else:
                    console.print(line, highlight=False)

            if not tail:
                break

            # Update start time to avoid duplicate events
            if all_events:
                filter_kwargs["startTime"] = (
                    all_events[-1].get("timestamp", start_time) + 1
                )

            time.sleep(2)

    except KeyboardInterrupt:
        if tail:
            console.print("\n[dim]Log streaming stopped[/dim]")
