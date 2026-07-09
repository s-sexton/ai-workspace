"""Update local assistant action approval status."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import find_workspace_root
from common.memory import (
    ACTION_APPROVAL_STATUSES,
    DuckDbMemoryStore,
    MemoryStoreError,
)


def update_action(
    *,
    action_id: str,
    approval_status: str,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
) -> str:
    """Update a local assistant action approval status."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    resolved_memory_path = _resolve_memory_path(workspace_root, Path(memory_path))
    if not resolved_memory_path.is_file():
        return f"No Clarity memory found at {resolved_memory_path}."

    store = DuckDbMemoryStore(resolved_memory_path)
    try:
        action = store.update_assistant_action_approval(
            action_id=action_id,
            approval_status=approval_status,
        )
        run = store.start_run(workflow="update-action")
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="update_action_approval",
            approval_status="not_required",
            result=(
                f"Updated assistant action {action.action_id} "
                f"to {action.approval_status}."
            ),
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary=f"Updated assistant action approval: {action.action_id}",
        )
    except MemoryStoreError as exc:
        return str(exc)
    finally:
        store.close()

    return f"Updated assistant action {action.action_id}: {action.approval_status}."


def main(argv: Sequence[str] | None = None) -> None:
    """Update assistant action approval status from the command line."""

    args = _parse_args(argv)
    print(
        update_action(
            action_id=args.action_id,
            approval_status=args.approval_status,
            memory_path=args.memory,
        )
    )


def _resolve_memory_path(workspace_root: Path, memory_path: Path) -> Path:
    if memory_path.is_absolute():
        return memory_path
    return workspace_root / memory_path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update a local Clarity action approval status."
    )
    parser.add_argument("action_id", help="Assistant action ID.")
    parser.add_argument(
        "approval_status",
        choices=ACTION_APPROVAL_STATUSES,
        help="New local approval status.",
    )
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path. Relative paths are resolved under the workspace root.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
