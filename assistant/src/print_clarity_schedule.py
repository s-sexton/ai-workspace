"""Print local Windows scheduling commands for Clarity."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Sequence

from common.configuration import find_workspace_root


DEFAULT_TASK_NAME = "Clarity Email Cycle"
DEFAULT_TASK_TIME = "07:30"
DEFAULT_TASK_LOG_PATH = "logs/clarity-cycle.log"
WORKFLOW_CYCLE = "cycle"
WORKFLOW_DAILY_BRIEF_SEND = "daily-brief-send"
WORKFLOW_DAILY_BRIEF_REPLY_POLL = "daily-brief-reply-poll"
WORKFLOWS = (
    WORKFLOW_CYCLE,
    WORKFLOW_DAILY_BRIEF_SEND,
    WORKFLOW_DAILY_BRIEF_REPLY_POLL,
)


def build_windows_task_scheduler_script(
    *,
    root: Path | str | None = None,
    workflow: str = WORKFLOW_CYCLE,
    task_name: str = DEFAULT_TASK_NAME,
    at: str = DEFAULT_TASK_TIME,
    mailbox: str | None = None,
    use_graph: bool = False,
    use_graph_bearer: bool = False,
    refresh_email: bool = False,
    use_gmail: bool = False,
    use_gmail_bearer: bool = False,
    use_sample_graph: bool = False,
    refresh_calendar: bool = False,
    calendar: str | None = None,
    calendar_date: str | None = None,
    use_graph_calendar: bool = False,
    use_google_calendar: bool = False,
    use_google_bearer: bool = False,
    memory_path: Path | str | None = None,
    brief_path: Path | str | None = None,
    daily_brief_date: str | None = None,
    daily_brief_limit: int | None = None,
    daily_brief_days: int | None = None,
    refresh_jira: bool = False,
    jira_bearer: bool = False,
    jira_report_path: Path | str | None = None,
    manifest_path: Path | str | None = None,
    cycle_report_path: Path | str | None = None,
    log_path: Path | str | None = DEFAULT_TASK_LOG_PATH,
    execute: bool = False,
) -> str:
    """Return PowerShell commands that register one local scheduled task."""

    if workflow not in WORKFLOWS:
        raise ValueError(f"workflow must be one of: {', '.join(WORKFLOWS)}.")
    if use_graph_bearer and not (use_graph or use_graph_calendar):
        raise ValueError("use_graph_bearer requires use_graph or use_graph_calendar.")
    if use_google_bearer and not use_google_calendar:
        raise ValueError("use_google_bearer requires use_google_calendar.")
    if use_graph and use_sample_graph:
        raise ValueError("use_graph and use_sample_graph are mutually exclusive.")
    if use_gmail and use_sample_graph:
        raise ValueError("use_gmail and use_sample_graph are mutually exclusive.")
    if use_gmail_bearer and not use_gmail:
        raise ValueError("use_gmail_bearer requires use_gmail.")
    if refresh_email and not (use_graph or use_gmail):
        raise ValueError("refresh_email requires use_graph or use_gmail.")
    if jira_bearer and not refresh_jira:
        raise ValueError("jira_bearer requires refresh_jira.")
    if (
        workflow == WORKFLOW_CYCLE
        and use_graph_calendar
        and use_google_calendar
    ):
        raise ValueError(
            "use_graph_calendar and use_google_calendar are mutually exclusive for cycle."
        )
    if calendar and not refresh_calendar:
        raise ValueError("calendar requires refresh_calendar.")
    if calendar_date and not refresh_calendar:
        raise ValueError("calendar_date requires refresh_calendar.")
    if use_graph_calendar and not refresh_calendar:
        raise ValueError("use_graph_calendar requires refresh_calendar.")
    if use_google_calendar and not refresh_calendar:
        raise ValueError("use_google_calendar requires refresh_calendar.")
    if not _is_valid_time(at):
        raise ValueError("at must be in HH:mm 24-hour format.")
    if workflow == WORKFLOW_DAILY_BRIEF_SEND and (
        use_sample_graph
        or calendar
        or calendar_date
        or cycle_report_path
    ):
        raise ValueError("cycle-only options require workflow='cycle'.")
    if (
        workflow == WORKFLOW_DAILY_BRIEF_SEND
        and (use_gmail or use_gmail_bearer)
        and not refresh_email
    ):
        raise ValueError("Gmail daily brief refresh requires refresh_email.")
    if workflow == WORKFLOW_DAILY_BRIEF_REPLY_POLL and (
        use_sample_graph
        or use_gmail
        or use_gmail_bearer
        or refresh_email
        or refresh_calendar
        or calendar
        or calendar_date
        or use_graph_calendar
        or use_google_calendar
        or use_google_bearer
        or refresh_jira
        or jira_bearer
        or jira_report_path
        or cycle_report_path
    ):
        raise ValueError("cycle-only options require workflow='cycle'.")
    if refresh_calendar and not (use_graph_calendar or use_google_calendar):
        raise ValueError("refresh_calendar requires a calendar provider.")
    if workflow == WORKFLOW_DAILY_BRIEF_SEND and execute != use_graph:
        raise ValueError("daily-brief-send requires use_graph and execute together.")
    if workflow == WORKFLOW_DAILY_BRIEF_REPLY_POLL and not use_graph:
        raise ValueError("daily-brief-reply-poll requires use_graph.")

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    workflow_command = _workflow_command(
        workflow=workflow,
        mailbox=mailbox,
        use_graph=use_graph,
        use_graph_bearer=use_graph_bearer,
        refresh_email=refresh_email,
        use_gmail=use_gmail,
        use_gmail_bearer=use_gmail_bearer,
        use_sample_graph=use_sample_graph,
        refresh_calendar=refresh_calendar,
        calendar=calendar,
        calendar_date=calendar_date,
        use_graph_calendar=use_graph_calendar,
        use_google_calendar=use_google_calendar,
        use_google_bearer=use_google_bearer,
        memory_path=memory_path,
        brief_path=brief_path,
        daily_brief_date=daily_brief_date,
        daily_brief_limit=daily_brief_limit,
        daily_brief_days=daily_brief_days,
        refresh_jira=refresh_jira,
        jira_bearer=jira_bearer,
        jira_report_path=jira_report_path,
        manifest_path=manifest_path,
        cycle_report_path=cycle_report_path,
        execute=execute,
    )
    scheduled_command = (
        "Set-Location -LiteralPath "
        + _ps_single_quote(str(workspace_root))
        + "; "
    )
    if log_path is not None:
        log_path_text = str(log_path)
        scheduled_command += (
            "$ClarityLog = "
            + _ps_single_quote(log_path_text)
            + "; "
            + "New-Item -ItemType Directory -Force -Path "
            + "(Split-Path -Parent $ClarityLog) | Out-Null; "
            + workflow_command
            + " *>> "
            + _ps_single_quote(log_path_text)
        )
    else:
        scheduled_command += workflow_command
    scheduled_argument = (
        "-NoProfile -ExecutionPolicy Bypass -Command "
        + _ps_double_quote(scheduled_command)
    )
    lines = [
        "$Action = New-ScheduledTaskAction "
        + "-Execute "
        + _ps_double_quote("powershell.exe")
        + " -Argument "
        + _ps_double_quote(scheduled_argument),
        "$Trigger = New-ScheduledTaskTrigger -Daily -At "
        + _ps_double_quote(at),
        "Register-ScheduledTask "
        + "-TaskName "
        + _ps_double_quote(task_name)
        + " -Action $Action -Trigger $Trigger "
        + "-Description "
        + _ps_double_quote(_workflow_description(workflow))
        + " -Force",
    ]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> None:
    """Print Windows Task Scheduler registration commands."""

    args = _parse_args(argv)
    print(
        build_windows_task_scheduler_script(
            workflow=args.workflow,
            task_name=args.task_name,
            at=args.at,
            mailbox=args.mailbox,
            use_graph=args.graph,
            use_graph_bearer=args.graph_bearer,
            refresh_email=args.refresh_email,
            use_gmail=args.gmail,
            use_gmail_bearer=args.gmail_bearer,
            use_sample_graph=args.sample_graph,
            refresh_calendar=args.refresh_calendar,
            calendar=args.calendar,
            calendar_date=args.calendar_date,
            use_graph_calendar=args.graph_calendar,
            use_google_calendar=args.google_calendar,
            use_google_bearer=args.google_bearer,
            memory_path=args.memory,
            brief_path=args.brief,
            daily_brief_date=args.date,
            daily_brief_limit=args.limit,
            daily_brief_days=args.days,
            refresh_jira=args.refresh_jira,
            jira_bearer=args.jira_bearer,
            jira_report_path=args.jira_report,
            manifest_path=args.manifest,
            cycle_report_path=args.cycle_report,
            log_path=args.log,
            execute=args.execute,
        ),
        end="",
    )


def _workflow_command(
    *,
    workflow: str,
    mailbox: str | None,
    use_graph: bool,
    use_graph_bearer: bool,
    refresh_email: bool,
    use_gmail: bool,
    use_gmail_bearer: bool,
    use_sample_graph: bool,
    refresh_calendar: bool,
    calendar: str | None,
    calendar_date: str | None,
    use_graph_calendar: bool,
    use_google_calendar: bool,
    use_google_bearer: bool,
    memory_path: Path | str | None,
    brief_path: Path | str | None,
    daily_brief_date: str | None,
    daily_brief_limit: int | None,
    daily_brief_days: int | None,
    refresh_jira: bool,
    jira_bearer: bool,
    jira_report_path: Path | str | None,
    manifest_path: Path | str | None,
    cycle_report_path: Path | str | None,
    execute: bool,
) -> str:
    if workflow == WORKFLOW_CYCLE:
        return _cycle_command(
            mailbox=mailbox,
            use_graph=use_graph,
            use_graph_bearer=use_graph_bearer,
            use_gmail=use_gmail,
            use_gmail_bearer=use_gmail_bearer,
            use_sample_graph=use_sample_graph,
            refresh_calendar=refresh_calendar,
            calendar=calendar,
            calendar_date=calendar_date,
            use_graph_calendar=use_graph_calendar,
            use_google_calendar=use_google_calendar,
            use_google_bearer=use_google_bearer,
            memory_path=memory_path,
            brief_path=brief_path,
            cycle_report_path=cycle_report_path,
        )
    if workflow == WORKFLOW_DAILY_BRIEF_SEND:
        return _daily_brief_send_command(
            use_graph=use_graph,
            use_graph_bearer=use_graph_bearer,
            refresh_email=refresh_email,
            use_gmail=use_gmail,
            use_gmail_bearer=use_gmail_bearer,
            refresh_calendar=refresh_calendar,
            use_graph_calendar=use_graph_calendar,
            use_google_calendar=use_google_calendar,
            use_google_bearer=use_google_bearer,
            memory_path=memory_path,
            brief_path=brief_path,
            daily_brief_date=daily_brief_date,
            daily_brief_limit=daily_brief_limit,
            daily_brief_days=daily_brief_days,
            refresh_jira=refresh_jira,
            jira_bearer=jira_bearer,
            jira_report_path=jira_report_path,
            execute=execute,
        )
    return _daily_brief_reply_poll_command(
        mailbox=mailbox,
        use_graph_bearer=use_graph_bearer,
        memory_path=memory_path,
        manifest_path=manifest_path,
        daily_brief_limit=daily_brief_limit,
        execute=execute,
    )


def _cycle_command(
    *,
    mailbox: str | None,
    use_graph: bool,
    use_graph_bearer: bool,
    use_gmail: bool,
    use_gmail_bearer: bool,
    use_sample_graph: bool,
    refresh_calendar: bool,
    calendar: str | None,
    calendar_date: str | None,
    use_graph_calendar: bool,
    use_google_calendar: bool,
    use_google_bearer: bool,
    memory_path: Path | str | None,
    brief_path: Path | str | None,
    cycle_report_path: Path | str | None,
) -> str:
    parts = ["python", "-m", "assistant.src.run_clarity_cycle"]
    if mailbox:
        parts.extend(("--mailbox", _ps_single_quote(mailbox)))
    if use_graph:
        parts.append("--graph")
    if use_graph_bearer:
        parts.append("--graph-bearer")
    if use_gmail:
        parts.append("--gmail")
    if use_gmail_bearer:
        parts.append("--gmail-bearer")
    if use_sample_graph:
        parts.append("--sample-graph")
    if refresh_calendar:
        parts.append("--refresh-calendar")
    if calendar:
        parts.extend(("--calendar", _ps_single_quote(calendar)))
    if calendar_date:
        parts.extend(("--calendar-date", _ps_single_quote(calendar_date)))
    if use_graph_calendar:
        parts.append("--graph-calendar")
    if use_google_calendar:
        parts.append("--google-calendar")
    if use_google_bearer:
        parts.append("--google-bearer")
    if memory_path is not None:
        parts.extend(("--memory", _ps_single_quote(str(memory_path))))
    if brief_path is not None:
        parts.extend(("--brief", _ps_single_quote(str(brief_path))))
    if cycle_report_path is not None:
        parts.extend(("--cycle-report", _ps_single_quote(str(cycle_report_path))))
    return " ".join(parts)


def _daily_brief_send_command(
    *,
    use_graph: bool,
    use_graph_bearer: bool,
    refresh_email: bool,
    use_gmail: bool,
    use_gmail_bearer: bool,
    refresh_calendar: bool,
    use_graph_calendar: bool,
    use_google_calendar: bool,
    use_google_bearer: bool,
    memory_path: Path | str | None,
    brief_path: Path | str | None,
    daily_brief_date: str | None,
    daily_brief_limit: int | None,
    daily_brief_days: int | None,
    refresh_jira: bool,
    jira_bearer: bool,
    jira_report_path: Path | str | None,
    execute: bool,
) -> str:
    parts = ["python", "-m", "assistant.src.send_daily_brief"]
    if memory_path is not None:
        parts.extend(("--memory", _ps_single_quote(str(memory_path))))
    if brief_path is not None:
        parts.extend(("--output", _ps_single_quote(str(brief_path))))
    if daily_brief_date is not None:
        parts.extend(("--date", _ps_single_quote(daily_brief_date)))
    if daily_brief_limit is not None:
        parts.extend(("--limit", str(daily_brief_limit)))
    if daily_brief_days is not None:
        parts.extend(("--days", str(daily_brief_days)))
    if refresh_email:
        parts.append("--refresh-email")
        if use_graph:
            parts.append("--graph-email")
    if use_gmail:
        parts.append("--gmail")
    if use_gmail_bearer:
        parts.append("--gmail-bearer")
    if refresh_calendar:
        parts.append("--refresh-calendars")
    if use_graph_calendar:
        parts.append("--graph-calendars")
    if use_google_calendar:
        parts.append("--google-calendars")
    if use_google_bearer:
        parts.append("--google-bearer")
    if refresh_jira:
        parts.append("--refresh-jira")
    if jira_report_path is not None:
        parts.extend(("--jira-output", _ps_single_quote(str(jira_report_path))))
    if jira_bearer:
        parts.append("--jira-bearer")
    if use_graph:
        parts.append("--graph")
    if use_graph_bearer:
        parts.append("--graph-bearer")
    if execute:
        parts.append("--execute")
    return " ".join(parts)


def _daily_brief_reply_poll_command(
    *,
    mailbox: str | None,
    use_graph_bearer: bool,
    memory_path: Path | str | None,
    manifest_path: Path | str | None,
    daily_brief_limit: int | None,
    execute: bool,
) -> str:
    parts = ["python", "-m", "assistant.src.poll_daily_brief_replies", "--graph"]
    if use_graph_bearer:
        parts.append("--graph-bearer")
    if mailbox:
        parts.extend(("--mailbox", _ps_single_quote(mailbox)))
    if memory_path is not None:
        parts.extend(("--memory", _ps_single_quote(str(memory_path))))
    if manifest_path is not None:
        parts.extend(("--manifest", _ps_single_quote(str(manifest_path))))
    if daily_brief_limit is not None:
        parts.extend(("--limit", str(daily_brief_limit)))
    if execute:
        parts.append("--execute")
    return " ".join(parts)


def _workflow_description(workflow: str) -> str:
    if workflow == WORKFLOW_DAILY_BRIEF_SEND:
        return "Generate and optionally send Clarity's daily brief email."
    if workflow == WORKFLOW_DAILY_BRIEF_REPLY_POLL:
        return "Poll Clarity's mailbox for authenticated daily brief replies."
    return "Run one local Clarity refresh cycle."


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print PowerShell commands for scheduling Clarity locally."
    )
    parser.add_argument(
        "--workflow",
        choices=WORKFLOWS,
        default=WORKFLOW_CYCLE,
        help="Clarity workflow to schedule.",
    )
    parser.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    parser.add_argument(
        "--at",
        default=DEFAULT_TASK_TIME,
        help="Daily start time in HH:mm 24-hour format.",
    )
    parser.add_argument(
        "--mailbox",
        default=None,
        help="Approved mailbox to refresh. Defaults to the configured mailbox.",
    )
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--sample-graph",
        action="store_true",
        help="Schedule the local Graph-shaped sample cycle; no network calls.",
    )
    source_group.add_argument(
        "--graph",
        action="store_true",
        help="Schedule live Microsoft Graph metadata reads.",
    )
    parser.add_argument(
        "--graph-bearer",
        action="store_true",
        help="Use GRAPH_ACCESS_TOKEN instead of app-only client credentials.",
    )
    parser.add_argument(
        "--refresh-email",
        action="store_true",
        help="Refresh approved inbox metadata before daily brief generation.",
    )
    parser.add_argument(
        "--gmail",
        action="store_true",
        help="Include Gmail inbox refresh for gmail.com approved mailboxes.",
    )
    parser.add_argument(
        "--gmail-bearer",
        action="store_true",
        help="Use GOOGLE_ACCESS_TOKEN for Gmail inbox refresh.",
    )
    parser.add_argument(
        "--refresh-calendar",
        action="store_true",
        help="Also schedule approved read-only calendar metadata refresh.",
    )
    parser.add_argument(
        "--calendar",
        default=None,
        help="Approved calendar label to refresh.",
    )
    parser.add_argument(
        "--calendar-date",
        default=None,
        help="Calendar date to refresh in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--graph-calendar",
        action="store_true",
        help="Schedule approved Microsoft Graph calendar metadata reads.",
    )
    parser.add_argument(
        "--google-calendar",
        action="store_true",
        help="Schedule approved Google Calendar metadata reads.",
    )
    parser.add_argument(
        "--google-bearer",
        action="store_true",
        help="Use GOOGLE_ACCESS_TOKEN instead of refresh-token credentials.",
    )
    parser.add_argument("--memory", default=None)
    parser.add_argument("--brief", default=None)
    parser.add_argument(
        "--date",
        default=None,
        help="Daily brief date in YYYY-MM-DD format. Defaults to command runtime date.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Daily brief item limit or reply poll limit.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Daily brief rolling calendar window in days.",
    )
    parser.add_argument(
        "--refresh-jira",
        action="store_true",
        help="Refresh live Jira report before daily brief generation.",
    )
    parser.add_argument(
        "--jira-bearer",
        action="store_true",
        help="Use JIRA_ACCESS_TOKEN Bearer auth for Jira refresh.",
    )
    parser.add_argument(
        "--jira-report",
        default=None,
        help="Jira report path used by the daily brief refresh phase.",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Daily brief manifest path for reply polling.",
    )
    parser.add_argument("--cycle-report", default="reports/clarity-cycle.md")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Include the workflow's explicit execution flag where supported.",
    )
    parser.add_argument(
        "--log",
        default=str(DEFAULT_TASK_LOG_PATH),
        help="Append scheduled task console output to this local log path.",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Do not add scheduled task output redirection.",
    )
    args = parser.parse_args(argv)
    if args.graph_bearer and not (args.graph or args.graph_calendar):
        parser.error("--graph-bearer requires --graph or --graph-calendar.")
    if args.google_bearer and not args.google_calendar:
        parser.error("--google-bearer requires --google-calendar.")
    if args.jira_bearer and not args.refresh_jira:
        parser.error("--jira-bearer requires --refresh-jira.")
    if args.refresh_email and not (args.graph or args.gmail):
        parser.error("--refresh-email requires --graph or --gmail.")
    if args.calendar and not args.refresh_calendar:
        parser.error("--calendar requires --refresh-calendar.")
    if args.calendar_date and not args.refresh_calendar:
        parser.error("--calendar-date requires --refresh-calendar.")
    if args.graph_calendar and not args.refresh_calendar:
        parser.error("--graph-calendar requires --refresh-calendar.")
    if args.google_calendar and not args.refresh_calendar:
        parser.error("--google-calendar requires --refresh-calendar.")
    if not _is_valid_time(args.at):
        parser.error("--at must be in HH:mm 24-hour format.")
    if args.workflow == WORKFLOW_CYCLE and args.graph_calendar and args.google_calendar:
        parser.error(
            "--graph-calendar and --google-calendar are mutually exclusive for --workflow cycle."
        )
    if args.workflow == WORKFLOW_DAILY_BRIEF_SEND and (
        args.sample_graph or args.calendar or args.calendar_date
    ):
        parser.error("cycle-only options require --workflow cycle.")
    if (
        args.workflow == WORKFLOW_DAILY_BRIEF_SEND
        and (args.gmail or args.gmail_bearer)
        and not args.refresh_email
    ):
        parser.error("--gmail for daily-brief-send requires --refresh-email.")
    if args.workflow == WORKFLOW_DAILY_BRIEF_REPLY_POLL and (
        args.sample_graph
        or args.refresh_email
        or args.gmail
        or args.gmail_bearer
        or args.refresh_calendar
        or args.calendar
        or args.calendar_date
        or args.graph_calendar
        or args.google_calendar
        or args.google_bearer
        or args.refresh_jira
        or args.jira_bearer
        or args.jira_report
    ):
        parser.error("cycle-only options require --workflow cycle.")
    if args.refresh_calendar and not (args.graph_calendar or args.google_calendar):
        parser.error("--refresh-calendar requires --graph-calendar or --google-calendar.")
    if args.workflow == WORKFLOW_DAILY_BRIEF_SEND and args.execute != args.graph:
        parser.error("--workflow daily-brief-send requires --graph and --execute together.")
    if args.workflow == WORKFLOW_DAILY_BRIEF_REPLY_POLL and not args.graph:
        parser.error("--workflow daily-brief-reply-poll requires --graph.")
    if args.workflow == WORKFLOW_CYCLE:
        args.date = None
        args.limit = None
        args.manifest = None
    else:
        args.cycle_report = None
    if args.no_log:
        args.log = None
    return args


def _is_valid_time(value: str) -> bool:
    if not re.fullmatch(r"\d{2}:\d{2}", value):
        return False
    hour, minute = (int(part) for part in value.split(":", 1))
    return 0 <= hour <= 23 and 0 <= minute <= 59


def _ps_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _ps_double_quote(value: str) -> str:
    return '"' + value.replace("`", "``").replace('"', '`"') + '"'


if __name__ == "__main__":
    main()
