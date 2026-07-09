"""Local runner for the first Jira Markdown report."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from assistant.src.jira_report import generate_jira_report
from common.configuration import JiraCredentials, load_workspace_config
from common.jira import JiraClient, JiraResponse


DEFAULT_REPORT_PATH = Path("reports") / "jira-report.md"


SAMPLE_JIRA_RESPONSE: Mapping[str, Any] = {
    "issues": [
        {
            "key": "STF-1",
            "fields": {
                "summary": "Build the first Jira report",
                "status": {"name": "In Progress"},
                "priority": {"name": "High"},
                "assignee": {
                    "displayName": "AI Workspace",
                    "accountId": "local-sample",
                },
                "updated": "2026-07-05T09:30:00.000-0500",
            },
        },
        {
            "key": "SUPP-2",
            "fields": {
                "summary": "Review support queue trends",
                "status": {"name": "To Do"},
                "priority": {"name": "Medium"},
                "assignee": None,
                "updated": "2026-07-05T10:00:00.000-0500",
            },
        },
    ]
}


@dataclass(frozen=True)
class StaticJiraResponse:
    """Static response used by the local report runner."""

    status_code: int
    payload: Mapping[str, Any]

    def json(self) -> Mapping[str, Any]:
        """Return the static JSON payload."""

        return self.payload


@dataclass
class StaticJiraTransport:
    """Fake Jira transport used to prove the local report workflow."""

    payload: Mapping[str, Any] = field(default_factory=lambda: SAMPLE_JIRA_RESPONSE)

    def get(
        self,
        url: str,
        headers: Mapping[str, str],
    ) -> JiraResponse:
        """Return a static Jira search response without using the network."""

        return StaticJiraResponse(status_code=200, payload=self.payload)


def generate_local_jira_report(
    *,
    root: Path | str | None = None,
    output_path: Path | str | None = None,
    generated_at: datetime | None = None,
    timezone_name: str = "America/Chicago",
    transport: StaticJiraTransport | None = None,
) -> Path:
    """Generate the local fake Jira report and return the output path."""

    config = load_workspace_config(root, include_process_env=False)
    workspace_root = config.root
    report_path = _resolve_output_path(
        workspace_root,
        Path(output_path) if output_path is not None else DEFAULT_REPORT_PATH,
    )

    client = JiraClient(
        settings=config.jira_settings,
        credentials=JiraCredentials(
            cloud_id="local-example",
            email="local@example.invalid",
            api_token="local-token",
        ),
        transport=transport or StaticJiraTransport(),
    )
    search_result = client.fetch_report_issues()
    markdown = generate_jira_report(
        search_result.issues,
        generated_at or datetime.now(),
        timezone_name=timezone_name,
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown, encoding="utf-8")
    return report_path


def main() -> None:
    """Generate the local Jira report from the current workspace."""

    report_path = generate_local_jira_report()
    print(f"Wrote {report_path}")


def _resolve_output_path(workspace_root: Path, output_path: Path) -> Path:
    if output_path.is_absolute():
        return output_path
    return workspace_root / output_path


if __name__ == "__main__":
    main()
