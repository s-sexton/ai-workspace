from __future__ import annotations

import pytest

from common.calendar import CalendarClient, CalendarClientError, StaticCalendarTransport


def test_static_calendar_transport_filters_by_calendar_and_date():
    client = CalendarClient(
        StaticCalendarTransport(
            (
                {
                    "event_id": "family-1",
                    "calendar": "family",
                    "title": "School pickup",
                    "starts_at": "2026-07-10T15:00:00-05:00",
                },
                {
                    "event_id": "work-1",
                    "calendar": "work",
                    "title": "Staff meeting",
                    "starts_at": "2026-07-10T09:00:00-05:00",
                },
            )
        )
    )

    result = client.list_events(calendar="family", date="2026-07-10")

    assert result.calendar == "family"
    assert result.date == "2026-07-10"
    assert len(result.events) == 1
    assert result.events[0].title == "School pickup"


def test_calendar_client_rejects_invalid_events():
    client = CalendarClient(
        StaticCalendarTransport(
            (
                {
                    "event_id": "broken",
                    "calendar": "family",
                    "starts_at": "2026-07-10T15:00:00-05:00",
                },
            )
        )
    )

    with pytest.raises(CalendarClientError):
        client.list_events(calendar="family", date="2026-07-10")
