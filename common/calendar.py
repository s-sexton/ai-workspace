"""Read-only calendar metadata boundary for AI Workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol


class CalendarClientError(RuntimeError):
    """Raised when calendar retrieval or normalization fails."""


class CalendarTransport(Protocol):
    """Minimal read-only calendar transport interface."""

    def list_events(
        self,
        calendar: str,
        date: str,
        limit: int,
    ) -> tuple[Mapping[str, Any], ...]:
        """Return raw calendar events for one date."""


@dataclass(frozen=True)
class CalendarEvent:
    """Normalized calendar metadata used by Clarity."""

    event_id: str
    calendar: str
    title: str
    starts_at: str
    ends_at: str | None = None
    location: str | None = None
    organizer: str | None = None
    status: str | None = None


@dataclass(frozen=True)
class CalendarReadResult:
    """Normalized read-only calendar result."""

    calendar: str
    date: str
    events: tuple[CalendarEvent, ...]


@dataclass(frozen=True)
class StaticCalendarTransport:
    """Fake read-only calendar transport for local workflow tests."""

    events: tuple[Mapping[str, Any], ...]

    def list_events(
        self,
        calendar: str,
        date: str,
        limit: int,
    ) -> tuple[Mapping[str, Any], ...]:
        """Return fake events matching the requested calendar and date."""

        if limit < 1:
            raise CalendarClientError("limit must be positive.")
        return tuple(
            event
            for event in self.events
            if event.get("calendar") == calendar
            and str(event.get("starts_at", "")).startswith(date)
        )[:limit]


@dataclass(frozen=True)
class CalendarClient:
    """Small read-only calendar client for metadata normalization."""

    transport: CalendarTransport

    def list_events(
        self,
        *,
        calendar: str,
        date: str,
        limit: int = 25,
    ) -> CalendarReadResult:
        """Read and normalize calendar event metadata."""

        if not calendar.strip():
            raise CalendarClientError("calendar must be a non-empty string.")
        if not date.strip():
            raise CalendarClientError("date must be a non-empty string.")
        if limit < 1:
            raise CalendarClientError("limit must be positive.")

        events = tuple(
            _normalize_event(event, calendar=calendar)
            for event in self.transport.list_events(calendar, date, limit)
        )
        return CalendarReadResult(calendar=calendar, date=date, events=events)


def graph_event_to_calendar_payload(
    event: Mapping[str, Any],
    *,
    calendar: str,
) -> Mapping[str, Any]:
    """Convert a Microsoft Graph event payload into Clarity calendar metadata."""

    event_id = event.get("id")
    subject = event.get("subject")
    start = event.get("start")
    end = event.get("end")
    location = event.get("location")
    organizer = event.get("organizer")

    return {
        "event_id": event_id,
        "calendar": calendar,
        "title": subject,
        "starts_at": _graph_date_time(start),
        "ends_at": _graph_date_time(end),
        "location": _graph_location(location),
        "organizer": _graph_organizer(organizer),
        "status": "cancelled" if event.get("isCancelled") is True else event.get("showAs"),
    }


def _normalize_event(event: Mapping[str, Any], *, calendar: str) -> CalendarEvent:
    event_id = _required_text(event, "event_id")
    title = _required_text(event, "title")
    starts_at = _required_text(event, "starts_at")
    return CalendarEvent(
        event_id=event_id,
        calendar=str(event.get("calendar") or calendar),
        title=title,
        starts_at=starts_at,
        ends_at=_optional_text(event.get("ends_at")),
        location=_optional_text(event.get("location")),
        organizer=_optional_text(event.get("organizer")),
        status=_optional_text(event.get("status")),
    )


def _required_text(event: Mapping[str, Any], key: str) -> str:
    value = event.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CalendarClientError(f"calendar event field must be non-empty: {key}")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    stripped = value.strip()
    return stripped or None


def _graph_date_time(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None
    date_time = value.get("dateTime")
    time_zone = value.get("timeZone")
    if not isinstance(date_time, str) or not date_time.strip():
        return None
    if isinstance(time_zone, str) and time_zone.strip():
        return f"{date_time.strip()} {time_zone.strip()}"
    return date_time.strip()


def _graph_location(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None
    display_name = value.get("displayName")
    if not isinstance(display_name, str) or not display_name.strip():
        return None
    return display_name.strip()


def _graph_organizer(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None
    email_address = value.get("emailAddress")
    if not isinstance(email_address, Mapping):
        return None
    address = email_address.get("address")
    name = email_address.get("name")
    if isinstance(address, str) and address.strip():
        return address.strip()
    if isinstance(name, str) and name.strip():
        return name.strip()
    return None
