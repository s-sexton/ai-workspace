"""Local runner for the first Jira Markdown report."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from assistant.src.jira_report import generate_jira_report
from common.configuration import JiraCredentials, load_workspace_config
from common.jira import JiraClient, JiraResponse, JiraTransport, UrllibJiraTransport


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


@dataclass(frozen=True)
class JiraReportRunResult:
    """Details from a Jira report run that are safe to display."""

    report_path: Path
    issue_count: int
    jql: str
    base_url: str
    max_results: int
    fields: tuple[str, ...]
    auth_mode: str


def generate_local_jira_report(
    *,
    root: Path | str | None = None,
    output_path: Path | str | None = None,
    generated_at: datetime | None = None,
    timezone_name: str = "America/Chicago",
    transport: JiraTransport | None = None,
    use_live_jira: bool = False,
    jql: str | None = None,
    use_bearer_auth: bool = False,
) -> JiraReportRunResult:
    """Generate a Jira report file and return safe run details."""

    config = load_workspace_config(root, include_process_env=use_live_jira)
    workspace_root = config.root
    report_path = _resolve_output_path(
        workspace_root,
        Path(output_path) if output_path is not None else DEFAULT_REPORT_PATH,
    )
    credentials = (
        config.require_jira_credentials(
            use_cloud_route=True,
            use_bearer_auth=use_bearer_auth,
        )
        if use_live_jira
        else JiraCredentials(
            cloud_id="local-example",
            site_url="https://local-example.atlassian.net",
            email="local@example.invalid",
            api_token="local-token",
            access_token="local-access-token",
        )
    )

    client = JiraClient(
        settings=config.jira_settings,
        credentials=credentials,
        transport=transport or _default_transport(use_live_jira),
        jql=jql,
        use_cloud_route=use_live_jira,
        use_bearer_auth=use_bearer_auth,
    )
    search_result = client.fetch_report_issues()
    markdown = generate_jira_report(
        search_result.issues,
        generated_at or datetime.now(),
        timezone_name=timezone_name,
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown, encoding="utf-8")
    return JiraReportRunResult(
        report_path=report_path,
        issue_count=len(search_result.issues),
        jql=client.effective_jql,
        base_url=client._base_url(),
        max_results=config.jira_settings.max_results,
        fields=config.jira_settings.report_fields,
        auth_mode="bearer" if use_bearer_auth else "basic",
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Generate the local Jira report from the current workspace."""

    args = _parse_args(argv)
    result = generate_local_jira_report(
        output_path=args.output,
        use_live_jira=args.live,
        jql=args.jql,
        use_bearer_auth=args.bearer,
    )
    if args.show_query:
        _print_safe_diagnostics(result)
    print(f"Wrote {result.report_path}")


def _resolve_output_path(workspace_root: Path, output_path: Path) -> Path:
    if output_path.is_absolute():
        return output_path
    return workspace_root / output_path


def _default_transport(use_live_jira: bool) -> JiraTransport:
    if use_live_jira:
        return UrllibJiraTransport()
    return StaticJiraTransport()


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the Clarity Assistant Jira Markdown report."
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Read from Jira Cloud using local credentials instead of sample data.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_REPORT_PATH),
        help="Report output path. Relative paths are resolved under the workspace root.",
    )
    parser.add_argument(
        "--jql",
        help="Override the configured Jira report JQL. Useful for live troubleshooting.",
    )
    parser.add_argument(
        "--show-query",
        action="store_true",
        help="Print safe query diagnostics without headers or credentials.",
    )
    parser.add_argument(
        "--bearer",
        action="store_true",
        help="Use JIRA_ACCESS_TOKEN Bearer auth instead of email/API-token Basic auth.",
    )
    return parser.parse_args(argv)


def _print_safe_diagnostics(result: JiraReportRunResult) -> None:
    print("Jira query diagnostics")
    print(f"Base URL: {result.base_url}")
    print(f"Auth mode: {result.auth_mode}")
    print(f"JQL: {result.jql}")
    print(f"Max results: {result.max_results}")
    print(f"Fields: {', '.join(result.fields)}")
    print(f"Returned issues: {result.issue_count}")


if __name__ == "__main__":
    main()

