"""Process Teams Workflow relay commands locally."""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Mapping, Sequence
from zoneinfo import ZoneInfo

from assistant.src.ask_memory import answer_memory_question
from assistant.src.delegate_task import delegate_task
from assistant.src.execute_email_moves import (
    build_gmail_move_transport_from_config,
    build_graph_move_transport_from_config,
    execute_email_moves,
)
from assistant.src.process_daily_brief_reply import (
    DEFAULT_DAILY_BRIEF_MANIFEST_PATH,
    process_daily_brief_reply,
)
from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from assistant.src.send_gmail_teams_summary import render_gmail_teams_summary
from assistant.src.send_jira_teams_summary import render_jira_teams_summary
from assistant.src.run_email_review import build_gmail_read_transport_from_config
from common.azure_storage_queue import AzureStorageTeamsRelayQueue
from common.azure_storage_queue import RELAY_PAYLOAD_ERROR_KEY
from common.configuration import ConfigurationError, load_workspace_config
from common.email import EmailClient
from common.jira import JiraClient, UrllibJiraTransport
from common.memory import DuckDbMemoryStore
from common.teams import (
    TeamsWebhookResponse,
    TeamsWebhookTransport,
    post_lightweight_card_to_teams,
)
from common.teams_manifest import read_teams_manifest, resolve_manifest_items
from common.teams_relay import (
    InMemoryTeamsRelayQueue,
    TeamsRelayAction,
    TeamsRelayError,
    TeamsRelayMessage,
    TeamsRelayQueue,
)


CommandHandler = Callable[[TeamsRelayMessage], str]
SleepFn = Callable[[float], None]
NowFn = Callable[[], datetime]
CENTRAL_TIME = ZoneInfo("America/Chicago")
DEFAULT_WATCHER_PID_PATH = Path("logs") / "clarity-teams-relay.pid"
MAX_TEAMS_RELAY_REPLY_CHARS = 3500


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
    receive_error_count: int


def process_next_teams_relay_message(
    *,
    queue: TeamsRelayQueue,
    allowed_senders: Sequence[str],
    allowed_sender_object_ids: Sequence[str] = (),
    require_sender_object_id: bool = False,
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
            allowed_sender_object_ids=allowed_sender_object_ids,
            require_sender_object_id=require_sender_object_id,
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
    allowed_sender_object_ids: Sequence[str] = (),
    require_sender_object_id: bool = False,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    root: Path | str | None = None,
    handlers: Mapping[str, CommandHandler] | None = None,
    limit: int = 1,
    post_replies: bool = False,
    webhook_url: str | None = None,
    reply_transport: TeamsWebhookTransport | None = None,
    action_manifest_path: Path | str | None = None,
    raise_on_error: bool = True,
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
                allowed_sender_object_ids=allowed_sender_object_ids,
                require_sender_object_id=require_sender_object_id,
                memory_path=memory_path,
                root=root,
                handlers=handlers,
                action_manifest_path=action_manifest_path,
            )
            results.append(result)
            if post_replies:
                response = _post_teams_relay_result(
                    result,
                    webhook_url=_required_webhook_url(webhook_url, root=root),
                    transport=reply_transport,
                )
                _record_teams_reply_audit(
                    memory_path=memory_path,
                    command_id=result.command_id,
                    status_code=response.status_code,
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
            if raise_on_error:
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
    allowed_sender_object_ids: Sequence[str] = (),
    require_sender_object_id: bool = False,
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
    receive_error_count = 0
    clock = now_fn or (lambda: datetime.now(CENTRAL_TIME))
    while max_iterations is None or iterations < max_iterations:
        try:
            run_result = process_teams_relay_queue(
                queue=queue,
                allowed_senders=allowed_senders,
                allowed_sender_object_ids=allowed_sender_object_ids,
                require_sender_object_id=require_sender_object_id,
                memory_path=memory_path,
                root=root,
                handlers=handlers,
                limit=limit,
                post_replies=post_replies,
                webhook_url=webhook_url,
                reply_transport=reply_transport,
                action_manifest_path=action_manifest_path,
                raise_on_error=False,
            )
        except Exception as exc:
            receive_error_count += 1
            iterations += 1
            _print(f"Queue receive failed: {exc}")
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
            continue
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
        receive_error_count=receive_error_count,
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
    allowed_sender_object_ids: Sequence[str] = (),
    require_sender_object_id: bool = False,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    root: Path | str | None = None,
    handlers: Mapping[str, CommandHandler] | None = None,
    action_manifest_path: Path | str | None = None,
) -> TeamsCommandResult:
    """Validate and process one Teams relay payload."""

    payload_error = payload.get(RELAY_PAYLOAD_ERROR_KEY)
    if isinstance(payload_error, str) and payload_error.strip():
        raise TeamsRelayError(payload_error.strip())

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
    if not _sender_object_id_allowed(
        message.sender.aad_object_id,
        allowed_sender_object_ids,
        require_sender_object_id=require_sender_object_id,
    ):
        response = "Rejected Teams command: sender object ID is not approved."
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
    if _looks_like_daily_brief_reply(message.text or ""):
        return _process_teams_daily_brief_reply(
            message,
            root=root,
            memory_path=memory_path,
        )
    text_action = parse_teams_text_action(message.text or "")
    if text_action is not None:
        return _process_teams_action_request(
            message,
            action=text_action,
            root=root,
            memory_path=memory_path,
            manifest_path=action_manifest_path,
            require_manifest_id=False,
            execute_after_approval=_text_action_requests_execution(
                message.text or ""
            ),
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
    if extract_learning_request(text) is not None:
        return "learning_request"
    if "health" in clean_text or "status" in clean_text:
        return "health"
    if "pending" in clean_text or "approval" in clean_text:
        return "pending_approvals"
    if "email" in clean_text and "move" in clean_text and "plan" in clean_text:
        return "email_move_plan"
    if (
        ("execute" in clean_text or "apply" in clean_text)
        and "gmail" in clean_text
        and ("email" in clean_text or "move" in clean_text)
    ):
        return "execute_gmail_email_moves"
    if (
        ("execute" in clean_text or "apply" in clean_text)
        and ("outlook" in clean_text or "graph" in clean_text)
        and ("email" in clean_text or "move" in clean_text)
    ):
        return "execute_graph_email_moves"
    if "comp" in clean_text and "ticket" in clean_text:
        return "open_comp_tickets"
    if "gmail" in clean_text and ("inbox" in clean_text or "email" in clean_text):
        return "gmail_inbox"
    return None


def _looks_like_daily_brief_reply(text: str) -> bool:
    clean_text = " ".join(text.strip().lower().split())
    if clean_text.startswith("clarity "):
        clean_text = clean_text.removeprefix("clarity ").strip()
    elif clean_text.startswith("@clarity "):
        clean_text = clean_text.removeprefix("@clarity ").strip()
    if not clean_text:
        return False
    if "pending cleanup actions" in clean_text:
        return True
    if re.search(r"\b(?:approve|reject)\s+action\s+[a-z0-9]{8,}\b", clean_text):
        return True
    if re.search(
        r"\b(?:delete|trash|move|file|mark sender)\s+(?:inbox|outlook|gmail|jira)\b",
        clean_text,
    ):
        return True
    if re.search(
        r"\b(?:mark|set|move|transition)\s+jira\s+(?:item\s+)?\d+",
        clean_text,
    ):
        return True
    return False


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

    def open_comp_tickets(_: TeamsRelayMessage) -> str:
        config = load_workspace_config(root, include_process_env=True)
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
        config = load_workspace_config(root, include_process_env=True)
        mailbox = "sesexton@gmail.com"
        messages = EmailClient(
            transport=build_gmail_read_transport_from_config(root=config.root)
        ).list_messages(mailbox=mailbox, limit=10).messages
        return render_gmail_teams_summary(
            messages,
            mailbox=mailbox,
            mention=None,
        )

    def email_move_plan(_: TeamsRelayMessage) -> str:
        return execute_email_moves(
            root=root,
            memory_path=memory_path,
            dry_run=True,
            limit=25,
        )

    def execute_gmail_email_moves(_: TeamsRelayMessage) -> str:
        config = load_workspace_config(root, include_process_env=True)
        if not config.teams_relay_settings.allow_provider_writes:
            return _provider_writes_disabled_response()
        gmail_mailboxes = _gmail_mailboxes_from_config(config)
        if not gmail_mailboxes:
            return "No configured Gmail mailboxes are approved for write access."
        move_transport = build_gmail_move_transport_from_config(root=config.root)
        return execute_email_moves(
            root=config.root,
            memory_path=memory_path,
            dry_run=False,
            move_transport=move_transport,
            gmail_spam_cleanup_transport=move_transport,
            include_gmail_spam_cleanup=True,
            mailboxes=gmail_mailboxes,
            limit=25,
        )

    def execute_graph_email_moves(_: TeamsRelayMessage) -> str:
        config = load_workspace_config(root, include_process_env=True)
        if not config.teams_relay_settings.allow_provider_writes:
            return _provider_writes_disabled_response()
        graph_mailboxes = _graph_mailboxes_from_config(config)
        if not graph_mailboxes:
            return "No configured Outlook/Graph mailboxes are approved for write access."
        return execute_email_moves(
            root=config.root,
            memory_path=memory_path,
            dry_run=False,
            move_transport=build_graph_move_transport_from_config(root=config.root),
            mailboxes=graph_mailboxes,
            limit=25,
        )

    def learning_request(message: TeamsRelayMessage) -> str:
        request = extract_learning_request(message.text or "")
        if request is None:
            raise TeamsRelayError("Learning request command is missing content.")
        return delegate_task(
            title="Clarity learning request",
            request=request,
            next_step="Review and decide whether to turn this into a supported Clarity behavior.",
            approval_required=True,
            root=root,
            memory_path=memory_path,
        )

    def health(_: TeamsRelayMessage) -> str:
        config = load_workspace_config(root, include_process_env=True)
        settings = config.teams_relay_settings
        return render_teams_relay_health(
            root=config.root,
            memory_path=memory_path,
            require_sender_object_id=settings.require_aad_object_id,
            approved_sender_count=len(settings.approved_sender_emails),
            approved_sender_object_id_count=len(settings.approved_sender_object_ids),
        )

    return {
        "pending_approvals": pending_approvals,
        "open_comp_tickets": open_comp_tickets,
        "gmail_inbox": gmail_inbox,
        "email_move_plan": email_move_plan,
        "execute_gmail_email_moves": execute_gmail_email_moves,
        "execute_graph_email_moves": execute_graph_email_moves,
        "learning_request": learning_request,
        "health": health,
    }


def extract_learning_request(text: str) -> str | None:
    """Return requested learning-list content from a Teams command."""

    normalized = text.strip()
    lower_normalized = normalized.lower()
    prefixes = (
        "clarity add this to your learning list:",
        "clarity, add this to your learning list:",
        "clarity to add this to your learning list:",
    )
    for prefix in prefixes:
        if lower_normalized.startswith(prefix):
            request = normalized[len(prefix) :].strip()
            return request or None
    return None


def parse_teams_text_action(text: str) -> TeamsRelayAction | None:
    """Parse a small approved-action command from Teams message text."""

    clean_text = " ".join(text.strip().lower().split())
    if clean_text.startswith("clarity "):
        clean_text = clean_text.removeprefix("clarity ").strip()
    elif clean_text.startswith("@clarity "):
        clean_text = clean_text.removeprefix("@clarity ").strip()

    action_type: str | None = None
    if re.search(r"\b(trash|delete|deleted)\b", clean_text):
        action_type = "trash"
    elif re.search(r"\b(review)\b", clean_text):
        action_type = "move_review"
    elif re.search(r"\b(noise|noisy)\b", clean_text):
        action_type = "move_noise"

    if action_type is None:
        return None

    item_numbers = tuple(int(value) for value in re.findall(r"\b\d+\b", clean_text))
    if not item_numbers:
        return None
    return TeamsRelayAction(action_type=action_type, item_numbers=item_numbers)


def _text_action_requests_execution(text: str) -> bool:
    clean_text = " ".join(text.strip().lower().split())
    return bool(
        re.search(r"\b(and execute|then execute|execute now|and apply|then apply)\b", clean_text)
    )


def _gmail_mailboxes_from_config(config) -> tuple[str, ...]:
    email_settings = config.email_settings
    return tuple(
        mailbox
        for mailbox in email_settings.approved_mailboxes
        if mailbox.endswith("@gmail.com")
        and email_settings.access_mode_for(mailbox) == "read_write"
    )


def _graph_mailboxes_from_config(config) -> tuple[str, ...]:
    email_settings = config.email_settings
    return tuple(
        mailbox
        for mailbox in email_settings.approved_mailboxes
        if not mailbox.endswith("@gmail.com")
        and email_settings.access_mode_for(mailbox) == "read_write"
    )


def _provider_writes_disabled_response() -> str:
    return (
        "Teams provider writes are disabled by configuration. Set "
        "assistant.teamsRelay.allowProviderWrites to true to allow explicit "
        "Teams execute commands."
    )


def _execute_provider_writes_for_action_ids(
    *,
    config,
    memory_path: Path | str,
    mailboxes: Sequence[str],
    action_ids: Sequence[str],
) -> str:
    if not config.teams_relay_settings.allow_provider_writes:
        return _provider_writes_disabled_response()

    gmail_mailboxes = tuple(mailbox for mailbox in mailboxes if mailbox.endswith("@gmail.com"))
    graph_mailboxes = tuple(mailbox for mailbox in mailboxes if not mailbox.endswith("@gmail.com"))
    outputs: list[str] = []
    if gmail_mailboxes:
        move_transport = build_gmail_move_transport_from_config(root=config.root)
        outputs.append(
            execute_email_moves(
                root=config.root,
                memory_path=memory_path,
                dry_run=False,
                move_transport=move_transport,
                gmail_spam_cleanup_transport=None,
                include_gmail_spam_cleanup=False,
                mailboxes=gmail_mailboxes,
                action_ids=action_ids,
                limit=max(25, len(action_ids)),
            )
        )
    if graph_mailboxes:
        outputs.append(
            execute_email_moves(
                root=config.root,
                memory_path=memory_path,
                dry_run=False,
                move_transport=build_graph_move_transport_from_config(root=config.root),
                mailboxes=graph_mailboxes,
                action_ids=action_ids,
                limit=max(25, len(action_ids)),
            )
        )
    return "\n\n".join(outputs) if outputs else "No provider write actions were eligible."


def _process_teams_daily_brief_reply(
    message: TeamsRelayMessage,
    *,
    root: Path | str | None,
    memory_path: Path | str,
) -> TeamsCommandResult:
    config = load_workspace_config(root, include_process_env=True)
    resolved_memory_path = _resolve_path(config.root, Path(memory_path))
    before_required = _required_email_action_ids(resolved_memory_path)
    reply_text = _strip_clarity_prefix(message.text or "")
    response = process_daily_brief_reply(
        reply_text,
        root=config.root,
        memory_path=resolved_memory_path,
        manifest_path=DEFAULT_DAILY_BRIEF_MANIFEST_PATH,
        execute=True,
    )
    if _text_action_requests_execution(message.text or ""):
        if not config.teams_relay_settings.allow_provider_writes:
            response = "\n\n".join((response, _provider_writes_disabled_response()))
        else:
            new_action_ids = _new_required_email_action_ids(
                resolved_memory_path,
                before_required=before_required,
            )
            if new_action_ids:
                action_mailboxes = _approve_email_actions(
                    resolved_memory_path,
                    action_ids=new_action_ids,
                )
                execution_response = _execute_provider_writes_for_action_ids(
                    config=config,
                    memory_path=resolved_memory_path,
                    mailboxes=action_mailboxes,
                    action_ids=new_action_ids,
                )
                response = "\n\n".join((response, execution_response))
            else:
                response = "\n\n".join(
                    (response, "No new email move actions were available to execute.")
                )
    _record_teams_command_audit(
        memory_path=resolved_memory_path,
        command_id=message.command_id,
        status="completed",
        response=response,
    )
    return TeamsCommandResult(
        command_id=message.command_id,
        status="completed",
        response_text=response,
    )


def _required_email_action_ids(memory_path: Path | str) -> set[str]:
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        return {
            action.action_id
            for action in store.pending_actions(limit=500)
            if action.action_type.startswith("propose_email_move_")
        }
    finally:
        store.close()


def _new_required_email_action_ids(
    memory_path: Path | str,
    *,
    before_required: set[str],
) -> tuple[str, ...]:
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        return tuple(
            action.action_id
            for action in store.pending_actions(limit=500)
            if action.action_type.startswith("propose_email_move_")
            and action.action_id not in before_required
        )
    finally:
        store.close()


def _approve_email_actions(
    memory_path: Path | str,
    *,
    action_ids: Sequence[str],
) -> tuple[str, ...]:
    store = DuckDbMemoryStore(memory_path)
    mailboxes: list[str] = []
    try:
        store.initialize_schema()
        pending_by_id = {
            action.action_id: action
            for action in store.pending_actions(limit=500)
            if action.action_type.startswith("propose_email_move_")
        }
        for action_id in action_ids:
            action = pending_by_id.get(action_id)
            if action is None:
                continue
            store.update_assistant_action_approval(
                action_id=action_id,
                approval_status="approved",
            )
            if action.source_scope_label:
                mailboxes.append(action.source_scope_label)
    finally:
        store.close()
    return tuple(dict.fromkeys(mailboxes))


def _strip_clarity_prefix(text: str) -> str:
    stripped = text.strip()
    lower = stripped.lower()
    if lower.startswith("clarity "):
        return stripped[8:].strip()
    if lower.startswith("@clarity "):
        return stripped[9:].strip()
    return stripped


def render_teams_relay_health(
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    pid_file: Path | str = DEFAULT_WATCHER_PID_PATH,
    require_sender_object_id: bool = False,
    approved_sender_count: int = 0,
    approved_sender_object_id_count: int = 0,
) -> str:
    """Render a small read-only health summary for Teams relay diagnostics."""

    resolved_root = Path(root) if root is not None else Path.cwd()
    resolved_pid_file = _resolve_path(resolved_root, Path(pid_file))
    pid_text = "missing"
    if resolved_pid_file.exists():
        pid_text = resolved_pid_file.read_text(encoding="utf-8").strip() or "empty"

    last_reply = "none recorded"
    memory = DuckDbMemoryStore(_resolve_path(resolved_root, Path(memory_path)))
    try:
        memory.initialize_schema()
        for action in memory.recent_actions(limit=25):
            if action.action_type == "post_teams_relay_reply":
                last_reply = action.result or action.created_at
                break
    finally:
        memory.close()

    return "\n".join(
        (
            "# Clarity Teams Relay Health",
            "",
            f"- Current processor PID: {os.getpid()}",
            f"- Watcher PID file: {pid_text}",
            f"- Sender object ID required: {require_sender_object_id}",
            f"- Approved sender emails: {approved_sender_count}",
            f"- Approved sender object IDs: {approved_sender_object_id_count}",
            f"- Last Teams reply: {last_reply}",
        )
    )


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


def write_watcher_pid_file(path: Path | str, *, pid: int | None = None) -> Path:
    """Write the current watcher PID to a small generated file."""

    resolved_path = Path(path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(f"{pid or os.getpid()}\n", encoding="utf-8")
    return resolved_path


def remove_watcher_pid_file_if_current(path: Path | str, *, pid: int | None = None) -> bool:
    """Remove a watcher PID file only when it still belongs to this process."""

    resolved_path = Path(path)
    if not resolved_path.exists():
        return False
    current_pid = str(pid or os.getpid())
    try:
        recorded_pid = resolved_path.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    if recorded_pid != current_pid:
        return False
    try:
        resolved_path.unlink()
    except OSError:
        return False
    return True


def _process_teams_action_request(
    message: TeamsRelayMessage,
    *,
    action: TeamsRelayAction | None = None,
    root: Path | str | None,
    memory_path: Path | str,
    manifest_path: Path | str | None,
    require_manifest_id: bool = True,
    execute_after_approval: bool = False,
) -> TeamsCommandResult:
    selected_action = action or message.action
    if selected_action is None:
        raise TeamsRelayError("Teams action is required.")
    action_type = selected_action.action_type
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
    if require_manifest_id and selected_action.manifest_id is None:
        raise TeamsRelayError("Teams action manifestId is required.")
    if not selected_action.item_numbers:
        raise TeamsRelayError("Teams action itemNumbers are required.")

    config = load_workspace_config(root, include_process_env=True)
    resolved_manifest_path = _resolve_path(
        config.root,
        Path(manifest_path or Path("reports") / "teams-gmail-manifest.json"),
    )
    manifest = read_teams_manifest(resolved_manifest_path)
    if (
        selected_action.manifest_id is not None
        and manifest.manifest_id != selected_action.manifest_id
    ):
        raise TeamsRelayError("Teams action manifestId does not match local manifest.")
    items = resolve_manifest_items(
        manifest,
        item_numbers=selected_action.item_numbers,
        required_action=action_type,
    )
    email_settings = config.email_settings
    target_folder = email_settings.folder_for_label(action_label)
    if target_folder is None:
        raise TeamsRelayError(f"No email folder policy for action: {action_type}.")

    memory = DuckDbMemoryStore(_resolve_path(config.root, Path(memory_path)))
    recorded_action_ids: list[str] = []
    action_mailboxes: list[str] = []
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
            action_record = memory.record_assistant_action(
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
            recorded_action_ids.append(action_record.action_id)
            action_mailboxes.append(item.mailbox)
            recorded += 1
        response = f"Recorded {recorded} approved local email action(s) for {target_folder}."
        if not execute_after_approval:
            response += " Run the email move executor to apply provider writes."
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
    if execute_after_approval:
        execution_response = _execute_provider_writes_for_action_ids(
            config=config,
            memory_path=memory_path,
            mailboxes=tuple(dict.fromkeys(action_mailboxes)),
            action_ids=tuple(recorded_action_ids),
        )
        response = "\n\n".join((response, execution_response))
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


def _record_teams_reply_audit(
    *,
    memory_path: Path | str,
    command_id: str,
    status_code: int,
) -> None:
    memory = DuckDbMemoryStore(memory_path)
    try:
        memory.initialize_schema()
        run = memory.start_run(workflow="teams-relay-reply")
        memory.record_assistant_action(
            run_id=run.run_id,
            action_type="post_teams_relay_reply",
            approval_status="not_required",
            action_target=command_id,
            result=f"Teams relay reply posted with status {status_code}.",
        )
        memory.finish_run(
            run.run_id,
            status="completed",
            summary=f"Teams relay reply for {command_id}: {status_code}.",
        )
    finally:
        memory.close()


def _sender_allowed(sender_email: str, allowed_senders: Sequence[str]) -> bool:
    allowed = {sender.strip().lower() for sender in allowed_senders if sender.strip()}
    return sender_email.strip().lower() in allowed


def _sender_object_id_allowed(
    sender_object_id: str | None,
    allowed_sender_object_ids: Sequence[str],
    *,
    require_sender_object_id: bool,
) -> bool:
    allowed = {
        object_id.strip().lower()
        for object_id in allowed_sender_object_ids
        if object_id.strip()
    }
    if not allowed:
        return not require_sender_object_id
    if sender_object_id is None:
        return False
    return sender_object_id.strip().lower() in allowed


def _unsupported_command_response() -> str:
    return (
        "I don't understand what you are asking yet. I can process these Teams "
        "commands locally right now: show open COMP tickets, show Gmail inbox, "
        "show pending approvals, Clarity show email move plan, Clarity health, "
        "Clarity execute Gmail email moves, Clarity execute Outlook email moves, "
        "or Clarity add this to your learning list: [request]."
    )


def _post_teams_relay_result(
    result: TeamsCommandResult,
    *,
    webhook_url: str,
    transport: TeamsWebhookTransport | None = None,
) -> TeamsWebhookResponse:
    return post_lightweight_card_to_teams(
        webhook_url=webhook_url,
        text=_format_teams_relay_result(result),
        transport=transport,
    )


def _format_teams_relay_result(result: TeamsCommandResult) -> str:
    timestamp = datetime.now(CENTRAL_TIME).strftime("%m/%d/%Y %I:%M:%S %p")
    return _limit_teams_reply_text(
        "\n".join(
            (
                "**Clarity Response**",
                "",
                f"Command: `{result.command_id}`",
                f"Status: **{result.status}**",
                f"Time: {timestamp}",
                "",
                result.response_text,
            )
        )
    )


def _limit_teams_reply_text(text: str) -> str:
    if len(text) <= MAX_TEAMS_RELAY_REPLY_CHARS:
        return text
    suffix = "\n\n_Response truncated for Teams. Ask Clarity for a narrower view._"
    return text[: MAX_TEAMS_RELAY_REPLY_CHARS - len(suffix)].rstrip() + suffix


def _console_safe(text: str) -> str:
    """Return text that can be printed on legacy Windows consoles."""

    encoding = sys.stdout.encoding or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding)


def _print(*values: object) -> None:
    print(*values, flush=True)


def _print_queue_run_result(result: TeamsRelayQueueRunResult) -> None:
    _print(f"Processed: {result.processed_count}")
    _print(f"Completed: {result.completed_count}")
    _print(f"Dead-lettered: {result.deadletter_count}")
    _print(f"Teams replies: {result.posted_count}")
    for command_result in result.results:
        _print("")
        _print(f"Command: {command_result.command_id}")
        _print(f"Status: {command_result.status}")
        _print(_console_safe(command_result.response_text))


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
        config = load_workspace_config(include_process_env=True)
        queue = build_azure_teams_relay_queue_from_config(root=config.root)
        relay_settings = config.teams_relay_settings
        allowed_senders = (
            relay_settings.approved_sender_emails
            if relay_settings.approved_sender_emails
            else tuple(args.allowed_sender)
        )
        allowed_sender_object_ids = (
            relay_settings.approved_sender_object_ids
            if relay_settings.approved_sender_object_ids
            else tuple(args.allowed_sender_object_id)
        )
        require_sender_object_id = (
            relay_settings.require_aad_object_id or args.require_sender_object_id
        )
        if args.watch:
            write_watcher_pid_file(args.pid_file)
            _print(f"Watcher PID: {os.getpid()}")
            _print(f"PID file: {args.pid_file}")
            try:
                result = watch_teams_relay_queue(
                    queue=queue,
                    allowed_senders=allowed_senders,
                    allowed_sender_object_ids=allowed_sender_object_ids,
                    require_sender_object_id=require_sender_object_id,
                    memory_path=args.memory,
                    limit=args.limit,
                    post_replies=args.post_reply,
                    action_manifest_path=args.teams_manifest,
                    active_interval_seconds=args.active_interval_seconds,
                    idle_interval_seconds=args.idle_interval_seconds,
                    active_start_hour=args.active_start_hour,
                    active_end_hour=args.active_end_hour,
                )
            finally:
                remove_watcher_pid_file_if_current(args.pid_file)
            _print("")
            _print(f"Watch iterations: {result.iterations}")
            _print(f"Total processed: {result.processed_count}")
            _print(f"Total completed: {result.completed_count}")
            _print(f"Total dead-lettered: {result.deadletter_count}")
            _print(f"Total Teams replies: {result.posted_count}")
            _print(f"Total receive errors: {result.receive_error_count}")
            return
        result = process_teams_relay_queue(
            queue=queue,
            allowed_senders=allowed_senders,
            allowed_sender_object_ids=allowed_sender_object_ids,
            require_sender_object_id=require_sender_object_id,
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
        allowed_sender_object_ids=args.allowed_sender_object_id,
        require_sender_object_id=args.require_sender_object_id,
        memory_path=args.memory,
        action_manifest_path=args.teams_manifest,
    )
    if result is None:
        _print("No Teams relay messages found.")
        return
    _print(f"Command: {result.command_id}")
    _print(f"Status: {result.status}")
    _print(_console_safe(result.response_text))


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
    parser.add_argument(
        "--allowed-sender-object-id",
        action="append",
        default=[],
        help="Approved Teams sender Entra object ID. Repeat for multiple senders.",
    )
    parser.add_argument(
        "--require-sender-object-id",
        action="store_true",
        help="Require the Teams sender Entra object ID to be approved.",
    )
    parser.add_argument("--memory", default=str(DEFAULT_MEMORY_PATH))
    parser.add_argument(
        "--teams-manifest",
        default=str(Path("reports") / "teams-gmail-manifest.json"),
        help="Teams action manifest path for card action item resolution.",
    )
    parser.add_argument(
        "--pid-file",
        default=str(DEFAULT_WATCHER_PID_PATH),
        help="Path where --watch records the running process ID.",
    )
    args = parser.parse_args(argv)
    if not args.azure and not args.text:
        parser.error("text is required unless --azure is supplied")
    if args.watch and not args.azure:
        parser.error("--watch requires --azure")
    return args


if __name__ == "__main__":
    main()
