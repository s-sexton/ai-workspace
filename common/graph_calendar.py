"""Microsoft Graph calendar transport boundary for AI Workspace."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Mapping
from urllib.parse import quote, urlencode

from common.calendar import (
    CalendarClientError,
    graph_event_to_calendar_payload,
)
from common.configuration import GraphCredentials
from common.graph_email import (
    GRAPH_BASE_URL,
    GraphClientCredentialsTokenProvider,
    GraphClientError,
    GraphTokenTransport,
    GraphTransport,
    UrllibGraphTokenTransport,
    UrllibGraphTransport,
)


def build_graph_calendar_read_transport(
    credentials: GraphCredentials,
    *,
    graph_transport: GraphTransport | None = None,
    token_transport: GraphTokenTransport | None = None,
    use_bearer_auth: bool = False,
) -> GraphCalendarReadTransport:
    """Build a Graph calendar read transport from local credentials."""

    if use_bearer_auth:
        access_token = _required_text(credentials.access_token, "access_token")
    else:
        provider = GraphClientCredentialsTokenProvider(
            credentials=credentials,
            transport=token_transport or UrllibGraphTokenTransport(),
        )
        access_token = provider.access_token()

    return GraphCalendarReadTransport(
        access_token=access_token,
        transport=graph_transport or UrllibGraphTransport(),
    )


@dataclass(frozen=True)
class GraphCalendarReadTransport:
    """Read calendar event metadata from Microsoft Graph."""

    access_token: str = field(repr=False)
    transport: GraphTransport = field(repr=False)
    base_url: str = GRAPH_BASE_URL

    def list_events(
        self,
        calendar: str,
        date: str,
        limit: int,
    ) -> tuple[Mapping[str, Any], ...]:
        """Return normalized calendar payloads for one user's calendar view."""

        clean_calendar = _required_text(calendar, "calendar")
        if limit < 1:
            raise CalendarClientError("limit must be positive.")

        payload = self._get_json(
            self._calendar_view_url(clean_calendar, date=date, limit=limit)
        )
        raw_events = payload.get("value")
        if not isinstance(raw_events, list):
            raise GraphClientError("Microsoft Graph calendar response missing value.")

        events = []
        for raw_event in raw_events:
            if not isinstance(raw_event, Mapping):
                raise GraphClientError(
                    "Microsoft Graph calendar response item must be an object."
                )
            events.append(
                graph_event_to_calendar_payload(raw_event, calendar=clean_calendar)
            )
        return tuple(events)

    def _get_json(self, url: str) -> Mapping[str, Any]:
        response = self.transport.get(url, headers=self._json_headers())
        if response.status_code != 200:
            raise GraphClientError(
                f"Microsoft Graph calendar read failed with status {response.status_code}"
            )
        return response.json()

    def _json_headers(self) -> dict[str, str]:
        token = _required_text(self.access_token, "access_token")
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Prefer": 'outlook.timezone="UTC"',
        }

    def _calendar_view_url(self, calendar: str, *, date: str, limit: int) -> str:
        encoded_calendar = quote(calendar, safe="")
        start, end = _date_window(date)
        query = urlencode(
            {
                "startDateTime": start,
                "endDateTime": end,
                "$top": str(limit),
                "$orderby": "start/dateTime",
                "$select": ",".join(
                    (
                        "id",
                        "subject",
                        "start",
                        "end",
                        "location",
                        "organizer",
                        "showAs",
                        "isCancelled",
                    )
                ),
            }
        )
        return (
            f"{self._base_url()}/users/{encoded_calendar}/calendarView?"
            f"{query}"
        )

    def _base_url(self) -> str:
        return self.base_url.rstrip("/")


def _date_window(value: str) -> tuple[str, str]:
    try:
        selected_date = date.fromisoformat(value)
    except ValueError as exc:
        raise CalendarClientError("date must use YYYY-MM-DD format.") from exc

    next_date = selected_date + timedelta(days=1)
    return (
        f"{selected_date.isoformat()}T00:00:00Z",
        f"{next_date.isoformat()}T00:00:00Z",
    )


def _required_text(value: str | None, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CalendarClientError(f"Microsoft Graph calendar value is required: {key}")
    return value.strip()
