"""Dry-run approved email move execution plan."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import EmailSettings, find_workspace_root, load_workspace_config
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


def execute_email_moves(
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    dry_run: bool = True,
    limit: int = 25,
) -> str:
    """Dry-run approved email move actions from local Clarity memory."""

    if not dry_run:
        return "Live email moves are not implemented. Run without --execute."

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    resolved_memory_path = _resolve_memory_path(workspace_root, Path(memory_path))
    if not resolved_memory_path.is_file():
        return f"No Clarity memory found at {resolved_memory_path}."

    store = DuckDbMemoryStore(resolved_memory_path)
    try:
        approved_plan = _approved_email_move_plan(store, limit=limit)
        if not approved_plan:
            return "No approved email moves found."
        email_settings = load_workspace_config(
            workspace_root,
            include_process_env=False,
        ).email_settings
        plan, blocked_plan = _validate_email_move_plan(
            approved_plan,
            email_settings=email_settings,
        )
        if not plan:
            return _format_blocked_plan(blocked_plan)

        run = store.start_run(workflow="execute-email-moves")
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="dry_run_email_moves",
            approval_status="not_required",
            result=f"Prepared dry-run plan for {len(plan)} approved email move(s).",
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary=f"Dry-run email move plan with {len(plan)} item(s).",
        )
    finally:
        store.close()

    lines = ["# Email Move Dry Run", ""]
    for item in plan:
        lines.append(
            f"- Would move message {item.message_id} in mailbox "
            f"{item.mailbox} to {item.target_folder}"
        )
        if item.subject:
            lines.append(f"  Subject: {item.subject}")
        lines.append(f"  Action: {item.action_id}")
    if blocked_plan:
        lines.extend(("", "## Blocked Moves", ""))
        lines.extend(_blocked_plan_lines(blocked_plan))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    """Print the local email move dry run."""

    args = _parse_args(argv)
    print(
        execute_email_moves(
            memory_path=args.memory,
            dry_run=not args.execute,
            limit=args.limit,
        )
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
        if item.target_folder not in configured_targets:
            blocked.append(
                _blocked_item(
                    item,
                    reason="target folder is not in the current email folder policy",
                )
            )
            continue
        executable.append(item)

    return tuple(executable), tuple(blocked)


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
    lines = ["# Email Move Dry Run", "", "No executable approved email moves found."]
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
        help="Reserved for future live moves. Currently reports unsupported.",
    )
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path. Relative paths are resolved under the workspace root.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
