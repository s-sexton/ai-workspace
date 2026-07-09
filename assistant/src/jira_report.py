"""Markdown report generation for normalized Jira issues."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Iterable

from common.jira import JiraIssue


UNKNOWN_VALUE = "Unassigned"


def generate_jira_report(
    issues: Iterable[JiraIssue],
    generated_at: datetime,
    *,
    timezone_name: str = "America/Chicago",
) -> str:
    """Generate a Markdown report for normalized Jira issues."""

    issue_list = list(issues)
    lines = [
        "# Jira Report",
        "",
        f"Generated: {generated_at:%Y-%m-%d %H:%M} {timezone_name}",
        "",
        "## Summary",
        "",
        f"- Total issues: {len(issue_list)}",
    ]

    lines.extend(_counter_section("By status", (issue.status for issue in issue_list)))
    lines.extend(_counter_section("By priority", (issue.priority for issue in issue_list)))
    lines.extend(
        [
            "",
            "## Issues",
            "",
            "| Key | Summary | Status | Priority | Assignee | Updated |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )

    if not issue_list:
        lines.append("| _None_ | _No issues found_ |  |  |  |  |")
    else:
        for issue in issue_list:
            lines.append(_issue_row(issue))

    return "\n".join(lines) + "\n"


def _counter_section(title: str, values: Iterable[str | None]) -> list[str]:
    counter = Counter(value or UNKNOWN_VALUE for value in values)
    lines = ["", f"- {title}:"]

    if not counter:
        lines.append(f"  - {UNKNOWN_VALUE}: 0")
        return lines

    for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"  - {_escape_inline(value)}: {count}")

    return lines


def _issue_row(issue: JiraIssue) -> str:
    assignee = issue.assignee.display_name if issue.assignee else None
    cells = (
        issue.key,
        issue.summary,
        issue.status,
        issue.priority,
        assignee,
        issue.updated,
    )
    return "| " + " | ".join(_escape_table_cell(value) for value in cells) + " |"


def _escape_table_cell(value: str | None) -> str:
    if value is None or value == "":
        return ""
    return _escape_inline(value).replace("\n", "<br>")


def _escape_inline(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|")
