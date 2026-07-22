"""Generate and optionally send Clarity's daily brief email."""

from __future__ import annotations

import argparse
import html
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol, Sequence

from assistant.src.generate_daily_brief import (
    DEFAULT_DAILY_BRIEF_PATH,
    DailyBriefResult,
    generate_daily_brief,
)
from assistant.src.run_calendar_review import (
    build_google_calendar_read_transport_from_config,
    build_graph_calendar_read_transport_from_config,
    run_calendar_review,
)
from assistant.src.run_email_review import (
    build_gmail_read_transport_from_config,
    build_graph_read_transport_from_config,
    run_email_review,
)
from assistant.src.run_jira_report import (
    DEFAULT_MEMORY_PATH,
    DEFAULT_REPORT_PATH as DEFAULT_JIRA_REPORT_PATH,
    generate_local_jira_report,
)
from common.calendar import CalendarTransport
from common.email import EmailTransport
from common.configuration import find_workspace_root, load_workspace_config
from common.graph_email import (
    GraphTokenTransport,
    GraphTransport,
    build_graph_email_send_transport,
)
from common.memory import DuckDbMemoryStore


class DailyBriefSendTransport(Protocol):
    """Transport for sending a rendered daily brief."""

    def send_mail(
        self,
        *,
        sender: str,
        recipients: tuple[str, ...],
        subject: str,
        body_text: str,
        body_html: str | None = None,
    ) -> None:
        """Send the rendered brief."""


@dataclass(frozen=True)
class SendDailyBriefResult:
    """Safe result details for daily brief send planning/execution."""

    brief: DailyBriefResult
    sender: str
    recipients: tuple[str, ...]
    subject: str
    sent: bool
    html_path: Path


def send_daily_brief(
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    output_path: Path | str = DEFAULT_DAILY_BRIEF_PATH,
    brief_date: str | None = None,
    limit: int = 10,
    calendar_window_days: int = 7,
    refresh_email: bool = False,
    use_graph_email: bool = False,
    use_gmail: bool = False,
    graph_email_transport: EmailTransport | None = None,
    gmail_transport: EmailTransport | None = None,
    refresh_calendars: bool = False,
    use_graph_calendars: bool = False,
    use_google_calendars: bool = False,
    graph_calendar_transport: CalendarTransport | None = None,
    google_calendar_transport: CalendarTransport | None = None,
    refresh_jira: bool = False,
    jira_output_path: Path | str = DEFAULT_JIRA_REPORT_PATH,
    use_jira_bearer_auth: bool = False,
    execute: bool = False,
    send_transport: DailyBriefSendTransport | None = None,
) -> SendDailyBriefResult:
    """Generate and optionally send Clarity's daily brief email."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    config = load_workspace_config(workspace_root, include_process_env=False)
    settings = config.daily_brief_settings
    selected_date = brief_date or date.today().isoformat()
    if refresh_email:
        _refresh_email_sources(
            root=workspace_root,
            memory_path=memory_path,
            output_path=output_path,
            limit=limit,
            use_graph_email=use_graph_email,
            use_gmail=use_gmail,
            graph_email_transport=graph_email_transport,
            gmail_transport=gmail_transport,
        )
    if refresh_calendars:
        _refresh_calendar_window(
            root=workspace_root,
            memory_path=memory_path,
            output_path=output_path,
            brief_date=selected_date,
            window_days=calendar_window_days,
            limit=limit,
            use_graph_calendars=use_graph_calendars,
            use_google_calendars=use_google_calendars,
            graph_calendar_transport=graph_calendar_transport,
            google_calendar_transport=google_calendar_transport,
        )
    if refresh_jira:
        generate_local_jira_report(
            root=workspace_root,
            output_path=jira_output_path,
            use_live_jira=True,
            use_bearer_auth=use_jira_bearer_auth,
            memory_path=memory_path,
        )
    brief = generate_daily_brief(
        root=workspace_root,
        memory_path=memory_path,
        output_path=output_path,
        brief_date=selected_date,
        limit=limit,
        calendar_window_days=calendar_window_days,
    )
    subject = f"{settings.subject_prefix} - {brief.brief_date}"
    body_text = brief.output_path.read_text(encoding="utf-8")
    body_html = render_daily_brief_html(body_text)
    html_path = brief.output_path.with_suffix(".html")
    html_path.write_text(body_html, encoding="utf-8")
    if execute:
        if send_transport is None:
            raise RuntimeError("send_transport is required when execute=True.")
        send_transport.send_mail(
            sender=settings.sender,
            recipients=settings.recipients,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )
        _record_send_memory(
            memory_path=brief.memory_path,
            output_path=brief.output_path,
            sender=settings.sender,
            recipients=settings.recipients,
            subject=subject,
        )
    return SendDailyBriefResult(
        brief=brief,
        sender=settings.sender,
        recipients=settings.recipients,
        subject=subject,
        sent=execute,
        html_path=html_path,
    )


def build_graph_send_transport_from_config(
    *,
    root: Path | str | None = None,
    graph_transport: GraphTransport | None = None,
    token_transport: GraphTokenTransport | None = None,
    use_bearer_auth: bool = False,
) -> DailyBriefSendTransport:
    """Build a Graph send transport from local workspace configuration."""

    config = load_workspace_config(root)
    credentials = config.require_graph_credentials(use_bearer_auth=use_bearer_auth)
    return build_graph_email_send_transport(
        credentials,
        graph_transport=graph_transport,
        token_transport=token_transport,
        use_bearer_auth=use_bearer_auth,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Generate and optionally send Clarity's daily brief email."""

    args = _parse_args(argv)
    transport = (
        build_graph_send_transport_from_config(use_bearer_auth=args.graph_bearer)
        if args.graph and args.execute
        else None
    )
    graph_email_transport = (
        build_graph_read_transport_from_config(use_bearer_auth=args.graph_bearer)
        if args.refresh_email and args.graph_email
        else None
    )
    gmail_transport = (
        build_gmail_read_transport_from_config(use_bearer_auth=args.gmail_bearer)
        if args.refresh_email and args.gmail
        else None
    )
    graph_calendar_transport = (
        build_graph_calendar_read_transport_from_config(
            use_bearer_auth=args.graph_bearer
        )
        if args.refresh_calendars and args.graph_calendars
        else None
    )
    google_calendar_transport = (
        build_google_calendar_read_transport_from_config(
            use_bearer_auth=args.google_bearer
        )
        if args.refresh_calendars and args.google_calendars
        else None
    )
    result = send_daily_brief(
        memory_path=args.memory,
        output_path=args.output,
        brief_date=args.date,
        limit=args.limit,
        calendar_window_days=args.days,
        refresh_email=args.refresh_email,
        use_graph_email=args.graph_email,
        use_gmail=args.gmail,
        graph_email_transport=graph_email_transport,
        gmail_transport=gmail_transport,
        refresh_calendars=args.refresh_calendars,
        use_graph_calendars=args.graph_calendars,
        use_google_calendars=args.google_calendars,
        graph_calendar_transport=graph_calendar_transport,
        google_calendar_transport=google_calendar_transport,
        refresh_jira=args.refresh_jira,
        jira_output_path=args.jira_output,
        use_jira_bearer_auth=args.jira_bearer,
        execute=args.execute,
        send_transport=transport,
    )
    print("# Clarity Daily Brief Email")
    print()
    print(f"Brief: {result.brief.output_path}")
    print(f"HTML: {result.html_path}")
    print(f"Sender: {result.sender}")
    print(f"Recipients: {', '.join(result.recipients)}")
    print(f"Subject: {result.subject}")
    print(f"Sent: {'yes' if result.sent else 'no'}")
    if not result.sent:
        print()
        print("Dry run only. Add --graph --execute to send through Microsoft Graph.")


def _refresh_email_sources(
    *,
    root: Path,
    memory_path: Path | str,
    output_path: Path | str,
    limit: int,
    use_graph_email: bool,
    use_gmail: bool,
    graph_email_transport: EmailTransport | None,
    gmail_transport: EmailTransport | None,
) -> None:
    config = load_workspace_config(root, include_process_env=False)
    refreshed_count = 0
    for mailbox in config.email_settings.approved_mailboxes:
        if config.email_settings.access_mode_for(mailbox) not in ("read", "read_write"):
            continue
        if _is_gmail_mailbox(mailbox):
            if not use_gmail:
                continue
            transport = gmail_transport
            use_gmail_transport = True
        else:
            if not use_graph_email:
                continue
            transport = graph_email_transport
            use_gmail_transport = False
        try:
            run_email_review(
                root=root,
                mailbox=mailbox,
                limit=limit,
                memory_path=memory_path,
                brief_output_path=output_path,
                transport=transport,
                use_gmail=use_gmail_transport,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Email refresh failed for mailbox {mailbox}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        refreshed_count += 1
    if refreshed_count == 0:
        raise RuntimeError("No approved email mailboxes matched the selected refresh providers.")


def _refresh_calendar_window(
    *,
    root: Path,
    memory_path: Path | str,
    output_path: Path | str,
    brief_date: str,
    window_days: int,
    limit: int,
    use_graph_calendars: bool,
    use_google_calendars: bool,
    graph_calendar_transport: CalendarTransport | None,
    google_calendar_transport: CalendarTransport | None,
) -> None:
    config = load_workspace_config(root, include_process_env=False)
    for calendar_scope in config.calendar_settings.approved_calendars.values():
        if calendar_scope.provider == "graph":
            if not use_graph_calendars:
                continue
            transport = graph_calendar_transport
            use_graph = True
            use_google = False
        elif calendar_scope.provider == "google":
            if not use_google_calendars:
                continue
            transport = google_calendar_transport
            use_graph = False
            use_google = True
        else:
            continue
        for review_date in _date_window(brief_date, window_days):
            run_calendar_review(
                root=root,
                calendar=calendar_scope.label,
                review_date=review_date,
                limit=limit,
                memory_path=memory_path,
                brief_output_path=output_path,
                transport=transport,
                use_graph=use_graph,
                use_google=use_google,
            )


def _date_window(brief_date: str, window_days: int) -> tuple[str, ...]:
    start = date.fromisoformat(brief_date)
    return tuple(
        (start + timedelta(days=offset)).isoformat()
        for offset in range(window_days)
    )


def _is_gmail_mailbox(mailbox: str) -> bool:
    return mailbox.lower().endswith("@gmail.com")


def render_daily_brief_html(markdown_text: str) -> str:
    """Render Clarity's daily brief Markdown into a compact HTML email body."""

    renderer = _HtmlEmailRenderer()
    return renderer.render(markdown_text)


class _HtmlEmailRenderer:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.calendar_section_lines: list[str] = []
        self.in_section = False
        self.in_item = False
        self.in_metrics = False
        self.current_section_title = ""

    def render(self, markdown_text: str) -> str:
        self.lines = [
            "<!doctype html>",
            "<html>",
            "<head>",
            '<meta charset="utf-8">',
            "<style>",
            _EMAIL_CSS,
            "</style>",
            "</head>",
            "<body>",
            '<main class="brief">',
        ]
        for raw_line in markdown_text.splitlines():
            self._render_line(raw_line.rstrip())
        self._close_item()
        self._close_metrics()
        self._close_section()
        self.lines.extend(["</main>", "</body>", "</html>"])
        return "\n".join(self.lines) + "\n"

    def _render_line(self, line: str) -> None:
        if not line.strip():
            return
        if line.startswith("# "):
            self._close_item()
            self._close_metrics()
            self._close_section()
            self.lines.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
            return
        if line.startswith("## "):
            self._close_item()
            self._close_metrics()
            self._close_section()
            self.current_section_title = line[3:].strip()
            title = html.escape(self.current_section_title)
            self.lines.append('<section class="section">')
            self.lines.append(f"<h2>{title}</h2>")
            self.in_section = True
            return
        if line.startswith("### "):
            self._close_item()
            self._close_metrics()
            self.lines.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
            return
        if self._is_calendar_section():
            self.calendar_section_lines.append(line)
            return
        numbered = re.match(r"^(\d+)\.\s+(.+)$", line)
        if numbered:
            self._close_metrics()
            self._close_item()
            self.in_item = True
            self.lines.append('<article class="item">')
            self.lines.append('<div class="item-body">')
            self.lines.append(
                '<div class="item-title">'
                f'<span class="item-number">{html.escape(numbered.group(1))}.</span> '
                f"{html.escape(numbered.group(2).strip())}</div>"
            )
            return
        field = re.match(r"^\s{2,}([^:]+):\s*(.*)$", line)
        if field:
            self._render_field(field.group(1), field.group(2))
            return
        if line.startswith("- "):
            self._render_metric(line[2:])
            return
        self._close_metrics()
        self.lines.append(f"<p>{html.escape(line.strip())}</p>")

    def _render_metric(self, line: str) -> None:
        if not self.in_metrics:
            self.lines.append('<div class="metrics">')
            self.in_metrics = True
        label, separator, value = line.partition(":")
        if separator:
            self.lines.append(
                '<div class="metric"><span>'
                f"{html.escape(label.strip())}</span><strong>"
                f"{html.escape(value.strip())}</strong></div>"
            )
        else:
            self.lines.append(
                f'<div class="metric full">{html.escape(line.strip())}</div>'
            )

    def _render_field(self, label: str, value: str) -> None:
        if not self.in_item:
            self.lines.append('<article class="item loose"><div class="item-body">')
            self.in_item = True
        clean_label = html.escape(label.strip())
        clean_value = html.escape(value.strip())
        value_class = self._field_value_class(label, value)
        field_class = f"field {value_class}".strip()
        self.lines.append(
            f'<div class="{field_class}"><span>'
            f"{clean_label}: </span><strong>"
            f"{clean_value}</strong></div>"
        )

    def _close_item(self) -> None:
        if self.in_item:
            self.lines.append("</div></article>")
            self.in_item = False

    def _close_metrics(self) -> None:
        if self.in_metrics:
            self.lines.append("</div>")
            self.in_metrics = False

    def _close_section(self) -> None:
        if self.in_section:
            if self._is_calendar_section():
                self.lines.extend(
                    _calendar_table(
                        self.calendar_section_lines,
                        section_title=self.current_section_title,
                    )
                )
            self.lines.append("</section>")
            self.in_section = False
            self.current_section_title = ""
            self.calendar_section_lines = []

    def _field_value_class(self, label: str, value: str) -> str:
        clean_label = label.strip().lower()
        if clean_label == "action":
            return "mono"
        if clean_label != "calendar":
            return ""
        clean_value = value.strip().lower()
        if "family" in clean_value or "sexton-family" in clean_value:
            return "calendar-name calendar-family"
        if (
            "sendthisfile" in clean_value
            or "stf" in clean_value
            or "work calendar" in clean_value
        ):
            return "calendar-name calendar-sendthisfile"
        return "calendar-name"

    def _is_calendar_section(self) -> bool:
        return self.current_section_title.startswith("Calendar:")


def _calendar_table(lines: Sequence[str], *, section_title: str) -> list[str]:
    events = _parse_calendar_events(lines)
    days = _calendar_days(section_title, events)
    if not days:
        return ["<p>No calendar events found for this window.</p>"]

    by_date: dict[str, list[dict[str, str]]] = {day: [] for day in days}
    for event in events:
        by_date.setdefault(event["date"], []).append(event)

    output = [
        '<div class="calendar-legend">',
        '<span><i class="legend-swatch calendar-family"></i>Family</span>',
        '<span><i class="legend-swatch calendar-sendthisfile"></i>SendThisFile</span>',
        '<span><i class="legend-swatch calendar-other"></i>Other</span>',
        "</div>",
        '<table class="calendar-table" role="presentation">',
        "<thead>",
        "<tr>",
    ]
    for day in days:
        output.append(
            "<th>"
            f'<span class="calendar-day">{html.escape(_weekday_label(day))}</span>'
            f'<span class="calendar-day-date">{html.escape(_date_label(day))}</span>'
            "</th>"
        )
    output.extend(["</tr>", "</thead>", "<tbody>", "<tr>"])
    for day in days:
        output.append("<td>")
        day_events = by_date.get(day, [])
        if day_events:
            for event in day_events:
                output.extend(_calendar_event_block(event))
        else:
            output.append('<div class="calendar-empty">No events</div>')
        output.append("</td>")
    output.extend(["</tr>", "</tbody>", "</table>"])
    return output


def _parse_calendar_events(lines: Sequence[str]) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in lines:
        numbered = re.match(
            r"^\d+\.\s+(\d{4}-\d{2}-\d{2})\s+"
            r"((?:All day)|(?:\d{1,2}:\d{2}\s+[AP]M-\d{1,2}:\d{2}\s+[AP]M))\s+(.+)$",
            line,
        )
        if numbered:
            if current is not None:
                events.append(current)
            current = {
                "date": numbered.group(1),
                "time": numbered.group(2),
                "subject": numbered.group(3),
                "calendar": "",
                "location": "",
            }
            continue
        field = re.match(r"^\s{2,}([^:]+):\s*(.*)$", line)
        if field and current is not None:
            label = field.group(1).strip().lower()
            if label in ("calendar", "location"):
                current[label] = field.group(2).strip()
    if current is not None:
        events.append(current)
    return events


def _calendar_days(section_title: str, events: Sequence[dict[str, str]]) -> tuple[str, ...]:
    match = re.search(
        r"(\d{4}-\d{2}-\d{2})\s+through\s+(\d{4}-\d{2}-\d{2})",
        section_title,
    )
    if match:
        start = date.fromisoformat(match.group(1))
        end = date.fromisoformat(match.group(2))
        days: list[str] = []
        current = start
        while current <= end:
            days.append(current.isoformat())
            current += timedelta(days=1)
        return tuple(days)
    return tuple(dict.fromkeys(event["date"] for event in events))


def _calendar_event_block(event: dict[str, str]) -> list[str]:
    color_class = _calendar_color_class(event.get("calendar", ""))
    output = [f'<div class="calendar-block {color_class}">']
    output.append(f'<div class="calendar-block-time">{html.escape(event["time"])}</div>')
    output.append(
        f'<div class="calendar-block-title">{html.escape(event["subject"])}</div>'
    )
    if event.get("calendar"):
        output.append(
            f'<div class="calendar-block-source">{html.escape(event["calendar"])}</div>'
        )
    if event.get("location"):
        output.append(
            f'<div class="calendar-block-location">{html.escape(event["location"])}</div>'
        )
    output.append("</div>")
    return output


def _calendar_color_class(calendar_name: str) -> str:
    clean_name = calendar_name.lower()
    if "family" in clean_name or "sexton-family" in clean_name:
        return "calendar-family"
    if "sendthisfile" in clean_name or "stf" in clean_name or "work calendar" in clean_name:
        return "calendar-sendthisfile"
    return "calendar-other"


def _weekday_label(day: str) -> str:
    return date.fromisoformat(day).strftime("%a")


def _date_label(day: str) -> str:
    return date.fromisoformat(day).strftime("%Y-%m-%d")


def _record_send_memory(
    *,
    memory_path: Path,
    output_path: Path,
    sender: str,
    recipients: tuple[str, ...],
    subject: str,
) -> None:
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="send-daily-brief")
        store.record_generated_artifact(
            run_id=run.run_id,
            artifact_type="sent_daily_brief_source",
            path=output_path,
            summary="Daily brief source sent by email.",
        )
        result = (
            f"Sent daily brief from {sender} to {', '.join(recipients)} "
            f"with subject {subject}."
        )
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="send_daily_brief_email",
            approval_status="not_required",
            result=result,
        )
        store.finish_run(run.run_id, status="completed", summary=result)
    finally:
        store.close()


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate and optionally send Clarity's daily brief email."
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
    parser.add_argument(
        "--graph",
        action="store_true",
        help="Send through Microsoft Graph. Requires --execute.",
    )
    parser.add_argument(
        "--graph-bearer",
        action="store_true",
        help="Use GRAPH_ACCESS_TOKEN instead of app-only client credentials.",
    )
    parser.add_argument(
        "--refresh-email",
        action="store_true",
        help="Refresh approved inbox metadata before generating the brief.",
    )
    parser.add_argument(
        "--graph-email",
        action="store_true",
        help="Refresh approved non-Gmail inboxes through Microsoft Graph.",
    )
    parser.add_argument(
        "--gmail",
        action="store_true",
        help="Refresh approved gmail.com inboxes through Gmail.",
    )
    parser.add_argument(
        "--gmail-bearer",
        action="store_true",
        help="Use GOOGLE_ACCESS_TOKEN for Gmail refresh.",
    )
    parser.add_argument(
        "--refresh-calendars",
        action="store_true",
        help="Refresh configured calendars for the rolling window before generating.",
    )
    parser.add_argument(
        "--graph-calendars",
        action="store_true",
        help="Refresh approved Microsoft Graph calendars.",
    )
    parser.add_argument(
        "--google-calendars",
        action="store_true",
        help="Refresh approved Google calendars.",
    )
    parser.add_argument(
        "--google-bearer",
        action="store_true",
        help="Use GOOGLE_ACCESS_TOKEN for Google Calendar refresh.",
    )
    parser.add_argument(
        "--refresh-jira",
        action="store_true",
        help="Refresh the live Jira report before generating the brief.",
    )
    parser.add_argument(
        "--jira-output",
        default=str(DEFAULT_JIRA_REPORT_PATH),
        help="Jira report output path used when --refresh-jira is supplied.",
    )
    parser.add_argument(
        "--jira-bearer",
        action="store_true",
        help="Use JIRA_ACCESS_TOKEN Bearer auth for Jira refresh.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Send the generated daily brief email.",
    )
    args = parser.parse_args(argv)
    if args.graph and not args.execute:
        parser.error("--graph requires --execute.")
    if args.graph_bearer and not (args.graph or args.graph_calendars or args.graph_email):
        parser.error("--graph-bearer requires --graph, --graph-email, or --graph-calendars.")
    if args.execute and not args.graph:
        parser.error("--execute requires --graph.")
    if (args.graph_email or args.gmail) and not args.refresh_email:
        parser.error("--graph-email and --gmail require --refresh-email.")
    if args.refresh_email and not (args.graph_email or args.gmail):
        parser.error("--refresh-email requires --graph-email or --gmail.")
    if args.gmail_bearer and not args.gmail:
        parser.error("--gmail-bearer requires --gmail.")
    if (args.graph_calendars or args.google_calendars) and not args.refresh_calendars:
        parser.error("--graph-calendars and --google-calendars require --refresh-calendars.")
    if args.refresh_calendars and not (args.graph_calendars or args.google_calendars):
        parser.error("--refresh-calendars requires at least one calendar provider flag.")
    if args.google_bearer and not args.google_calendars:
        parser.error("--google-bearer requires --google-calendars.")
    if args.jira_bearer and not args.refresh_jira:
        parser.error("--jira-bearer requires --refresh-jira.")
    return args


_EMAIL_CSS = """
body {
  margin: 0;
  background: #f4f6f8;
  color: #1f2933;
  font-family: Arial, Helvetica, sans-serif;
  line-height: 1.45;
}
.brief {
  max-width: 860px;
  margin: 0 auto;
  padding: 24px;
}
h1 {
  margin: 0 0 16px;
  color: #102a43;
  font-size: 28px;
}
.section {
  margin: 16px 0;
  padding: 18px;
  background: #ffffff;
  border: 1px solid #d9e2ec;
  border-radius: 8px;
}
h2 {
  margin: 0 0 12px;
  color: #102a43;
  font-size: 19px;
}
h3 {
  margin: 18px 0 8px;
  color: #334e68;
  font-size: 15px;
}
p {
  margin: 8px 0;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 10px;
}
.metric {
  padding: 10px 12px;
  background: #f8fafc;
  border: 1px solid #e6edf3;
  border-radius: 6px;
}
.metric span,
.field span {
  color: #627d98;
  font-size: 14px;
  font-weight: 700;
}
.metric strong {
  display: block;
  margin-top: 4px;
  color: #102a43;
  font-size: 14px;
  font-weight: 700;
}
.item {
  margin: 10px 0;
  padding: 12px;
  background: #fbfdff;
  border: 1px solid #e6edf3;
  border-radius: 6px;
}
.item-number {
  color: #102a43;
  font-weight: 700;
}
.item-title {
  margin-bottom: 8px;
  color: #102a43;
  font-size: 15px;
  font-weight: 700;
}
.field {
  margin-top: 6px;
}
.field strong {
  color: #243b53;
  font-size: 14px;
  font-weight: 400;
}
.mono {
  font-family: Consolas, Monaco, monospace;
  word-break: break-all;
}
.mono strong {
  font-family: Consolas, Monaco, monospace;
}
.calendar-table {
  width: 100%;
  table-layout: fixed;
  border-collapse: separate;
  border-spacing: 6px;
}
.calendar-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 10px;
  color: #334e68;
  font-size: 12px;
  font-weight: 700;
}
.calendar-legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.legend-swatch {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 3px;
  border: 1px solid #d9e2ec;
}
.calendar-table th {
  padding: 8px 6px;
  background: #102a43;
  color: #ffffff;
  border-radius: 6px;
  text-align: left;
  vertical-align: top;
}
.calendar-day {
  display: block;
  font-size: 15px;
  font-weight: 700;
}
.calendar-day-date {
  display: block;
  margin-top: 2px;
  color: #d9e2ec;
  font-size: 11px;
  font-weight: 400;
}
.calendar-table td {
  padding: 0;
  vertical-align: top;
}
.calendar-block {
  margin-bottom: 6px;
  padding: 8px;
  border-radius: 6px;
  border: 1px solid #d9e2ec;
}
.calendar-block-time {
  margin-bottom: 3px;
  font-size: 12px;
  font-weight: 700;
}
.calendar-block-title {
  color: #102a43;
  font-size: 13px;
  font-weight: 700;
}
.calendar-block-source,
.calendar-block-location {
  margin-top: 3px;
  font-size: 11px;
}
.calendar-family {
  color: #7f1d1d;
  background: #fee2e2;
  border-color: #fecaca;
}
.calendar-sendthisfile {
  color: #1e3a8a;
  background: #dbeafe;
  border-color: #bfdbfe;
}
.calendar-other {
  color: #334e68;
  background: #eef2f7;
  border-color: #d9e2ec;
}
.calendar-empty {
  padding: 8px;
  color: #829ab1;
  font-size: 12px;
}
""".strip()


if __name__ == "__main__":
    main()
