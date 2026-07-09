"""Read-only Jira Cloud client boundary for AI Workspace."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from common.configuration import JiraCredentials, JiraSettings


JIRA_SEARCH_PATH = "/rest/api/3/search/jql"


class JiraClientError(RuntimeError):
    """Raised when Jira issue retrieval or normalization fails."""


class JiraTransport(Protocol):
    """Minimal HTTP transport interface used by the Jira client."""

    def get(
        self,
        url: str,
        headers: Mapping[str, str],
    ) -> JiraResponse:
        """Send a GET request and return a response."""


class JiraResponse(Protocol):
    """Minimal HTTP response interface used by the Jira client."""

    status_code: int

    def json(self) -> Mapping[str, Any]:
        """Return the response body as JSON data."""


@dataclass(frozen=True)
class UrllibJiraResponse:
    """Jira response backed by a standard-library HTTP response."""

    status_code: int
    body: bytes = field(repr=False)

    def json(self) -> Mapping[str, Any]:
        """Decode the response body as JSON."""

        try:
            payload = json.loads(self.body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise JiraClientError("Jira response body was not valid JSON.") from exc

        if not isinstance(payload, Mapping):
            raise JiraClientError("Jira response body must be a JSON object.")

        return payload


@dataclass(frozen=True)
class UrllibJiraTransport:
    """Read-only Jira transport using Python's standard library."""

    timeout_seconds: float = 30.0

    def get(
        self,
        url: str,
        headers: Mapping[str, str],
    ) -> UrllibJiraResponse:
        """Send a read-only GET request to Jira Cloud."""

        request = Request(url, headers=dict(headers), method="GET")

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                status_code = int(response.status)
                body = response.read()
        except HTTPError as exc:
            return UrllibJiraResponse(status_code=int(exc.code), body=exc.read())
        except URLError as exc:
            raise JiraClientError("Jira issue search request failed.") from exc

        return UrllibJiraResponse(status_code=status_code, body=body)


@dataclass(frozen=True)
class JiraUser:
    """Normalized Jira user details used in reports."""

    display_name: str | None = None
    account_id: str | None = None


@dataclass(frozen=True)
class JiraIssue:
    """Normalized Jira issue details used by assistant reports."""

    key: str
    summary: str
    status: str | None = None
    priority: str | None = None
    assignee: JiraUser | None = None
    updated: str | None = None
    raw_fields: Mapping[str, Any] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class JiraIssueSearchResult:
    """Normalized Jira search result."""

    issues: tuple[JiraIssue, ...]
    next_page_token: str | None = None


@dataclass(frozen=True)
class JiraClient:
    """Small read-only Jira client for the first report milestone."""

    settings: JiraSettings
    credentials: JiraCredentials = field(repr=False)
    transport: JiraTransport = field(repr=False)
    jql: str | None = None
    use_cloud_route: bool = True
    use_bearer_auth: bool = False

    def fetch_report_issues(self) -> JiraIssueSearchResult:
        """Fetch and normalize the Jira issues needed for the first report."""

        response = self.transport.get(
            self._build_search_url(),
            headers=self._build_headers(),
        )
        if response.status_code != 200:
            raise JiraClientError(f"Jira issue search failed with status {response.status_code}")

        return normalize_search_result(response.json())

    def _build_search_url(self) -> str:
        query = {
            "jql": self.effective_jql,
            "maxResults": str(self.settings.max_results),
            "fields": ",".join(_jira_api_fields(self.settings.report_fields)),
        }
        return f"{self._base_url()}{JIRA_SEARCH_PATH}?{urlencode(query)}"

    @property
    def effective_jql(self) -> str:
        """Return the custom JQL override or the configured report JQL."""

        if self.jql is not None and self.jql.strip():
            return self.jql.strip()
        return build_report_jql(self.settings)

    def _build_headers(self) -> dict[str, str]:
        if self.use_bearer_auth:
            if not self.credentials.access_token:
                raise JiraClientError("Jira access token is required for Bearer auth.")
            return {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.credentials.access_token}",
            }

        if not self.credentials.email or not self.credentials.api_token:
            raise JiraClientError("Jira email and API token are required for Basic auth.")
        token = f"{self.credentials.email}:{self.credentials.api_token}".encode("utf-8")
        return {
            "Accept": "application/json",
            "Authorization": "Basic "
            + base64.b64encode(token).decode("ascii"),
        }

    def _base_url(self) -> str:
        if self.use_cloud_route:
            return f"https://api.atlassian.com/ex/jira/{_normalized_cloud_id(self.credentials.cloud_id)}"
        return _normalized_site_url(self.credentials.site_url)


def build_report_jql(settings: JiraSettings) -> str:
    """Build the configured read-only report JQL."""

    projects = ", ".join(settings.projects)
    return f"project in ({projects}) ORDER BY {settings.sort_order}"


def _normalized_site_url(site_url: str | None) -> str:
    if site_url is None or not site_url.strip():
        raise JiraClientError("Jira site URL is required.")

    stripped = site_url.strip().rstrip("/")
    if not stripped.startswith("https://"):
        raise JiraClientError("Jira site URL must start with https://.")

    return stripped


def _normalized_cloud_id(cloud_id: str | None) -> str:
    if cloud_id is None or not cloud_id.strip():
        raise JiraClientError("Jira cloud ID is required.")

    return cloud_id.strip().strip("/")


def _jira_api_fields(report_fields: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(field_name for field_name in report_fields if field_name != "key")


def normalize_search_result(payload: Mapping[str, Any]) -> JiraIssueSearchResult:
    """Normalize a Jira issue search response."""

    raw_issues = payload.get("issues")
    if not isinstance(raw_issues, list):
        raise JiraClientError("Jira search response missing issues list.")

    return JiraIssueSearchResult(
        issues=tuple(_normalize_issue(issue) for issue in raw_issues),
        next_page_token=_optional_string(payload.get("nextPageToken")),
    )


def _normalize_issue(payload: Any) -> JiraIssue:
    if not isinstance(payload, Mapping):
        raise JiraClientError("Jira issue must be an object.")

    key = payload.get("key")
    fields = payload.get("fields")
    if not isinstance(key, str) or not key.strip():
        raise JiraClientError("Jira issue missing key.")
    if not isinstance(fields, Mapping):
        raise JiraClientError(f"Jira issue missing fields: {key}")

    summary = fields.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise JiraClientError(f"Jira issue missing summary: {key}")

    return JiraIssue(
        key=key,
        summary=summary,
        status=_nested_name(fields.get("status")),
        priority=_nested_name(fields.get("priority")),
        assignee=_normalize_user(fields.get("assignee")),
        updated=_optional_string(fields.get("updated")),
        raw_fields=dict(fields),
    )


def _normalize_user(value: Any) -> JiraUser | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise JiraClientError("Jira assignee must be an object when present.")

    display_name = _optional_string(value.get("displayName"))
    account_id = _optional_string(value.get("accountId"))
    if display_name is None and account_id is None:
        return None

    return JiraUser(display_name=display_name, account_id=account_id)


def _nested_name(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise JiraClientError("Jira named field must be an object when present.")
    return _optional_string(value.get("name"))


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise JiraClientError("Jira field value must be a string when present.")
