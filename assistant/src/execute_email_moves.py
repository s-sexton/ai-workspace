"""Dry-run approved email move execution plan."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import EmailSettings, find_workspace_root, load_workspace_config
from common.email import EmailMoveClient, EmailMoveTransport
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


def execute_email_moves(
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    dry_run: bool = True,
    move_transport: EmailMoveTransport | None = None,
    limit: int = 25,
) -> str:
    """Dry-run approved email move actions from local Clarity memory."""

    if not dry_run and move_transport is None:
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
        if dry_run:
            result_summary = (
                f"Prepared dry-run plan for {len(plan)} approved email move(s)."
            )
            run_summary = f"Dry-run email move plan with {len(plan)} item(s)."
            action_type = "dry_run_email_moves"
        else:
            _execute_plan(plan, move_transport=move_transport)
            for item in plan:
                store.update_assistant_action_approval(
                    action_id=item.action_id,
                    approval_status="executed",
                )
            result_summary = f"Executed {len(plan)} approved email move(s)."
            run_summary = f"Executed email move plan with {len(plan)} item(s)."
            action_type = "execute_email_moves"
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

    lines = ["# Email Move Dry Run" if dry_run else "# Email Move Execution", ""]
    for item in plan:
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
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    """Print the local email move dry run."""

    args = _parse_args(argv)
    move_transport = (
        build_graph_move_transport_from_config(use_bearer_auth=args.graph_bearer)
        if args.graph and args.execute
        else None
    )
    print(
        execute_email_moves(
            memory_path=args.memory,
            dry_run=not args.execute,
            move_transport=move_transport,
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
    return build_graph_email_move_transport(
        credentials,
        graph_transport=graph_transport,
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
) -> None:
    if move_transport is None:
        raise RuntimeError("move_transport is required for email move execution.")
    client = EmailMoveClient(transport=move_transport)
    for item in plan:
        client.move_message(
            mailbox=item.mailbox,
            message_id=item.message_id,
            target_folder=item.target_folder,
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
        help="Execute approved moves. Requires --graph for live Graph moves.",
    )
    parser.add_argument(
        "--graph",
        action="store_true",
        help="Use Microsoft Graph for live move execution.",
    )
    parser.add_argument(
        "--graph-bearer",
        action="store_true",
        help="Use GRAPH_ACCESS_TOKEN instead of app-only client credentials.",
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
    if args.graph_bearer and not args.graph:
        parser.error("--graph-bearer requires --graph.")
    return args


if __name__ == "__main__":
    main()
