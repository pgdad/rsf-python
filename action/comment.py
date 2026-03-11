"""Post RSF workflow plan summary as a GitHub PR comment.

Uses only Python stdlib (urllib, json, os) — no external dependencies required.
Updates an existing RSF comment in-place to prevent comment spam on multiple pushes.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

# ─── Configuration ───────────────────────────────────────────────────────────

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
PR_NUMBER = os.environ.get("PR_NUMBER", "")

VALIDATE_OUTPUT = os.environ.get("VALIDATE_OUTPUT", "")
GENERATE_OUTPUT = os.environ.get("GENERATE_OUTPUT", "")
DEPLOY_OUTPUT = os.environ.get("DEPLOY_OUTPUT", "")
VALIDATE_RESULT = os.environ.get("VALIDATE_RESULT", "skipped")
GENERATE_RESULT = os.environ.get("GENERATE_RESULT", "skipped")
DEPLOY_RESULT = os.environ.get("DEPLOY_RESULT", "skipped")
DEPLOY_ENABLED = os.environ.get("DEPLOY_ENABLED", "false")

COMMENT_MARKER = "<!-- rsf-action-comment -->"

# ─── Status Formatting ──────────────────────────────────────────────────────

STATUS_ICONS = {
    "pass": ":white_check_mark: Pass",
    "fail": ":x: Fail",
    "skipped": ":fast_forward: Skipped",
}


def _status(result: str) -> str:
    """Map result string to emoji + label."""
    return STATUS_ICONS.get(result, f":grey_question: {result}")


# ─── Build Comment Body ─────────────────────────────────────────────────────


def build_comment_body() -> str:
    """Build the markdown body for the PR comment."""
    lines: list[str] = [COMMENT_MARKER]
    lines.append("## RSF Workflow Plan")
    lines.append("")

    # Summary table
    lines.append("| Step | Status |")
    lines.append("|------|--------|")
    lines.append(f"| Validate | {_status(VALIDATE_RESULT)} |")
    lines.append(f"| Generate | {_status(GENERATE_RESULT)} |")

    if DEPLOY_ENABLED == "true":
        lines.append(f"| Deploy | {_status(DEPLOY_RESULT)} |")
    else:
        lines.append("| Deploy | :fast_forward: Skipped (not enabled) |")

    lines.append("")

    # Validation details
    if VALIDATE_RESULT == "fail":
        # Show validation errors expanded (not collapsed) for visibility
        lines.append("### Validation Errors")
        lines.append("")
        lines.append("```")
        lines.append(VALIDATE_OUTPUT or "(no output)")
        lines.append("```")
        lines.append("")
    elif VALIDATE_OUTPUT:
        lines.append("<details>")
        lines.append("<summary>Validation Output</summary>")
        lines.append("")
        lines.append("```")
        lines.append(VALIDATE_OUTPUT)
        lines.append("```")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    # Generation details
    if GENERATE_OUTPUT and GENERATE_RESULT != "skipped":
        lines.append("<details>")
        lines.append("<summary>Generated Changes</summary>")
        lines.append("")
        lines.append("```")
        lines.append(GENERATE_OUTPUT)
        lines.append("```")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    # Deploy details
    if DEPLOY_OUTPUT and DEPLOY_RESULT != "skipped":
        lines.append("<details>")
        lines.append("<summary>Deploy Output</summary>")
        lines.append("")
        lines.append("```")
        lines.append(DEPLOY_OUTPUT)
        lines.append("```")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.append("---")
    lines.append(f"*Posted by [RSF Action](https://github.com/{GITHUB_REPOSITORY})*")

    return "\n".join(lines)


# ─── GitHub API ──────────────────────────────────────────────────────────────


def _github_api(
    method: str,
    url: str,
    data: dict | None = None,
) -> dict | list | None:
    """Make a GitHub API request. Returns parsed JSON or None."""
    encoded_data = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=encoded_data, method=method)
    req.add_header("Authorization", f"token {GITHUB_TOKEN}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/vnd.github.v3+json")

    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status == 204:
                return None
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        print(f"GitHub API error: {exc.code} {exc.reason}", file=sys.stderr)
        body = exc.read().decode() if exc.fp else ""
        print(f"  Response: {body[:500]}", file=sys.stderr)
        return None


def find_existing_comment() -> int | None:
    """Find an existing RSF Action comment on the PR. Returns comment ID or None."""
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/issues/{PR_NUMBER}/comments?per_page=100"
    comments = _github_api("GET", url)
    if not isinstance(comments, list):
        return None

    for comment in comments:
        body = comment.get("body", "")
        if COMMENT_MARKER in body:
            return comment["id"]
    return None


def post_or_update_comment(body: str) -> None:
    """Post a new comment or update an existing RSF Action comment."""
    existing_id = find_existing_comment()

    if existing_id:
        # Update existing comment
        url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/issues/comments/{existing_id}"
        result = _github_api("PATCH", url, {"body": body})
        if result:
            print(f"Updated existing PR comment (ID: {existing_id})")
        else:
            print("Failed to update existing comment, creating new one")
            _create_new_comment(body)
    else:
        _create_new_comment(body)


def _create_new_comment(body: str) -> None:
    """Create a new PR comment."""
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/issues/{PR_NUMBER}/comments"
    result = _github_api("POST", url, {"body": body})
    if result:
        print(f"Posted new PR comment (ID: {result.get('id')})")
    else:
        print("Failed to post PR comment", file=sys.stderr)


# ─── Main ────────────────────────────────────────────────────────────────────


def main() -> None:
    """Build and post the RSF plan summary comment."""
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN not set, skipping PR comment", file=sys.stderr)
        return
    if not PR_NUMBER:
        print("PR_NUMBER not set, skipping PR comment", file=sys.stderr)
        return
    if not GITHUB_REPOSITORY:
        print("GITHUB_REPOSITORY not set, skipping PR comment", file=sys.stderr)
        return

    body = build_comment_body()
    post_or_update_comment(body)


if __name__ == "__main__":
    main()
