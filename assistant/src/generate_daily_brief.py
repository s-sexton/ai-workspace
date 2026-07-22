"""Generate Clarity's daily email-ready brief."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import ConfigurationError, find_workspace_root, load_workspace_config
from common.memory import (
    DelegatedTaskRecord,
    DuckDbMemoryStore,
    PendingActionRecord,
    SourceMemoryRecord,
)


DEFAULT_DAILY_BRIEF_PATH = Path("reports") / "clarity-daily-brief.md"
CENTRAL_TIME = ZoneInfo("America/Chicago")


@dataclass(frozen=True)
class DailyBriefResult:
    """Safe details from a daily brief generation."""

    output_path: Path
    manifest_path: Path
    memory_path: Path
    brief_date: str
    calendar_window_days: int
    outlook_attention_count: int
    calendar_event_count: int
    jira_ticket_count: int
    open_task_count: int
    pending_action_count: int


def generate_daily_brief(
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    output_path: Path | str = DEFAULT_DAILY_BRIEF_PATH,
    brief_date: str | None = None,
    generated_at: datetime | None = None,
    limit: int = 10,
    calendar_window_days: int = 7,
) -> DailyBriefResult:
    """Generate a local daily brief suitable for future email delivery."""

    if calendar_window_days < 1:
        raise ValueError("calendar_window_days must be positive.")

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
                calendar_window_days=calendar_window_days,
                generated_at=resolved_generated_at,
                inbox_items=(),
                calendar_items=(),
                jira_items=(),
                open_tasks=(),
                pending_actions=(),
            ),
        )
        return DailyBriefResult(
            output_path=resolved_output_path,
            manifest_path=resolved_manifest_path,
            memory_path=resolved_memory_path,
            brief_date=selected_date,
            calendar_window_days=calendar_window_days,
            outlook_attention_count=0,
            calendar_event_count=0,
            jira_ticket_count=0,
            open_task_count=0,
            pending_action_count=0,
        )

    store = DuckDbMemoryStore(resolved_memory_path)
    try:
        daily_brief_sender, daily_brief_subject_prefix = _daily_brief_identity(
            workspace_root
        )
        mailbox_order = _approved_mailboxes(workspace_root)
        inbox_items = _inbox_attention_items(
            store,
            limit=limit,
            mailboxes=mailbox_order,
            daily_brief_sender=daily_brief_sender,
            daily_brief_subject_prefix=daily_brief_subject_prefix,
        )
        calendar_items = _calendar_items_for_window(
            store,
            brief_date=selected_date,
            window_days=calendar_window_days,
            limit=limit,
        )
        jira_items = _unique_records(
            store.recent_memory_by_source_type(
                "jira",
                label="review",
                limit=limit * 3,
            )
        )[:limit]
        open_tasks = store.list_open_delegated_tasks()[:limit]
        pending_actions = store.pending_actions(limit=limit)
        content = render_daily_brief(
            brief_date=selected_date,
            calendar_window_days=calendar_window_days,
            generated_at=resolved_generated_at,
            inbox_items=inbox_items,
            inbox_mailboxes=mailbox_order,
            calendar_items=calendar_items,
            jira_items=jira_items,
            open_tasks=open_tasks,
            pending_actions=pending_actions,
        )
        resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_output_path.write_text(content, encoding="utf-8")
        _write_manifest(
            resolved_manifest_path,
            manifest=_brief_manifest(
                brief_date=selected_date,
                calendar_window_days=calendar_window_days,
                generated_at=resolved_generated_at,
                inbox_items=inbox_items,
                calendar_items=calendar_items,
                jira_items=jira_items,
                open_tasks=open_tasks,
                pending_actions=pending_actions,
            ),
        )
        _record_daily_brief_memory(
            store,
            output_path=resolved_output_path,
            manifest_path=resolved_manifest_path,
            brief_date=selected_date,
            calendar_window_days=calendar_window_days,
            inbox_attention_count=len(inbox_items),
            calendar_event_count=len(calendar_items),
            jira_ticket_count=len(jira_items),
            open_task_count=len(open_tasks),
            pending_action_count=len(pending_actions),
        )
    finally:
        store.close()

    return DailyBriefResult(
        output_path=resolved_output_path,
        manifest_path=resolved_manifest_path,
        memory_path=resolved_memory_path,
        brief_date=selected_date,
        calendar_window_days=calendar_window_days,
        outlook_attention_count=len(inbox_items),
        calendar_event_count=len(calendar_items),
        jira_ticket_count=len(jira_items),
        open_task_count=len(open_tasks),
        pending_action_count=len(pending_actions),
    )


def render_daily_brief(
    *,
    brief_date: str,
    calendar_window_days: int,
    generated_at: datetime,
    inbox_items: Sequence[SourceMemoryRecord],
    calendar_items: Sequence[SourceMemoryRecord],
    jira_items: Sequence[SourceMemoryRecord],
    open_tasks: Sequence[DelegatedTaskRecord],
    pending_actions: Sequence[PendingActionRecord],
    inbox_mailboxes: Sequence[str] = (),
) -> str:
    """Render the daily brief as compact Markdown."""

    lines = [
        "# Clarity Daily Brief",
        "",
        f"Date: {_brief_date_label(brief_date, calendar_window_days)}",
        f"Generated: {generated_at.isoformat(timespec='seconds')}",
        "",
        "## At A Glance",
        "",
        f"- Inbox items that may need attention: {len(inbox_items)}",
        f"- Calendar events next {calendar_window_days} days: {len(calendar_items)}",
        f"- Open Jira tickets: {len(jira_items)}",
        f"- Open tasks: {len(open_tasks)}",
        f"- Pending Clarity approvals: {len(pending_actions)}",
        "",
    ]
    lines.extend(_email_attention_section(inbox_items, mailboxes=inbox_mailboxes))
    lines.extend(("",))
    lines.extend(
        _calendar_section(
            calendar_items,
            brief_date=brief_date,
            window_days=calendar_window_days,
        )
    )
    lines.extend(("",))
    lines.extend(_numbered_section("Open Jira Tickets", jira_items, show_external_id=True))
    lines.extend(("",))
    lines.extend(_open_tasks_section(open_tasks))
    lines.extend(("",))
    lines.extend(_pending_approvals_section(pending_actions))
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
            "- Approve action ACTION_ID",
            "- Reject action ACTION_ID",
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
        calendar_window_days=args.days,
    )
    print(f"Wrote {result.output_path}")
    print(f"Manifest: {result.manifest_path}")
    print(f"Inbox attention: {result.outlook_attention_count}")
    print(f"Calendar events ({result.calendar_window_days} days): {result.calendar_event_count}")
    print(f"Open Jira tickets: {result.jira_ticket_count}")
    print(f"Open tasks: {result.open_task_count}")
    print(f"Pending approvals: {result.pending_action_count}")


def _inbox_attention_items(
    store: DuckDbMemoryStore,
    *,
    limit: int,
    mailboxes: Sequence[str],
    daily_brief_sender: str | None = None,
    daily_brief_subject_prefix: str | None = None,
) -> tuple[SourceMemoryRecord, ...]:
    records = _latest_email_review_records_by_mailbox(
        store,
        mailboxes=mailboxes,
        limit=limit,
    )
    if not records and not mailboxes:
        records = store.recent_memory_by_source_type(
            "email",
            label="review",
            limit=limit * 3,
        )
    attention_records = [
        record
        for record in records
        if not _is_daily_brief_message(
            record,
            sender=daily_brief_sender,
            subject_prefix=daily_brief_subject_prefix,
        )
    ]
    unique_records = _unique_records(attention_records)
    if mailboxes:
        return unique_records
    return unique_records[:limit]


def _latest_email_review_records_by_mailbox(
    store: DuckDbMemoryStore,
    *,
    mailboxes: Sequence[str],
    limit: int,
) -> tuple[SourceMemoryRecord, ...]:
    records: list[SourceMemoryRecord] = []
    for mailbox in mailboxes:
        records.extend(
            _latest_email_review_records(
                store,
                mailbox=mailbox,
                limit=limit,
            )
        )
    return tuple(records)


def _latest_email_review_records(
    store: DuckDbMemoryStore,
    *,
    mailbox: str,
    limit: int,
) -> tuple[SourceMemoryRecord, ...]:
    row = store._connection.execute(
        """
        SELECT r.run_id
        FROM runs r
        JOIN items_seen i ON i.first_seen_run_id = r.run_id
        JOIN sources s ON s.source_id = i.source_id
        WHERE r.workflow = 'email-review'
          AND s.source_type = 'email'
          AND s.scope_label = ?
          AND i.item_type = 'email_message'
        ORDER BY r.started_at DESC, r.run_id DESC
        LIMIT 1
        """,
        [mailbox],
    ).fetchone()
    if row is None:
        return ()
    rows = store._connection.execute(
        """
        SELECT i.item_id, i.external_id, s.source_type, s.display_name,
               s.scope_label, i.item_type, i.subject, i.sender_or_owner,
               i.updated_at, c.label, c.reason
        FROM items_seen i
        JOIN sources s ON s.source_id = i.source_id
        JOIN classifications c ON c.item_id = i.item_id
        WHERE i.first_seen_run_id = ?
          AND s.scope_label = ?
          AND i.item_type = 'email_message'
          AND c.label = 'review'
          AND NOT EXISTS (
              SELECT 1
              FROM assistant_actions a
              WHERE a.item_id = i.item_id
                AND a.approval_status = 'executed'
                AND a.action_type LIKE 'propose_email_move_%'
          )
        ORDER BY COALESCE(i.updated_at, '') DESC, i.item_id DESC
        LIMIT ?
        """,
        [row[0], mailbox, limit],
    ).fetchall()
    return tuple(SourceMemoryRecord(*record) for record in rows)


def _daily_brief_identity(workspace_root: Path) -> tuple[str | None, str | None]:
    try:
        settings = load_workspace_config(
            workspace_root,
            include_process_env=False,
        ).daily_brief_settings
    except ConfigurationError:
        return None, None
    return settings.sender, settings.subject_prefix


def _is_daily_brief_message(
    record: SourceMemoryRecord,
    *,
    sender: str | None,
    subject_prefix: str | None,
) -> bool:
    if sender and (record.sender_or_owner or "").strip().lower() == sender.lower():
        return True
    if subject_prefix:
        clean_subject = " ".join(record.subject.lower().strip().split())
        clean_prefix = " ".join(subject_prefix.lower().strip().split())
        return clean_subject.startswith(clean_prefix)
    return False


def _approved_mailboxes(workspace_root: Path) -> tuple[str, ...]:
    try:
        config = load_workspace_config(workspace_root, include_process_env=False)
        approved_mailboxes = config.email_settings.approved_mailboxes
    except ConfigurationError:
        return ()
    return tuple(approved_mailboxes)


def _calendar_items_for_window(
    store: DuckDbMemoryStore,
    *,
    brief_date: str,
    window_days: int,
    limit: int,
) -> tuple[SourceMemoryRecord, ...]:
    dates = _date_window(brief_date, window_days)
    latest_run_records = tuple(
        record
        for window_date in dates
        for record in _latest_calendar_review_records_for_date(
            store,
            brief_date=window_date,
            limit=limit,
        )
    )
    records = store.recent_memory_by_source_type(
        "calendar",
        limit=max(limit * window_days * 3, limit),
    )
    filtered = [
        record
        for record in records
        if _calendar_details(record.reason or "").get("date") in dates
    ]
    return _unique_records(
        sorted((*latest_run_records, *filtered), key=_calendar_sort_key)
    )


def _latest_calendar_review_records_for_date(
    store: DuckDbMemoryStore,
    *,
    brief_date: str,
    limit: int,
) -> tuple[SourceMemoryRecord, ...]:
    row = store._connection.execute(
        """
        SELECT run_id
        FROM runs
        WHERE workflow = 'calendar-review'
          AND summary LIKE ?
        ORDER BY started_at DESC, run_id DESC
        LIMIT 1
        """,
        [f"% for {brief_date}."],
    ).fetchone()
    if row is None:
        return ()
    rows = store._connection.execute(
        """
        SELECT i.item_id, i.external_id, s.source_type, s.display_name,
               s.scope_label, i.item_type, i.subject, i.sender_or_owner,
               i.updated_at, c.label, c.reason
        FROM items_seen i
        JOIN sources s ON s.source_id = i.source_id
        LEFT JOIN classifications c ON c.item_id = i.item_id
        WHERE s.source_type = 'calendar'
          AND (i.first_seen_run_id = ? OR i.last_seen_run_id = ?)
        ORDER BY COALESCE(i.updated_at, '') ASC, i.item_id ASC
        LIMIT ?
        """,
        [row[0], row[0], limit],
    ).fetchall()
    return tuple(SourceMemoryRecord(*record) for record in rows)


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


def _email_attention_section(
    records: Sequence[SourceMemoryRecord],
    *,
    mailboxes: Sequence[str],
) -> list[str]:
    lines = ["## Inbox Attention", ""]
    grouped = _records_by_scope(records)
    ordered_mailboxes = _ordered_mailboxes(mailboxes, grouped)
    if not ordered_mailboxes:
        lines.append("Nothing found.")
        return lines

    item_number = 1
    for mailbox in ordered_mailboxes:
        lines.append(f"### {mailbox}")
        lines.append("")
        mailbox_records = grouped.get(mailbox, ())
        item_lines = _numbered_items(mailbox_records, start=item_number)
        lines.extend(item_lines)
        lines.append("")
        item_number += len(mailbox_records)

    if lines[-1] == "":
        lines.pop()
    return lines


def _open_tasks_section(tasks: Sequence[DelegatedTaskRecord]) -> list[str]:
    lines = ["## Open Tasks", ""]
    if not tasks:
        lines.append("Nothing found.")
        return lines
    for index, task in enumerate(tasks, 1):
        lines.append(f"{index}. {task.title}")
        lines.append(f"   Status: {task.status}")
        if task.next_step:
            lines.append(f"   Next step: {task.next_step}")
        if task.approval_required:
            lines.append("   Approval: required")
        lines.append("")
    if lines[-1] == "":
        lines.pop()
    return lines


def _pending_approvals_section(actions: Sequence[PendingActionRecord]) -> list[str]:
    lines = ["## Pending Approvals", ""]
    if not actions:
        lines.append("Nothing waiting for approval.")
        return lines

    for index, action in enumerate(actions, 1):
        lines.append(f"{index}. {_pending_action_title(action)}")
        lines.append("")

    if lines[-1] == "":
        lines.pop()
    return lines


def _pending_action_title(action: PendingActionRecord) -> str:
    action_label = _pending_action_label(action)
    subject = action.item_subject or action.item_external_id or "Unlinked action"
    source = f" ({action.source_scope_label})" if action.source_scope_label else ""
    return f"{action_label}: {subject}{source}"


def _pending_action_label(action: PendingActionRecord) -> str:
    if action.action_type == "propose_jira_delete":
        return "Delete Jira"
    if action.action_type.startswith("propose_jira_transition_"):
        target = action.action_target or action.action_type.rsplit("_", maxsplit=1)[-1]
        return f"Move Jira to {target}"
    if action.action_type.startswith("propose_email_move_"):
        target = action.action_target or action.action_type.rsplit("_", maxsplit=1)[-1]
        return f"Move email to {target}"
    return action.action_type.replace("_", " ").removeprefix("propose ").title()


def _compact_text(value: str) -> str:
    return " ".join(value.split())


def _records_by_scope(
    records: Sequence[SourceMemoryRecord],
) -> dict[str, tuple[SourceMemoryRecord, ...]]:
    grouped: dict[str, list[SourceMemoryRecord]] = {}
    for record in records:
        grouped.setdefault(record.scope_label, []).append(record)
    return {mailbox: tuple(items) for mailbox, items in grouped.items()}


def _ordered_mailboxes(
    configured_mailboxes: Sequence[str],
    grouped_records: dict[str, tuple[SourceMemoryRecord, ...]],
) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for mailbox in configured_mailboxes:
        if mailbox in grouped_records and mailbox not in seen:
            ordered.append(mailbox)
            seen.add(mailbox)
    for mailbox in grouped_records:
        if mailbox not in seen:
            ordered.append(mailbox)
            seen.add(mailbox)
    return tuple(ordered)


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
    lines.extend(_numbered_items(records, start=1, show_external_id=show_external_id))
    return lines


def _numbered_items(
    records: Sequence[SourceMemoryRecord],
    *,
    start: int,
    show_external_id: bool = False,
) -> list[str]:
    lines: list[str] = []
    for index, record in enumerate(records, start):
        subject = record.subject
        if show_external_id:
            subject = f"{record.external_id}: {subject}"
        lines.append(f"{index}. Date: {_central_datetime_label(record.updated_at)}")
        lines.append(f"   From: {record.sender_or_owner or 'Unknown'}")
        lines.append(f"   Subject: {subject}")
        lines.append(f"   Recommendation: {record.reason or 'Review when time allows.'}")
        lines.append("")
    if lines[-1] == "":
        lines.pop()
    return lines


def _calendar_section(
    records: Sequence[SourceMemoryRecord],
    *,
    brief_date: str,
    window_days: int,
) -> list[str]:
    lines = [f"## Calendar: {_brief_date_label(brief_date, window_days)}", ""]
    if not records:
        lines.append("No calendar events found for this window.")
        return lines
    for index, record in enumerate(records, 1):
        details = _calendar_details(record.reason or "")
        time_label = _time_range_label(details)
        date_label = _event_date_label(details)
        lines.append(f"{index}. {date_label} {time_label} {record.subject}".strip())
        lines.append(f"   Calendar: {record.display_name}")
        if details.get("location"):
            lines.append(f"   Location: {details['location']}")
        lines.append("")
    if lines[-1] == "":
        lines.pop()
    return lines


def _brief_date_label(brief_date: str, window_days: int) -> str:
    dates = _date_window(brief_date, window_days)
    if window_days == 1:
        return brief_date
    return f"{dates[0]} through {dates[-1]}"


def _date_window(brief_date: str, window_days: int) -> tuple[str, ...]:
    start = date.fromisoformat(brief_date)
    return tuple(
        (start + timedelta(days=offset)).isoformat()
        for offset in range(window_days)
    )


def _event_date_label(details: dict[str, str]) -> str:
    start = details.get("start")
    if not start:
        return ""
    if "T" not in start:
        return start
    parsed_start = _parse_datetime(start)
    if parsed_start is None:
        return details.get("date", "")
    return parsed_start.astimezone(CENTRAL_TIME).date().isoformat()


def _time_range_label(details: dict[str, str]) -> str:
    start = details.get("start")
    end = details.get("end")
    if not start:
        return ""
    if "T" not in start:
        return "All day"
    start_time = _central_clock_time(start)
    if not end:
        return start_time
    return f"{start_time}-{_central_clock_time(end)}"


def _central_clock_time(value: str) -> str:
    if "T" not in value:
        return value
    parsed_value = _parse_datetime(value)
    if parsed_value is None:
        return value.split("T", maxsplit=1)[1][:5]
    return _ampm_time(parsed_value.astimezone(CENTRAL_TIME))


def _central_datetime_label(value: str | None) -> str:
    if not value:
        return "Unknown"
    parsed_value = _parse_datetime(value)
    if parsed_value is None:
        return value
    central_value = parsed_value.astimezone(CENTRAL_TIME)
    return f"{central_value.date().isoformat()} {_ampm_time(central_value)}"


def _parse_datetime(value: str) -> datetime | None:
    clean_value = value.strip()
    if not clean_value:
        return None
    if clean_value.endswith("Z"):
        clean_value = clean_value[:-1] + "+00:00"
    try:
        parsed_value = datetime.fromisoformat(clean_value)
    except ValueError:
        return None
    if parsed_value.tzinfo is None:
        return parsed_value.replace(tzinfo=CENTRAL_TIME)
    return parsed_value


def _ampm_time(value: datetime) -> str:
    return value.strftime("%I:%M %p").lstrip("0")


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
    calendar_window_days: int,
    inbox_attention_count: int,
    calendar_event_count: int,
    jira_ticket_count: int,
    open_task_count: int,
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
        f"Daily brief for {brief_date}: calendarWindowDays={calendar_window_days}, "
        f"inbox={inbox_attention_count}, "
        f"calendar={calendar_event_count}, jira={jira_ticket_count}, "
        f"tasks={open_task_count}, pending={pending_action_count}."
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
    calendar_window_days: int,
    generated_at: datetime,
    inbox_items: Sequence[SourceMemoryRecord],
    calendar_items: Sequence[SourceMemoryRecord],
    jira_items: Sequence[SourceMemoryRecord],
    open_tasks: Sequence[DelegatedTaskRecord],
    pending_actions: Sequence[PendingActionRecord],
) -> dict[str, Any]:
    return {
        "briefDate": brief_date,
        "calendarWindowDays": calendar_window_days,
        "generatedAt": generated_at.isoformat(timespec="seconds"),
        "sections": {
            "inbox": _manifest_items(inbox_items),
            "outlook": _manifest_items(inbox_items),
            "calendar": _manifest_items(calendar_items),
            "jira": _manifest_items(jira_items),
            "tasks": _manifest_tasks(open_tasks),
            "pendingApprovals": _manifest_pending_actions(pending_actions),
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


def _manifest_tasks(tasks: Sequence[DelegatedTaskRecord]) -> list[dict[str, Any]]:
    return [
        {
            "number": index,
            "taskId": task.task_id,
            "title": task.title,
            "status": task.status,
            "nextStep": task.next_step,
            "approvalRequired": task.approval_required,
        }
        for index, task in enumerate(tasks, 1)
    ]


def _manifest_pending_actions(
    actions: Sequence[PendingActionRecord],
) -> list[dict[str, Any]]:
    return [
        {
            "number": index,
            "actionId": action.action_id,
            "actionType": action.action_type,
            "approvalStatus": action.approval_status,
            "target": action.action_target,
            "itemId": action.item_id,
            "externalId": action.item_external_id,
            "sourceType": action.source_type,
            "sourceScope": action.source_scope_label,
            "itemType": action.item_type,
            "subject": action.item_subject,
            "senderOrOwner": action.item_sender_or_owner,
            "result": action.result,
            "createdAt": action.created_at,
        }
        for index, action in enumerate(actions, 1)
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
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Rolling calendar window size in days. Defaults to 7.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
