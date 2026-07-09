"""Record human feedback into local Clarity memory."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import find_workspace_root
from common.memory import DuckDbMemoryStore


FEEDBACK_TYPES = (
    "useful",
    "noise",
    "review",
    "wrong",
)


def record_memory_feedback(
    *,
    item_reference: str,
    feedback_type: str,
    feedback_text: str,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
) -> str:
    """Record feedback for a remembered item and return a safe summary."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    resolved_memory_path = _resolve_memory_path(workspace_root, Path(memory_path))
    if not resolved_memory_path.is_file():
        return f"No Clarity memory found at {resolved_memory_path}."

    if feedback_type not in FEEDBACK_TYPES:
        supported = ", ".join(FEEDBACK_TYPES)
        return f"Unsupported feedback type: {feedback_type}. Supported types: {supported}."

    store = DuckDbMemoryStore(resolved_memory_path)
    try:
        item = store.find_item_seen(item_reference)
        if item is None:
            return f"No remembered item found for: {item_reference}."

        run = store.latest_run()
        if run is None:
            return "No Clarity runs found for feedback."

        feedback = store.record_feedback(
            item_id=item.item_id,
            run_id=run.run_id,
            feedback_type=feedback_type,
            feedback_text=feedback_text,
        )
        store.record_assistant_action(
            run_id=run.run_id,
            item_id=item.item_id,
            action_type="record_feedback",
            approval_status="not_required",
            result=f"Recorded {feedback.feedback_type} feedback for {item.external_id}.",
        )
    finally:
        store.close()

    return (
        "Recorded feedback "
        f"{feedback.feedback_id} for {item.external_id}: {feedback.feedback_type}."
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Record local human feedback for a remembered item."""

    args = _parse_args(argv)
    print(
        record_memory_feedback(
            item_reference=args.item,
            feedback_type=args.feedback_type,
            feedback_text=args.text,
            memory_path=args.memory,
        )
    )


def _resolve_memory_path(workspace_root: Path, memory_path: Path) -> Path:
    if memory_path.is_absolute():
        return memory_path
    return workspace_root / memory_path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record local feedback for a remembered Clarity item."
    )
    parser.add_argument(
        "item",
        help="Remembered item ID or external ID, such as a Jira key.",
    )
    parser.add_argument(
        "feedback_type",
        choices=FEEDBACK_TYPES,
        help="Feedback category.",
    )
    parser.add_argument(
        "text",
        help="Short feedback note.",
    )
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path. Relative paths are resolved under the workspace root.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
