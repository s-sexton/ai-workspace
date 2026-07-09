"""Update delegated task status in local Clarity memory."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import find_workspace_root
from common.memory import TASK_STATUSES, DuckDbMemoryStore, MemoryStoreError


def update_task(
    *,
    task_id: str,
    status: str,
    next_step: str | None = None,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
) -> str:
    """Update a delegated task in local Clarity memory."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    resolved_memory_path = _resolve_memory_path(workspace_root, Path(memory_path))
    if not resolved_memory_path.is_file():
        return f"No Clarity memory found at {resolved_memory_path}."

    store = DuckDbMemoryStore(resolved_memory_path)
    try:
        task = store.update_delegated_task_status(
            task_id=task_id,
            status=status,
            next_step=next_step,
        )
        run = store.start_run(workflow="update-task")
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="update_task",
            approval_status="not_required",
            result=f"Updated delegated task {task.task_id} to {task.status}.",
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary=f"Updated delegated task: {task.task_id}",
        )
    except MemoryStoreError as exc:
        return str(exc)
    finally:
        store.close()

    return f"Updated delegated task {task.task_id}: {task.status}."


def main(argv: Sequence[str] | None = None) -> None:
    """Update delegated work from the command line."""

    args = _parse_args(argv)
    print(
        update_task(
            task_id=args.task_id,
            status=args.status,
            next_step=args.next_step,
            memory_path=args.memory,
        )
    )


def _resolve_memory_path(workspace_root: Path, memory_path: Path) -> Path:
    if memory_path.is_absolute():
        return memory_path
    return workspace_root / memory_path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update a delegated task in local Clarity memory."
    )
    parser.add_argument("task_id", help="Delegated task ID.")
    parser.add_argument("status", choices=TASK_STATUSES, help="New task status.")
    parser.add_argument("--next-step", help="Updated next step.")
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path. Relative paths are resolved under the workspace root.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
