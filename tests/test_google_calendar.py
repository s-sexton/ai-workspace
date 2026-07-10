from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import parse_qs, urlparse

import pytest

from common.calendar import CalendarClientError
from common.configuration import GoogleCredentials
from common.google_calendar import (
    GoogleCalendarClientError,
    GoogleCalendarReadTransport,
    GoogleRefreshTokenProvider,
    UrllibGoogleCalendarResponse,
    build_google_calendar_read_transport,
)


@dataclass
class FakeGoogleResponse:
    status_code: int
    payload: Mapping[str, Any]

    def json(self) -> Mapping[str, Any]:
        return self.payload


class FakeGoogleCalendarTransport:
    def __init__(self, responses: Mapping[str, FakeGoogleResponse]):
        self.responses = responses
        self.get_calls: list[tuple[str, Mapping[str, str]]] = []

    def get(self, url: str, headers: Mapping[str, str]) -> FakeGoogleResponse:
        self.get_calls.append((url, headers))
        return self.responses[url]


class FakeGoogleTokenTransport:
    def __init__(self, response: FakeGoogleResponse):
        self.response = response
        self.calls: list[tuple[str, Mapping[str, str], Mapping[str, str]]] = []

    def post_form(
        self,
        url: str,
        headers: Mapping[str, str],
        form: Mapping[str, str],
    ) -> FakeGoogleResponse:
        self.calls.append((url, headers, form))
        return self.response


def test_google_refresh_token_provider_posts_expected_form():
    transport = FakeGoogleTokenTransport(
        FakeGoogleResponse(200, {"access_token": "access-token"})
    )
    provider = GoogleRefreshTokenProvider(
        credentials=GoogleCredentials(
            client_id="client-id",
            client_secret="super-secret",
            refresh_token="refresh-secret",
        ),
        transport=transport,
        token_url="https://oauth.example/token",
    )

    token = provider.access_token()

    assert token == "access-token"
    assert len(transport.calls) == 1
    url, headers, form = transport.calls[0]
    assert url == "https://oauth.example/token"
    assert headers["Accept"] == "application/json"
    assert form == {
        "client_id": "client-id",
        "client_secret": "super-secret",
        "refresh_token": "refresh-secret",
        "grant_type": "refresh_token",
    }
    assert "super-secret" not in repr(provider)
    assert "refresh-secret" not in repr(provider)


def test_build_google_calendar_read_transport_can_use_direct_access_token():
    calendar_transport = FakeGoogleCalendarTransport({})
    token_transport = FakeGoogleTokenTransport(
        FakeGoogleResponse(200, {"access_token": "should-not-be-used"})
    )

    transport = build_google_calendar_read_transport(
        GoogleCredentials(access_token="direct-token"),
        calendar_transport=calendar_transport,
        token_transport=token_transport,
        use_bearer_auth=True,
    )

    assert isinstance(transport, GoogleCalendarReadTransport)
    assert "direct-token" not in repr(transport)
    assert token_transport.calls == []


def test_build_google_calendar_read_transport_can_refresh_token():
    calendar_transport = FakeGoogleCalendarTransport({})
    token_transport = FakeGoogleTokenTransport(
        FakeGoogleResponse(200, {"access_token": "acquired-token"})
    )

    transport = build_google_calendar_read_transport(
        GoogleCredentials(
            client_id="client-id",
            client_secret="super-secret",
            refresh_token="refresh-secret",
        ),
        calendar_transport=calendar_transport,
        token_transport=token_transport,
    )

    assert isinstance(transport, GoogleCalendarReadTransport)
    assert len(token_transport.calls) == 1
    assert "super-secret" not in repr(transport)


def test_google_calendar_read_transport_lists_events():
    base_url = "https://google.example/calendar/v3"
    list_url = (
        "https://google.example/calendar/v3/calendars/"
        "family%40group.calendar.google.com/events?"
        "timeMin=2026-07-10T00%3A00%3A00Z&"
        "timeMax=2026-07-11T00%3A00%3A00Z&singleEvents=true&"
        "orderBy=startTime&maxResults=2&fields="
        "items%28id%2Csummary%2Cstart%2Cend%2Clocation%2Corganizer%2Cstatus%29"
    )
    transport = FakeGoogleCalendarTransport(
        {
            list_url: FakeGoogleResponse(
                200,
                {
                    "items": [
                        {
                            "id": "event-1",
                            "summary": "Family dinner",
                            "start": {"dateTime": "2026-07-10T18:00:00-05:00"},
                            "end": {"dateTime": "2026-07-10T19:00:00-05:00"},
                            "location": "Home",
                            "organizer": {
                                "email": "family@group.calendar.google.com"
                            },
                            "status": "confirmed",
                        }
                    ]
                },
            )
        }
    )
    client = GoogleCalendarReadTransport(
        access_token="access-token",
        transport=transport,
        base_url=base_url,
    )

    events = client.list_events("family@group.calendar.google.com", "2026-07-10", 2)

    assert len(events) == 1
    event = events[0]
    assert event["event_id"] == "event-1"
    assert event["calendar"] == "family@group.calendar.google.com"
    assert event["title"] == "Family dinner"
    assert event["starts_at"] == "2026-07-10T18:00:00-05:00"
    assert event["location"] == "Home"
    assert event["organizer"] == "family@group.calendar.google.com"
    assert transport.get_calls[0][1]["Authorization"] == "Bearer access-token"
    parsed = urlparse(transport.get_calls[0][0])
    assert parsed.path.endswith("/events")
    assert parse_qs(parsed.query)["timeMin"] == ["2026-07-10T00:00:00Z"]


def test_google_calendar_read_transport_rejects_invalid_date():
    client = GoogleCalendarReadTransport(
        access_token="access-token",
        transport=FakeGoogleCalendarTransport({}),
        base_url="https://google.example/calendar/v3",
    )

    with pytest.raises(CalendarClientError):
        client.list_events("family", "07/10/2026", 1)


def test_google_calendar_read_transport_rejects_missing_items_list():
    list_url = (
        "https://google.example/calendar/v3/calendars/family/events?"
        "timeMin=2026-07-10T00%3A00%3A00Z&"
        "timeMax=2026-07-11T00%3A00%3A00Z&singleEvents=true&"
        "orderBy=startTime&maxResults=1&fields="
        "items%28id%2Csummary%2Cstart%2Cend%2Clocation%2Corganizer%2Cstatus%29"
    )
    client = GoogleCalendarReadTransport(
        access_token="access-token",
        transport=FakeGoogleCalendarTransport({list_url: FakeGoogleResponse(200, {})}),
        base_url="https://google.example/calendar/v3",
    )

    with pytest.raises(GoogleCalendarClientError):
        client.list_events("family", "2026-07-10", 1)


def test_urllib_google_response_rejects_non_object_json():
    response = UrllibGoogleCalendarResponse(status_code=200, body=b"[]")

    with pytest.raises(GoogleCalendarClientError):
        response.json()
