"""Record delegated work in local Clarity memory."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import find_workspace_root
from common.memory import DuckDbMemoryStore


def delegate_task(
    *,
    title: str,
    request: str,
    next_step: str | None = None,
    approval_required: bool = True,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
) -> str:
    """Record a delegated task in local Clarity memory."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    resolved_memory_path = _resolve_memory_path(workspace_root, Path(memory_path))
    resolved_memory_path.parent.mkdir(parents=True, exist_ok=True)

    store = DuckDbMemoryStore(resolved_memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="delegated-task")
        task = store.create_delegated_task(
            created_run_id=run.run_id,
            title=title,
            request=request,
            next_step=next_step,
            approval_required=approval_required,
        )
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="delegate_task",
            approval_status="not_required",
            result=f"Recorded delegated task {task.task_id}.",
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary=f"Recorded delegated task: {task.title}",
        )
    finally:
        store.close()

    return f"Recorded delegated task {task.task_id}: {task.title}."


def main(argv: Sequence[str] | None = None) -> None:
    """Record delegated work from the command line."""

    args = _parse_args(argv)
    print(
        delegate_task(
            title=args.title,
            request=args.request,
            next_step=args.next_step,
            approval_required=not args.no_approval_required,
            memory_path=args.memory,
        )
    )


def _resolve_memory_path(workspace_root: Path, memory_path: Path) -> Path:
    if memory_path.is_absolute():
        return memory_path
    return workspace_root / memory_path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record a delegated task in local Clarity memory."
    )
    parser.add_argument("title", help="Short task title.")
    parser.add_argument("request", help="What Clarity should remember about the task.")
    parser.add_argument(
        "--next-step",
        help="Suggested next step or current blocker.",
    )
    parser.add_argument(
        "--no-approval-required",
        action="store_true",
        help="Mark the task as not requiring approval for local-only follow-up.",
    )
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path. Relative paths are resolved under the workspace root.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
