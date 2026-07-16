"""Generate Clarity's daily email-ready brief."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Sequence

from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import find_workspace_root
from common.memory import DuckDbMemoryStore, SourceMemoryRecord


DEFAULT_DAILY_BRIEF_PATH = Path("reports") / "clarity-daily-brief.md"


@dataclass(frozen=True)
class DailyBriefResult:
    """Safe details from a daily brief generation."""

    output_path: Path
    manifest_path: Path
    memory_path: Path
    brief_date: str
    outlook_attention_count: int
    calendar_event_count: int
    jira_ticket_count: int
    pending_action_count: int


def generate_daily_brief(
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    output_path: Path | str = DEFAULT_DAILY_BRIEF_PATH,
    brief_date: str | None = None,
    generated_at: datetime | None = None,
    limit: int = 10,
) -> DailyBriefResult:
    """Generate a local daily brief suitable for future email delivery."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    resolved_memory_path = _resolve_path(workspace_root, Path(memory_path))
    resolved_output_path = _resolve_path(workspace_root, Path(output_path))
    resolved_manifest_path = resolved_output_path.with_suffix(".json")
    selected_date = brief_date or date.today().isoformat()
    resolved_generated_at = generated_at or datetime.now()

    if not resolved_memory_path.is_file():
        resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_output_path.write_text(
            "\n".join(
                (
                    "# Clarity Daily Brief",
                    "",
                    f"Date: {selected_date}",
                    "",
                    f"No Clarity memory found at {resolved_memory_path}.",
                    "",
                )
            ),
            encoding="utf-8",
        )
        _write_manifest(
            resolved_manifest_path,
            manifest=_brief_manifest(
                brief_date=selected_date,
                generated_at=resolved_generated_at,
                outlook_items=(),
                calendar_items=(),
                jira_items=(),
            ),
        )
        return DailyBriefResult(
            output_path=resolved_output_path,
            manifest_path=resolved_manifest_path,
            memory_path=resolved_memory_path,
            brief_date=selected_date,
            outlook_attention_count=0,
            calendar_event_count=0,
            jira_ticket_count=0,
            pending_action_count=0,
        )

    store = DuckDbMemoryStore(resolved_memory_path)
    try:
        outlook_items = _outlook_attention_items(store, limit=limit)
        calendar_items = _calendar_items_for_date(
            store,
            brief_date=selected_date,
            limit=limit,
        )
        jira_items = _unique_records(
            store.recent_memory_by_source_type(
                "jira",
                label="review",
                limit=limit * 3,
            )
        )[:limit]
        pending_actions = store.pending_actions(limit=limit)
        content = render_daily_brief(
            brief_date=selected_date,
            generated_at=resolved_generated_at,
            outlook_items=outlook_items,
            calendar_items=calendar_items,
            jira_items=jira_items,
            pending_action_count=len(pending_actions),
        )
        resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_output_path.write_text(content, encoding="utf-8")
        _write_manifest(
            resolved_manifest_path,
            manifest=_brief_manifest(
                brief_date=selected_date,
                generated_at=resolved_generated_at,
                outlook_items=outlook_items,
                calendar_items=calendar_items,
                jira_items=jira_items,
            ),
        )
        _record_daily_brief_memory(
            store,
            output_path=resolved_output_path,
            manifest_path=resolved_manifest_path,
            brief_date=selected_date,
            outlook_attention_count=len(outlook_items),
            calendar_event_count=len(calendar_items),
            jira_ticket_count=len(jira_items),
            pending_action_count=len(pending_actions),
        )
    finally:
        store.close()

    return DailyBriefResult(
        output_path=resolved_output_path,
        manifest_path=resolved_manifest_path,
        memory_path=resolved_memory_path,
        brief_date=selected_date,
        outlook_attention_count=len(outlook_items),
        calendar_event_count=len(calendar_items),
        jira_ticket_count=len(jira_items),
        pending_action_count=len(pending_actions),
    )


def render_daily_brief(
    *,
    brief_date: str,
    generated_at: datetime,
    outlook_items: Sequence[SourceMemoryRecord],
    calendar_items: Sequence[SourceMemoryRecord],
    jira_items: Sequence[SourceMemoryRecord],
    pending_action_count: int,
) -> str:
    """Render the daily brief as compact Markdown."""

    lines = [
        "# Clarity Daily Brief",
        "",
        f"Date: {brief_date}",
        f"Generated: {generated_at.isoformat(timespec='seconds')}",
        "",
        "## At A Glance",
        "",
        f"- Outlook items that may need attention: {len(outlook_items)}",
        f"- Calendar events today: {len(calendar_items)}",
        f"- Open Jira tickets: {len(jira_items)}",
        f"- Pending Clarity approvals: {pending_action_count}",
        "",
    ]
    lines.extend(_numbered_section("Outlook Inbox Attention", outlook_items))
    lines.extend(("",))
    lines.extend(_calendar_section(calendar_items))
    lines.extend(("",))
    lines.extend(_numbered_section("Open Jira Tickets", jira_items, show_external_id=True))
    lines.extend(
        (
            "",
            "## Reply To Clarity",
            "",
            "Reply with short directions such as:",
            "",
            "- Move item 1 to Review",
            "- Mark sender from item 2 as noise",
            "- Approve pending cleanup actions",
            "",
            "Clarity will only process authenticated replies from approved senders.",
        )
    )
    return "\n".join(lines).rstrip() + "\n"


def main(argv: Sequence[str] | None = None) -> None:
    """Generate Clarity's daily email-ready brief."""

    args = _parse_args(argv)
    result = generate_daily_brief(
        memory_path=args.memory,
        output_path=args.output,
        brief_date=args.date,
        limit=args.limit,
    )
    print(f"Wrote {result.output_path}")
    print(f"Manifest: {result.manifest_path}")
    print(f"Outlook attention: {result.outlook_attention_count}")
    print(f"Calendar events: {result.calendar_event_count}")
    print(f"Open Jira tickets: {result.jira_ticket_count}")
    print(f"Pending approvals: {result.pending_action_count}")


def _outlook_attention_items(
    store: DuckDbMemoryStore,
    *,
    limit: int,
) -> tuple[SourceMemoryRecord, ...]:
    records = store.recent_memory_by_source_type("email", label="review", limit=limit * 3)
    outlook_records = [
        record
        for record in records
        if "gmail.com" not in record.scope_label.lower()
    ]
    return _unique_records(outlook_records)[:limit]


def _calendar_items_for_date(
    store: DuckDbMemoryStore,
    *,
    brief_date: str,
    limit: int,
) -> tuple[SourceMemoryRecord, ...]:
    records = store.recent_memory_by_source_type("calendar", limit=limit * 3)
    filtered = [
        record
        for record in records
        if _calendar_details(record.reason or "").get("date") == brief_date
    ]
    return _unique_records(sorted(filtered, key=_calendar_sort_key))[:limit]


def _unique_records(records: Sequence[SourceMemoryRecord]) -> tuple[SourceMemoryRecord, ...]:
    unique_records: list[SourceMemoryRecord] = []
    seen: set[tuple[str, str, str]] = set()
    for record in records:
        key = (record.source_type, record.scope_label, record.external_id)
        if key in seen:
            continue
        seen.add(key)
        unique_records.append(record)
    return tuple(unique_records)


def _numbered_section(
    title: str,
    records: Sequence[SourceMemoryRecord],
    *,
    show_external_id: bool = False,
) -> list[str]:
    lines = [f"## {title}", ""]
    if not records:
        lines.append("Nothing found.")
        return lines
    for index, record in enumerate(records, 1):
        subject = record.subject
        if show_external_id:
            subject = f"{record.external_id}: {subject}"
        lines.append(f"{index}. {subject}")
        lines.append(f"   Source: {record.display_name}")
        if record.sender_or_owner:
            lines.append(f"   From/Owner: {record.sender_or_owner}")
        if record.updated_at:
            lines.append(f"   Updated: {record.updated_at}")
        if record.reason:
            lines.append(f"   Why: {record.reason}")
        lines.append(f"   Clarity item: {record.item_id}")
    return lines


def _calendar_section(records: Sequence[SourceMemoryRecord]) -> list[str]:
    lines = ["## Day In A Glance", ""]
    if not records:
        lines.append("No calendar events found for this date.")
        return lines
    for index, record in enumerate(records, 1):
        details = _calendar_details(record.reason or "")
        time_label = _time_range_label(details)
        lines.append(f"{index}. {time_label} {record.subject}".strip())
        lines.append(f"   Calendar: {record.display_name}")
        if details.get("location"):
            lines.append(f"   Location: {details['location']}")
        lines.append(f"   Clarity item: {record.item_id}")
    return lines


def _time_range_label(details: dict[str, str]) -> str:
    start = details.get("start")
    end = details.get("end")
    if not start:
        return ""
    start_time = _clock_time(start)
    if not end:
        return start_time
    return f"{start_time}-{_clock_time(end)}"


def _clock_time(value: str) -> str:
    if "T" not in value:
        return value
    return value.split("T", maxsplit=1)[1][:5]


def _calendar_sort_key(record: SourceMemoryRecord) -> tuple[int, str, str]:
    start = _calendar_details(record.reason or "").get("start")
    return (0 if start else 1, start or "", record.subject)


def _calendar_details(reason: str) -> dict[str, str]:
    details: dict[str, str] = {}
    for key, prefix in (
        ("start", "Calendar event starts at "),
        ("end", "Ends at "),
        ("location", "Location: "),
    ):
        marker = reason.find(prefix)
        if marker == -1:
            continue
        value_start = marker + len(prefix)
        value_end = reason.find(".", value_start)
        if value_end == -1:
            value_end = len(reason)
        details[key] = reason[value_start:value_end]
    if "start" in details:
        details["date"] = details["start"].split("T", maxsplit=1)[0]
    return details


def _record_daily_brief_memory(
    store: DuckDbMemoryStore,
    *,
    output_path: Path,
    manifest_path: Path,
    brief_date: str,
    outlook_attention_count: int,
    calendar_event_count: int,
    jira_ticket_count: int,
    pending_action_count: int,
) -> None:
    run = store.start_run(workflow="daily-brief")
    store.record_generated_artifact(
        run_id=run.run_id,
        artifact_type="markdown_daily_brief",
        path=output_path,
        summary=f"Daily brief for {brief_date}.",
    )
    store.record_generated_artifact(
        run_id=run.run_id,
        artifact_type="json_daily_brief_manifest",
        path=manifest_path,
        summary=f"Daily brief item manifest for {brief_date}.",
    )
    summary = (
        f"Daily brief for {brief_date}: outlook={outlook_attention_count}, "
        f"calendar={calendar_event_count}, jira={jira_ticket_count}, "
        f"pending={pending_action_count}."
    )
    store.record_assistant_action(
        run_id=run.run_id,
        action_type="generate_daily_brief",
        approval_status="not_required",
        result=summary,
    )
    store.finish_run(run.run_id, status="completed", summary=summary)


def _brief_manifest(
    *,
    brief_date: str,
    generated_at: datetime,
    outlook_items: Sequence[SourceMemoryRecord],
    calendar_items: Sequence[SourceMemoryRecord],
    jira_items: Sequence[SourceMemoryRecord],
) -> dict[str, Any]:
    return {
        "briefDate": brief_date,
        "generatedAt": generated_at.isoformat(timespec="seconds"),
        "sections": {
            "outlook": _manifest_items(outlook_items),
            "calendar": _manifest_items(calendar_items),
            "jira": _manifest_items(jira_items),
        },
    }


def _manifest_items(records: Sequence[SourceMemoryRecord]) -> list[dict[str, Any]]:
    return [
        {
            "number": index,
            "itemId": record.item_id,
            "externalId": record.external_id,
            "sourceType": record.source_type,
            "sourceScope": record.scope_label,
            "itemType": record.item_type,
            "subject": record.subject,
            "senderOrOwner": record.sender_or_owner,
            "updatedAt": record.updated_at,
            "label": record.label,
        }
        for index, record in enumerate(records, 1)
    ]


def _write_manifest(path: Path, *, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _resolve_path(workspace_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return workspace_root / path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Clarity's daily email-ready brief."
    )
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_DAILY_BRIEF_PATH),
        help="Daily brief output path.",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Brief date in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument("--limit", type=int, default=10)
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
