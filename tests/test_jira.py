from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

import pytest

from common.configuration import JiraCredentials, JiraSettings
from common.jira import (
    JIRA_SEARCH_PATH,
    JiraClient,
    JiraClientError,
    UrllibJiraResponse,
    UrllibJiraTransport,
    build_report_jql,
    normalize_search_result,
)


@dataclass
class FakeResponse:
    status_code: int
    payload: Mapping[str, Any]

    def json(self) -> Mapping[str, Any]:
        return self.payload


class FakeTransport:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.calls: list[tuple[str, Mapping[str, str]]] = []

    def get(self, url: str, headers: Mapping[str, str]) -> FakeResponse:
        self.calls.append((url, headers))
        return self.response


def test_build_report_jql_uses_projects_and_sort_order():
    settings = _settings(projects=("STF", "SUPP"), sort_order="updated DESC")

    assert build_report_jql(settings) == "project in (STF, SUPP) ORDER BY updated DESC"


def test_fetch_report_issues_builds_read_only_search_request():
    transport = FakeTransport(FakeResponse(200, {"issues": []}))
    client = JiraClient(
        settings=_settings(),
        credentials=_credentials(),
        transport=transport,
    )

    result = client.fetch_report_issues()

    assert result.issues == ()
    assert len(transport.calls) == 1
    url, headers = transport.calls[0]
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "api.atlassian.com"
    assert parsed.path == f"/ex/jira/example-cloud-id{JIRA_SEARCH_PATH}"
    assert query["jql"] == ["project in (STF) ORDER BY updated DESC"]
    assert query["maxResults"] == ["10"]
    assert query["fields"] == ["summary,status,priority,assignee,updated"]
    assert headers["Accept"] == "application/json"
    expected = base64.b64encode(b"user@example.com:token").decode("ascii")
    assert headers["Authorization"] == f"Basic {expected}"


def test_fetch_report_issues_can_use_bearer_auth_with_cloud_route():
    transport = FakeTransport(FakeResponse(200, {"issues": []}))
    client = JiraClient(
        settings=_settings(),
        credentials=_credentials(),
        transport=transport,
        use_bearer_auth=True,
    )

    client.fetch_report_issues()

    _, headers = transport.calls[0]
    assert headers["Authorization"] == "Bearer access-token"


def test_fetch_report_issues_accepts_jql_override():
    transport = FakeTransport(FakeResponse(200, {"issues": []}))
    client = JiraClient(
        settings=_settings(),
        credentials=_credentials(),
        transport=transport,
        jql="project = ACCT ORDER BY updated DESC",
    )

    client.fetch_report_issues()

    url, _ = transport.calls[0]
    query = parse_qs(urlparse(url).query)
    assert query["jql"] == ["project = ACCT ORDER BY updated DESC"]
    assert client.effective_jql == "project = ACCT ORDER BY updated DESC"


def test_fetch_report_issues_can_use_basic_auth_without_exposing_token_in_repr():
    transport = FakeTransport(FakeResponse(200, {"issues": []}))
    credentials = _credentials(api_token="super-secret")
    client = JiraClient(
        settings=_settings(),
        credentials=credentials,
        transport=transport,
        use_cloud_route=False,
    )

    client.fetch_report_issues()

    _, headers = transport.calls[0]
    expected = base64.b64encode(b"user@example.com:super-secret").decode("ascii")
    assert headers["Authorization"] == f"Basic {expected}"
    assert "super-secret" not in repr(client)
    assert "super-secret" not in repr(credentials)


def test_fetch_report_issues_normalizes_jira_response():
    transport = FakeTransport(
        FakeResponse(
            200,
            {
                "nextPageToken": "next-token",
                "issues": [
                    {
                        "key": "STF-1",
                        "fields": {
                            "summary": "Build the first report",
                            "status": {"name": "In Progress"},
                            "priority": {"name": "High"},
                            "assignee": {
                                "displayName": "Ada Lovelace",
                                "accountId": "abc123",
                            },
                            "updated": "2026-07-02T12:34:56.000-0500",
                        },
                    }
                ],
            },
        )
    )
    client = JiraClient(
        settings=_settings(),
        credentials=_credentials(),
        transport=transport,
    )

    result = client.fetch_report_issues()

    issue = result.issues[0]
    assert result.next_page_token == "next-token"
    assert issue.key == "STF-1"
    assert issue.summary == "Build the first report"
    assert issue.status == "In Progress"
    assert issue.priority == "High"
    assert issue.assignee is not None
    assert issue.assignee.display_name == "Ada Lovelace"
    assert issue.assignee.account_id == "abc123"
    assert issue.updated == "2026-07-02T12:34:56.000-0500"


def test_fetch_report_issues_raises_for_non_success_status():
    transport = FakeTransport(FakeResponse(401, {"errorMessages": ["Unauthorized"]}))
    client = JiraClient(
        settings=_settings(),
        credentials=_credentials(api_token="super-secret"),
        transport=transport,
    )

    with pytest.raises(JiraClientError) as exc_info:
        client.fetch_report_issues()

    assert "401" in str(exc_info.value)
    assert "super-secret" not in str(exc_info.value)


def test_normalize_search_result_requires_issues_list():
    with pytest.raises(JiraClientError):
        normalize_search_result({})


def test_normalize_search_result_requires_issue_key_and_summary():
    with pytest.raises(JiraClientError):
        normalize_search_result({"issues": [{"fields": {"summary": "Missing key"}}]})

    with pytest.raises(JiraClientError):
        normalize_search_result({"issues": [{"key": "STF-1", "fields": {}}]})


def test_urllib_jira_transport_sends_get_request(monkeypatch):
    calls = []

    class FakeHttpResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b'{"issues": []}'

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return FakeHttpResponse()

    monkeypatch.setattr("common.jira.urlopen", fake_urlopen)

    response = UrllibJiraTransport(timeout_seconds=5).get(
        "https://example.atlassian.net/rest/api/3/search/jql",
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 200
    assert response.json() == {"issues": []}
    request, timeout = calls[0]
    assert request.get_method() == "GET"
    assert request.full_url == "https://example.atlassian.net/rest/api/3/search/jql"
    assert request.get_header("Accept") == "application/json"
    assert timeout == 5


def test_urllib_jira_transport_wraps_network_error(monkeypatch):
    def fake_urlopen(request, timeout):
        raise URLError("network down")

    monkeypatch.setattr("common.jira.urlopen", fake_urlopen)

    with pytest.raises(JiraClientError):
        UrllibJiraTransport().get(
            "https://example.atlassian.net/rest/api/3/search/jql",
            headers={},
        )


def test_urllib_jira_response_requires_json_object():
    with pytest.raises(JiraClientError):
        UrllibJiraResponse(status_code=200, body=b"[]").json()

    with pytest.raises(JiraClientError):
        UrllibJiraResponse(status_code=200, body=b"not-json").json()


def _settings(
    *,
    projects: tuple[str, ...] = ("STF",),
    sort_order: str = "updated DESC",
) -> JiraSettings:
    return JiraSettings(
        projects=projects,
        max_results=10,
        sort_order=sort_order,
        report_fields=("key", "summary", "status", "priority", "assignee", "updated"),
    )


def _credentials(api_token: str = "token") -> JiraCredentials:
    return JiraCredentials(
        cloud_id="example-cloud-id",
        site_url="https://example.atlassian.net",
        email="user@example.com",
        api_token=api_token,
        access_token="access-token",
    )
