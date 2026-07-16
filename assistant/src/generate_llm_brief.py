"""Generate a local fake LLM brief through the safe summary pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from assistant.src.llm_context import build_llm_prompt
from assistant.src.llm_summary import generate_llm_summary
from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import find_workspace_root, load_workspace_config
from common.memory import DuckDbMemoryStore
from common.openai_llm import (
    OpenAITransport,
    build_openai_summary_provider,
)


DEFAULT_LLM_BRIEF_PATH = Path("reports") / "clarity-llm-brief.md"
DEFAULT_CODEX_HANDOFF_PATH = Path("reports") / "clarity-codex-handoff.md"


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
        _record_llm_brief_memory(
            memory_path=_resolve_path(workspace_root, Path(memory_path)),
            output_path=resolved_output_path,
        )
    return report


def generate_openai_llm_brief(
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    output_path: Path | str = DEFAULT_LLM_BRIEF_PATH,
    limit: int = 10,
    write: bool = True,
    transport: OpenAITransport | None = None,
) -> str:
    """Generate a validated live OpenAI LLM brief and optionally write it."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    config = load_workspace_config(workspace_root)
    provider = build_openai_summary_provider(
        config.require_openai_credentials(),
        transport=transport,
    )
    result = generate_llm_summary(
        summarizer=provider,
        root=workspace_root,
        memory_path=memory_path,
        limit=limit,
    )
    report = "\n".join(
        (
            "# Clarity LLM Brief",
            "",
            "This brief was generated from bounded local Clarity context.",
            "",
            result.summary,
        )
    ).rstrip() + "\n"
    if write:
        resolved_output_path = _resolve_path(workspace_root, Path(output_path))
        resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_output_path.write_text(report, encoding="utf-8")
        _record_llm_brief_memory(
            memory_path=_resolve_path(workspace_root, Path(memory_path)),
            output_path=resolved_output_path,
            workflow="llm-brief",
            artifact_type="markdown_llm_brief",
            action_type="generate_llm_brief",
            summary="Generated validated OpenAI LLM brief.",
        )
    return report


def generate_codex_handoff(
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    output_path: Path | str = DEFAULT_CODEX_HANDOFF_PATH,
    limit: int = 10,
    user_request: str | None = None,
    write: bool = True,
) -> str:
    """Generate a Codex-ready handoff without calling an LLM provider."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    prompt = build_llm_prompt(
        root=workspace_root,
        memory_path=memory_path,
        limit=limit,
        user_request=user_request,
    )
    report = "\n".join(
        (
            "# Clarity Codex Handoff",
            "",
            "Use this with ChatGPT/Codex as the summarization surface. No API call was made.",
            "",
            "Instructions for Codex:",
            "",
            "- Summarize the bounded Clarity context below.",
            "- Recommend what needs attention and what needs approval.",
            "- Do not claim that any action was performed.",
            "- Do not ask for secrets or credentials.",
            "- Do not approve, send, move, delete, create, or modify anything.",
            "",
            "Copy-ready request:",
            "",
            "```text",
            "Summarize this Clarity handoff and help me decide what to focus on.",
            "```",
            "",
            "Bounded Clarity prompt:",
            "",
            "```text",
            prompt,
            "```",
        )
    ).rstrip() + "\n"
    if write:
        resolved_output_path = _resolve_path(workspace_root, Path(output_path))
        resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_output_path.write_text(report, encoding="utf-8")
        _record_llm_brief_memory(
            memory_path=_resolve_path(workspace_root, Path(memory_path)),
            output_path=resolved_output_path,
            workflow="codex-handoff",
            artifact_type="markdown_codex_handoff",
            action_type="generate_codex_handoff",
            summary="Generated Codex-ready Clarity handoff.",
        )
    return report


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.codex_handoff:
        report = generate_codex_handoff(
            memory_path=args.memory,
            output_path=args.output,
            limit=args.limit,
            user_request=args.request,
            write=not args.no_write,
        )
    elif args.openai:
        report = generate_openai_llm_brief(
            memory_path=args.memory,
            output_path=args.output,
            limit=args.limit,
            write=not args.no_write,
        )
    else:
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


def _record_llm_brief_memory(
    *,
    memory_path: Path,
    output_path: Path,
    workflow: str = "fake-llm-brief",
    artifact_type: str = "markdown_fake_llm_brief",
    action_type: str = "generate_fake_llm_brief",
    summary: str = "Generated local deterministic fake LLM brief.",
) -> None:
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow=workflow)
        store.record_generated_artifact(
            run_id=run.run_id,
            artifact_type=artifact_type,
            path=output_path,
            summary=summary,
        )
        store.record_assistant_action(
            run_id=run.run_id,
            action_type=action_type,
            approval_status="not_required",
            result=f"Wrote {output_path}",
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary=summary,
        )
    finally:
        store.close()


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a local fake LLM brief without calling a model."
    )
    parser.add_argument("--memory", default=str(DEFAULT_MEMORY_PATH))
    parser.add_argument("--output", default=str(DEFAULT_LLM_BRIEF_PATH))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--request",
        default=None,
        help="Optional human request to include in the generated prompt.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Print the fake LLM brief without writing a report.",
    )
    parser.add_argument(
        "--openai",
        action="store_true",
        help="Use the live OpenAI Responses API instead of the deterministic provider.",
    )
    parser.add_argument(
        "--codex-handoff",
        action="store_true",
        help="Write a Codex-ready handoff prompt without calling an API provider.",
    )
    args = parser.parse_args(argv)
    if args.openai and args.codex_handoff:
        parser.error("--openai and --codex-handoff are mutually exclusive.")
    if args.codex_handoff and args.output == str(DEFAULT_LLM_BRIEF_PATH):
        args.output = str(DEFAULT_CODEX_HANDOFF_PATH)
    return args


if __name__ == "__main__":
    main()
