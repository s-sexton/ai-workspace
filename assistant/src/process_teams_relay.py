"""Process Teams Workflow relay commands locally."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from assistant.src.ask_memory import answer_memory_question
from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.memory import DuckDbMemoryStore
from common.teams_relay import (
    InMemoryTeamsRelayQueue,
    TeamsQueueMessage,
    TeamsRelayError,
    TeamsRelayMessage,
    TeamsRelayQueue,
)


CommandHandler = Callable[[TeamsRelayMessage], str]


@dataclass(frozen=True)
class TeamsCommandResult:
    """Safe result from processing one Teams relay command."""

    command_id: str
    status: str
    response_text: str


def process_next_teams_relay_message(
    *,
    queue: TeamsRelayQueue,
    allowed_senders: Sequence[str],
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    root: Path | str | None = None,
    handlers: Mapping[str, CommandHandler] | None = None,
) -> TeamsCommandResult | None:
    """Process one visible Teams relay queue message."""

    messages = queue.receive(limit=1)
    if not messages:
        return None
    queue_message = messages[0]
    try:
        result = process_teams_relay_payload(
            queue_message.payload,
            allowed_senders=allowed_senders,
            memory_path=memory_path,
            root=root,
            handlers=handlers,
        )
    except Exception as exc:
        queue.dead_letter(queue_message.queue_message_id, reason=str(exc))
        raise

    queue.complete(queue_message.queue_message_id)
    return result


def process_teams_relay_payload(
    payload: Mapping[str, object],
    *,
    allowed_senders: Sequence[str],
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    root: Path | str | None = None,
    handlers: Mapping[str, CommandHandler] | None = None,
) -> TeamsCommandResult:
    """Validate and process one Teams relay payload."""

    message = TeamsRelayMessage.from_mapping(payload)
    if not _sender_allowed(message.sender.email, allowed_senders):
        response = "Rejected Teams command: sender is not approved."
        _record_teams_command_audit(
            memory_path=memory_path,
            command_id=message.command_id,
            status="rejected",
            response=response,
        )
        return TeamsCommandResult(
            command_id=message.command_id,
            status="rejected",
            response_text=response,
        )

    if message.action is not None:
        response = "Teams card actions are not enabled yet; command was recorded only."
        _record_teams_command_audit(
            memory_path=memory_path,
            command_id=message.command_id,
            status="unsupported_action",
            response=response,
        )
        return TeamsCommandResult(
            command_id=message.command_id,
            status="unsupported_action",
            response_text=response,
        )

    route = route_teams_text_command(message.text or "")
    if route is None:
        response = _unsupported_command_response()
        _record_teams_command_audit(
            memory_path=memory_path,
            command_id=message.command_id,
            status="unsupported",
            response=response,
        )
        return TeamsCommandResult(
            command_id=message.command_id,
            status="unsupported",
            response_text=response,
        )

    active_handlers = handlers or default_teams_command_handlers(
        root=root,
        memory_path=memory_path,
    )
    handler = active_handlers.get(route)
    if handler is None:
        raise TeamsRelayError(f"No Teams command handler configured for {route}.")
    response = handler(message)
    _record_teams_command_audit(
        memory_path=memory_path,
        command_id=message.command_id,
        status="completed",
        response=response,
    )
    return TeamsCommandResult(
        command_id=message.command_id,
        status="completed",
        response_text=response,
    )


def route_teams_text_command(text: str) -> str | None:
    """Route supported read-only Teams command text."""

    clean_text = " ".join(text.strip().lower().split())
    if not clean_text:
        return None
    if "pending" in clean_text or "approval" in clean_text:
        return "pending_approvals"
    if "comp" in clean_text and "ticket" in clean_text:
        return "open_comp_tickets"
    if "gmail" in clean_text and ("inbox" in clean_text or "email" in clean_text):
        return "gmail_inbox"
    return None


def default_teams_command_handlers(
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
) -> Mapping[str, CommandHandler]:
    """Return local read-only Teams command handlers."""

    def pending_approvals(_: TeamsRelayMessage) -> str:
        return answer_memory_question(
            "pending-actions",
            root=root,
            memory_path=memory_path,
            limit=10,
        )

    return {
        "pending_approvals": pending_approvals,
        "open_comp_tickets": lambda _: (
            "Open COMP ticket refresh is available from Teams summaries; "
            "live relay execution will be wired after the local queue path is proven."
        ),
        "gmail_inbox": lambda _: (
            "Gmail inbox refresh is available from Teams summaries; "
            "live relay execution will be wired after the local queue path is proven."
        ),
    }


def _record_teams_command_audit(
    *,
    memory_path: Path | str,
    command_id: str,
    status: str,
    response: str,
) -> None:
    memory = DuckDbMemoryStore(memory_path)
    try:
        memory.initialize_schema()
        run = memory.start_run(workflow="teams-relay-command")
        memory.record_assistant_action(
            run_id=run.run_id,
            action_type="process_teams_relay_command",
            approval_status="not_required",
            action_target=command_id,
            result=f"{status}: {response}",
        )
        memory.finish_run(
            run.run_id,
            status="completed" if status == "completed" else "rejected",
            summary=f"Teams relay command {command_id}: {status}.",
        )
    finally:
        memory.close()


def _sender_allowed(sender_email: str, allowed_senders: Sequence[str]) -> bool:
    allowed = {sender.strip().lower() for sender in allowed_senders if sender.strip()}
    return sender_email.strip().lower() in allowed


def _unsupported_command_response() -> str:
    return (
        "I can only process these Teams relay commands locally right now: "
        "show open COMP tickets, show Gmail inbox, or show pending approvals."
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Run a local fake Teams relay command."""

    args = _parse_args(argv)
    queue = InMemoryTeamsRelayQueue()
    queue.enqueue(
        {
            "schemaVersion": 1,
            "source": "teams",
            "commandId": "local-sample-command",
            "receivedAt": "2026-08-03T15:30:00Z",
            "from": {
                "displayName": "Scott Sexton",
                "email": args.sender,
            },
            "conversation": {
                "team": "AI Workspace",
                "channel": "Clarity",
            },
            "text": args.text,
            "action": None,
        }
    )
    result = process_next_teams_relay_message(
        queue=queue,
        allowed_senders=args.allowed_sender,
        memory_path=args.memory,
    )
    if result is None:
        print("No Teams relay messages found.")
        return
    print(f"Command: {result.command_id}")
    print(f"Status: {result.status}")
    print(result.response_text)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process a local fake Teams Workflow relay command."
    )
    parser.add_argument("text", help="Teams command text to process.")
    parser.add_argument("--sender", default="scott.sexton@sendthisfile.com")
    parser.add_argument(
        "--allowed-sender",
        action="append",
        default=["scott.sexton@sendthisfile.com"],
        help="Approved Teams sender email. Repeat for multiple senders.",
    )
    parser.add_argument("--memory", default=str(DEFAULT_MEMORY_PATH))
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
