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
    "feedback",
    "actions",
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
        if question == "feedback":
            return _format_feedback(store, limit=limit)
        if question == "actions":
            return _format_actions(store, limit=limit)
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
    feedback_records = store.recent_feedback(limit=limit)
    open_tasks = store.list_open_delegated_tasks()

    lines = ["# Clarity Memory Summary", ""]
    if latest_run is None:
        lines.append("- Latest Jira run: none")
    else:
        run_summary = latest_run.summary or latest_run.status
        lines.append(f"- Latest Jira run: {run_summary}")
    lines.append(f"- Items marked for review: {len(review_items)}")
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
