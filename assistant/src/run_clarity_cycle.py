"""Scheduled-friendly Clarity refresh workflow."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from assistant.src.ask_memory import answer_memory_question
from assistant.src.run_email_review import (
    build_graph_read_transport_from_config,
    run_email_review,
)
from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.email import EmailTransport


@dataclass(frozen=True)
class ClarityCycleResult:
    """Safe result details for a Clarity cycle."""

    memory_path: Path
    brief_path: Path
    mailbox: str
    message_count: int
    review_count: int
    noise_count: int
    trash_count: int
    proposed_action_count: int
    review_answer: str
    pending_answer: str


def run_clarity_cycle(
    *,
    root: Path | str | None = None,
    mailbox: str | None = None,
    limit: int = 25,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    brief_path: Path | str | None = None,
    transport: EmailTransport | None = None,
    use_sample_graph: bool = False,
) -> ClarityCycleResult:
    """Refresh email memory and return the key local Clarity answers."""

    review_result = run_email_review(
        root=root,
        mailbox=mailbox or "",
        limit=limit,
        memory_path=memory_path,
        brief_output_path=brief_path,
        transport=transport,
        use_sample_graph=use_sample_graph,
    )
    review_answer = answer_memory_question(
        "review-items",
        root=root,
        memory_path=review_result.memory_path,
        limit=limit,
    )
    pending_answer = answer_memory_question(
        "pending-actions",
        root=root,
        memory_path=review_result.memory_path,
        limit=limit,
    )
    return ClarityCycleResult(
        memory_path=review_result.memory_path,
        brief_path=review_result.brief_path,
        mailbox=review_result.mailbox,
        message_count=review_result.message_count,
        review_count=review_result.review_count,
        noise_count=review_result.noise_count,
        trash_count=review_result.trash_count,
        proposed_action_count=review_result.proposed_action_count,
        review_answer=review_answer,
        pending_answer=pending_answer,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Run one non-interactive Clarity cycle."""

    args = _parse_args(argv)
    transport = (
        build_graph_read_transport_from_config(use_bearer_auth=args.graph_bearer)
        if args.graph
        else None
    )
    result = run_clarity_cycle(
        mailbox=args.mailbox,
        limit=args.limit,
        memory_path=args.memory,
        brief_path=args.brief,
        transport=transport,
        use_sample_graph=args.sample_graph,
    )
    print("# Clarity Cycle")
    print()
    print(f"Mailbox: {result.mailbox}")
    print(f"Read: {result.message_count}")
    print(f"Review: {result.review_count}")
    print(f"Noise: {result.noise_count}")
    print(f"Trash: {result.trash_count}")
    print(f"Proposed actions: {result.proposed_action_count}")
    print(f"Brief: {result.brief_path}")
    print()
    print(result.review_answer)
    print()
    print(result.pending_answer)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one scheduled-friendly Clarity refresh cycle."
    )
    parser.add_argument(
        "--mailbox",
        default=None,
        help="Approved mailbox to refresh. Defaults to the configured mailbox.",
    )
    parser.add_argument("--limit", type=int, default=25)
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--sample-graph",
        action="store_true",
        help="Use local Microsoft Graph-shaped sample messages; no network calls.",
    )
    source_group.add_argument(
        "--graph",
        action="store_true",
        help="Read approved mailbox metadata from Microsoft Graph.",
    )
    parser.add_argument(
        "--graph-bearer",
        action="store_true",
        help="Use GRAPH_ACCESS_TOKEN instead of app-only client credentials.",
    )
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path.",
    )
    parser.add_argument(
        "--brief",
        default=None,
        help="Local brief output path.",
    )
    args = parser.parse_args(argv)
    if args.graph_bearer and not args.graph:
        parser.error("--graph-bearer requires --graph.")
    return args


if __name__ == "__main__":
    main()
