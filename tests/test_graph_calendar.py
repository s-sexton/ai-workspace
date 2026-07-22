from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import parse_qs, urlparse

import pytest

from common.calendar import CalendarClientError
from common.configuration import GraphCredentials
from common.graph_calendar import (
    GraphCalendarReadTransport,
    build_graph_calendar_read_transport,
    graph_calendar_reference,
)
from common.graph_email import GraphClientError


@dataclass
class FakeGraphResponse:
    status_code: int
    payload: Mapping[str, Any]

    def json(self) -> Mapping[str, Any]:
        return self.payload


class FakeGraphTransport:
    def __init__(self, responses: Mapping[str, FakeGraphResponse]):
        self.responses = responses
        self.get_calls: list[tuple[str, Mapping[str, str]]] = []

    def get(self, url: str, headers: Mapping[str, str]) -> FakeGraphResponse:
        self.get_calls.append((url, headers))
        return self.responses[url]


class FakeGraphTokenTransport:
    def __init__(self, response: FakeGraphResponse):
        self.response = response
        self.calls: list[tuple[str, Mapping[str, str], Mapping[str, str]]] = []

    def post_form(
        self,
        url: str,
        headers: Mapping[str, str],
        form: Mapping[str, str],
    ) -> FakeGraphResponse:
        self.calls.append((url, headers, form))
        return self.response


def test_build_graph_calendar_read_transport_can_use_direct_access_token():
    graph_transport = FakeGraphTransport({})
    token_transport = FakeGraphTokenTransport(
        FakeGraphResponse(200, {"access_token": "should-not-be-used"})
    )

    transport = build_graph_calendar_read_transport(
        GraphCredentials(access_token="direct-token"),
        graph_transport=graph_transport,
        token_transport=token_transport,
        use_bearer_auth=True,
    )

    assert isinstance(transport, GraphCalendarReadTransport)
    assert "direct-token" not in repr(transport)
    assert token_transport.calls == []


def test_build_graph_calendar_read_transport_can_acquire_client_credentials_token():
    graph_transport = FakeGraphTransport({})
    token_transport = FakeGraphTokenTransport(
        FakeGraphResponse(200, {"access_token": "acquired-token"})
    )

    transport = build_graph_calendar_read_transport(
        GraphCredentials(
            tenant_id="tenant",
            client_id="client-id",
            client_secret="super-secret",
        ),
        graph_transport=graph_transport,
        token_transport=token_transport,
    )

    assert isinstance(transport, GraphCalendarReadTransport)
    assert len(token_transport.calls) == 1
    assert "super-secret" not in repr(transport)


def test_graph_calendar_read_transport_lists_calendar_view():
    base_url = "https://graph.example/v1.0"
    list_url = (
        "https://graph.example/v1.0/users/scott.sexton%40example.invalid/"
        "calendarView?startDateTime=2026-07-10T00%3A00%3A00Z&"
        "endDateTime=2026-07-11T00%3A00%3A00Z&%24top=2&"
        "%24orderby=start%2FdateTime&%24select="
        "id%2Csubject%2Cstart%2Cend%2Clocation%2Corganizer%2CshowAs%2CisCancelled"
    )
    transport = FakeGraphTransport(
        {
            list_url: FakeGraphResponse(
                200,
                {
                    "value": [
                        {
                            "id": "event-1",
                            "subject": "Family dinner",
                            "start": {
                                "dateTime": "2026-07-10T18:00:00",
                                "timeZone": "Central Standard Time",
                            },
                            "end": {
                                "dateTime": "2026-07-10T19:00:00",
                                "timeZone": "Central Standard Time",
                            },
                            "location": {"displayName": "Home"},
                            "organizer": {
                                "emailAddress": {
                                    "address": "scott.sexton@example.invalid"
                                }
                            },
                            "showAs": "busy",
                            "isCancelled": False,
                        }
                    ]
                },
            )
        }
    )
    client = GraphCalendarReadTransport(
        access_token="access-token",
        transport=transport,
        base_url=base_url,
    )

    events = client.list_events("scott.sexton@example.invalid", "2026-07-10", 2)

    assert len(events) == 1
    event = events[0]
    assert event["event_id"] == "event-1"
    assert event["calendar"] == "scott.sexton@example.invalid"
    assert event["title"] == "Family dinner"
    assert event["starts_at"] == "2026-07-10T18:00:00 Central Standard Time"
    assert event["location"] == "Home"
    assert event["organizer"] == "scott.sexton@example.invalid"
    assert transport.get_calls[0][1]["Authorization"] == "Bearer access-token"
    assert transport.get_calls[0][1]["Prefer"] == 'outlook.timezone="UTC"'
    parsed = urlparse(transport.get_calls[0][0])
    assert parsed.path.endswith("/calendarView")
    assert parse_qs(parsed.query)["startDateTime"] == ["2026-07-10T00:00:00Z"]


def test_graph_calendar_read_transport_lists_named_calendar_view():
    base_url = "https://graph.example/v1.0"
    calendars_url = (
        "https://graph.example/v1.0/users/scott.sexton%40example.invalid/"
        "calendars?%24top=100&%24select=id%2Cname"
    )
    list_url = (
        "https://graph.example/v1.0/users/scott.sexton%40example.invalid/"
        "calendars/calendar-id-1/calendarView?"
        "startDateTime=2026-07-10T00%3A00%3A00Z&"
        "endDateTime=2026-07-11T00%3A00%3A00Z&%24top=2&"
        "%24orderby=start%2FdateTime&%24select="
        "id%2Csubject%2Cstart%2Cend%2Clocation%2Corganizer%2CshowAs%2CisCancelled"
    )
    transport = FakeGraphTransport(
        {
            calendars_url: FakeGraphResponse(
                200,
                {
                    "value": [
                        {
                            "id": "calendar-id-1",
                            "name": "SendThisFile Holiday and Vacation Schedule",
                        }
                    ]
                },
            ),
            list_url: FakeGraphResponse(
                200,
                {
                    "value": [
                        {
                            "id": "event-1",
                            "subject": "Company Holiday",
                            "start": {
                                "dateTime": "2026-07-10T00:00:00",
                                "timeZone": "Central Standard Time",
                            },
                            "end": {
                                "dateTime": "2026-07-11T00:00:00",
                                "timeZone": "Central Standard Time",
                            },
                        }
                    ]
                },
            ),
        }
    )
    client = GraphCalendarReadTransport(
        access_token="access-token",
        transport=transport,
        base_url=base_url,
    )

    events = client.list_events(
        graph_calendar_reference(
            "scott.sexton@example.invalid",
            "SendThisFile Holiday and Vacation Schedule",
        ),
        "2026-07-10",
        2,
    )

    assert events[0]["title"] == "Company Holiday"
    assert (
        events[0]["calendar"]
        == "scott.sexton@example.invalid::SendThisFile Holiday and Vacation Schedule"
    )
    assert transport.get_calls[0][0] == calendars_url
    assert transport.get_calls[1][0] == list_url


def test_graph_calendar_read_transport_rejects_missing_named_calendar():
    base_url = "https://graph.example/v1.0"
    calendars_url = (
        "https://graph.example/v1.0/users/scott.sexton%40example.invalid/"
        "calendars?%24top=100&%24select=id%2Cname"
    )
    client = GraphCalendarReadTransport(
        access_token="access-token",
        transport=FakeGraphTransport(
            {calendars_url: FakeGraphResponse(200, {"value": []})}
        ),
        base_url=base_url,
    )

    with pytest.raises(GraphClientError, match="calendar was not found"):
        client.list_events(
            graph_calendar_reference(
                "scott.sexton@example.invalid",
                "SendThisFile Holiday and Vacation Schedule",
            ),
            "2026-07-10",
            1,
        )


def test_graph_calendar_read_transport_rejects_invalid_date():
    client = GraphCalendarReadTransport(
        access_token="access-token",
        transport=FakeGraphTransport({}),
        base_url="https://graph.example/v1.0",
    )

    with pytest.raises(CalendarClientError):
        client.list_events("scott.sexton@example.invalid", "07/10/2026", 1)


def test_graph_calendar_read_transport_rejects_missing_value_list():
    list_url = (
        "https://graph.example/v1.0/users/scott.sexton%40example.invalid/"
        "calendarView?startDateTime=2026-07-10T00%3A00%3A00Z&"
        "endDateTime=2026-07-11T00%3A00%3A00Z&%24top=1&"
        "%24orderby=start%2FdateTime&%24select="
        "id%2Csubject%2Cstart%2Cend%2Clocation%2Corganizer%2CshowAs%2CisCancelled"
    )
    client = GraphCalendarReadTransport(
        access_token="access-token",
        transport=FakeGraphTransport({list_url: FakeGraphResponse(200, {})}),
        base_url="https://graph.example/v1.0",
    )

    with pytest.raises(GraphClientError):
        client.list_events("scott.sexton@example.invalid", "2026-07-10", 1)
