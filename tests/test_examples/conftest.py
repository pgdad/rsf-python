"""Shared integration test harness for RSF example workflows.

Provides:
- make_execution_id(): UUID-suffixed execution names for collision avoidance
- poll_execution(): Wait for durable execution terminal state with backoff
- query_logs(): CloudWatch Logs Insights query with propagation buffer
- terraform_deploy() / terraform_teardown(): Deploy/destroy + orphan cleanup
- iam_propagation_wait(): 15s buffer for IAM role propagation

Requirements covered: HARN-01, HARN-02, HARN-03, HARN-04, HARN-06, HARN-07
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import pytest
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Terminal states for durable executions
TERMINAL_STATUSES = frozenset({"SUCCEEDED", "FAILED", "TIMED_OUT", "STOPPED"})

# Project and examples root paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
EXAMPLES_ROOT = PROJECT_ROOT / "examples"


# ---------------------------------------------------------------------------
# Pytest marker registration
# ---------------------------------------------------------------------------


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: AWS integration tests (require credentials and terraform)",
    )


# ---------------------------------------------------------------------------
# UUID execution ID generator (HARN-06)
# ---------------------------------------------------------------------------


def make_execution_id(name: str) -> str:
    """Generate a unique execution ID for integration tests.

    Format: test-{name}-{YYYYMMDD}T{HHMMSS}-{uuid8}

    The UUID suffix prevents collisions across parallel or sequential re-runs.

    Args:
        name: Short name for the test (e.g. "order-processing").

    Returns:
        Unique execution ID string.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    uid = uuid.uuid4().hex[:8]
    return f"test-{name}-{ts}-{uid}"


# ---------------------------------------------------------------------------
# Polling helper (HARN-01)
# ---------------------------------------------------------------------------


def poll_execution(
    lambda_client: Any,
    function_name: str,
    execution_name: str,
    timeout: float = 300,
    poll_interval: float = 5.0,
) -> dict[str, Any]:
    """Poll for durable execution completion with exponential backoff on throttle.

    Uses list_durable_executions_by_function filtered by DurableExecutionName
    to check execution status. Polls every poll_interval seconds. On
    TooManyRequestsException, applies exponential backoff (max 30s).

    Args:
        lambda_client: boto3 Lambda client.
        function_name: Lambda function name.
        execution_name: The durable execution name to poll for.
        timeout: Maximum seconds to wait before raising TimeoutError.
        poll_interval: Base polling interval in seconds (default 5).

    Returns:
        Dict with execution summary: DurableExecutionArn, DurableExecutionName,
        Status, FunctionArn, StartTimestamp, EndTimestamp.

    Raises:
        TimeoutError: If execution does not reach terminal state within timeout.
    """
    deadline = time.monotonic() + timeout
    backoff = poll_interval

    while time.monotonic() < deadline:
        try:
            response = lambda_client.list_durable_executions_by_function(
                FunctionName=function_name,
                DurableExecutionName=execution_name,
                MaxItems=1,
            )
            executions = response.get("DurableExecutions", [])

            if executions:
                execution = executions[0]
                status = execution.get("Status", "")
                logger.info("poll_execution: %s status=%s", execution_name, status)
                if status in TERMINAL_STATUSES:
                    return execution

            # Reset backoff on successful API call
            backoff = poll_interval

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in ("TooManyRequestsException", "ThrottlingException"):
                logger.warning("poll_execution: throttled, backing off %.1fs", backoff)
                backoff = min(backoff * 2, 30.0)
            else:
                raise

        remaining = deadline - time.monotonic()
        sleep_time = min(backoff, max(remaining, 0))
        if sleep_time <= 0:
            break
        time.sleep(sleep_time)

    raise TimeoutError(f"Execution {execution_name!r} did not reach terminal state within {timeout}s")


# ---------------------------------------------------------------------------
# CloudWatch Logs query helper (HARN-02)
# ---------------------------------------------------------------------------


def query_logs(
    logs_client: Any,
    log_group: str,
    query: str,
    start_time: datetime,
    end_time: datetime | None = None,
    propagation_wait: float = 15.0,
    max_retries: int = 5,
    retry_interval: float = 5.0,
) -> list[list[dict[str, str]]]:
    """Query CloudWatch Logs Insights with propagation buffer and retry.

    Applies a propagation wait before the first query to account for log
    delivery delays and IAM timing. Retries until results are non-empty
    or max_retries is exhausted.

    Args:
        logs_client: boto3 CloudWatch Logs client.
        log_group: CloudWatch log group name.
        query: CloudWatch Logs Insights query string.
        start_time: Query start time (UTC datetime).
        end_time: Query end time (UTC datetime, defaults to now).
        propagation_wait: Seconds to wait before first query (default 15).
        max_retries: Maximum query attempts (default 5).
        retry_interval: Seconds between retries (default 5).

    Returns:
        List of result rows, where each row is a list of
        {field, value} dicts.
    """
    if end_time is None:
        end_time = datetime.now(timezone.utc)

    # Propagation buffer (HARN-07 overlap)
    logger.info("query_logs: waiting %.0fs for log propagation", propagation_wait)
    time.sleep(propagation_wait)

    for attempt in range(1, max_retries + 1):
        # Start the Insights query
        start_response = logs_client.start_query(
            logGroupName=log_group,
            startTime=int(start_time.timestamp()),
            endTime=int(end_time.timestamp()),
            queryString=query,
        )
        query_id = start_response["queryId"]

        # Poll for query completion
        while True:
            result = logs_client.get_query_results(queryId=query_id)
            status = result["status"]
            if status in ("Complete", "Failed", "Cancelled", "Timeout"):
                break
            time.sleep(1)

        results = result.get("results", [])
        if results:
            logger.info(
                "query_logs: got %d results on attempt %d",
                len(results),
                attempt,
            )
            return results

        logger.info(
            "query_logs: empty results on attempt %d/%d, retrying in %.0fs",
            attempt,
            max_retries,
            retry_interval,
        )
        if attempt < max_retries:
            time.sleep(retry_interval)

    logger.warning("query_logs: no results after %d attempts", max_retries)
    return []


# ---------------------------------------------------------------------------
# Terraform helpers
# ---------------------------------------------------------------------------


def terraform_deploy(example_dir: Path) -> dict[str, str]:
    """Deploy an example's Terraform infrastructure.

    Runs terraform init + apply in the example's terraform/ directory.
    Captures and returns terraform outputs as a dict.

    Args:
        example_dir: Path to the example directory (e.g. examples/order-processing).

    Returns:
        Dict of terraform output values (function_name, function_arn,
        log_group_name, etc.).
    """
    tf_dir = example_dir / "terraform"
    assert tf_dir.exists(), f"Terraform dir not found: {tf_dir}"

    logger.info("terraform_deploy: init %s", tf_dir)
    subprocess.run(
        ["terraform", "init", "-input=false"],
        cwd=tf_dir,
        check=True,
        capture_output=True,
        text=True,
    )

    logger.info("terraform_deploy: apply %s", tf_dir)
    subprocess.run(
        ["terraform", "apply", "-auto-approve", "-input=false"],
        cwd=tf_dir,
        check=True,
        capture_output=True,
        text=True,
    )

    logger.info("terraform_deploy: reading outputs %s", tf_dir)
    result = subprocess.run(
        ["terraform", "output", "-json"],
        cwd=tf_dir,
        check=True,
        capture_output=True,
        text=True,
    )

    raw_outputs = json.loads(result.stdout)
    # terraform output -json wraps each in {"value": ..., "type": ...}
    return {k: v["value"] for k, v in raw_outputs.items()}


def terraform_teardown(
    example_dir: Path,
    logs_client: Any | None = None,
    log_group_name: str | None = None,
) -> None:
    """Destroy an example's Terraform infrastructure and clean orphaned resources.

    Runs terraform destroy, then explicitly deletes the CloudWatch log group
    to prevent orphaned resources. (HARN-03)

    Args:
        example_dir: Path to the example directory.
        logs_client: boto3 CloudWatch Logs client (optional).
        log_group_name: Log group to delete (optional).
    """
    tf_dir = example_dir / "terraform"

    logger.info("terraform_teardown: destroy %s", tf_dir)
    subprocess.run(
        ["terraform", "destroy", "-auto-approve", "-input=false"],
        cwd=tf_dir,
        check=True,
        capture_output=True,
        text=True,
    )

    # Explicitly delete orphaned log groups (HARN-03)
    if logs_client and log_group_name:
        logger.info("terraform_teardown: deleting log group %s", log_group_name)
        try:
            logs_client.delete_log_group(logGroupName=log_group_name)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.info(
                    "terraform_teardown: log group already deleted: %s",
                    log_group_name,
                )
            else:
                raise


# ---------------------------------------------------------------------------
# IAM propagation buffer (HARN-07)
# ---------------------------------------------------------------------------


def iam_propagation_wait(seconds: float = 15.0) -> None:
    """Wait for IAM role/policy propagation after terraform apply.

    AWS IAM changes can take up to 15 seconds to propagate. This buffer
    prevents Lambda invocation failures due to missing permissions.

    Args:
        seconds: Seconds to wait (default 15).
    """
    logger.info("iam_propagation_wait: waiting %.0fs", seconds)
    time.sleep(seconds)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def aws_region():
    """AWS region for integration tests."""
    return "us-east-2"


@pytest.fixture(scope="session")
def lambda_client(aws_region):
    """Shared boto3 Lambda client for integration tests."""
    return boto3.client("lambda", region_name=aws_region)


@pytest.fixture(scope="session")
def logs_client(aws_region):
    """Shared boto3 CloudWatch Logs client for integration tests."""
    return boto3.client("logs", region_name=aws_region)
