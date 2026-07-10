"""Local read-only calendar metadata review workflow."""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Mapping, Sequence

from assistant.src.generate_brief import generate_memory_brief
from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.calendar import (
    CalendarClient,
    CalendarEvent,
    CalendarTransport,
    StaticCalendarTransport,
)
from common.configuration import find_workspace_root
from common.memory import DuckDbMemoryStore


DEFAULT_CALENDAR = "family"

SAMPLE_CALENDAR_EVENTS: tuple[Mapping[str, object], ...] = (
    {
        "event_id": "family-school-pickup",
        "calendar": "family",
        "title": "School pickup",
        "starts_at": "2026-07-10T15:00:00-05:00",
        "ends_at": "2026-07-10T15:30:00-05:00",
        "location": "School",
        "organizer": "Family Calendar",
        "status": "confirmed",
    },
    {
        "event_id": "family-dinner",
        "calendar": "family",
        "title": "Family dinner",
        "starts_at": "2026-07-10T18:00:00-05:00",
        "ends_at": "2026-07-10T19:00:00-05:00",
        "location": "Home",
        "organizer": "Family Calendar",
        "status": "confirmed",
    },
)


@dataclass(frozen=True)
class CalendarReviewResult:
    """Safe result details for a local calendar review run."""

    memory_path: Path
    brief_path: Path
    run_id: str
    calendar: str
    review_date: str
    event_count: int


def run_calendar_review(
    *,
    root: Path | str | None = None,
    calendar: str = DEFAULT_CALENDAR,
    review_date: str | None = None,
    limit: int = 25,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    brief_output_path: Path | str | None = None,
    transport: CalendarTransport | None = None,
) -> CalendarReviewResult:
    """Read local calendar metadata, write memory, and generate a local brief."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    selected_date = review_date or date.today().isoformat()
    resolved_memory_path = _resolve_path(workspace_root, Path(memory_path))
    client = CalendarClient(
        transport=transport or StaticCalendarTransport(SAMPLE_CALENDAR_EVENTS)
    )
    read_result = client.list_events(
        calendar=calendar,
        date=selected_date,
        limit=limit,
    )
    run_id = _record_calendar_memory(
        memory_path=resolved_memory_path,
        calendar=read_result.calendar,
        review_date=read_result.date,
        events=read_result.events,
    )
    brief_path = generate_memory_brief(
        root=workspace_root,
        memory_path=resolved_memory_path,
        output_path=brief_output_path or Path("reports") / "clarity-brief.md",
    )
    return CalendarReviewResult(
        memory_path=resolved_memory_path,
        brief_path=brief_path,
        run_id=run_id,
        calendar=read_result.calendar,
        review_date=read_result.date,
        event_count=len(read_result.events),
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Run the local read-only calendar review workflow."""

    args = _parse_args(argv)
    result = run_calendar_review(
        calendar=args.calendar,
        review_date=args.date,
        limit=args.limit,
        memory_path=args.memory,
        brief_output_path=args.brief,
    )
    print(
        f"Read {result.event_count} calendar event(s) "
        f"from {result.calendar} for {result.review_date}"
    )
    print(f"Wrote brief {result.brief_path}")


def _record_calendar_memory(
    *,
    memory_path: Path,
    calendar: str,
    review_date: str,
    events: tuple[CalendarEvent, ...],
) -> str:
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="calendar-review")
        source = store.record_source(
            source_type="calendar",
            display_name=f"{calendar} calendar",
            scope_label=calendar,
            access_mode="read",
        )
        for event in events:
            item = store.record_item_seen(
                source_id=source.source_id,
                external_id=event.event_id,
                item_type="calendar_event",
                subject=event.title,
                sender_or_owner=event.organizer,
                updated_at=event.starts_at,
                content_hash=_event_hash(event),
                first_seen_run_id=run.run_id,
            )
            store.record_classification(
                item_id=item.item_id,
                run_id=run.run_id,
                label="calendar",
                reason=_event_reason(event),
            )
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="read_calendar_metadata",
            approval_status="not_required",
            result=f"Read {len(events)} event(s) from {calendar} for {review_date}.",
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary=f"Read {len(events)} event(s) from {calendar} for {review_date}.",
        )
        return run.run_id
    finally:
        store.close()


def _event_reason(event: CalendarEvent) -> str:
    parts = [f"Calendar event starts at {event.starts_at}."]
    if event.ends_at:
        parts.append(f"Ends at {event.ends_at}.")
    if event.location:
        parts.append(f"Location: {event.location}.")
    return " ".join(parts)


def _event_hash(event: CalendarEvent) -> str:
    stable = "|".join(
        (
            event.event_id,
            event.calendar,
            event.title,
            event.starts_at,
            event.ends_at or "",
            event.location or "",
            event.organizer or "",
            event.status or "",
        )
    )
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def _resolve_path(workspace_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return workspace_root / path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a local read-only calendar metadata review."
    )
    parser.add_argument(
        "--calendar",
        default=DEFAULT_CALENDAR,
        help="Calendar label to read from the local sample transport.",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Date to review in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path.",
    )
    parser.add_argument(
        "--brief",
        default=None,
        help="Local brief output path.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
