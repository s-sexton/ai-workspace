"""Read-only questions over local Clarity memory."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import find_workspace_root
from common.memory import DuckDbMemoryStore


SUPPORTED_QUESTIONS = (
    "summary",
    "latest-jira-run",
    "recent-items",
    "review-items",
    "noise-items",
    "feedback",
    "actions",
    "pending-actions",
    "approved-actions",
    "email-move-plan",
    "open-tasks",
)


def answer_memory_question(
    question: str,
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    limit: int = 10,
) -> str:
    """Answer a supported question from local Clarity memory."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    resolved_memory_path = _resolve_memory_path(workspace_root, Path(memory_path))
    if not resolved_memory_path.is_file():
        return f"No Clarity memory found at {resolved_memory_path}."

    store = DuckDbMemoryStore(resolved_memory_path)
    try:
        if question == "summary":
            return _format_summary(store, limit=limit)
        if question == "latest-jira-run":
            return _answer_latest_jira_run(store)
        if question == "recent-items":
            return _format_recent_items(
                "Recent Items",
                store.recent_memory(limit=limit),
            )
        if question == "review-items":
            return _format_recent_items(
                "Items Marked For Review",
                store.recent_memory_by_label("review", limit=limit),
            )
        if question == "noise-items":
            return _format_recent_items(
                "Items Marked As Noise",
                store.recent_memory_by_label("noise", limit=limit),
            )
        if question == "feedback":
            return _format_feedback(store, limit=limit)
        if question == "actions":
            return _format_actions(store, limit=limit)
        if question == "pending-actions":
            return _format_pending_actions(store, limit=limit)
        if question == "approved-actions":
            return _format_approved_actions(store, limit=limit)
        if question == "email-move-plan":
            return _format_email_move_plan(store, limit=limit)
        if question == "open-tasks":
            return _format_open_tasks(store)
    finally:
        store.close()

    supported = ", ".join(SUPPORTED_QUESTIONS)
    return f"Unsupported question: {question}. Supported questions: {supported}."


def main(argv: Sequence[str] | None = None) -> None:
    """Print an answer from local Clarity memory."""

    args = _parse_args(argv)
    print(
        answer_memory_question(
            args.question,
            memory_path=args.memory,
            limit=args.limit,
        )
    )


def _answer_latest_jira_run(store: DuckDbMemoryStore) -> str:
    run = store.latest_run(workflow="jira-report")
    if run is None:
        return "No Jira report runs found in Clarity memory."

    lines = [
        "# Latest Jira Report Run",
        "",
        f"- Run ID: {run.run_id}",
        f"- Status: {run.status}",
        f"- Started: {run.started_at}",
    ]
    if run.completed_at is not None:
        lines.append(f"- Completed: {run.completed_at}")
    if run.summary:
        lines.append(f"- Summary: {run.summary}")
    artifacts = store.list_generated_artifacts(run_id=run.run_id)
    for artifact in artifacts:
        lines.append(f"- Artifact: {artifact.path} ({artifact.artifact_type})")
        if artifact.summary:
            lines.append(f"  Artifact summary: {artifact.summary}")
    return "\n".join(lines)


def _format_summary(store: DuckDbMemoryStore, *, limit: int) -> str:
    latest_run = store.latest_run(workflow="jira-report")
    review_items = store.recent_memory_by_label("review", limit=limit)
    noise_items = store.recent_memory_by_label("noise", limit=limit)
    feedback_records = store.recent_feedback(limit=limit)
    open_tasks = store.list_open_delegated_tasks()

    lines = ["# Clarity Memory Summary", ""]
    if latest_run is None:
        lines.append("- Latest Jira run: none")
    else:
        run_summary = latest_run.summary or latest_run.status
        lines.append(f"- Latest Jira run: {run_summary}")
    lines.append(f"- Items marked for review: {len(review_items)}")
    lines.append(f"- Items marked as noise: {len(noise_items)}")
    lines.append(f"- Recent feedback records: {len(feedback_records)}")
    lines.append(f"- Open delegated tasks: {len(open_tasks)}")
    if open_tasks:
        lines.append("")
        lines.append("## Next Attention")
        for task in open_tasks[:3]:
            lines.append(f"- {task.title}: {task.next_step or task.status}")
    return "\n".join(lines)


def _format_recent_items(title: str, records) -> str:
    if not records:
        return f"# {title}\n\nNo matching items found in Clarity memory."

    lines = [f"# {title}", ""]
    for record in records:
        label = f" [{record.label}]" if record.label else ""
        lines.append(f"- {record.subject}{label}")
        lines.append(f"  Source: {record.display_name} ({record.source_type})")
        if record.reason:
            lines.append(f"  Reason: {record.reason}")
    return "\n".join(lines)


def _format_open_tasks(store: DuckDbMemoryStore) -> str:
    tasks = store.list_open_delegated_tasks()
    if not tasks:
        return "# Open Delegated Tasks\n\nNo open delegated tasks found."

    lines = ["# Open Delegated Tasks", ""]
    for task in tasks:
        approval = "approval required" if task.approval_required else "no approval required"
        lines.append(f"- {task.title} [{task.status}, {approval}]")
        lines.append(f"  Request: {task.request}")
        if task.next_step:
            lines.append(f"  Next step: {task.next_step}")
    return "\n".join(lines)


def _format_feedback(store: DuckDbMemoryStore, *, limit: int) -> str:
    feedback_records = store.recent_feedback(limit=limit)
    if not feedback_records:
        return "# Recent Feedback\n\nNo feedback found in Clarity memory."

    lines = ["# Recent Feedback", ""]
    for feedback in feedback_records:
        lines.append(
            f"- {feedback.external_id}: {feedback.feedback_type} - {feedback.subject}"
        )
        lines.append(f"  Feedback: {feedback.feedback_text}")
    return "\n".join(lines)


def _format_actions(store: DuckDbMemoryStore, *, limit: int) -> str:
    actions = store.recent_actions(limit=limit)
    if not actions:
        return "# Recent Actions\n\nNo actions found in Clarity memory."

    lines = ["# Recent Actions", ""]
    for action in actions:
        lines.append(f"- {action.action_type} [{action.approval_status}]")
        if action.result:
            lines.append(f"  Result: {action.result}")
    return "\n".join(lines)


def _format_pending_actions(store: DuckDbMemoryStore, *, limit: int) -> str:
    pending_actions = store.pending_actions(limit=limit)
    if not pending_actions:
        return "# Pending Actions\n\nNo pending actions found."

    return _format_action_queue("Pending Actions", pending_actions)


def _format_approved_actions(store: DuckDbMemoryStore, *, limit: int) -> str:
    approved_actions = store.actions_by_approval_status("approved", limit=limit)
    if not approved_actions:
        return "# Approved Actions\n\nNo approved actions found."

    return _format_action_queue("Approved Actions", approved_actions)


def _format_email_move_plan(store: DuckDbMemoryStore, *, limit: int) -> str:
    approved_actions = store.actions_by_approval_status("approved", limit=limit)
    move_actions = [
        action
        for action in approved_actions
        if action.action_type.startswith("propose_email_move_")
        and action.item_external_id
        and action.action_target
    ]
    if not move_actions:
        return "# Email Move Plan\n\nNo approved email moves found."

    lines = ["# Email Move Plan", ""]
    for action in move_actions:
        source_scope = action.source_scope_label or "unknown mailbox"
        lines.append(
            f"- In mailbox {source_scope}, move message "
            f"{action.item_external_id} to {action.action_target}"
        )
        if action.item_subject:
            lines.append(f"  Subject: {action.item_subject}")
        lines.append(f"  Action: {action.action_id}")
    return "\n".join(lines)


def _format_action_queue(title: str, actions) -> str:
    lines = [f"# {title}", ""]
    for action in actions:
        subject = f" - {action.item_subject}" if action.item_subject else ""
        lines.append(f"- {action.action_type}{subject} [{action.approval_status}]")
        if action.item_external_id:
            lines.append(f"  Item: {action.item_external_id}")
        if action.source_scope_label:
            lines.append(f"  Source: {action.source_scope_label}")
        if action.action_target:
            lines.append(f"  Target: {action.action_target}")
        if action.result:
            lines.append(f"  Proposal: {action.result}")
    return "\n".join(lines)


def _resolve_memory_path(workspace_root: Path, memory_path: Path) -> Path:
    if memory_path.is_absolute():
        return memory_path
    return workspace_root / memory_path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ask a read-only question from local Clarity memory."
    )
    parser.add_argument(
        "question",
        choices=SUPPORTED_QUESTIONS,
        help="Question to answer from local memory.",
    )
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path. Relative paths are resolved under the workspace root.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of memory items to show.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
