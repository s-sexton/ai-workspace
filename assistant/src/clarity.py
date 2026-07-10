"""Natural-language command surface for Clarity."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Sequence

from assistant.src.ask_memory import answer_memory_question
from assistant.src.email_preferences import record_email_sender_preference
from assistant.src.record_feedback import record_memory_feedback
from assistant.src.run_email_review import (
    build_graph_read_transport_from_config,
    run_email_review,
)
from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.console import print_text


def answer_clarity_request(
    request: str,
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    limit: int = 10,
    refresh_email: bool = False,
    mailbox: str | None = None,
    use_graph: bool = False,
    use_graph_bearer: bool = False,
    use_sample_graph: bool = False,
    brief_path: Path | str | None = None,
) -> str:
    """Answer a small deterministic Clarity request."""

    if refresh_email:
        _refresh_email_memory(
            root=root,
            mailbox=mailbox,
            limit=limit,
            memory_path=memory_path,
            brief_path=brief_path,
            use_graph=use_graph,
            use_graph_bearer=use_graph_bearer,
            use_sample_graph=use_sample_graph,
        )

    feedback_request = _parse_feedback_request(request)
    if feedback_request is not None:
        item_reference, feedback_type, feedback_text = feedback_request
        return record_memory_feedback(
            item_reference=item_reference,
            feedback_type=feedback_type,
            feedback_text=feedback_text,
            root=root,
            memory_path=memory_path,
        )

    preference_request = _parse_preference_request(request)
    if preference_request is not None:
        match_type, pattern, label = preference_request
        return record_email_sender_preference(
            mailbox=mailbox,
            match_type=match_type,
            pattern=pattern,
            label=label,
            root=root,
            memory_path=memory_path,
        )

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
        _run_prompt(
            memory_path=args.memory,
            limit=args.limit,
            refresh_email=args.refresh_email,
            mailbox=args.mailbox,
            use_graph=args.graph,
            use_graph_bearer=args.graph_bearer,
            use_sample_graph=args.sample_graph,
            brief_path=args.brief,
        )
        return

    print_text(
        answer_clarity_request(
            args.request,
            memory_path=args.memory,
            limit=args.limit,
            refresh_email=args.refresh_email,
            mailbox=args.mailbox,
            use_graph=args.graph,
            use_graph_bearer=args.graph_bearer,
            use_sample_graph=args.sample_graph,
            brief_path=args.brief,
        )
    )


def _route_request(request: str) -> str | None:
    clean_request = " ".join(request.lower().strip().split())
    if not clean_request:
        return None

    if any(
        phrase in clean_request
        for phrase in (
            "command center",
            "daily brief",
            "morning brief",
            "organize my day",
        )
    ):
        return "command-center"
    if any(
        phrase in clean_request
        for phrase in (
            "focus plan",
            "what should i focus on",
            "help me focus",
            "get organized",
            "organize me",
            "what should i work on",
        )
    ):
        return "focus-plan"
    if any(
        phrase in clean_request
        for phrase in (
            "attention brief",
            "brief me",
            "what needs my attention",
            "what should i know",
        )
    ):
        return "attention-brief"
    if any(phrase in clean_request for phrase in ("what did you do", "what happened")):
        return "actions"
    if any(
        phrase in clean_request
        for phrase in (
            "last llm brief",
            "latest llm brief",
            "last fake llm brief",
            "latest fake llm brief",
        )
    ):
        return "latest-llm-brief"
    if any(
        phrase in clean_request
        for phrase in (
            "last cycle",
            "last run",
            "when did you run",
            "when did clarity run",
        )
    ):
        return "last-cycle"
    if "pending" in clean_request or "needs approval" in clean_request:
        return "pending-actions"
    if "approved" in clean_request and "move" in clean_request:
        return "email-move-plan"
    if "move plan" in clean_request or "email move" in clean_request:
        return "email-move-plan"
    if "open task" in clean_request or "delegated" in clean_request:
        return "open-tasks"
    if "calendar" in clean_request or "schedule" in clean_request:
        return "calendar-items"
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
    if "summary" in clean_request:
        return "summary"
    return None


def _parse_feedback_request(request: str) -> tuple[str, str, str] | None:
    clean_request = " ".join(request.strip().split())
    if not clean_request:
        return None

    patterns = (
        r"^(?:mark|classify|teach)\s+(?P<item>\S+)\s+as\s+(?P<type>noise|review)(?:\s+(?:because|as|since)\s+(?P<text>.+))?$",
        r"^(?:this is|that is)\s+(?P<type>noise|review)\s+(?:for|on)\s+(?P<item>\S+)(?:\s+(?:because|as|since)\s+(?P<text>.+))?$",
    )
    for pattern in patterns:
        match = re.match(pattern, clean_request, flags=re.IGNORECASE)
        if match is None:
            continue
        item_reference = match.group("item")
        feedback_type = match.group("type").lower()
        feedback_text = match.group("text") or _default_feedback_text(feedback_type)
        return item_reference, feedback_type, feedback_text
    return None


def _parse_preference_request(request: str) -> tuple[str, str, str] | None:
    clean_request = " ".join(request.strip().split())
    if not clean_request:
        return None

    patterns = (
        r"^(?:always\s+)?mark\s+emails\s+from\s+(?P<pattern>\S+)\s+as\s+(?P<label>noise|review)$",
        r"^(?:always\s+)?classify\s+emails\s+from\s+(?P<pattern>\S+)\s+as\s+(?P<label>noise|review)$",
    )
    for pattern in patterns:
        match = re.match(pattern, clean_request, flags=re.IGNORECASE)
        if match is None:
            continue
        preference_pattern = match.group("pattern").strip().lower()
        label = match.group("label").lower()
        match_type = "sender" if "@" in preference_pattern else "domain"
        return match_type, preference_pattern, label
    return None


def _default_feedback_text(feedback_type: str) -> str:
    if feedback_type == "noise":
        return "Marked as noise from the Clarity command surface."
    return "Marked for review from the Clarity command surface."


def _unsupported_response() -> str:
    return (
        "I do not know how to answer that yet from local Clarity memory.\n\n"
        "Try one of:\n"
        "- Give me my command center.\n"
        "- What should I focus on?\n"
        "- What is on my family calendar today?\n"
        "- What emails need immediate attention?\n"
        "- What needs my attention?\n"
        "- What needs approval?\n"
        "- What did you do?\n"
        "- When did Clarity last run?\n"
        "- Show my email move plan.\n"
        "- What tasks are open?\n"
        "- Mark ITEM_ID as noise because this is promotional.\n"
        "- Mark ITEM_ID as review because this needs attention.\n"
        "- Always mark emails from sender@example.com as noise.\n"
        "- Always mark emails from example.com as review."
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
    parser.add_argument(
        "--brief",
        default=None,
        help="Local brief output path for refresh runs.",
    )
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--refresh-email",
        action="store_true",
        help="Run the configured email review before answering.",
    )
    parser.add_argument(
        "--mailbox",
        default=None,
        help="Approved mailbox to refresh before answering.",
    )
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--sample-graph",
        action="store_true",
        help="Use local Microsoft Graph-shaped sample messages during refresh.",
    )
    source_group.add_argument(
        "--graph",
        action="store_true",
        help="Read approved mailbox metadata from Microsoft Graph during refresh.",
    )
    parser.add_argument(
        "--graph-bearer",
        action="store_true",
        help="Use GRAPH_ACCESS_TOKEN instead of app-only client credentials.",
    )
    args = parser.parse_args(argv)
    if args.graph_bearer and not args.graph:
        parser.error("--graph-bearer requires --graph.")
    if (args.sample_graph or args.graph) and not args.refresh_email:
        parser.error("--sample-graph and --graph require --refresh-email.")
    return args


def _run_prompt(
    *,
    memory_path: Path | str,
    limit: int,
    refresh_email: bool,
    mailbox: str | None,
    use_graph: bool,
    use_graph_bearer: bool,
    use_sample_graph: bool,
    brief_path: Path | str | None,
) -> None:
    print_text("Clarity local prompt. Type 'exit' or 'quit' to leave.")
    while True:
        try:
            request = input("Clarity> ")
        except EOFError:
            print_text()
            return

        clean_request = request.strip()
        if clean_request.lower() in {"exit", "quit"}:
            return
        if not clean_request:
            continue

        print_text(
            answer_clarity_request(
                clean_request,
                memory_path=memory_path,
                limit=limit,
                refresh_email=refresh_email,
                mailbox=mailbox,
                use_graph=use_graph,
                use_graph_bearer=use_graph_bearer,
                use_sample_graph=use_sample_graph,
                brief_path=brief_path,
            )
        )


def _refresh_email_memory(
    *,
    root: Path | str | None,
    mailbox: str | None,
    limit: int,
    memory_path: Path | str,
    brief_path: Path | str | None,
    use_graph: bool,
    use_graph_bearer: bool,
    use_sample_graph: bool,
) -> None:
    transport = (
        build_graph_read_transport_from_config(
            root=root,
            use_bearer_auth=use_graph_bearer,
        )
        if use_graph
        else None
    )
    run_email_review(
        root=root,
        mailbox=mailbox or "",
        limit=limit,
        memory_path=memory_path,
        brief_output_path=brief_path,
        transport=transport,
        use_sample_graph=use_sample_graph,
    )


if __name__ == "__main__":
    main()
