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


_NAMED_CALENDAR_SEPARATOR = "::"


def graph_calendar_reference(user: str, calendar_name: str | None = None) -> str:
    """Return an opaque Graph calendar reference for the transport."""

    clean_user = _required_text(user, "user")
    if calendar_name is None:
        return clean_user
    clean_name = _required_text(calendar_name, "calendar_name")
    return f"{clean_user}{_NAMED_CALENDAR_SEPARATOR}{clean_name}"


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
        user, calendar_name = _split_calendar_reference(clean_calendar)
        if limit < 1:
            raise CalendarClientError("limit must be positive.")

        calendar_id = (
            self._calendar_id_for_name(user, calendar_name)
            if calendar_name is not None
            else None
        )
        payload = self._get_json(
            self._calendar_view_url(
                user,
                calendar_id=calendar_id,
                date=date,
                limit=limit,
            )
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

    def _calendar_id_for_name(self, user: str, calendar_name: str) -> str:
        payload = self._get_json(self._calendars_url(user))
        raw_calendars = payload.get("value")
        if not isinstance(raw_calendars, list):
            raise GraphClientError("Microsoft Graph calendars response missing value.")
        clean_name = calendar_name.casefold()
        for raw_calendar in raw_calendars:
            if not isinstance(raw_calendar, Mapping):
                raise GraphClientError(
                    "Microsoft Graph calendar response item must be an object."
                )
            name = raw_calendar.get("name")
            calendar_id = raw_calendar.get("id")
            if (
                isinstance(name, str)
                and name.casefold() == clean_name
                and isinstance(calendar_id, str)
                and calendar_id.strip()
            ):
                return calendar_id
        raise GraphClientError(f"Microsoft Graph calendar was not found: {calendar_name}")

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

    def _calendars_url(self, user: str) -> str:
        encoded_user = quote(user, safe="")
        query = urlencode(
            {
                "$top": "100",
                "$select": "id,name",
            }
        )
        return f"{self._base_url()}/users/{encoded_user}/calendars?{query}"

    def _calendar_view_url(
        self,
        user: str,
        *,
        calendar_id: str | None = None,
        date: str,
        limit: int,
    ) -> str:
        encoded_user = quote(user, safe="")
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
        calendar_segment = (
            "calendarView"
            if calendar_id is None
            else f"calendars/{quote(calendar_id, safe='')}/calendarView"
        )
        return (
            f"{self._base_url()}/users/{encoded_user}/{calendar_segment}?"
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


def _split_calendar_reference(calendar: str) -> tuple[str, str | None]:
    if _NAMED_CALENDAR_SEPARATOR not in calendar:
        return calendar, None
    user, calendar_name = calendar.split(_NAMED_CALENDAR_SEPARATOR, maxsplit=1)
    return (
        _required_text(user, "calendar user"),
        _required_text(calendar_name, "calendar name"),
    )


def _required_text(value: str | None, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CalendarClientError(f"Microsoft Graph calendar value is required: {key}")
    return value.strip()
