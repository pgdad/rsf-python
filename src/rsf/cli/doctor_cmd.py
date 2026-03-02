"""RSF doctor subcommand — diagnose environment and project health."""

from __future__ import annotations

import importlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import typer
from rich.console import Console

console = Console()

CheckStatus = Literal["PASS", "WARN", "FAIL"]


@dataclass
class CheckResult:
    """Result of a single doctor check."""

    name: str
    status: CheckStatus
    version: str | None = None
    message: str = ""
    fix_hint: str | None = None


def _check_python() -> CheckResult:
    """Check Python version >= 3.10."""
    v = sys.version_info
    version_str = f"{v[0]}.{v[1]}.{v[2]}"
    if v >= (3, 10):
        return CheckResult(
            name="Python",
            status="PASS",
            version=version_str,
            message=f"Python {version_str}",
        )
    elif v >= (3, 8):
        return CheckResult(
            name="Python",
            status="WARN",
            version=version_str,
            message=f"Python {version_str} — RSF recommends >= 3.10",
            fix_hint="Upgrade: https://python.org/downloads/",
        )
    else:
        return CheckResult(
            name="Python",
            status="FAIL",
            version=version_str,
            message=f"Python {version_str} — RSF requires >= 3.10",
            fix_hint="Install Python >= 3.10: https://python.org/downloads/",
        )


def _check_terraform() -> CheckResult:
    """Check Terraform binary and version >= 1.0."""
    tf_path = shutil.which("terraform")
    if not tf_path:
        return CheckResult(
            name="Terraform",
            status="FAIL",
            message="Not found",
            fix_hint="Install: brew install terraform or https://terraform.io/downloads",
        )

    try:
        proc = subprocess.run(
            ["terraform", "version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Parse version from output like "Terraform v1.5.7"
        output = proc.stdout.strip().split("\n")[0]
        match = re.search(r"v?(\d+\.\d+\.\d+)", output)
        if match:
            version_str = match.group(1)
            major = int(version_str.split(".")[0])
            if major >= 1:
                return CheckResult(
                    name="Terraform",
                    status="PASS",
                    version=version_str,
                    message=f"Terraform {version_str}",
                )
            else:
                return CheckResult(
                    name="Terraform",
                    status="WARN",
                    version=version_str,
                    message=f"Terraform {version_str} — RSF recommends >= 1.0",
                    fix_hint="Upgrade: https://terraform.io/downloads",
                )
    except (subprocess.SubprocessError, OSError):
        pass

    return CheckResult(
        name="Terraform",
        status="WARN",
        message="Found but could not determine version",
    )


def _check_aws_credentials() -> CheckResult:
    """Check AWS credential validity."""
    try:
        import boto3

        session = boto3.Session()
        credentials = session.get_credentials()
        if credentials is not None:
            # Try to resolve credentials (checks if they're actually valid)
            resolved = credentials.get_frozen_credentials()
            if resolved.access_key:
                return CheckResult(
                    name="AWS Credentials",
                    status="PASS",
                    message="Credentials available",
                )
    except Exception:
        pass

    return CheckResult(
        name="AWS Credentials",
        status="FAIL",
        message="No valid AWS credentials found",
        fix_hint="Configure: aws configure, or set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY env vars",
    )


def _check_boto3() -> CheckResult:
    """Check boto3 SDK availability."""
    try:
        mod = importlib.import_module("boto3")
        version_str = getattr(mod, "__version__", "unknown")
        return CheckResult(
            name="boto3 SDK",
            status="PASS",
            version=version_str,
            message=f"boto3 {version_str}",
        )
    except ImportError:
        return CheckResult(
            name="boto3 SDK",
            status="FAIL",
            message="Not installed",
            fix_hint="Install: pip install boto3",
        )


def _check_aws_cli() -> CheckResult:
    """Check AWS CLI availability (optional but recommended)."""
    aws_path = shutil.which("aws")
    if not aws_path:
        return CheckResult(
            name="AWS CLI",
            status="WARN",
            message="Not found (optional)",
            fix_hint="Install: brew install awscli or https://aws.amazon.com/cli/",
        )

    try:
        proc = subprocess.run(
            ["aws", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        version_output = proc.stdout.strip() or proc.stderr.strip()
        match = re.search(r"aws-cli/(\S+)", version_output)
        if match:
            return CheckResult(
                name="AWS CLI",
                status="PASS",
                version=match.group(1),
                message=f"AWS CLI {match.group(1)}",
            )
    except (subprocess.SubprocessError, OSError):
        pass

    return CheckResult(
        name="AWS CLI",
        status="PASS",
        message="Found",
    )


def _check_workflow(workflow_path: Path) -> CheckResult:
    """Check workflow.yaml exists and is valid."""
    if not workflow_path.exists():
        return CheckResult(
            name="workflow.yaml",
            status="FAIL",
            message="Not found",
            fix_hint=f"Create one with: rsf init <project> or create {workflow_path}",
        )

    try:
        from rsf.dsl.parser import load_definition

        load_definition(workflow_path)
        return CheckResult(
            name="workflow.yaml",
            status="PASS",
            message="Valid workflow definition",
        )
    except Exception as exc:
        return CheckResult(
            name="workflow.yaml",
            status="WARN",
            message=f"Exists but invalid: {exc}",
            fix_hint="Fix validation errors and try again",
        )


def _check_directory(name: str, path: Path) -> CheckResult:
    """Check a project directory exists."""
    if path.exists() and path.is_dir():
        return CheckResult(
            name=name,
            status="PASS",
            message=f"{path} exists",
        )
    return CheckResult(
        name=name,
        status="WARN",
        message=f"{path} not found",
        fix_hint=f"Run rsf generate to create {name}",
    )


def run_all_checks(
    workflow_path: Path | None = None,
    tf_dir: Path | None = None,
    handlers_dir: Path | None = None,
) -> list[CheckResult]:
    """Run all doctor checks and return results.

    Environment checks always run. Project checks run when
    workflow_path is provided and the file or parent dir exists.
    """
    results: list[CheckResult] = []

    # Environment checks (always)
    results.append(_check_python())
    results.append(_check_terraform())
    results.append(_check_aws_credentials())
    results.append(_check_boto3())
    results.append(_check_aws_cli())

    # Project checks (when in a project directory)
    if workflow_path and (workflow_path.exists() or workflow_path.parent.exists()):
        results.append(_check_workflow(workflow_path))
        if tf_dir:
            results.append(_check_directory("terraform/", tf_dir))
        if handlers_dir:
            results.append(_check_directory("handlers/", handlers_dir))

    return results


ENV_CHECK_NAMES = {"Python", "Terraform", "AWS Credentials", "boto3 SDK", "AWS CLI"}

STATUS_SYMBOLS = {
    "PASS": "[green]✓[/green]",
    "WARN": "[yellow]⚠[/yellow]",
    "FAIL": "[red]✗[/red]",
}

STATUS_SYMBOLS_PLAIN = {
    "PASS": "PASS",
    "WARN": "WARN",
    "FAIL": "FAIL",
}


def _render_results(
    results: list[CheckResult],
    *,
    no_color: bool = False,
) -> None:
    """Render check results as a Rich checklist."""
    env_checks = [r for r in results if r.name in ENV_CHECK_NAMES]
    project_checks = [r for r in results if r.name not in ENV_CHECK_NAMES]

    symbols = STATUS_SYMBOLS_PLAIN if no_color else STATUS_SYMBOLS

    console.print("\n[bold]Environment[/bold]" if not no_color else "\nEnvironment")
    for check in env_checks:
        sym = symbols[check.status]
        version = f" ({check.version})" if check.version else ""
        line = f"  {sym} {check.name}{version}"
        if check.status != "PASS":
            line += f" — {check.message}"
        console.print(line, highlight=False)
        if check.fix_hint and check.status in ("FAIL", "WARN"):
            console.print(
                f"    [dim]Fix: {check.fix_hint}[/dim]"
                if not no_color
                else f"    Fix: {check.fix_hint}",
                highlight=False,
            )

    if project_checks:
        console.print(
            "\n[bold]Project[/bold]" if not no_color else "\nProject"
        )
        for check in project_checks:
            sym = symbols[check.status]
            line = f"  {sym} {check.name}"
            if check.status != "PASS":
                line += f" — {check.message}"
            console.print(line, highlight=False)
            if check.fix_hint and check.status in ("FAIL", "WARN"):
                console.print(
                    f"    [dim]Fix: {check.fix_hint}[/dim]"
                    if not no_color
                    else f"    Fix: {check.fix_hint}",
                    highlight=False,
                )

    # Summary
    pass_count = sum(1 for r in results if r.status == "PASS")
    warn_count = sum(1 for r in results if r.status == "WARN")
    fail_count = sum(1 for r in results if r.status == "FAIL")
    total = len(results)

    console.print()
    if fail_count:
        console.print(
            f"[red bold]{fail_count} issue(s) found[/red bold] "
            f"({pass_count}/{total} passed, {warn_count} warning(s))"
            if not no_color
            else f"{fail_count} issue(s) found ({pass_count}/{total} passed, {warn_count} warning(s))"
        )
    elif warn_count:
        console.print(
            f"[yellow]All checks passed with {warn_count} warning(s)[/yellow]"
            if not no_color
            else f"All checks passed with {warn_count} warning(s)"
        )
    else:
        console.print(
            "[green bold]All checks passed[/green bold]"
            if not no_color
            else "All checks passed"
        )


def doctor(
    workflow: Path = typer.Argument(
        "workflow.yaml", exists=False, help="Path to workflow YAML file"
    ),
    tf_dir: Path = typer.Option(
        "terraform", "--tf-dir", help="Terraform directory to check"
    ),
    output_json: bool = typer.Option(
        False, "--json", help="Output JSON report"
    ),
    no_color: bool = typer.Option(
        False, "--no-color", help="Disable colored output"
    ),
) -> None:
    """Diagnose environment and project health.

    Checks Python version, Terraform binary, AWS credentials, and SDK availability.
    When run inside a project directory, also validates workflow.yaml and directory structure.
    """
    handlers_dir = workflow.parent / "handlers" if workflow else None

    results = run_all_checks(
        workflow_path=workflow,
        tf_dir=tf_dir,
        handlers_dir=handlers_dir,
    )

    if output_json:
        report = {
            "checks": [
                {
                    "name": r.name,
                    "status": r.status,
                    "version": r.version,
                    "message": r.message,
                    "fix_hint": r.fix_hint,
                }
                for r in results
            ],
            "summary": {
                "total": len(results),
                "pass": sum(1 for r in results if r.status == "PASS"),
                "warn": sum(1 for r in results if r.status == "WARN"),
                "fail": sum(1 for r in results if r.status == "FAIL"),
            },
        }
        typer.echo(json.dumps(report, indent=2))
    else:
        _render_results(results, no_color=no_color)

    # Exit code: 1 if any FAIL, 0 otherwise
    has_failures = any(r.status == "FAIL" for r in results)
    raise typer.Exit(code=1 if has_failures else 0)
