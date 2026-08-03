from __future__ import annotations

from common.jira import JiraIssue, JiraUser
from assistant.src.send_jira_teams_summary import (
    _project_jql,
    render_jira_teams_summary,
)


def test_render_jira_teams_summary_uses_markdown_ticket_links():
    issue = JiraIssue(
        key="COMP-78",
        summary="Complete August business tasks",
        status="In Progress",
        assignee=JiraUser(display_name="Scott Sexton"),
    )

    text = render_jira_teams_summary(
        [issue],
        site_url="https://example.atlassian.net/",
        title="COMP Jira Tickets",
        mention="Scott Sexton",
    )

    assert "Scott Sexton" in text
    assert "**COMP Jira Tickets**" in text
    assert (
        "[COMP-78](https://example.atlassian.net/browse/COMP-78) - **In Progress** - "
        "Complete August business tasks"
    ) in text
    assert "Assignee:" not in text


def test_project_jql_excludes_done_by_default():
    assert (
        _project_jql("comp", include_done=False)
        == "project = COMP AND statusCategory != Done ORDER BY updated DESC"
    )


def test_project_jql_can_include_done():
    assert _project_jql("COMP", include_done=True) == (
        "project = COMP ORDER BY updated DESC"
    )
