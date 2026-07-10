"""Google Calendar transport boundary for AI Workspace."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from common.calendar import CalendarClientError, google_event_to_calendar_payload
from common.configuration import GoogleCredentials


GOOGLE_CALENDAR_BASE_URL = "https://www.googleapis.com/calendar/v3"


class GoogleCalendarClientError(RuntimeError):
    """Raised when Google Calendar operations fail."""


class GoogleCalendarTransport(Protocol):
    """Minimal HTTP transport interface used by Google Calendar adapters."""

    def get(self, url: str, headers: Mapping[str, str]) -> GoogleCalendarResponse:
        """Send a GET request and return a response."""


class GoogleTokenTransport(Protocol):
    """Minimal HTTP transport interface for Google token refresh."""

    def post_form(
        self,
        url: str,
        headers: Mapping[str, str],
        form: Mapping[str, str],
    ) -> GoogleCalendarResponse:
        """Send a form-encoded POST request and return a response."""


class GoogleCalendarResponse(Protocol):
    """Minimal Google response interface."""

    status_code: int

    def json(self) -> Mapping[str, Any]:
        """Return the response body as JSON data."""


@dataclass(frozen=True)
class UrllibGoogleCalendarResponse:
    """Google response backed by a standard-library HTTP response."""

    status_code: int
    body: bytes = field(repr=False)

    def json(self) -> Mapping[str, Any]:
        """Decode the response body as JSON."""

        if not self.body:
            return {}
        try:
            payload = json.loads(self.body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise GoogleCalendarClientError(
                "Google Calendar response body was not valid JSON."
            ) from exc

        if not isinstance(payload, Mapping):
            raise GoogleCalendarClientError(
                "Google Calendar response body must be a JSON object."
            )
        return payload


@dataclass(frozen=True)
class UrllibGoogleCalendarTransport:
    """Google Calendar transport using Python's standard library."""

    timeout_seconds: float = 30.0

    def get(
        self,
        url: str,
        headers: Mapping[str, str],
    ) -> UrllibGoogleCalendarResponse:
        """Send a GET request to Google Calendar."""

        request = Request(url, headers=dict(headers), method="GET")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                status_code = int(response.status)
                response_body = response.read()
        except HTTPError as exc:
            return UrllibGoogleCalendarResponse(
                status_code=int(exc.code),
                body=exc.read(),
            )
        except URLError as exc:
            raise GoogleCalendarClientError("Google Calendar request failed.") from exc

        return UrllibGoogleCalendarResponse(
            status_code=status_code,
            body=response_body,
        )


@dataclass(frozen=True)
class UrllibGoogleTokenTransport:
    """Google OAuth token transport using Python's standard library."""

    timeout_seconds: float = 30.0

    def post_form(
        self,
        url: str,
        headers: Mapping[str, str],
        form: Mapping[str, str],
    ) -> UrllibGoogleCalendarResponse:
        """Send a form-encoded POST request."""

        body = urlencode(form).encode("utf-8")
        request_headers = dict(headers)
        request_headers.setdefault(
            "Content-Type",
            "application/x-www-form-urlencoded",
        )
        request = Request(url, headers=request_headers, data=body, method="POST")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                status_code = int(response.status)
                response_body = response.read()
        except HTTPError as exc:
            return UrllibGoogleCalendarResponse(
                status_code=int(exc.code),
                body=exc.read(),
            )
        except URLError as exc:
            raise GoogleCalendarClientError("Google token request failed.") from exc

        return UrllibGoogleCalendarResponse(
            status_code=status_code,
            body=response_body,
        )


@dataclass(frozen=True)
class GoogleRefreshTokenProvider:
    """Acquire Google access tokens with a local refresh token."""

    credentials: GoogleCredentials = field(repr=False)
    transport: GoogleTokenTransport = field(repr=False)
    token_url: str = "https://oauth2.googleapis.com/token"

    def access_token(self) -> str:
        """Return a Google access token from a refresh token."""

        client_id = _required_text(self.credentials.client_id, "client_id")
        client_secret = _required_text(
            self.credentials.client_secret,
            "client_secret",
        )
        refresh_token = _required_text(
            self.credentials.refresh_token,
            "refresh_token",
        )
        response = self.transport.post_form(
            self.token_url,
            headers={"Accept": "application/json"},
            form={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if response.status_code != 200:
            raise GoogleCalendarClientError(
                f"Google token request failed with status {response.status_code}"
            )
        payload = response.json()
        token = payload.get("access_token")
        if not isinstance(token, str) or not token.strip():
            raise GoogleCalendarClientError(
                "Google token response missing access_token."
            )
        return token.strip()


def build_google_calendar_read_transport(
    credentials: GoogleCredentials,
    *,
    calendar_transport: GoogleCalendarTransport | None = None,
    token_transport: GoogleTokenTransport | None = None,
    use_bearer_auth: bool = False,
) -> GoogleCalendarReadTransport:
    """Build a Google Calendar read transport from local credentials."""

    if use_bearer_auth:
        access_token = _required_text(credentials.access_token, "access_token")
    else:
        provider = GoogleRefreshTokenProvider(
            credentials=credentials,
            transport=token_transport or UrllibGoogleTokenTransport(),
        )
        access_token = provider.access_token()

    return GoogleCalendarReadTransport(
        access_token=access_token,
        transport=calendar_transport or UrllibGoogleCalendarTransport(),
    )


@dataclass(frozen=True)
class GoogleCalendarReadTransport:
    """Read event metadata from Google Calendar."""

    access_token: str = field(repr=False)
    transport: GoogleCalendarTransport = field(repr=False)
    base_url: str = GOOGLE_CALENDAR_BASE_URL

    def list_events(
        self,
        calendar: str,
        date: str,
        limit: int,
    ) -> tuple[Mapping[str, Any], ...]:
        """Return normalized Google Calendar payloads for one calendar view."""

        clean_calendar = _required_text(calendar, "calendar")
        if limit < 1:
            raise CalendarClientError("limit must be positive.")

        payload = self._get_json(
            self._events_url(clean_calendar, date=date, limit=limit)
        )
        raw_events = payload.get("items")
        if not isinstance(raw_events, list):
            raise GoogleCalendarClientError(
                "Google Calendar events response missing items."
            )

        events = []
        for raw_event in raw_events:
            if not isinstance(raw_event, Mapping):
                raise GoogleCalendarClientError(
                    "Google Calendar event response item must be an object."
                )
            events.append(
                google_event_to_calendar_payload(
                    raw_event,
                    calendar=clean_calendar,
                )
            )
        return tuple(events)

    def _get_json(self, url: str) -> Mapping[str, Any]:
        response = self.transport.get(url, headers=self._json_headers())
        if response.status_code != 200:
            raise GoogleCalendarClientError(
                f"Google Calendar read failed with status {response.status_code}"
            )
        return response.json()

    def _json_headers(self) -> dict[str, str]:
        token = _required_text(self.access_token, "access_token")
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def _events_url(self, calendar: str, *, date: str, limit: int) -> str:
        encoded_calendar = quote(calendar, safe="")
        start, end = _date_window(date)
        query = urlencode(
            {
                "timeMin": start,
                "timeMax": end,
                "singleEvents": "true",
                "orderBy": "startTime",
                "maxResults": str(limit),
                "fields": ",".join(
                    (
                        "items(id,summary,start,end,location,organizer,status)",
                    )
                ),
            }
        )
        return f"{self._base_url()}/calendars/{encoded_calendar}/events?{query}"

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
        raise CalendarClientError(f"Google Calendar value is required: {key}")
    return value.strip()
