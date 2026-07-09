from __future__ import annotations

from datetime import datetime

from assistant.src.run_jira_report import (
    StaticJiraTransport,
    generate_local_jira_report,
)


def test_generate_local_jira_report_writes_markdown_report(tmp_path):
    _write_config(tmp_path)
    output_path = tmp_path / "reports" / "jira-report.md"

    result_path = generate_local_jira_report(
        root=tmp_path,
        output_path=output_path,
        generated_at=datetime(2026, 7, 5, 9, 30),
    )

    assert result_path == output_path
    report = output_path.read_text(encoding="utf-8")
    assert "# Jira Report" in report
    assert "Generated: 2026-07-05 09:30 America/Chicago" in report
    assert "- Total issues: 2" in report
    assert "| STF-1 | Build the first Jira report | In Progress | High | AI Workspace | 2026-07-05T09:30:00.000-0500 |" in report


def test_generate_local_jira_report_accepts_custom_static_transport(tmp_path):
    _write_config(tmp_path)
    output_path = tmp_path / "custom-report.md"
    transport = StaticJiraTransport(
        payload={
            "issues": [
                {
                    "key": "ACCT-9",
                    "fields": {
                        "summary": "Check account status",
                        "status": {"name": "Done"},
                        "priority": {"name": "Low"},
                        "assignee": None,
                        "updated": "2026-07-05T11:00:00.000-0500",
                    },
                }
            ]
        }
    )

    generate_local_jira_report(
        root=tmp_path,
        output_path=output_path,
        generated_at=datetime(2026, 7, 5, 9, 30),
        transport=transport,
    )

    report = output_path.read_text(encoding="utf-8")
    assert "- Total issues: 1" in report
    assert "| ACCT-9 | Check account status | Done | Low |  | 2026-07-05T11:00:00.000-0500 |" in report


def test_generate_local_jira_report_resolves_relative_output_under_workspace(tmp_path):
    _write_config(tmp_path)

    result_path = generate_local_jira_report(
        root=tmp_path,
        output_path="reports/local.md",
        generated_at=datetime(2026, 7, 5, 9, 30),
    )

    assert result_path == tmp_path / "reports" / "local.md"
    assert result_path.is_file()


def _write_config(root):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "jira": {
              "projects": ["STF", "SUPP", "ACCT"],
              "maxResults": 10,
              "sortOrder": "updated DESC",
              "reportFields": [
                "key",
                "summary",
                "status",
                "priority",
                "assignee",
                "updated"
              ]
            }
          }
        }
        """,
        encoding="utf-8",
    )
