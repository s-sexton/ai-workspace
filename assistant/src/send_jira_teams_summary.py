"""Send a lightweight Jira ticket summary to Microsoft Teams."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import load_workspace_config
from common.jira import JiraClient, JiraIssue, UrllibJiraTransport
from common.teams import TeamsWebhookTransport, post_lightweight_card_to_teams


@dataclass(frozen=True)
class JiraTeamsSummaryResult:
    """Safe Jira-to-Teams summary details."""

    issue_count: int
    jql: str
    response_status: int | None


def send_jira_teams_summary(
    *,
    project: str,
    root: Path | str | None = None,
    jql: str | None = None,
    include_done: bool = False,
    execute: bool = False,
    mention: str | None = "Scott Sexton",
    transport: TeamsWebhookTransport | None = None,
) -> JiraTeamsSummaryResult:
    """Fetch Jira issues and optionally send a lightweight Teams summary."""

    config = load_workspace_config(root, include_process_env=True)
    credentials = config.require_jira_credentials(use_cloud_route=True)
    effective_jql = jql or _project_jql(project, include_done=include_done)
    client = JiraClient(
        settings=config.jira_settings,
        credentials=credentials,
        transport=UrllibJiraTransport(),
        jql=effective_jql,
        use_cloud_route=True,
    )
    issues = client.fetch_report_issues().issues
    text = render_jira_teams_summary(
        issues,
        site_url=credentials.site_url,
        title=f"{project.upper()} Jira Tickets",
        mention=mention,
    )
    response_status = None
    if execute:
        webhook_url = config.env.get("TEAMS_CLARITY_WEBHOOK_URL", "")
        response = post_lightweight_card_to_teams(
            webhook_url=webhook_url,
            text=text,
            transport=transport,
        )
        response_status = response.status_code
    return JiraTeamsSummaryResult(
        issue_count=len(issues),
        jql=effective_jql,
        response_status=response_status,
    )


def render_jira_teams_summary(
    issues: Sequence[JiraIssue],
    *,
    site_url: str | None,
    title: str,
    mention: str | None = None,
) -> str:
    """Render a compact Teams text summary with linked Jira issue keys."""

    clean_site_url = _clean_site_url(site_url)
    lines: list[str] = []
    if mention:
        lines.append(mention.strip())
        lines.append("")
    lines.append(f"**{title}**")
    lines.append("")
    if not issues:
        lines.append("No tickets found.")
        return "\n".join(lines)

    for issue in issues:
        status = issue.status or "Unassigned"
        link = f"{clean_site_url}/browse/{issue.key}"
        lines.append(f"- [{issue.key}]({link}) - **{status}** - {issue.summary}")
    return "\n".join(lines)


def _project_jql(project: str, *, include_done: bool) -> str:
    clean_project = project.strip().upper()
    if not clean_project:
        raise ValueError("Project key is required.")
    done_filter = "" if include_done else " AND statusCategory != Done"
    return f"project = {clean_project}{done_filter} ORDER BY updated DESC"


def _clean_site_url(site_url: str | None) -> str:
    if site_url is None or not site_url.strip():
        raise ValueError("JIRA_SITE_URL is required for Jira ticket links.")
    return site_url.strip().rstrip("/")


def main(argv: Sequence[str] | None = None) -> None:
    """Send a lightweight Jira ticket summary to Microsoft Teams."""

    args = _parse_args(argv)
    result = send_jira_teams_summary(
        project=args.project,
        jql=args.jql,
        include_done=args.include_done,
        execute=args.execute,
        mention=args.mention,
    )
    print(f"JQL: {result.jql}")
    print(f"Tickets: {result.issue_count}")
    if result.response_status is None:
        print("Teams send: dry-run")
    else:
        print(f"Teams send: HTTP {result.response_status}")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a lightweight Jira ticket summary to Teams."
    )
    parser.add_argument("--project", default="COMP", help="Jira project key.")
    parser.add_argument("--jql", help="Override the generated project JQL.")
    parser.add_argument(
        "--include-done",
        action="store_true",
        help="Include tickets in a Done status category.",
    )
    parser.add_argument(
        "--mention",
        default="Scott Sexton",
        help="Plain mention/header text to include before the summary.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Post the summary to Teams. Omit for a dry-run.",
    )
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help=argparse.SUPPRESS,
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
