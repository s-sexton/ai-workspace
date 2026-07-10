"""Build bounded local context for future LLM summarization."""

from __future__ import annotations

from pathlib import Path

from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import find_workspace_root
from common.memory import DuckDbMemoryStore


def build_llm_context(
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    limit: int = 10,
) -> str:
    """Return sanitized local context suitable for a future LLM prompt."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    resolved_memory_path = _resolve_path(workspace_root, Path(memory_path))
    if not resolved_memory_path.is_file():
        return f"No Clarity memory found at {resolved_memory_path}."

    store = DuckDbMemoryStore(resolved_memory_path)
    try:
        latest_cycle = store.latest_run(workflow="clarity-cycle")
        review_items = store.recent_memory_by_label("review", limit=limit)
        pending_actions = store.pending_actions(limit=limit)
        approved_moves = [
            action
            for action in store.actions_by_approval_status("approved", limit=limit)
            if action.action_type.startswith("propose_email_move_")
            and action.item_external_id
            and action.action_target
        ]
        open_tasks = store.list_open_delegated_tasks()
    finally:
        store.close()

    lines = [
        "# Clarity LLM Context",
        "",
        "Purpose: bounded local context for summarization only.",
        "The model may summarize and recommend questions to ask the human.",
        "The model must not approve, execute, send, move, delete, or modify anything.",
        "",
        "## Last Cycle",
    ]
    if latest_cycle is None:
        lines.append("- none")
    else:
        lines.append(f"- Status: {latest_cycle.status}")
        lines.append(f"- Started: {latest_cycle.started_at}")
        if latest_cycle.completed_at:
            lines.append(f"- Completed: {latest_cycle.completed_at}")
        if latest_cycle.summary:
            lines.append(f"- Summary: {latest_cycle.summary}")

    lines.extend(("", "## Review Items"))
    if review_items:
        for item in review_items:
            lines.append(f"- Subject: {item.subject}")
            lines.append(f"  Source: {item.display_name} ({item.source_type})")
            if item.reason:
                lines.append(f"  Reason: {item.reason}")
    else:
        lines.append("- none")

    lines.extend(("", "## Pending Approvals"))
    if pending_actions:
        for action in pending_actions:
            lines.append(f"- Action: {action.action_id}")
            lines.append(f"  Type: {action.action_type}")
            if action.item_subject:
                lines.append(f"  Subject: {action.item_subject}")
            if action.source_scope_label:
                lines.append(f"  Mailbox: {action.source_scope_label}")
            if action.action_target:
                lines.append(f"  Target: {action.action_target}")
    else:
        lines.append("- none")

    lines.extend(("", "## Approved Email Moves"))
    if approved_moves:
        for action in approved_moves:
            lines.append(f"- Action: {action.action_id}")
            lines.append(f"  Mailbox: {action.source_scope_label or 'unknown mailbox'}")
            lines.append(f"  Message ID: {action.item_external_id}")
            if action.item_subject:
                lines.append(f"  Subject: {action.item_subject}")
            lines.append(f"  Target: {action.action_target}")
    else:
        lines.append("- none")

    lines.extend(("", "## Open Delegated Tasks"))
    if open_tasks:
        for task in open_tasks[:limit]:
            lines.append(f"- Task: {task.title}")
            lines.append(f"  Status: {task.status}")
            lines.append(f"  Approval required: {task.approval_required}")
            if task.next_step:
                lines.append(f"  Next step: {task.next_step}")
    else:
        lines.append("- none")

    return "\n".join(lines)


def _resolve_path(workspace_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return workspace_root / path
