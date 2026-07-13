"""Scheduled-friendly Clarity refresh workflow."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from assistant.src.ask_memory import answer_memory_question
from assistant.src.run_calendar_review import (
    build_google_calendar_read_transport_from_config,
    build_graph_calendar_read_transport_from_config,
    run_calendar_review,
)
from assistant.src.run_email_review import (
    build_graph_read_transport_from_config,
    run_email_review,
)
from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.calendar import CalendarTransport
from common.configuration import find_workspace_root
from common.email import EmailTransport
from common.memory import DuckDbMemoryStore


DEFAULT_CYCLE_REPORT_PATH = Path("reports") / "clarity-cycle.md"


@dataclass(frozen=True)
class ClarityCycleResult:
    """Safe result details for a Clarity cycle."""

    memory_path: Path
    brief_path: Path
    mailbox: str
    message_count: int
    review_count: int
    noise_count: int
    trash_count: int
    proposed_action_count: int
    calendar: str | None
    calendar_event_count: int
    calendar_review_date: str | None
    cycle_report_path: Path
    focus_answer: str
    review_answer: str
    pending_answer: str


def run_clarity_cycle(
    *,
    root: Path | str | None = None,
    mailbox: str | None = None,
    limit: int = 25,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    brief_path: Path | str | None = None,
    cycle_report_path: Path | str = DEFAULT_CYCLE_REPORT_PATH,
    transport: EmailTransport | None = None,
    calendar_transport: CalendarTransport | None = None,
    use_sample_graph: bool = False,
    refresh_calendar: bool = False,
    calendar: str | None = None,
    calendar_date: str | None = None,
    use_graph_calendar: bool = False,
    use_google_calendar: bool = False,
) -> ClarityCycleResult:
    """Refresh approved memory and return the key local Clarity answers."""

    review_result = run_email_review(
        root=root,
        mailbox=mailbox or "",
        limit=limit,
        memory_path=memory_path,
        brief_output_path=brief_path,
        transport=transport,
        use_sample_graph=use_sample_graph,
    )
    calendar_result = None
    if refresh_calendar:
        calendar_result = run_calendar_review(
            root=root,
            calendar=calendar or "",
            review_date=calendar_date,
            limit=limit,
            memory_path=review_result.memory_path,
            brief_output_path=brief_path,
            transport=calendar_transport,
            use_graph=use_graph_calendar,
            use_google=use_google_calendar,
        )
    review_answer = answer_memory_question(
        "review-items",
        root=root,
        memory_path=review_result.memory_path,
        limit=limit,
    )
    pending_answer = answer_memory_question(
        "pending-actions",
        root=root,
        memory_path=review_result.memory_path,
        limit=limit,
    )
    focus_answer = answer_memory_question(
        "command-center",
        root=root,
        memory_path=review_result.memory_path,
        limit=limit,
    )
    resolved_cycle_report_path = _write_cycle_report(
        root=root,
        output_path=cycle_report_path,
        mailbox=review_result.mailbox,
        message_count=review_result.message_count,
        review_count=review_result.review_count,
        noise_count=review_result.noise_count,
        trash_count=review_result.trash_count,
        proposed_action_count=review_result.proposed_action_count,
        calendar=calendar_result.calendar if calendar_result else None,
        calendar_event_count=calendar_result.event_count if calendar_result else 0,
        calendar_review_date=calendar_result.review_date if calendar_result else None,
        brief_path=review_result.brief_path,
        focus_answer=focus_answer,
        review_answer=review_answer,
        pending_answer=pending_answer,
    )
    _record_cycle_memory(
        memory_path=review_result.memory_path,
        cycle_report_path=resolved_cycle_report_path,
        mailbox=review_result.mailbox,
        message_count=review_result.message_count,
        review_count=review_result.review_count,
        noise_count=review_result.noise_count,
        trash_count=review_result.trash_count,
        proposed_action_count=review_result.proposed_action_count,
        calendar=calendar_result.calendar if calendar_result else None,
        calendar_event_count=calendar_result.event_count if calendar_result else 0,
        calendar_review_date=calendar_result.review_date if calendar_result else None,
    )
    return ClarityCycleResult(
        memory_path=review_result.memory_path,
        brief_path=review_result.brief_path,
        mailbox=review_result.mailbox,
        message_count=review_result.message_count,
        review_count=review_result.review_count,
        noise_count=review_result.noise_count,
        trash_count=review_result.trash_count,
        proposed_action_count=review_result.proposed_action_count,
        calendar=calendar_result.calendar if calendar_result else None,
        calendar_event_count=calendar_result.event_count if calendar_result else 0,
        calendar_review_date=calendar_result.review_date if calendar_result else None,
        cycle_report_path=resolved_cycle_report_path,
        focus_answer=focus_answer,
        review_answer=review_answer,
        pending_answer=pending_answer,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Run one non-interactive Clarity cycle."""

    args = _parse_args(argv)
    try:
        transport = (
            build_graph_read_transport_from_config(use_bearer_auth=args.graph_bearer)
            if args.graph
            else None
        )
        calendar_transport = _build_calendar_transport(args)
        result = run_clarity_cycle(
            mailbox=args.mailbox,
            limit=args.limit,
            memory_path=args.memory,
            brief_path=args.brief,
            cycle_report_path=args.cycle_report,
            transport=transport,
            calendar_transport=calendar_transport,
            use_sample_graph=args.sample_graph,
            refresh_calendar=args.refresh_calendar,
            calendar=args.calendar,
            calendar_date=args.calendar_date,
            use_graph_calendar=args.graph_calendar,
            use_google_calendar=args.google_calendar,
        )
    except Exception as exc:
        safe_error = _safe_error_message(exc)
        failure_report_path = _write_cycle_failure_report(
            output_path=args.cycle_report,
            error=safe_error,
        )
        _record_cycle_failure_memory(
            memory_path=args.memory,
            cycle_report_path=failure_report_path,
            error=safe_error,
        )
        print("# Clarity Cycle Failed")
        print()
        print(f"Error: {safe_error}")
        print(f"Cycle report: {failure_report_path}")
        raise SystemExit(1) from exc

    print("# Clarity Cycle")
    print()
    print(f"Mailbox: {result.mailbox}")
    print(f"Read: {result.message_count}")
    print(f"Review: {result.review_count}")
    print(f"Noise: {result.noise_count}")
    print(f"Trash: {result.trash_count}")
    print(f"Proposed actions: {result.proposed_action_count}")
    if result.calendar:
        print(f"Calendar: {result.calendar}")
        print(f"Calendar date: {result.calendar_review_date}")
        print(f"Calendar events: {result.calendar_event_count}")
    print(f"Brief: {result.brief_path}")
    print(f"Cycle report: {result.cycle_report_path}")
    print()
    print(result.focus_answer)
    print()
    print(result.review_answer)
    print()
    print(result.pending_answer)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one scheduled-friendly Clarity refresh cycle."
    )
    parser.add_argument(
        "--mailbox",
        default=None,
        help="Approved mailbox to refresh. Defaults to the configured mailbox.",
    )
    parser.add_argument("--limit", type=int, default=25)
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--sample-graph",
        action="store_true",
        help="Use local Microsoft Graph-shaped sample messages; no network calls.",
    )
    source_group.add_argument(
        "--graph",
        action="store_true",
        help="Read approved mailbox metadata from Microsoft Graph.",
    )
    parser.add_argument(
        "--refresh-calendar",
        action="store_true",
        help="Also refresh approved read-only calendar metadata.",
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
    calendar_group = parser.add_mutually_exclusive_group()
    calendar_group.add_argument(
        "--graph-calendar",
        action="store_true",
        help="Read approved calendar metadata from Microsoft Graph.",
    )
    calendar_group.add_argument(
        "--google-calendar",
        action="store_true",
        help="Read approved calendar metadata from Google Calendar.",
    )
    parser.add_argument(
        "--graph-bearer",
        action="store_true",
        help="Use GRAPH_ACCESS_TOKEN instead of app-only client credentials.",
    )
    parser.add_argument(
        "--google-bearer",
        action="store_true",
        help="Use GOOGLE_ACCESS_TOKEN instead of refresh-token credentials.",
    )
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
    parser.add_argument(
        "--cycle-report",
        default=str(DEFAULT_CYCLE_REPORT_PATH),
        help="Local cycle report output path.",
    )
    args = parser.parse_args(argv)
    if args.graph_bearer and not (args.graph or args.graph_calendar):
        parser.error("--graph-bearer requires --graph or --graph-calendar.")
    if args.google_bearer and not args.google_calendar:
        parser.error("--google-bearer requires --google-calendar.")
    if args.calendar and not args.refresh_calendar:
        parser.error("--calendar requires --refresh-calendar.")
    if args.calendar_date and not args.refresh_calendar:
        parser.error("--calendar-date requires --refresh-calendar.")
    if args.graph_calendar and not args.refresh_calendar:
        parser.error("--graph-calendar requires --refresh-calendar.")
    if args.google_calendar and not args.refresh_calendar:
        parser.error("--google-calendar requires --refresh-calendar.")
    return args


def _build_calendar_transport(args: argparse.Namespace) -> CalendarTransport | None:
    if args.graph_calendar:
        return build_graph_calendar_read_transport_from_config(
            use_bearer_auth=args.graph_bearer
        )
    if args.google_calendar:
        return build_google_calendar_read_transport_from_config(
            use_bearer_auth=args.google_bearer
        )
    return None


def _write_cycle_report(
    *,
    root: Path | str | None,
    output_path: Path | str,
    mailbox: str,
    message_count: int,
    review_count: int,
    noise_count: int,
    trash_count: int,
    proposed_action_count: int,
    calendar: str | None,
    calendar_event_count: int,
    calendar_review_date: str | None,
    brief_path: Path,
    focus_answer: str,
    review_answer: str,
    pending_answer: str,
) -> Path:
    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    resolved_output_path = _resolve_path(workspace_root, Path(output_path))
    lines = [
        "# Clarity Cycle",
        "",
        f"Mailbox: {mailbox}",
        f"Read: {message_count}",
        f"Review: {review_count}",
        f"Noise: {noise_count}",
        f"Trash: {trash_count}",
        f"Proposed actions: {proposed_action_count}",
    ]
    if calendar:
        lines.extend(
            (
                f"Calendar: {calendar}",
                f"Calendar date: {calendar_review_date}",
                f"Calendar events: {calendar_event_count}",
            )
        )
    lines.extend(
        (
            f"Brief: {brief_path}",
            "",
            focus_answer,
            "",
            review_answer,
            "",
            pending_answer,
        )
    )
    report = "\n".join(lines).rstrip() + "\n"
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(report, encoding="utf-8")
    return resolved_output_path


def _write_cycle_failure_report(
    *,
    output_path: Path | str,
    error: str,
) -> Path:
    workspace_root = _best_effort_workspace_root()
    resolved_output_path = _resolve_path(workspace_root, Path(output_path))
    report = "\n".join(
        (
            "# Clarity Cycle Failed",
            "",
            f"Error: {error}",
        )
    ).rstrip() + "\n"
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(report, encoding="utf-8")
    return resolved_output_path


def _resolve_path(workspace_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return workspace_root / path


def _best_effort_workspace_root() -> Path:
    try:
        return find_workspace_root()
    except Exception:
        return Path.cwd().resolve()


def _record_cycle_memory(
    *,
    memory_path: Path,
    cycle_report_path: Path,
    mailbox: str,
    message_count: int,
    review_count: int,
    noise_count: int,
    trash_count: int,
    proposed_action_count: int,
    calendar: str | None,
    calendar_event_count: int,
    calendar_review_date: str | None,
) -> None:
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="clarity-cycle")
        store.record_generated_artifact(
            run_id=run.run_id,
            artifact_type="markdown_cycle_report",
            path=cycle_report_path,
            summary=f"Clarity cycle report for {mailbox}.",
        )
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="run_clarity_cycle",
            approval_status="not_required",
            result=_cycle_summary(
                mailbox=mailbox,
                message_count=message_count,
                review_count=review_count,
                noise_count=noise_count,
                trash_count=trash_count,
                proposed_action_count=proposed_action_count,
                calendar=calendar,
                calendar_event_count=calendar_event_count,
                calendar_review_date=calendar_review_date,
            ),
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary=_cycle_summary(
                mailbox=mailbox,
                message_count=message_count,
                review_count=review_count,
                noise_count=noise_count,
                trash_count=trash_count,
                proposed_action_count=proposed_action_count,
                calendar=calendar,
                calendar_event_count=calendar_event_count,
                calendar_review_date=calendar_review_date,
            ),
        )
    finally:
        store.close()


def _cycle_summary(
    *,
    mailbox: str,
    message_count: int,
    review_count: int,
    noise_count: int,
    trash_count: int,
    proposed_action_count: int,
    calendar: str | None,
    calendar_event_count: int,
    calendar_review_date: str | None,
) -> str:
    summary = (
        f"Read {message_count} message(s) from {mailbox}; "
        f"review={review_count}, noise={noise_count}, trash={trash_count}, "
        f"proposed_actions={proposed_action_count}."
    )
    if calendar:
        summary += (
            f" Read {calendar_event_count} calendar event(s) "
            f"from {calendar} for {calendar_review_date}."
        )
    return summary


def _record_cycle_failure_memory(
    *,
    memory_path: Path | str,
    cycle_report_path: Path,
    error: str,
) -> None:
    resolved_memory_path = _resolve_path(_best_effort_workspace_root(), Path(memory_path))
    try:
        resolved_memory_path.parent.mkdir(parents=True, exist_ok=True)
        store = DuckDbMemoryStore(resolved_memory_path)
    except Exception:
        return

    try:
        store.initialize_schema()
        run = store.start_run(workflow="clarity-cycle")
        store.record_generated_artifact(
            run_id=run.run_id,
            artifact_type="markdown_cycle_report",
            path=cycle_report_path,
            summary="Failed Clarity cycle report.",
        )
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="run_clarity_cycle",
            approval_status="not_required",
            result=f"Clarity cycle failed: {error}",
        )
        store.finish_run(
            run.run_id,
            status="failed",
            summary=f"Clarity cycle failed: {error}",
        )
    except Exception:
        return
    finally:
        store.close()


def _safe_error_message(exc: Exception) -> str:
    message = f"{type(exc).__name__}: {exc}"
    message = re.sub(
        r"(?i)\b([a-z0-9_]*(?:api[_-]?token|access[_-]?token|client[_-]?secret|password))\s*[:=]\s*\S+",
        r"\1=<redacted>",
        message,
    )
    message = re.sub(r"(?i)\b(bearer|basic)\s+\S+", r"\1 <redacted>", message)
    return message


if __name__ == "__main__":
    main()
