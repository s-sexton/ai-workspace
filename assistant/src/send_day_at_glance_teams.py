"""Post Clarity's refreshed Day at a Glance brief to Teams."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from assistant.src.generate_daily_brief import DEFAULT_DAILY_BRIEF_PATH
from assistant.src.run_jira_report import (
    DEFAULT_MEMORY_PATH,
    DEFAULT_REPORT_PATH as DEFAULT_JIRA_REPORT_PATH,
)
from assistant.src.send_daily_brief import (
    SendDailyBriefResult,
    build_google_calendar_read_transport_from_config,
    build_gmail_read_transport_from_config,
    build_graph_calendar_read_transport_from_config,
    build_graph_read_transport_from_config,
    send_daily_brief,
)


@dataclass(frozen=True)
class DayAtGlanceTeamsResult:
    """Safe result details for a Teams Day at a Glance post."""

    daily_brief: SendDailyBriefResult


@dataclass
class _LazyEmailTransport:
    """Defer live email transport construction until the refresh loop uses it."""

    factory: Callable[[], object]
    _transport: object | None = None
    _error: Exception | None = None

    def list_messages(self, mailbox: str, limit: int):  # type: ignore[no-untyped-def]
        transport = self._resolve()
        return transport.list_messages(mailbox, limit)

    def _resolve(self):
        if self._error is not None:
            raise self._error
        if self._transport is None:
            try:
                self._transport = self.factory()
            except Exception as exc:  # pragma: no cover - defensive cache
                self._error = exc
                raise
        return self._transport


@dataclass
class _LazyCalendarTransport:
    """Defer live calendar transport construction until the refresh loop uses it."""

    factory: Callable[[], object]
    _transport: object | None = None
    _error: Exception | None = None

    def list_events(self, calendar: str, date: str, limit: int):  # type: ignore[no-untyped-def]
        transport = self._resolve()
        return transport.list_events(calendar, date, limit)

    def _resolve(self):
        if self._error is not None:
            raise self._error
        if self._transport is None:
            try:
                self._transport = self.factory()
            except Exception as exc:  # pragma: no cover - defensive cache
                self._error = exc
                raise
        return self._transport


def send_day_at_glance_teams(
    *,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    output_path: Path | str = DEFAULT_DAILY_BRIEF_PATH,
    brief_date: str | None = None,
    limit: int = 10,
    calendar_window_days: int = 7,
    refresh_email: bool = True,
    refresh_calendars: bool = True,
    refresh_jira: bool = True,
    execute: bool = False,
) -> DayAtGlanceTeamsResult:
    """Refresh Clarity sources and optionally post the brief to Teams."""

    graph_email_transport = (
        _LazyEmailTransport(build_graph_read_transport_from_config)
        if refresh_email
        else None
    )
    gmail_transport = (
        _LazyEmailTransport(build_gmail_read_transport_from_config)
        if refresh_email
        else None
    )
    graph_calendar_transport = (
        _LazyCalendarTransport(build_graph_calendar_read_transport_from_config)
        if refresh_calendars
        else None
    )
    google_calendar_transport = (
        _LazyCalendarTransport(build_google_calendar_read_transport_from_config)
        if refresh_calendars
        else None
    )
    result = send_daily_brief(
        memory_path=memory_path,
        output_path=output_path,
        brief_date=brief_date,
        limit=limit,
        calendar_window_days=calendar_window_days,
        refresh_email=refresh_email,
        use_graph_email=refresh_email,
        use_gmail=refresh_email,
        graph_email_transport=graph_email_transport,
        gmail_transport=gmail_transport,
        refresh_calendars=refresh_calendars,
        use_graph_calendars=refresh_calendars,
        use_google_calendars=refresh_calendars,
        graph_calendar_transport=graph_calendar_transport,
        google_calendar_transport=google_calendar_transport,
        refresh_jira=refresh_jira,
        jira_output_path=DEFAULT_JIRA_REPORT_PATH,
        execute=execute,
        post_to_teams=True,
        continue_on_refresh_error=True,
    )
    return DayAtGlanceTeamsResult(daily_brief=result)


def main(argv: Sequence[str] | None = None) -> None:
    """Post or dry-run Clarity's Day at a Glance Teams brief."""

    args = _parse_args(argv)
    result = send_day_at_glance_teams(
        memory_path=args.memory,
        output_path=args.output,
        brief_date=args.date,
        limit=args.limit,
        calendar_window_days=args.days,
        refresh_email=not args.no_refresh_email,
        refresh_calendars=not args.no_refresh_calendars,
        refresh_jira=not args.no_refresh_jira,
        execute=args.execute,
    )
    brief = result.daily_brief.brief
    print("# Clarity Day at a Glance Teams")
    print()
    print(f"Brief: {brief.output_path}")
    print(f"Manifest: {brief.manifest_path}")
    print(f"Inbox attention: {brief.outlook_attention_count}")
    print(f"Calendar events ({brief.calendar_window_days} days): {brief.calendar_event_count}")
    print(f"Open Jira tickets: {brief.jira_ticket_count}")
    print(f"Open tasks: {brief.open_task_count}")
    print(f"Pending approvals: {brief.pending_action_count}")
    print(f"Teams posted: {'yes' if result.daily_brief.teams_posted else 'no'}")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh Clarity sources and post Day at a Glance to Teams."
    )
    parser.add_argument("--memory", default=str(DEFAULT_MEMORY_PATH))
    parser.add_argument("--output", default=str(DEFAULT_DAILY_BRIEF_PATH))
    parser.add_argument("--date", default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--no-refresh-email", action="store_true")
    parser.add_argument("--no-refresh-calendars", action="store_true")
    parser.add_argument("--no-refresh-jira", action="store_true")
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
