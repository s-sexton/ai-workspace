"""Generate and optionally send Clarity's daily brief email."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from assistant.src.generate_daily_brief import (
    DEFAULT_DAILY_BRIEF_PATH,
    DailyBriefResult,
    generate_daily_brief,
)
from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
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


def send_daily_brief(
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    output_path: Path | str = DEFAULT_DAILY_BRIEF_PATH,
    brief_date: str | None = None,
    limit: int = 10,
    execute: bool = False,
    send_transport: DailyBriefSendTransport | None = None,
) -> SendDailyBriefResult:
    """Generate and optionally send Clarity's daily brief email."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    config = load_workspace_config(workspace_root, include_process_env=False)
    settings = config.daily_brief_settings
    brief = generate_daily_brief(
        root=workspace_root,
        memory_path=memory_path,
        output_path=output_path,
        brief_date=brief_date,
        limit=limit,
    )
    subject = f"{settings.subject_prefix} - {brief.brief_date}"
    if execute:
        if send_transport is None:
            raise RuntimeError("send_transport is required when execute=True.")
        body_text = brief.output_path.read_text(encoding="utf-8")
        send_transport.send_mail(
            sender=settings.sender,
            recipients=settings.recipients,
            subject=subject,
            body_text=body_text,
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
    result = send_daily_brief(
        memory_path=args.memory,
        output_path=args.output,
        brief_date=args.date,
        limit=args.limit,
        execute=args.execute,
        send_transport=transport,
    )
    print("# Clarity Daily Brief Email")
    print()
    print(f"Brief: {result.brief.output_path}")
    print(f"Sender: {result.sender}")
    print(f"Recipients: {', '.join(result.recipients)}")
    print(f"Subject: {result.subject}")
    print(f"Sent: {'yes' if result.sent else 'no'}")
    if not result.sent:
        print()
        print("Dry run only. Add --graph --execute to send through Microsoft Graph.")


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
        "--execute",
        action="store_true",
        help="Send the generated daily brief email.",
    )
    args = parser.parse_args(argv)
    if args.graph and not args.execute:
        parser.error("--graph requires --execute.")
    if args.graph_bearer and not args.graph:
        parser.error("--graph-bearer requires --graph.")
    if args.execute and not args.graph:
        parser.error("--execute requires --graph.")
    return args


if __name__ == "__main__":
    main()
