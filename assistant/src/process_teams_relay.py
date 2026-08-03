"""Process Teams Workflow relay commands locally."""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Mapping, Sequence
from zoneinfo import ZoneInfo

from assistant.src.ask_memory import answer_memory_question
from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from assistant.src.send_gmail_teams_summary import render_gmail_teams_summary
from assistant.src.send_jira_teams_summary import render_jira_teams_summary
from assistant.src.run_email_review import build_gmail_read_transport_from_config
from common.azure_storage_queue import AzureStorageTeamsRelayQueue
from common.configuration import ConfigurationError, load_workspace_config
from common.email import EmailClient
from common.jira import JiraClient, UrllibJiraTransport
from common.memory import DuckDbMemoryStore
from common.teams import TeamsWebhookTransport, post_lightweight_card_to_teams
from common.teams_manifest import read_teams_manifest, resolve_manifest_items
from common.teams_relay import (
    InMemoryTeamsRelayQueue,
    TeamsRelayError,
    TeamsRelayMessage,
    TeamsRelayQueue,
)


CommandHandler = Callable[[TeamsRelayMessage], str]
SleepFn = Callable[[float], None]
NowFn = Callable[[], datetime]
CENTRAL_TIME = ZoneInfo("America/Chicago")


@dataclass(frozen=True)
class TeamsCommandResult:
    """Safe result from processing one Teams relay command."""

    command_id: str
    status: str
    response_text: str


@dataclass(frozen=True)
class TeamsRelayQueueRunResult:
    """Summary from one Teams relay queue worker run."""

    processed_count: int = 0
    completed_count: int = 0
    deadletter_count: int = 0
    posted_count: int = 0
    results: tuple[TeamsCommandResult, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TeamsRelayWatchResult:
    """Summary from a bounded Teams relay watch run."""

    iterations: int
    processed_count: int
    completed_count: int
    deadletter_count: int
    posted_count: int


def process_next_teams_relay_message(
    *,
    queue: TeamsRelayQueue,
    allowed_senders: Sequence[str],
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    root: Path | str | None = None,
    handlers: Mapping[str, CommandHandler] | None = None,
    action_manifest_path: Path | str | None = None,
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
            action_manifest_path=action_manifest_path,
        )
    except Exception as exc:
        queue.dead_letter(queue_message.queue_message_id, reason=str(exc))
        raise

    queue.complete(queue_message.queue_message_id)
    return result


def process_teams_relay_queue(
    *,
    queue: TeamsRelayQueue,
    allowed_senders: Sequence[str],
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    root: Path | str | None = None,
    handlers: Mapping[str, CommandHandler] | None = None,
    limit: int = 1,
    post_replies: bool = False,
    webhook_url: str | None = None,
    reply_transport: TeamsWebhookTransport | None = None,
    action_manifest_path: Path | str | None = None,
) -> TeamsRelayQueueRunResult:
    """Process visible Teams relay queue messages with live-worker semantics."""

    if limit < 1:
        raise TeamsRelayError("limit must be positive.")
    messages = queue.receive(limit=limit)
    results: list[TeamsCommandResult] = []
    completed_count = 0
    deadletter_count = 0
    posted_count = 0
    for queue_message in messages:
        try:
            result = process_teams_relay_payload(
                queue_message.payload,
                allowed_senders=allowed_senders,
                memory_path=memory_path,
                root=root,
                handlers=handlers,
                action_manifest_path=action_manifest_path,
            )
            results.append(result)
            if post_replies:
                _post_teams_relay_result(
                    result,
                    webhook_url=_required_webhook_url(webhook_url, root=root),
                    transport=reply_transport,
                )
                posted_count += 1
            if result.status == "completed":
                queue.complete(queue_message.queue_message_id)
                completed_count += 1
            else:
                queue.dead_letter(queue_message.queue_message_id, reason=result.status)
                deadletter_count += 1
        except Exception as exc:
            queue.dead_letter(queue_message.queue_message_id, reason=str(exc))
            deadletter_count += 1
            raise

    return TeamsRelayQueueRunResult(
        processed_count=len(messages),
        completed_count=completed_count,
        deadletter_count=deadletter_count,
        posted_count=posted_count,
        results=tuple(results),
    )


def watch_teams_relay_queue(
    *,
    queue: TeamsRelayQueue,
    allowed_senders: Sequence[str],
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    root: Path | str | None = None,
    handlers: Mapping[str, CommandHandler] | None = None,
    limit: int = 1,
    post_replies: bool = False,
    webhook_url: str | None = None,
    reply_transport: TeamsWebhookTransport | None = None,
    action_manifest_path: Path | str | None = None,
    active_interval_seconds: int = 30,
    idle_interval_seconds: int = 3600,
    active_start_hour: int = 5,
    active_end_hour: int = 19,
    now_fn: NowFn | None = None,
    sleep_fn: SleepFn = time.sleep,
    max_iterations: int | None = None,
) -> TeamsRelayWatchResult:
    """Continuously poll Teams relay messages using a business-hours cadence."""

    if active_interval_seconds < 1:
        raise TeamsRelayError("active_interval_seconds must be positive.")
    if idle_interval_seconds < 1:
        raise TeamsRelayError("idle_interval_seconds must be positive.")
    _validate_hour(active_start_hour, "active_start_hour")
    _validate_hour(active_end_hour, "active_end_hour")
    if active_start_hour == active_end_hour:
        raise TeamsRelayError("active_start_hour and active_end_hour must differ.")
    if max_iterations is not None and max_iterations < 1:
        raise TeamsRelayError("max_iterations must be positive.")

    iterations = 0
    processed_count = 0
    completed_count = 0
    deadletter_count = 0
    posted_count = 0
    clock = now_fn or (lambda: datetime.now(CENTRAL_TIME))
    while max_iterations is None or iterations < max_iterations:
        run_result = process_teams_relay_queue(
            queue=queue,
            allowed_senders=allowed_senders,
            memory_path=memory_path,
            root=root,
            handlers=handlers,
            limit=limit,
            post_replies=post_replies,
            webhook_url=webhook_url,
            reply_transport=reply_transport,
            action_manifest_path=action_manifest_path,
        )
        iterations += 1
        processed_count += run_result.processed_count
        completed_count += run_result.completed_count
        deadletter_count += run_result.deadletter_count
        posted_count += run_result.posted_count
        _print_queue_run_result(run_result)
        if max_iterations is not None and iterations >= max_iterations:
            break
        sleep_fn(
            teams_relay_poll_interval_seconds(
                now=clock(),
                active_interval_seconds=active_interval_seconds,
                idle_interval_seconds=idle_interval_seconds,
                active_start_hour=active_start_hour,
                active_end_hour=active_end_hour,
            )
        )

    return TeamsRelayWatchResult(
        iterations=iterations,
        processed_count=processed_count,
        completed_count=completed_count,
        deadletter_count=deadletter_count,
        posted_count=posted_count,
    )


def teams_relay_poll_interval_seconds(
    *,
    now: datetime,
    active_interval_seconds: int = 30,
    idle_interval_seconds: int = 3600,
    active_start_hour: int = 5,
    active_end_hour: int = 19,
) -> int:
    """Return the current Teams relay polling interval in seconds."""

    local_now = now.astimezone(CENTRAL_TIME) if now.tzinfo else now.replace(tzinfo=CENTRAL_TIME)
    if _is_active_relay_window(
        local_now,
        active_start_hour=active_start_hour,
        active_end_hour=active_end_hour,
    ):
        return active_interval_seconds
    return idle_interval_seconds


def _is_active_relay_window(
    local_now: datetime,
    *,
    active_start_hour: int,
    active_end_hour: int,
) -> bool:
    if local_now.weekday() >= 5:
        return False
    if active_start_hour < active_end_hour:
        return active_start_hour <= local_now.hour < active_end_hour
    return local_now.hour >= active_start_hour or local_now.hour < active_end_hour


def process_teams_relay_payload(
    payload: Mapping[str, object],
    *,
    allowed_senders: Sequence[str],
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    root: Path | str | None = None,
    handlers: Mapping[str, CommandHandler] | None = None,
    action_manifest_path: Path | str | None = None,
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
        return _process_teams_action_request(
            message,
            root=root,
            memory_path=memory_path,
            manifest_path=action_manifest_path,
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

    config = load_workspace_config(root, include_process_env=True)

    def pending_approvals(_: TeamsRelayMessage) -> str:
        return answer_memory_question(
            "pending-actions",
            root=root,
            memory_path=memory_path,
            limit=10,
        )

    def open_comp_tickets(_: TeamsRelayMessage) -> str:
        credentials = config.require_jira_credentials(use_cloud_route=True)
        client = JiraClient(
            settings=config.jira_settings,
            credentials=credentials,
            transport=UrllibJiraTransport(),
            jql="project = COMP AND statusCategory != Done ORDER BY updated DESC",
            use_cloud_route=True,
        )
        issues = client.fetch_report_issues().issues
        return render_jira_teams_summary(
            issues,
            site_url=credentials.site_url,
            title="Open COMP Jira Tickets",
            mention=None,
        )

    def gmail_inbox(_: TeamsRelayMessage) -> str:
        mailbox = "sesexton@gmail.com"
        messages = EmailClient(
            transport=build_gmail_read_transport_from_config(root=config.root)
        ).list_messages(mailbox=mailbox, limit=10).messages
        return render_gmail_teams_summary(
            messages,
            mailbox=mailbox,
            mention=None,
        )

    return {
        "pending_approvals": pending_approvals,
        "open_comp_tickets": open_comp_tickets,
        "gmail_inbox": gmail_inbox,
    }


def build_azure_teams_relay_queue_from_config(
    *,
    root: Path | str | None = None,
) -> AzureStorageTeamsRelayQueue:
    """Build the configured Azure Storage Queue Teams relay transport."""

    config = load_workspace_config(root, include_process_env=True)
    inbound_url = config.env.get("AZURE_TEAMS_RELAY_INBOUND_QUEUE_URL", "")
    deadletter_url = config.env.get("AZURE_TEAMS_RELAY_DEADLETTER_QUEUE_URL", "")
    missing = [
        name
        for name, value in (
            ("AZURE_TEAMS_RELAY_INBOUND_QUEUE_URL", inbound_url),
            ("AZURE_TEAMS_RELAY_DEADLETTER_QUEUE_URL", deadletter_url),
        )
        if not value.strip()
    ]
    if missing:
        raise ConfigurationError(
            "Missing required Teams relay environment values: " + ", ".join(missing)
        )
    return AzureStorageTeamsRelayQueue(
        inbound_queue_url=inbound_url,
        deadletter_queue_url=deadletter_url,
    )


def _process_teams_action_request(
    message: TeamsRelayMessage,
    *,
    root: Path | str | None,
    memory_path: Path | str,
    manifest_path: Path | str | None,
) -> TeamsCommandResult:
    if message.action is None:
        raise TeamsRelayError("Teams action is required.")
    action_type = message.action.action_type
    action_label = _email_action_label(action_type)
    if action_label is None:
        response = "Teams card action is not supported yet."
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
    if message.action.manifest_id is None:
        raise TeamsRelayError("Teams action manifestId is required.")
    if not message.action.item_numbers:
        raise TeamsRelayError("Teams action itemNumbers are required.")

    config = load_workspace_config(root, include_process_env=True)
    resolved_manifest_path = _resolve_path(
        config.root,
        Path(manifest_path or Path("reports") / "teams-gmail-manifest.json"),
    )
    manifest = read_teams_manifest(resolved_manifest_path)
    if manifest.manifest_id != message.action.manifest_id:
        raise TeamsRelayError("Teams action manifestId does not match local manifest.")
    items = resolve_manifest_items(
        manifest,
        item_numbers=message.action.item_numbers,
        required_action=action_type,
    )
    email_settings = config.email_settings
    target_folder = email_settings.folder_for_label(action_label)
    if target_folder is None:
        raise TeamsRelayError(f"No email folder policy for action: {action_type}.")

    memory = DuckDbMemoryStore(_resolve_path(config.root, Path(memory_path)))
    try:
        memory.initialize_schema()
        run = memory.start_run(workflow="teams-relay-action")
        recorded = 0
        for item in items:
            if item.source_type not in ("email", "gmail"):
                raise TeamsRelayError("Teams email actions only support email items.")
            if item.mailbox is None:
                raise TeamsRelayError("Teams email action item must include a mailbox.")
            if item.mailbox not in email_settings.approved_mailboxes:
                raise TeamsRelayError(f"Email mailbox is not approved: {item.mailbox}")
            if email_settings.access_mode_for(item.mailbox) != "read_write":
                raise TeamsRelayError(
                    f"Email mailbox is not approved for writes: {item.mailbox}"
                )
            remembered_item = memory.find_item_seen(item.external_id)
            memory.record_assistant_action(
                run_id=run.run_id,
                item_id=remembered_item.item_id if remembered_item else None,
                action_type=f"propose_email_move_{action_label}",
                approval_status="approved",
                action_target=target_folder,
                result=(
                    "Teams action approved moving "
                    f"{item.external_id} from {item.mailbox} to {target_folder}. "
                    "No provider write was performed."
                ),
            )
            recorded += 1
        response = (
            f"Recorded {recorded} approved local email action(s) for "
            f"{target_folder}. Run the email move executor to apply provider writes."
        )
        memory.record_assistant_action(
            run_id=run.run_id,
            action_type="process_teams_relay_action",
            approval_status="not_required",
            action_target=message.command_id,
            result=response,
        )
        memory.finish_run(run.run_id, status="completed", summary=response)
    finally:
        memory.close()
    return TeamsCommandResult(
        command_id=message.command_id,
        status="completed",
        response_text=response,
    )


def _email_action_label(action_type: str) -> str | None:
    return {
        "trash": "trash",
        "move_review": "review",
        "move_noise": "noise",
    }.get(action_type)


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


def _post_teams_relay_result(
    result: TeamsCommandResult,
    *,
    webhook_url: str,
    transport: TeamsWebhookTransport | None = None,
) -> None:
    post_lightweight_card_to_teams(
        webhook_url=webhook_url,
        text=_format_teams_relay_result(result),
        transport=transport,
    )


def _format_teams_relay_result(result: TeamsCommandResult) -> str:
    return "\n".join(
        (
            "**Clarity Reply**",
            "",
            f"Command: `{result.command_id}`",
            f"Status: **{result.status}**",
            "",
            result.response_text,
        )
    )


def _required_webhook_url(webhook_url: str | None, *, root: Path | str | None) -> str:
    if webhook_url is not None:
        return webhook_url
    return load_workspace_config(root, include_process_env=True).env.get(
        "TEAMS_CLARITY_WEBHOOK_URL", ""
    )


def _resolve_path(workspace_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return workspace_root / path


def _validate_hour(value: int, field_name: str) -> None:
    if value < 0 or value > 23:
        raise TeamsRelayError(f"{field_name} must be between 0 and 23.")


def main(argv: Sequence[str] | None = None) -> None:
    """Run the local or Azure Teams relay command worker."""

    args = _parse_args(argv)
    if args.azure:
        queue = build_azure_teams_relay_queue_from_config()
        if args.watch:
            result = watch_teams_relay_queue(
                queue=queue,
                allowed_senders=args.allowed_sender,
                memory_path=args.memory,
                limit=args.limit,
                post_replies=args.post_reply,
                action_manifest_path=args.teams_manifest,
                active_interval_seconds=args.active_interval_seconds,
                idle_interval_seconds=args.idle_interval_seconds,
                active_start_hour=args.active_start_hour,
                active_end_hour=args.active_end_hour,
            )
            print("")
            print(f"Watch iterations: {result.iterations}")
            print(f"Total processed: {result.processed_count}")
            print(f"Total completed: {result.completed_count}")
            print(f"Total dead-lettered: {result.deadletter_count}")
            print(f"Total Teams replies: {result.posted_count}")
            return
        result = process_teams_relay_queue(
            queue=queue,
            allowed_senders=args.allowed_sender,
            memory_path=args.memory,
            limit=args.limit,
            post_replies=args.post_reply,
            action_manifest_path=args.teams_manifest,
        )
        _print_queue_run_result(result)
        return

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
        action_manifest_path=args.teams_manifest,
    )
    if result is None:
        print("No Teams relay messages found.")
        return
    print(f"Command: {result.command_id}")
    print(f"Status: {result.status}")
    print(_console_safe(result.response_text))


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process Teams Workflow relay commands."
    )
    parser.add_argument(
        "text",
        nargs="?",
        help="Teams command text to process for the local fake queue.",
    )
    parser.add_argument(
        "--azure",
        action="store_true",
        help="Process live commands from the configured Azure Storage Queue.",
    )
    parser.add_argument(
        "--post-reply",
        action="store_true",
        help="Post command results back to Teams through TEAMS_CLARITY_WEBHOOK_URL.",
    )
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Keep polling the relay queue until stopped.",
    )
    parser.add_argument(
        "--active-interval-seconds",
        type=int,
        default=30,
        help="Watch sleep interval during active weekday hours.",
    )
    parser.add_argument(
        "--idle-interval-seconds",
        type=int,
        default=3600,
        help="Watch sleep interval outside active weekday hours.",
    )
    parser.add_argument(
        "--active-start-hour",
        type=int,
        default=5,
        help="Central-time hour when active polling starts.",
    )
    parser.add_argument(
        "--active-end-hour",
        type=int,
        default=19,
        help="Central-time hour when active polling ends.",
    )
    parser.add_argument("--sender", default="scott.sexton@sendthisfile.com")
    parser.add_argument(
        "--allowed-sender",
        action="append",
        default=["scott.sexton@sendthisfile.com"],
        help="Approved Teams sender email. Repeat for multiple senders.",
    )
    parser.add_argument("--memory", default=str(DEFAULT_MEMORY_PATH))
    parser.add_argument(
        "--teams-manifest",
        default=str(Path("reports") / "teams-gmail-manifest.json"),
        help="Teams action manifest path for card action item resolution.",
    )
    args = parser.parse_args(argv)
    if not args.azure and not args.text:
        parser.error("text is required unless --azure is supplied")
    if args.watch and not args.azure:
        parser.error("--watch requires --azure")
    return args


def _print_queue_run_result(result: TeamsRelayQueueRunResult) -> None:
    print(f"Processed: {result.processed_count}")
    print(f"Completed: {result.completed_count}")
    print(f"Dead-lettered: {result.deadletter_count}")
    print(f"Teams replies: {result.posted_count}")
    for command_result in result.results:
        print("")
        print(f"Command: {command_result.command_id}")
        print(f"Status: {command_result.status}")
        print(_console_safe(command_result.response_text))


def _console_safe(text: str) -> str:
    """Return text that can be printed on legacy Windows consoles."""

    encoding = sys.stdout.encoding or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding)


if __name__ == "__main__":
    main()
