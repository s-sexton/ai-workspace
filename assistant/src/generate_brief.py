"""Generate a local Clarity brief from memory."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Sequence

from assistant.src.ask_memory import answer_memory_question
from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import find_workspace_root
from common.memory import DuckDbMemoryStore


DEFAULT_BRIEF_PATH = Path("reports") / "clarity-brief.md"


def generate_memory_brief(
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    output_path: Path | str = DEFAULT_BRIEF_PATH,
    generated_at: datetime | None = None,
    limit: int = 10,
) -> Path:
    """Generate a local Markdown brief from Clarity memory."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    resolved_memory_path = _resolve_path(workspace_root, Path(memory_path))
    resolved_output_path = _resolve_path(workspace_root, Path(output_path))

    if not resolved_memory_path.is_file():
        brief = f"# Clarity Brief\n\nNo Clarity memory found at {resolved_memory_path}.\n"
        resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_output_path.write_text(brief, encoding="utf-8")
        return resolved_output_path

    sections = [
        "# Clarity Brief",
        "",
        f"Generated: {(generated_at or datetime.now()).isoformat(timespec='seconds')}",
        "",
        answer_memory_question(
            "summary",
            root=workspace_root,
            memory_path=resolved_memory_path,
            limit=limit,
        ),
        "",
        answer_memory_question(
            "review-items",
            root=workspace_root,
            memory_path=resolved_memory_path,
            limit=limit,
        ),
        "",
        answer_memory_question(
            "open-tasks",
            root=workspace_root,
            memory_path=resolved_memory_path,
            limit=limit,
        ),
        "",
        answer_memory_question(
            "actions",
            root=workspace_root,
            memory_path=resolved_memory_path,
            limit=limit,
        ),
    ]
    brief = "\n".join(sections).rstrip() + "\n"

    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(brief, encoding="utf-8")
    _record_brief_memory(
        memory_path=resolved_memory_path,
        output_path=resolved_output_path,
    )
    return resolved_output_path


def main(argv: Sequence[str] | None = None) -> None:
    """Generate a local Clarity brief from memory."""

    args = _parse_args(argv)
    output_path = generate_memory_brief(
        memory_path=args.memory,
        output_path=args.output,
        limit=args.limit,
    )
    print(f"Wrote {output_path}")


def _record_brief_memory(*, memory_path: Path, output_path: Path) -> None:
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="clarity-brief")
        store.record_generated_artifact(
            run_id=run.run_id,
            artifact_type="markdown_brief",
            path=output_path,
            summary="Local Clarity memory brief.",
        )
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="generate_clarity_brief",
            approval_status="not_required",
            result=f"Wrote {output_path}",
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary="Generated local Clarity memory brief.",
        )
    finally:
        store.close()


def _resolve_path(workspace_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return workspace_root / path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a local Markdown brief from Clarity memory."
    )
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path. Relative paths are resolved under the workspace root.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_BRIEF_PATH),
        help="Brief output path. Relative paths are resolved under the workspace root.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of memory items per section.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
