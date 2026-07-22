"""Dry-run approved email move execution plan."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import (
    ConfigurationError,
    EmailSettings,
    find_workspace_root,
    load_workspace_config,
)
from common.email import EmailMoveClient, EmailMoveTransport
from common.google_gmail import (
    GoogleCalendarTransport,
    GoogleTokenTransport,
    build_google_gmail_move_transport,
)
from common.graph_email import (
    GraphTokenTransport,
    GraphTransport,
    build_graph_email_move_transport,
)
from common.memory import DuckDbMemoryStore


@dataclass(frozen=True)
class EmailMovePlanItem:
    """A local approved email move plan item."""

    action_id: str
    mailbox: str
    message_id: str
    target_folder: str
    source_type: str | None = None
    item_type: str | None = None
    subject: str | None = None


@dataclass(frozen=True)
class BlockedEmailMovePlanItem:
    """An approved local email move that cannot currently execute."""

    action_id: str
    mailbox: str
    message_id: str
    target_folder: str
    reason: str
    source_type: str | None = None
    item_type: str | None = None
    subject: str | None = None


@dataclass(frozen=True)
class FailedEmailMovePlanItem:
    """An approved local email move that failed during provider execution."""

    action_id: str
    mailbox: str
    message_id: str
    target_folder: str
    reason: str
    subject: str | None = None


@dataclass(frozen=True)
class GmailSpamCleanupResult:
    """Messages moved from Gmail Spam to Trash for one mailbox."""

    mailbox: str
    message_ids: tuple[str, ...]


class GmailSpamCleanupTransport(Protocol):
    """Provider operation for configured Gmail Spam cleanup."""

    def trash_spam_messages(self, mailbox: str) -> tuple[str, ...]:
        """Move current Spam messages to Trash and return message IDs."""


def execute_email_moves(
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    dry_run: bool = True,
    move_transport: EmailMoveTransport | None = None,
    gmail_spam_cleanup_transport: GmailSpamCleanupTransport | None = None,
    include_gmail_spam_cleanup: bool = False,
    limit: int = 25,
) -> str:
    """Dry-run approved email move actions from local Clarity memory."""

    if not dry_run and move_transport is None:
        return "Live email moves are not implemented. Run without --execute."

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    resolved_memory_path = _resolve_memory_path(workspace_root, Path(memory_path))
    email_settings: EmailSettings | None = None
    gmail_spam_mailboxes: tuple[str, ...] = ()
    if include_gmail_spam_cleanup:
        email_settings = load_workspace_config(
            workspace_root,
            include_process_env=False,
        ).email_settings
        gmail_spam_mailboxes = _configured_gmail_spam_cleanup_mailboxes(
            email_settings,
            include_cleanup=include_gmail_spam_cleanup,
        )
    if gmail_spam_mailboxes and not dry_run and gmail_spam_cleanup_transport is None:
        return "Live Gmail Spam cleanup requires a Gmail cleanup transport."

    if not resolved_memory_path.is_file() and not gmail_spam_mailboxes:
        return f"No Clarity memory found at {resolved_memory_path}."

    store = DuckDbMemoryStore(resolved_memory_path)
    try:
        if not resolved_memory_path.is_file():
            store.initialize_schema()
        approved_plan = _approved_email_move_plan(store, limit=limit)
        if not approved_plan and not gmail_spam_mailboxes:
            return "No approved email moves found."
        if email_settings is None:
            email_settings = load_workspace_config(
                workspace_root,
                include_process_env=False,
            ).email_settings
        plan, blocked_plan = _validate_email_move_plan(
            approved_plan,
            email_settings=email_settings,
        )
        if not plan and not gmail_spam_mailboxes:
            return _format_blocked_plan(blocked_plan)

        run = store.start_run(workflow="execute-email-moves")
        gmail_spam_cleanup_results = _execute_or_preview_gmail_spam_cleanup(
            gmail_spam_mailboxes,
            dry_run=dry_run,
            cleanup_transport=gmail_spam_cleanup_transport,
        )
        if dry_run:
            result_summary = (
                _summary_sentence(
                    action="Prepared dry-run plan",
                    plan=plan,
                    blocked_plan=blocked_plan,
                    gmail_spam_cleanup_results=gmail_spam_cleanup_results,
                )
            )
            run_summary = _summary_sentence(
                action="Dry-run email move plan",
                plan=plan,
                blocked_plan=blocked_plan,
                gmail_spam_cleanup_results=gmail_spam_cleanup_results,
            )
            action_type = "dry_run_email_moves"
        else:
            moved_plan, failed_plan = _execute_plan(
                plan,
                move_transport=move_transport,
            )
            for item in moved_plan:
                store.update_assistant_action_approval(
                    action_id=item.action_id,
                    approval_status="executed",
                )
            for item in failed_plan:
                store.update_assistant_action_approval(
                    action_id=item.action_id,
                    approval_status="failed",
                )
            result_summary = _summary_sentence(
                action="Executed",
                plan=moved_plan,
                blocked_plan=blocked_plan,
                failed_plan=failed_plan,
                gmail_spam_cleanup_results=gmail_spam_cleanup_results,
            )
            run_summary = _summary_sentence(
                action="Executed email move plan",
                plan=moved_plan,
                blocked_plan=blocked_plan,
                failed_plan=failed_plan,
                gmail_spam_cleanup_results=gmail_spam_cleanup_results,
            )
            action_type = "execute_email_moves"
        if dry_run:
            moved_plan = plan
            failed_plan = ()
        store.record_assistant_action(
            run_id=run.run_id,
            action_type=action_type,
            approval_status="not_required",
            result=result_summary,
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary=run_summary,
        )
    finally:
        store.close()

    lines = [
        "# Email Move Dry Run" if dry_run else "# Email Move Execution",
        "",
        "## Summary",
        "",
    ]
    lines.extend(
        _summary_lines(
            plan if dry_run else moved_plan,
            blocked_plan=blocked_plan,
            failed_plan=failed_plan,
            dry_run=dry_run,
            gmail_spam_cleanup_results=gmail_spam_cleanup_results,
        )
    )
    lines.extend(("", "## Moves", ""))
    rendered_plan = plan if dry_run else moved_plan
    for item in rendered_plan:
        verb = "Would move" if dry_run else "Moved"
        lines.append(
            f"- {verb} message {item.message_id} in mailbox "
            f"{item.mailbox} to {item.target_folder}"
        )
        if item.subject:
            lines.append(f"  Subject: {item.subject}")
        lines.append(f"  Action: {item.action_id}")
    if blocked_plan:
        lines.extend(("", "## Blocked Moves", ""))
        lines.extend(_blocked_plan_lines(blocked_plan))
    if failed_plan:
        lines.extend(("", "## Failed Moves", ""))
        lines.extend(_failed_plan_lines(failed_plan))
    if gmail_spam_cleanup_results:
        lines.extend(("", "## Gmail Spam Cleanup", ""))
        verb = "Would trash" if dry_run else "Trashed"
        for result in gmail_spam_cleanup_results:
            lines.append(
                f"- {verb} {len(result.message_ids)} Spam message(s) "
                f"from {result.mailbox}"
            )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    """Print the local email move dry run."""

    args = _parse_args(argv)
    move_transport = (
        build_graph_move_transport_from_config(use_bearer_auth=args.graph_bearer)
        if args.graph and args.execute
        else build_gmail_move_transport_from_config(use_bearer_auth=args.gmail_bearer)
        if args.gmail and args.execute
        else None
    )
    print(
        execute_email_moves(
            memory_path=args.memory,
            dry_run=not args.execute,
            move_transport=move_transport,
            gmail_spam_cleanup_transport=move_transport
            if args.gmail and args.execute
            else None,
            include_gmail_spam_cleanup=args.gmail and args.execute,
            limit=args.limit,
        )
    )


def build_graph_move_transport_from_config(
    *,
    root: Path | str | None = None,
    graph_transport: GraphTransport | None = None,
    token_transport: GraphTokenTransport | None = None,
    use_bearer_auth: bool = False,
) -> EmailMoveTransport:
    """Build a Graph email move transport from local workspace configuration."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    config = load_workspace_config(workspace_root)
    credentials = config.require_graph_credentials(use_bearer_auth=use_bearer_auth)
    try:
        mailbox_identity_overrides = config.email_settings.mailbox_graph_user_ids
    except ConfigurationError:
        mailbox_identity_overrides = {}
    return build_graph_email_move_transport(
        credentials,
        graph_transport=graph_transport,
        token_transport=token_transport,
        use_bearer_auth=use_bearer_auth,
        mailbox_identity_overrides=mailbox_identity_overrides,
    )


def build_gmail_move_transport_from_config(
    *,
    root: Path | str | None = None,
    gmail_transport: GoogleCalendarTransport | None = None,
    token_transport: GoogleTokenTransport | None = None,
    use_bearer_auth: bool = False,
) -> EmailMoveTransport:
    """Build a Gmail move transport from local workspace configuration."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    config = load_workspace_config(workspace_root)
    credentials = config.require_google_credentials(use_bearer_auth=use_bearer_auth)
    return build_google_gmail_move_transport(
        credentials,
        gmail_transport=gmail_transport,
        token_transport=token_transport,
        use_bearer_auth=use_bearer_auth,
    )


def _approved_email_move_plan(
    store: DuckDbMemoryStore,
    *,
    limit: int,
) -> tuple[EmailMovePlanItem, ...]:
    approved_actions = store.actions_by_approval_status("approved", limit=limit)
    return tuple(
        EmailMovePlanItem(
            action_id=action.action_id,
            mailbox=action.source_scope_label or "unknown mailbox",
            message_id=action.item_external_id,
            target_folder=action.action_target,
            source_type=action.source_type,
            item_type=action.item_type,
            subject=action.item_subject,
        )
        for action in approved_actions
        if action.action_type.startswith("propose_email_move_")
        and action.item_external_id
        and action.action_target
    )


def _execute_plan(
    plan: tuple[EmailMovePlanItem, ...],
    *,
    move_transport: EmailMoveTransport | None,
) -> tuple[tuple[EmailMovePlanItem, ...], tuple[FailedEmailMovePlanItem, ...]]:
    if move_transport is None:
        raise RuntimeError("move_transport is required for email move execution.")
    client = EmailMoveClient(transport=move_transport)
    moved: list[EmailMovePlanItem] = []
    failed: list[FailedEmailMovePlanItem] = []
    for item in plan:
        try:
            client.move_message(
                mailbox=item.mailbox,
                message_id=item.message_id,
                target_folder=item.target_folder,
            )
        except Exception as exc:
            failed.append(
                FailedEmailMovePlanItem(
                    action_id=item.action_id,
                    mailbox=item.mailbox,
                    message_id=item.message_id,
                    target_folder=item.target_folder,
                    reason=str(exc),
                    subject=item.subject,
                )
            )
        else:
            moved.append(item)
    return tuple(moved), tuple(failed)


def _configured_gmail_spam_cleanup_mailboxes(
    email_settings: EmailSettings,
    *,
    include_cleanup: bool,
) -> tuple[str, ...]:
    if not include_cleanup:
        return ()
    policy = email_settings.gmail_cleanup_policy
    if not policy.trash_spam:
        return ()
    return policy.mailboxes


def _execute_or_preview_gmail_spam_cleanup(
    mailboxes: tuple[str, ...],
    *,
    dry_run: bool,
    cleanup_transport: GmailSpamCleanupTransport | None,
) -> tuple[GmailSpamCleanupResult, ...]:
    if not mailboxes:
        return ()
    if dry_run:
        return tuple(
            GmailSpamCleanupResult(mailbox=mailbox, message_ids=())
            for mailbox in mailboxes
        )
    if cleanup_transport is None:
        raise RuntimeError("cleanup_transport is required for Gmail Spam cleanup.")
    return tuple(
        GmailSpamCleanupResult(
            mailbox=mailbox,
            message_ids=cleanup_transport.trash_spam_messages(mailbox),
        )
        for mailbox in mailboxes
    )


def _validate_email_move_plan(
    plan: tuple[EmailMovePlanItem, ...],
    *,
    email_settings: EmailSettings,
) -> tuple[tuple[EmailMovePlanItem, ...], tuple[BlockedEmailMovePlanItem, ...]]:
    executable: list[EmailMovePlanItem] = []
    blocked: list[BlockedEmailMovePlanItem] = []
    configured_targets = set(email_settings.folder_policy.values())

    for item in plan:
        if item.source_type != "email" or item.item_type != "email_message":
            blocked.append(
                _blocked_item(
                    item,
                    reason="action is not attached to an email message source",
                )
            )
            continue
        access_mode = email_settings.access_mode_for(item.mailbox)
        if access_mode != "read_write":
            blocked.append(
                _blocked_item(
                    item,
                    reason=(
                        "mailbox is not approved for read_write email actions"
                    ),
                )
            )
            continue
        if not _is_allowed_target_folder(
            item.target_folder,
            configured_targets=configured_targets,
            folder_namespace=email_settings.folder_namespace,
        ):
            blocked.append(
                _blocked_item(
                    item,
                    reason=(
                        "target folder is not in the current email folder policy "
                        "or assistant folder namespace"
                    ),
                )
            )
            continue
        executable.append(item)

    return tuple(executable), tuple(blocked)


def _is_allowed_target_folder(
    target_folder: str,
    *,
    configured_targets: set[str],
    folder_namespace: str,
) -> bool:
    if target_folder in configured_targets:
        return True
    namespace_prefix = f"{folder_namespace}/"
    if not target_folder.lower().startswith(namespace_prefix.lower()):
        return False
    segments = target_folder.split("/")
    if len(segments) < 2:
        return False
    for segment in segments:
        clean_segment = segment.strip()
        if (
            not clean_segment
            or clean_segment in {".", ".."}
            or any(character in clean_segment for character in '<>:"|?*')
        ):
            return False
    return True


def _blocked_item(
    item: EmailMovePlanItem,
    *,
    reason: str,
) -> BlockedEmailMovePlanItem:
    return BlockedEmailMovePlanItem(
        action_id=item.action_id,
        mailbox=item.mailbox,
        message_id=item.message_id,
        target_folder=item.target_folder,
        reason=reason,
        source_type=item.source_type,
        item_type=item.item_type,
        subject=item.subject,
    )


def _format_blocked_plan(blocked_plan: tuple[BlockedEmailMovePlanItem, ...]) -> str:
    lines = [
        "# Email Move Dry Run",
        "",
        "## Summary",
        "",
        "- Ready to move: 0",
        f"- Blocked/skipped: {len(blocked_plan)}",
        "",
        "No executable approved email moves found.",
    ]
    if blocked_plan:
        lines.extend(("", "## Blocked Moves", ""))
        lines.extend(_blocked_plan_lines(blocked_plan))
    return "\n".join(lines)


def _blocked_plan_lines(
    blocked_plan: tuple[BlockedEmailMovePlanItem, ...],
) -> list[str]:
    lines: list[str] = []
    for item in blocked_plan:
        lines.append(
            f"- Blocked message {item.message_id} in mailbox {item.mailbox} "
            f"to {item.target_folder}: {item.reason}."
        )
        if item.subject:
            lines.append(f"  Subject: {item.subject}")
        lines.append(f"  Action: {item.action_id}")
    return lines


def _failed_plan_lines(
    failed_plan: tuple[FailedEmailMovePlanItem, ...],
) -> list[str]:
    lines: list[str] = []
    for item in failed_plan:
        lines.append(
            f"- Failed message {item.message_id} in mailbox {item.mailbox} "
            f"to {item.target_folder}: {item.reason}."
        )
        if item.subject:
            lines.append(f"  Subject: {item.subject}")
        lines.append(f"  Action: {item.action_id}")
    return lines


def _summary_sentence(
    *,
    action: str,
    plan: tuple[EmailMovePlanItem, ...],
    blocked_plan: tuple[BlockedEmailMovePlanItem, ...],
    failed_plan: tuple[FailedEmailMovePlanItem, ...] = (),
    gmail_spam_cleanup_results: tuple[GmailSpamCleanupResult, ...],
) -> str:
    gmail_spam_count = sum(
        len(result.message_ids) for result in gmail_spam_cleanup_results
    )
    summary = (
        f"{action} for {len(plan)} approved email move(s); "
        f"{len(blocked_plan)} blocked/skipped; {len(failed_plan)} failed."
    )
    if gmail_spam_cleanup_results:
        summary += f" {gmail_spam_count} Gmail Spam message(s) trashed."
    return summary


def _summary_lines(
    plan: tuple[EmailMovePlanItem, ...],
    *,
    blocked_plan: tuple[BlockedEmailMovePlanItem, ...],
    failed_plan: tuple[FailedEmailMovePlanItem, ...] = (),
    dry_run: bool,
    gmail_spam_cleanup_results: tuple[GmailSpamCleanupResult, ...],
) -> list[str]:
    ready_label = "Ready to move" if dry_run else "Moved"
    gmail_spam_label = "Gmail Spam mailboxes" if dry_run else "Gmail Spam trashed"
    gmail_spam_count = sum(
        len(result.message_ids) for result in gmail_spam_cleanup_results
    )
    lines = [
        f"- {ready_label}: {len(plan)}",
        f"- Blocked/skipped: {len(blocked_plan)}",
        f"- Failed: {len(failed_plan)}",
    ]
    if gmail_spam_cleanup_results:
        if dry_run:
            lines.append(
                f"- {gmail_spam_label}: "
                + ", ".join(result.mailbox for result in gmail_spam_cleanup_results)
            )
        else:
            lines.append(f"- {gmail_spam_label}: {gmail_spam_count}")
    for mailbox, items in _group_plan_by_mailbox(plan):
        lines.append(f"- Mailbox {mailbox}: {len(items)} move(s)")
    for target_folder, items in _group_plan_by_target(plan):
        lines.append(f"- Destination {target_folder}: {len(items)} move(s)")
    return lines


def _group_plan_by_mailbox(
    plan: tuple[EmailMovePlanItem, ...],
) -> tuple[tuple[str, tuple[EmailMovePlanItem, ...]], ...]:
    mailboxes = sorted({item.mailbox for item in plan})
    return tuple(
        (mailbox, tuple(item for item in plan if item.mailbox == mailbox))
        for mailbox in mailboxes
    )


def _group_plan_by_target(
    plan: tuple[EmailMovePlanItem, ...],
) -> tuple[tuple[str, tuple[EmailMovePlanItem, ...]], ...]:
    targets = sorted({item.target_folder for item in plan})
    return tuple(
        (target, tuple(item for item in plan if item.target_folder == target))
        for target in targets
    )


def _resolve_memory_path(workspace_root: Path, memory_path: Path) -> Path:
    if memory_path.is_absolute():
        return memory_path
    return workspace_root / memory_path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run approved Clarity email move actions."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute approved moves. Requires --graph for live Graph moves.",
    )
    provider_group = parser.add_mutually_exclusive_group()
    provider_group.add_argument(
        "--graph",
        action="store_true",
        help="Use Microsoft Graph for live move execution.",
    )
    provider_group.add_argument(
        "--gmail",
        action="store_true",
        help="Use Gmail for live move/trash execution.",
    )
    parser.add_argument(
        "--graph-bearer",
        action="store_true",
        help="Use GRAPH_ACCESS_TOKEN instead of app-only client credentials.",
    )
    parser.add_argument(
        "--gmail-bearer",
        action="store_true",
        help="Use GOOGLE_ACCESS_TOKEN instead of refresh-token credentials.",
    )
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path. Relative paths are resolved under the workspace root.",
    )
    args = parser.parse_args(argv)
    if args.graph and not args.execute:
        parser.error("--graph requires --execute.")
    if args.gmail and not args.execute:
        parser.error("--gmail requires --execute.")
    if args.graph_bearer and not args.graph:
        parser.error("--graph-bearer requires --graph.")
    if args.gmail_bearer and not args.gmail:
        parser.error("--gmail-bearer requires --gmail.")
    return args


if __name__ == "__main__":
    main()
