"""Local read-only email metadata review workflow."""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from assistant.src.generate_brief import generate_memory_brief
from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import ConfigurationError, load_workspace_config
from common.email import (
    EmailClient,
    EmailMessage,
    StaticEmailTransport,
    classify_email_message,
    propose_email_folder_action,
)
from common.memory import DuckDbMemoryStore


SAMPLE_EMAIL_MESSAGES: tuple[Mapping[str, object], ...] = (
    {
        "message_id": "sample-legal-1",
        "mailbox": "inbox@example.invalid",
        "subject": "Legal review needed for vendor terms",
        "sender": "legal@example.invalid",
        "received_at": "2026-07-09T08:15:00-05:00",
        "preview": "Please review the updated terms before approval.",
    },
    {
        "message_id": "sample-marketing-1",
        "mailbox": "inbox@example.invalid",
        "subject": "July product newsletter",
        "sender": "marketing@example.invalid",
        "received_at": "2026-07-09T09:00:00-05:00",
        "preview": "News, webinar, and unsubscribe links.",
    },
)


@dataclass(frozen=True)
class EmailReviewResult:
    """Safe result details for a local email review run."""

    memory_path: Path
    brief_path: Path
    run_id: str
    mailbox: str
    message_count: int
    review_count: int
    noise_count: int
    proposed_action_count: int


def run_email_review(
    *,
    root: Path | str | None = None,
    mailbox: str = "inbox@example.invalid",
    limit: int = 25,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    brief_output_path: Path | str | None = None,
    transport: StaticEmailTransport | None = None,
) -> EmailReviewResult:
    """Read fake email metadata, write memory, and generate a local brief."""

    config = load_workspace_config(root, include_process_env=False)
    workspace_root = config.root
    email_settings = config.email_settings
    requested_mailbox = mailbox or email_settings.default_mailbox
    if requested_mailbox not in email_settings.approved_mailboxes:
        raise ConfigurationError(f"Email mailbox is not approved: {requested_mailbox}")
    access_mode = email_settings.access_mode_for(requested_mailbox)
    if access_mode not in ("read", "read_write"):
        raise ConfigurationError(
            f"Email mailbox is not approved for read access: {requested_mailbox}"
        )
    effective_limit = min(limit, email_settings.max_messages)

    resolved_memory_path = _resolve_path(workspace_root, Path(memory_path))
    client = EmailClient(transport=transport or StaticEmailTransport(SAMPLE_EMAIL_MESSAGES))
    read_result = client.list_messages(mailbox=requested_mailbox, limit=effective_limit)

    run_id, review_count, noise_count, proposed_action_count = _record_email_memory(
        memory_path=resolved_memory_path,
        mailbox=requested_mailbox,
        messages=read_result.messages,
        folder_policy=email_settings.folder_policy,
    )
    brief_path = generate_memory_brief(
        root=workspace_root,
        memory_path=resolved_memory_path,
        output_path=brief_output_path or Path("reports") / "clarity-brief.md",
    )
    return EmailReviewResult(
        memory_path=resolved_memory_path,
        brief_path=brief_path,
        run_id=run_id,
        mailbox=requested_mailbox,
        message_count=len(read_result.messages),
        review_count=review_count,
        noise_count=noise_count,
        proposed_action_count=proposed_action_count,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Run the local read-only email review workflow."""

    args = _parse_args(argv)
    result = run_email_review(
        mailbox=args.mailbox,
        limit=args.limit,
        memory_path=args.memory,
        brief_output_path=args.brief,
    )
    print(f"Read {result.message_count} email message(s) from {result.mailbox}")
    print(f"Review: {result.review_count}")
    print(f"Noise: {result.noise_count}")
    print(f"Proposed actions: {result.proposed_action_count}")
    print(f"Wrote brief {result.brief_path}")


def _record_email_memory(
    *,
    memory_path: Path,
    mailbox: str,
    messages: tuple[EmailMessage, ...],
    folder_policy: Mapping[str, str],
) -> tuple[str, int, int, int]:
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    review_count = 0
    noise_count = 0
    proposed_action_count = 0
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="email-review")
        source = store.record_source(
            source_type="email",
            display_name=mailbox,
            scope_label=mailbox,
            access_mode="read",
        )
        for message in messages:
            classification = classify_email_message(message)
            if classification.label == "review":
                review_count += 1
            elif classification.label == "noise":
                noise_count += 1
            item = store.record_item_seen(
                source_id=source.source_id,
                external_id=message.message_id,
                item_type="email_message",
                subject=message.subject,
                sender_or_owner=message.sender,
                updated_at=message.received_at,
                content_hash=_message_hash(message),
                first_seen_run_id=run.run_id,
            )
            store.record_classification(
                item_id=item.item_id,
                run_id=run.run_id,
                label=classification.label,
                reason=classification.reason,
            )
            proposal = propose_email_folder_action(classification, folder_policy)
            store.record_assistant_action(
                run_id=run.run_id,
                item_id=item.item_id,
                action_type=proposal.action_type,
                approval_status="required",
                result=(
                    f"Proposed moving message metadata for {message.message_id} "
                    f"to {proposal.target_folder}. {proposal.reason}"
                ),
            )
            proposed_action_count += 1
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="read_email_metadata",
            approval_status="not_required",
            result=f"Read {len(messages)} message(s) from {mailbox}.",
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary=f"Reviewed {len(messages)} email message(s) from {mailbox}.",
        )
        return run.run_id, review_count, noise_count, proposed_action_count
    finally:
        store.close()


def _message_hash(message: EmailMessage) -> str:
    content = "\n".join(
        (
            message.message_id,
            message.subject,
            message.sender or "",
            message.received_at or "",
            message.preview or "",
        )
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _resolve_path(workspace_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return workspace_root / path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the local read-only Clarity email review workflow."
    )
    parser.add_argument(
        "--mailbox",
        default="inbox@example.invalid",
        help="Approved mailbox label to read from fake local transport.",
    )
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path.",
    )
    parser.add_argument(
        "--brief",
        default=str(Path("reports") / "clarity-brief.md"),
        help="Local brief output path.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
