"""Poll the Clarity mailbox for daily brief replies."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from assistant.src.generate_daily_brief import DEFAULT_DAILY_BRIEF_PATH
from assistant.src.process_daily_brief_reply import process_daily_brief_reply
from assistant.src.run_email_review import build_graph_read_transport_from_config
from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import ConfigurationError, find_workspace_root, load_workspace_config
from common.email import EmailClient, EmailMessage, EmailTransport
from common.memory import DuckDbMemoryStore


DEFAULT_DAILY_BRIEF_MANIFEST_PATH = DEFAULT_DAILY_BRIEF_PATH.with_suffix(".json")


@dataclass(frozen=True)
class PolledReply:
    """One daily brief reply selected for processing."""

    message_id: str
    sender: str | None
    subject: str
    result: str
    processed: bool


@dataclass(frozen=True)
class PollDailyBriefRepliesResult:
    """Safe result details for a reply poll run."""

    mailbox: str
    read_count: int
    selected_count: int
    skipped_count: int
    processed_count: int
    replies: tuple[PolledReply, ...]


def poll_daily_brief_replies(
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    manifest_path: Path | str = DEFAULT_DAILY_BRIEF_MANIFEST_PATH,
    mailbox: str | None = None,
    limit: int = 25,
    transport: EmailTransport,
    execute: bool = False,
) -> PollDailyBriefRepliesResult:
    """Poll approved Clarity mailbox replies and process supported directions."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    config = load_workspace_config(workspace_root, include_process_env=False)
    email_settings = config.email_settings
    daily_brief_settings = config.daily_brief_settings
    resolved_mailbox = mailbox or daily_brief_settings.sender
    if resolved_mailbox not in email_settings.approved_mailboxes:
        raise ConfigurationError(f"Reply mailbox is not approved: {resolved_mailbox}")
    allowed_senders = email_settings.allowed_senders_for(resolved_mailbox)
    if not allowed_senders:
        raise ConfigurationError(
            f"Reply mailbox must define allowedSenders: {resolved_mailbox}"
        )

    client = EmailClient(transport=transport)
    read_result = client.list_messages(mailbox=resolved_mailbox, limit=limit)
    already_processed = _processed_reply_ids(
        root=workspace_root,
        memory_path=memory_path,
    )
    replies: list[PolledReply] = []
    skipped_count = 0
    processed_count = 0
    for message in read_result.messages:
        skip_reason = _skip_reason(
            message,
            allowed_senders=allowed_senders,
            subject_prefix=daily_brief_settings.subject_prefix,
            already_processed=already_processed,
        )
        if skip_reason:
            skipped_count += 1
            replies.append(
                PolledReply(
                    message_id=message.message_id,
                    sender=message.sender,
                    subject=message.subject,
                    result=skip_reason,
                    processed=False,
                )
            )
            continue
        reply_text = message.preview or ""
        result = process_daily_brief_reply(
            reply_text,
            root=workspace_root,
            memory_path=memory_path,
            manifest_path=manifest_path,
            execute=execute,
        )
        selected = "No supported reply commands found" not in result
        if selected and execute:
            _record_processed_reply(
                root=workspace_root,
                memory_path=memory_path,
                mailbox=resolved_mailbox,
                message=message,
            )
            processed_count += 1
        elif selected:
            processed_count += 1
        else:
            skipped_count += 1
        replies.append(
            PolledReply(
                message_id=message.message_id,
                sender=message.sender,
                subject=message.subject,
                result=result,
                processed=selected,
            )
        )

    return PollDailyBriefRepliesResult(
        mailbox=resolved_mailbox,
        read_count=len(read_result.messages),
        selected_count=sum(1 for reply in replies if reply.processed),
        skipped_count=skipped_count,
        processed_count=processed_count,
        replies=tuple(replies),
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Poll the Clarity mailbox for daily brief replies."""

    args = _parse_args(argv)
    transport = build_graph_read_transport_from_config(
        use_bearer_auth=args.graph_bearer,
        include_body_text=True,
    )
    result = poll_daily_brief_replies(
        memory_path=args.memory,
        manifest_path=args.manifest,
        mailbox=args.mailbox,
        limit=args.limit,
        transport=transport,
        execute=args.execute,
    )
    print(_format_result(result, execute=args.execute))


def _skip_reason(
    message: EmailMessage,
    *,
    allowed_senders: tuple[str, ...],
    subject_prefix: str,
    already_processed: set[str],
) -> str | None:
    if message.message_id in already_processed:
        return "Skipped: reply already processed."
    if not _sender_allowed(message.sender, allowed_senders):
        return "Skipped: sender is not allowed."
    if not _authentication_passes(message, allowed_senders=allowed_senders):
        return "Skipped: message authentication did not pass."
    if not _subject_matches_daily_brief(message.subject, subject_prefix):
        return "Skipped: message is not tied to a Clarity daily brief."
    if not (message.preview or "").strip():
        return "Skipped: no reply text found in message preview."
    return None


def _sender_allowed(sender: str | None, allowed_senders: tuple[str, ...]) -> bool:
    if sender is None:
        return False
    clean_sender = sender.strip().lower()
    return clean_sender in {allowed_sender.lower() for allowed_sender in allowed_senders}


def _authentication_passes(
    message: EmailMessage,
    *,
    allowed_senders: tuple[str, ...],
) -> bool:
    return _internet_authentication_passes(message) or _exchange_internal_auth_passes(
        message,
        allowed_senders=allowed_senders,
    )


def _internet_authentication_passes(message: EmailMessage) -> bool:
    return _auth_passes(message.dmarc) and (
        _auth_passes(message.spf) or _auth_passes(message.dkim)
    )


def _exchange_internal_auth_passes(
    message: EmailMessage,
    *,
    allowed_senders: tuple[str, ...],
) -> bool:
    if (message.exchange_auth_as or "").strip().lower() != "internal":
        return False
    if not _sender_allowed(message.sender, allowed_senders):
        return False
    return _sender_allowed(message.return_path, allowed_senders)


def _subject_matches_daily_brief(subject: str, subject_prefix: str) -> bool:
    clean_subject = " ".join(subject.lower().strip().split())
    clean_prefix = " ".join(subject_prefix.lower().strip().split())
    return clean_prefix in clean_subject


def _auth_passes(value: str | None) -> bool:
    return value is not None and value.strip().lower() == "pass"


def _processed_reply_ids(
    *,
    root: Path,
    memory_path: Path | str,
) -> set[str]:
    resolved_memory_path = _resolve_path(root, Path(memory_path))
    if not resolved_memory_path.is_file():
        return set()
    store = DuckDbMemoryStore(resolved_memory_path)
    try:
        item_records = store.recent_memory_by_source_type(
            "email",
            limit=500,
        )
    finally:
        store.close()
    return {
        record.external_id
        for record in item_records
        if record.item_type == "daily_brief_reply"
    }


def _record_processed_reply(
    *,
    root: Path,
    memory_path: Path | str,
    mailbox: str,
    message: EmailMessage,
) -> None:
    resolved_memory_path = _resolve_path(root, Path(memory_path))
    resolved_memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(resolved_memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="poll-daily-brief-replies")
        source = store.record_source(
            source_type="email",
            display_name=mailbox,
            scope_label=mailbox,
            access_mode="read",
        )
        item = store.record_item_seen(
            source_id=source.source_id,
            external_id=message.message_id,
            item_type="daily_brief_reply",
            subject=message.subject,
            sender_or_owner=message.sender,
            updated_at=message.received_at,
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=item.item_id,
            run_id=run.run_id,
            label="processed_reply",
            reason="Processed authenticated daily brief reply.",
        )
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="record_processed_daily_brief_reply",
            approval_status="not_required",
            result=f"Processed reply {message.message_id} from {message.sender}.",
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary=f"Processed daily brief reply {message.message_id}.",
        )
    finally:
        store.close()


def _format_result(result: PollDailyBriefRepliesResult, *, execute: bool) -> str:
    lines = [
        "# Daily Brief Reply Poll",
        "",
        "## Summary",
        "",
        f"- Mode: {'execute' if execute else 'dry-run'}",
        f"- Mailbox: {result.mailbox}",
        f"- Read: {result.read_count}",
        f"- Selected: {result.selected_count}",
        f"- Skipped: {result.skipped_count}",
        f"- Processed: {result.processed_count}",
    ]
    if result.replies:
        lines.extend(("", "## Replies", ""))
        for reply in result.replies:
            lines.append(f"- {reply.subject}")
            lines.append(f"  Message: {reply.message_id}")
            if reply.sender:
                lines.append(f"  Sender: {reply.sender}")
            lines.append("  Result:")
            for result_line in (reply.result or "").splitlines():
                lines.append(f"    {result_line}")
    return "\n".join(lines)


def _resolve_path(workspace_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return workspace_root / path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Poll Clarity mailbox replies to daily brief emails."
    )
    parser.add_argument(
        "--graph",
        action="store_true",
        required=True,
        help="Read replies from Microsoft Graph.",
    )
    parser.add_argument(
        "--graph-bearer",
        action="store_true",
        help="Use GRAPH_ACCESS_TOKEN instead of app-only client credentials.",
    )
    parser.add_argument("--mailbox", default=None)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_DAILY_BRIEF_MANIFEST_PATH),
        help="Daily brief manifest path.",
    )
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply supported local reply commands and record replies as processed.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
