from __future__ import annotations

from datetime import datetime

from assistant.src.jira_report import generate_jira_report
from common.jira import JiraIssue, JiraUser


def test_generate_jira_report_handles_empty_issue_list():
    report = generate_jira_report(
        [],
        datetime(2026, 7, 5, 9, 30),
    )

    assert "# Jira Report" in report
    assert "Generated: 2026-07-05 09:30 America/Chicago" in report
    assert "- Total issues: 0" in report
    assert "| _None_ | _No issues found_ |  |  |  |  |" in report


def test_generate_jira_report_includes_issue_table():
    issue = JiraIssue(
        key="STF-1",
        summary="Build the first report",
        status="In Progress",
        priority="High",
        assignee=JiraUser(display_name="Ada Lovelace", account_id="abc123"),
        updated="2026-07-02T12:34:56.000-0500",
    )

    report = generate_jira_report(
        [issue],
        datetime(2026, 7, 5, 9, 30),
    )

    assert (
        "| STF-1 | Build the first report | In Progress | High | "
        "Ada Lovelace | 2026-07-02T12:34:56.000-0500 |"
    ) in report


def test_generate_jira_report_counts_status_and_priority():
    issues = [
        JiraIssue(key="STF-1", summary="One", status="In Progress", priority="High"),
        JiraIssue(key="STF-2", summary="Two", status="In Progress", priority="Medium"),
        JiraIssue(key="STF-3", summary="Three", status="To Do", priority="Medium"),
    ]

    report = generate_jira_report(
        issues,
        datetime(2026, 7, 5, 9, 30),
    )

    assert "- By status:\n  - In Progress: 2\n  - To Do: 1" in report
    assert "- By priority:\n  - Medium: 2\n  - High: 1" in report


def test_generate_jira_report_handles_missing_optional_values():
    issue = JiraIssue(
        key="STF-1",
        summary="Needs triage",
    )

    report = generate_jira_report(
        [issue],
        datetime(2026, 7, 5, 9, 30),
    )

    assert "- By status:\n  - Unassigned: 1" in report
    assert "- By priority:\n  - Unassigned: 1" in report
    assert "| STF-1 | Needs triage |  |  |  |  |" in report


def test_generate_jira_report_escapes_markdown_table_values():
    issue = JiraIssue(
        key="STF-1",
        summary="Fix pipe | and newline\ninside summary",
        status="Ready | Blocked",
        priority="High",
    )

    report = generate_jira_report(
        [issue],
        datetime(2026, 7, 5, 9, 30),
    )

    assert "Fix pipe \\| and newline<br>inside summary" in report
    assert "Ready \\| Blocked" in report


def test_generate_jira_report_accepts_timezone_label():
    report = generate_jira_report(
        [],
        datetime(2026, 7, 5, 9, 30),
        timezone_name="UTC",
    )

    assert "Generated: 2026-07-05 09:30 UTC" in report
