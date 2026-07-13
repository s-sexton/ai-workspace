"""Review-before-execute email cleanup planning."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from assistant.src.execute_email_moves import (
    EmailMovePlanItem,
    _approved_email_move_plan,
    _blocked_plan_lines,
    _validate_email_move_plan,
)
from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import find_workspace_root, load_workspace_config
from common.console import print_text
from common.memory import DuckDbMemoryStore, PendingActionRecord


def build_email_cleanup_plan(
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    mailbox: str | None = None,
    limit: int = 100,
) -> str:
    """Return a read-only cleanup plan for proposed and approved email filing."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    resolved_memory_path = _resolve_memory_path(workspace_root, Path(memory_path))
    if not resolved_memory_path.is_file():
        return f"No Clarity memory found at {resolved_memory_path}."

    config = load_workspace_config(workspace_root, include_process_env=False)
    store = DuckDbMemoryStore(resolved_memory_path)
    try:
        approved_plan = _filter_plan_by_mailbox(
            _approved_email_move_plan(store, limit=limit),
            mailbox=mailbox,
        )
        ready_plan, blocked_plan = _validate_email_move_plan(
            approved_plan,
            email_settings=config.email_settings,
        )
        pending_actions = _filter_pending_by_mailbox(
            _pending_email_move_actions(store, limit=limit),
            mailbox=mailbox,
        )
    finally:
        store.close()

    lines = ["# Email Cleanup Plan", ""]
    if mailbox:
        lines.append(f"- Mailbox: {mailbox}")
    lines.extend(
        (
            f"- Ready to execute: {len(ready_plan)}",
            f"- Needs approval: {len(pending_actions)}",
            f"- Blocked approved moves: {len(blocked_plan)}",
            "",
        )
    )

    if ready_plan:
        lines.append("## Ready To Execute")
        lines.extend(_ready_lines(ready_plan))
        lines.append("")
        lines.append("Execute approved Gmail cleanup with:")
        lines.append("")
        lines.append("``` powershell")
        lines.append("python -m assistant.src.execute_email_moves --gmail --execute")
        lines.append("```")
        lines.append("")

    if pending_actions:
        lines.append("## Needs Approval")
        lines.extend(_pending_lines(pending_actions))
        lines.append("")

    if blocked_plan:
        lines.append("## Blocked Approved Moves")
        lines.extend(_blocked_plan_lines(blocked_plan))
        lines.append("")

    if not ready_plan and not pending_actions and not blocked_plan:
        lines.append("No email cleanup actions found.")

    return "\n".join(lines).rstrip()


def main(argv: Sequence[str] | None = None) -> None:
    """Print a read-only email cleanup plan."""

    args = _parse_args(argv)
    print_text(
        build_email_cleanup_plan(
            memory_path=args.memory,
            mailbox=args.mailbox,
            limit=args.limit,
        )
    )


def _pending_email_move_actions(
    store: DuckDbMemoryStore,
    *,
    limit: int,
) -> tuple[PendingActionRecord, ...]:
    return tuple(
        action
        for action in store.pending_actions(limit=limit)
        if action.action_type.startswith("propose_email_move_")
        and action.item_external_id
        and action.action_target
    )


def _filter_plan_by_mailbox(
    plan: tuple[EmailMovePlanItem, ...],
    *,
    mailbox: str | None,
) -> tuple[EmailMovePlanItem, ...]:
    if mailbox is None:
        return plan
    return tuple(item for item in plan if item.mailbox == mailbox)


def _filter_pending_by_mailbox(
    actions: tuple[PendingActionRecord, ...],
    *,
    mailbox: str | None,
) -> tuple[PendingActionRecord, ...]:
    if mailbox is None:
        return actions
    return tuple(action for action in actions if action.source_scope_label == mailbox)


def _ready_lines(plan: tuple[EmailMovePlanItem, ...]) -> list[str]:
    lines: list[str] = []
    for target_folder, items in _group_ready_by_target(plan):
        lines.append(f"- {len(items)} message(s) to {target_folder}")
        for item in items:
            lines.append(f"  - {item.message_id} in {item.mailbox}")
            if item.subject:
                lines.append(f"    Subject: {item.subject}")
            lines.append(f"    Action: {item.action_id}")
    return lines


def _group_ready_by_target(
    plan: tuple[EmailMovePlanItem, ...],
) -> tuple[tuple[str, tuple[EmailMovePlanItem, ...]], ...]:
    targets = sorted({item.target_folder for item in plan})
    return tuple(
        (
            target,
            tuple(item for item in plan if item.target_folder == target),
        )
        for target in targets
    )


def _pending_lines(actions: tuple[PendingActionRecord, ...]) -> list[str]:
    lines: list[str] = []
    for action in actions:
        lines.append(
            f"- {action.item_external_id} in {action.source_scope_label} "
            f"to {action.action_target}"
        )
        if action.item_subject:
            lines.append(f"  Subject: {action.item_subject}")
        lines.append(f"  Action: {action.action_id}")
        lines.append(
            "  Approve: "
            f"python -m assistant.src.update_action {action.action_id} approved"
        )
    return lines


def _resolve_memory_path(workspace_root: Path, memory_path: Path) -> Path:
    if memory_path.is_absolute():
        return memory_path
    return workspace_root / memory_path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a read-only email cleanup plan."
    )
    parser.add_argument("--mailbox", default=None, help="Optional mailbox filter.")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
