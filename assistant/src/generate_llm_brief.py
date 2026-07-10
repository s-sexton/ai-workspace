"""Generate a local fake LLM brief through the safe summary pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from assistant.src.llm_summary import generate_llm_summary
from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import find_workspace_root


DEFAULT_LLM_BRIEF_PATH = Path("reports") / "clarity-llm-brief.md"


class DeterministicSummaryProvider:
    """Local provider used to exercise the LLM summary pipeline without a model."""

    def summarize(self, prompt: str) -> str:
        """Return a safe deterministic summary from the prompt text."""

        review_count = _section_item_count(prompt, "## Review Items")
        pending_count = _section_item_count(prompt, "## Pending Approvals")
        approved_move_count = _section_item_count(prompt, "## Approved Email Moves")
        task_count = _section_item_count(prompt, "## Open Delegated Tasks")
        return "\n".join(
            (
                "1. What matters now",
                f"- Review items: {review_count}",
                f"- Pending approvals: {pending_count}",
                f"- Approved email moves: {approved_move_count}",
                f"- Open delegated tasks: {task_count}",
                "",
                "2. Why it matters",
                "- These are the local Clarity items most likely to need human attention.",
                "",
                "3. What needs approval",
                "- Review pending approval action IDs before any deterministic executor runs.",
                "",
                "4. Safe next commands",
                "- python -m assistant.src.clarity \"What needs my attention?\"",
                "- python -m assistant.src.ask_memory pending-actions",
                "- python -m assistant.src.ask_memory email-move-plan",
            )
        )


def generate_fake_llm_brief(
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    output_path: Path | str = DEFAULT_LLM_BRIEF_PATH,
    limit: int = 10,
    write: bool = True,
) -> str:
    """Generate a safe local fake LLM brief and optionally write it."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    result = generate_llm_summary(
        summarizer=DeterministicSummaryProvider(),
        root=workspace_root,
        memory_path=memory_path,
        limit=limit,
    )
    report = "\n".join(
        (
            "# Clarity Fake LLM Brief",
            "",
            "This brief uses a deterministic local provider. No LLM was called.",
            "",
            result.summary,
        )
    ).rstrip() + "\n"
    if write:
        resolved_output_path = _resolve_path(workspace_root, Path(output_path))
        resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_output_path.write_text(report, encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    report = generate_fake_llm_brief(
        memory_path=args.memory,
        output_path=args.output,
        limit=args.limit,
        write=not args.no_write,
    )
    print(report, end="")
    if not args.no_write:
        print(f"\nWrote {args.output}")


def _section_item_count(text: str, heading: str) -> int:
    section = _section_text(text, heading)
    if "- none" in section:
        return 0
    return sum(1 for line in section.splitlines() if line.startswith("- "))


def _section_text(text: str, heading: str) -> str:
    marker = text.find(heading)
    if marker < 0:
        return ""
    rest = text[marker + len(heading):]
    next_heading = rest.find("\n## ")
    if next_heading >= 0:
        return rest[:next_heading]
    return rest


def _resolve_path(workspace_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return workspace_root / path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a local fake LLM brief without calling a model."
    )
    parser.add_argument("--memory", default=str(DEFAULT_MEMORY_PATH))
    parser.add_argument("--output", default=str(DEFAULT_LLM_BRIEF_PATH))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Print the fake LLM brief without writing a report.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
