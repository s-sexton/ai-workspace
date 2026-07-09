from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

import pytest

from common.configuration import ConfigurationError
from assistant.src.run_jira_report import (
    StaticJiraResponse,
    StaticJiraTransport,
    generate_local_jira_report,
    main,
)


def test_generate_local_jira_report_writes_markdown_report(tmp_path):
    _write_config(tmp_path)
    output_path = tmp_path / "reports" / "jira-report.md"

    result = generate_local_jira_report(
        root=tmp_path,
        output_path=output_path,
        generated_at=datetime(2026, 7, 5, 9, 30),
    )

    assert result.report_path == output_path
    assert result.issue_count == 2
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

    result = generate_local_jira_report(
        root=tmp_path,
        output_path=output_path,
        generated_at=datetime(2026, 7, 5, 9, 30),
        transport=transport,
    )

    assert result.issue_count == 1
    report = output_path.read_text(encoding="utf-8")
    assert "- Total issues: 1" in report
    assert "| ACCT-9 | Check account status | Done | Low |  | 2026-07-05T11:00:00.000-0500 |" in report


def test_generate_local_jira_report_resolves_relative_output_under_workspace(tmp_path):
    _write_config(tmp_path)

    result = generate_local_jira_report(
        root=tmp_path,
        output_path="reports/local.md",
        generated_at=datetime(2026, 7, 5, 9, 30),
    )

    assert result.report_path == tmp_path / "reports" / "local.md"
    assert result.report_path.is_file()


def test_generate_local_jira_report_live_mode_uses_local_credentials(tmp_path):
    _write_config(tmp_path)
    _write_env(tmp_path)
    output_path = tmp_path / "reports" / "live.md"
    transport = RecordingTransport(
        payload={
            "issues": [
                {
                    "key": "STF-7",
                    "fields": {
                        "summary": "Live mode through fake transport",
                        "status": {"name": "In Progress"},
                        "priority": {"name": "High"},
                        "assignee": None,
                        "updated": "2026-07-09T08:00:00.000-0500",
                    },
                }
            ]
        }
    )

    result = generate_local_jira_report(
        root=tmp_path,
        output_path=output_path,
        generated_at=datetime(2026, 7, 9, 8, 30),
        transport=transport,
        use_live_jira=True,
    )

    assert result.issue_count == 1
    assert output_path.is_file()
    assert transport.calls
    url, headers = transport.calls[0]
    assert "api.atlassian.com/ex/jira/company-example" in url
    assert headers["Authorization"].startswith("Basic ")
    assert "secret-token" not in repr(transport.calls)
    assert "access-token" not in repr(result)
    assert result.auth_mode == "basic"


def test_generate_local_jira_report_applies_jql_override(tmp_path):
    _write_config(tmp_path)
    _write_env(tmp_path)
    transport = RecordingTransport(payload={"issues": []})

    result = generate_local_jira_report(
        root=tmp_path,
        output_path=tmp_path / "reports" / "override.md",
        generated_at=datetime(2026, 7, 9, 8, 30),
        transport=transport,
        use_live_jira=True,
        jql="project = STF ORDER BY updated DESC",
    )

    url, _ = transport.calls[0]
    assert "project+%3D+STF+ORDER+BY+updated+DESC" in url
    assert result.jql == "project = STF ORDER BY updated DESC"


def test_generate_local_jira_report_live_mode_requires_credentials(tmp_path):
    _write_config(tmp_path)

    with pytest.raises(ConfigurationError):
        generate_local_jira_report(
            root=tmp_path,
            generated_at=datetime(2026, 7, 9, 8, 30),
            use_live_jira=True,
        )


def test_main_accepts_output_argument(tmp_path, monkeypatch):
    _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    main(["--output", "reports/from-main.md"])

    assert (tmp_path / "reports" / "from-main.md").is_file()


def test_main_can_print_safe_query_diagnostics(tmp_path, monkeypatch, capsys):
    _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    main(["--output", "reports/from-main.md", "--show-query"])

    output = capsys.readouterr().out
    assert "Jira query diagnostics" in output
    assert "JQL: project in (STF, SUPP, ACCT) ORDER BY updated DESC" in output
    assert "Returned issues: 2" in output
    assert "Authorization" not in output


class RecordingTransport:
    def __init__(self, payload: Mapping[str, Any]):
        self.payload = payload
        self.calls: list[tuple[str, Mapping[str, str]]] = []

    def get(
        self,
        url: str,
        headers: Mapping[str, str],
    ) -> StaticJiraResponse:
        self.calls.append((url, headers))
        return StaticJiraResponse(status_code=200, payload=self.payload)


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


def _write_env(root):
    (root / "config" / ".env").write_text(
        "JIRA_CLOUD_ID=company-example\n"
        "JIRA_SITE_URL=https://company-example.atlassian.net\n"
        "JIRA_EMAIL=user@example.com\n"
        "JIRA_API_TOKEN=secret-token\n"
        "JIRA_ACCESS_TOKEN=access-token\n",
        encoding="utf-8",
    )
