"""Natural-language command surface for Clarity."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from assistant.src.ask_memory import answer_memory_question
from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH


def answer_clarity_request(
    request: str,
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    limit: int = 10,
) -> str:
    """Answer a small deterministic Clarity request."""

    intent = _route_request(request)
    if intent is None:
        return _unsupported_response()
    return answer_memory_question(
        intent,
        root=root,
        memory_path=memory_path,
        limit=limit,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Run the first Clarity natural-language command surface."""

    args = _parse_args(argv)
    if args.request is None:
        _run_prompt(memory_path=args.memory, limit=args.limit)
        return

    print(
        answer_clarity_request(
            args.request,
            memory_path=args.memory,
            limit=args.limit,
        )
    )


def _route_request(request: str) -> str | None:
    clean_request = " ".join(request.lower().strip().split())
    if not clean_request:
        return None

    if any(phrase in clean_request for phrase in ("what did you do", "what happened")):
        return "actions"
    if "pending" in clean_request or "needs approval" in clean_request:
        return "pending-actions"
    if "approved" in clean_request and "move" in clean_request:
        return "email-move-plan"
    if "move plan" in clean_request or "email move" in clean_request:
        return "email-move-plan"
    if "open task" in clean_request or "delegated" in clean_request:
        return "open-tasks"
    if "noise" in clean_request or "junk" in clean_request:
        return "noise-items"
    if (
        "email" in clean_request
        and any(
            phrase in clean_request
            for phrase in ("need attention", "needs attention", "immediate attention")
        )
    ):
        return "review-items"
    if "review" in clean_request or "attention" in clean_request:
        return "review-items"
    if "summary" in clean_request or "what should i know" in clean_request:
        return "summary"
    return None


def _unsupported_response() -> str:
    return (
        "I do not know how to answer that yet from local Clarity memory.\n\n"
        "Try one of:\n"
        "- What emails need immediate attention?\n"
        "- What needs approval?\n"
        "- What did you do?\n"
        "- Show my email move plan.\n"
        "- What tasks are open?"
    )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ask Clarity a deterministic natural-language question."
    )
    parser.add_argument(
        "request",
        nargs="?",
        help="Natural-language request for Clarity. Omit to open a local prompt.",
    )
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path. Relative paths are resolved under the workspace root.",
    )
    parser.add_argument("--limit", type=int, default=10)
    return parser.parse_args(argv)


def _run_prompt(*, memory_path: Path | str, limit: int) -> None:
    print("Clarity local prompt. Type 'exit' or 'quit' to leave.")
    while True:
        try:
            request = input("Clarity> ")
        except EOFError:
            print()
            return

        clean_request = request.strip()
        if clean_request.lower() in {"exit", "quit"}:
            return
        if not clean_request:
            continue

        print(answer_clarity_request(clean_request, memory_path=memory_path, limit=limit))


if __name__ == "__main__":
    main()
