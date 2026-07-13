"""Bulk approve proposed local email move actions."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import find_workspace_root
from common.console import print_text
from common.memory import DuckDbMemoryStore, PendingActionRecord


def approve_email_moves(
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    mailbox: str | None = None,
    classification: str | None = None,
    limit: int = 100,
    execute: bool = False,
) -> str:
    """Preview or approve pending email move suggestions in local memory."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    resolved_memory_path = _resolve_memory_path(workspace_root, Path(memory_path))
    if not resolved_memory_path.is_file():
        return f"No Clarity memory found at {resolved_memory_path}."

    store = DuckDbMemoryStore(resolved_memory_path)
    try:
        actions = _filtered_pending_email_moves(
            store,
            mailbox=mailbox,
            classification=classification,
            limit=limit,
        )
        if execute and actions:
            for action in actions:
                store.update_assistant_action_approval(
                    action_id=action.action_id,
                    approval_status="approved",
                )
            run = store.start_run(workflow="approve-email-moves")
            store.record_assistant_action(
                run_id=run.run_id,
                action_type="approve_email_moves",
                approval_status="not_required",
                result=_summary_text(actions, execute=True),
            )
            store.finish_run(
                run.run_id,
                status="completed",
                summary=_summary_text(actions, execute=True),
            )
    finally:
        store.close()

    return _format_result(
        actions,
        mailbox=mailbox,
        classification=classification,
        execute=execute,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Preview or approve pending email move suggestions from the command line."""

    args = _parse_args(argv)
    print_text(
        approve_email_moves(
            memory_path=args.memory,
            mailbox=args.mailbox,
            classification=args.classification,
            limit=args.limit,
            execute=args.execute,
        )
    )


def _filtered_pending_email_moves(
    store: DuckDbMemoryStore,
    *,
    mailbox: str | None,
    classification: str | None,
    limit: int,
) -> tuple[PendingActionRecord, ...]:
    actions = tuple(
        action
        for action in store.pending_actions(limit=limit)
        if action.action_type.startswith("propose_email_move_")
        and action.item_external_id
        and action.action_target
    )
    if mailbox:
        actions = tuple(
            action for action in actions if action.source_scope_label == mailbox
        )
    if classification:
        action_type = f"propose_email_move_{classification}"
        actions = tuple(action for action in actions if action.action_type == action_type)
    return actions


def _format_result(
    actions: tuple[PendingActionRecord, ...],
    *,
    mailbox: str | None,
    classification: str | None,
    execute: bool,
) -> str:
    title = "# Email Move Bulk Approval"
    mode = "Executed" if execute else "Dry Run"
    lines = [title, "", "## Summary", f"- Mode: {mode}"]
    if mailbox:
        lines.append(f"- Mailbox: {mailbox}")
    if classification:
        lines.append(f"- Classification: {classification}")
    lines.append(f"- Matching pending moves: {len(actions)}")

    if not actions:
        lines.append("")
        lines.append("No matching pending email move suggestions found.")
        return "\n".join(lines)

    if not execute:
        lines.append("")
        lines.append("No approvals were changed. To approve these suggestions, run:")
        lines.append("")
        lines.append("``` powershell")
        command = "python -m assistant.src.approve_email_moves --execute"
        if mailbox:
            command += f" --mailbox {mailbox}"
        if classification:
            command += f" --classification {classification}"
        lines.append(command)
        lines.append("```")

    lines.append("")
    lines.append("## Moves")
    for action in actions:
        lines.append(
            f"- {action.item_external_id} in {action.source_scope_label} "
            f"to {action.action_target}"
        )
        if action.item_subject:
            lines.append(f"  Subject: {action.item_subject}")
        lines.append(f"  Action: {action.action_id}")
    return "\n".join(lines)


def _summary_text(actions: tuple[PendingActionRecord, ...], *, execute: bool) -> str:
    verb = "Approved" if execute else "Matched"
    return f"{verb} {len(actions)} pending email move suggestion(s)."


def _resolve_memory_path(workspace_root: Path, memory_path: Path) -> Path:
    if memory_path.is_absolute():
        return memory_path
    return workspace_root / memory_path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview or approve pending Clarity email move suggestions."
    )
    parser.add_argument("--mailbox", default=None, help="Optional mailbox filter.")
    parser.add_argument(
        "--classification",
        choices=("review", "noise", "trash"),
        default=None,
        help="Optional email move classification filter.",
    )
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Approve matching pending email move suggestions in local memory.",
    )
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
