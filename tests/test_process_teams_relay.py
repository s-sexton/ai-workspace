from __future__ import annotations

from typing import Any, Mapping

from common.memory import DuckDbMemoryStore
from common.teams import TeamsWebhookResponse
from common.teams_relay import InMemoryTeamsRelayQueue
from assistant.src.process_teams_relay import (
    process_teams_relay_queue,
    process_next_teams_relay_message,
    process_teams_relay_payload,
    route_teams_text_command,
)


def test_route_teams_text_command_supports_read_only_commands():
    assert route_teams_text_command("show open COMP tickets") == "open_comp_tickets"
    assert route_teams_text_command("show Gmail inbox") == "gmail_inbox"
    assert route_teams_text_command("what needs approval?") == "pending_approvals"


def test_process_teams_relay_payload_rejects_unapproved_sender(tmp_path):
    memory_path = tmp_path / "memory.duckdb"

    result = process_teams_relay_payload(
        _payload(sender="intruder@example.com"),
        allowed_senders=("scott@example.com",),
        memory_path=memory_path,
    )

    assert result.status == "rejected"
    assert "sender is not approved" in result.response_text
    assert _recent_action_result(memory_path).startswith("rejected:")


def test_process_teams_relay_payload_uses_injected_handler(tmp_path):
    result = process_teams_relay_payload(
        _payload(text="show open COMP tickets"),
        allowed_senders=("scott@example.com",),
        memory_path=tmp_path / "memory.duckdb",
        handlers={"open_comp_tickets": lambda message: f"Handled {message.command_id}"},
    )

    assert result.status == "completed"
    assert result.response_text == "Handled cmd-1"


def test_process_next_teams_relay_message_completes_success(tmp_path):
    queue = InMemoryTeamsRelayQueue()
    queued = queue.enqueue(_payload(text="show Gmail inbox"))

    result = process_next_teams_relay_message(
        queue=queue,
        allowed_senders=("scott@example.com",),
        memory_path=tmp_path / "memory.duckdb",
        handlers={"gmail_inbox": lambda _: "Gmail handled"},
    )

    assert result is not None
    assert result.status == "completed"
    assert queue.receive() == ()
    assert queue.completed[0].queue_message_id == queued.queue_message_id


def test_process_teams_relay_queue_posts_reply_and_completes_success(tmp_path):
    queue = InMemoryTeamsRelayQueue()
    queued = queue.enqueue(_payload(text="show Gmail inbox"))
    transport = RecordingTeamsTransport()

    result = process_teams_relay_queue(
        queue=queue,
        allowed_senders=("scott@example.com",),
        memory_path=tmp_path / "memory.duckdb",
        handlers={"gmail_inbox": lambda _: "Gmail handled"},
        post_replies=True,
        webhook_url="https://example.webhook.office.com/test",
        reply_transport=transport,
    )

    assert result.processed_count == 1
    assert result.completed_count == 1
    assert result.deadletter_count == 0
    assert result.posted_count == 1
    assert queue.receive() == ()
    assert queue.completed[0].queue_message_id == queued.queue_message_id
    _, payload, _ = transport.calls[0]
    body = payload["attachments"][0]["content"]["body"][0]["text"]
    assert "Gmail handled" in body


def test_process_teams_relay_queue_deadletters_rejected_sender(tmp_path):
    queue = InMemoryTeamsRelayQueue()
    queued = queue.enqueue(_payload(sender="intruder@example.com"))

    result = process_teams_relay_queue(
        queue=queue,
        allowed_senders=("scott@example.com",),
        memory_path=tmp_path / "memory.duckdb",
        post_replies=False,
    )

    assert result.processed_count == 1
    assert result.completed_count == 0
    assert result.deadletter_count == 1
    assert queue.receive() == ()
    dead_lettered, reason = queue.dead_letters[0]
    assert dead_lettered.queue_message_id == queued.queue_message_id
    assert reason == "rejected"


def test_process_teams_relay_action_is_recorded_but_not_executed(tmp_path):
    result = process_teams_relay_payload(
        _payload(
            text=None,
            action={
                "type": "gmail_trash",
                "manifestId": "manifest-1",
                "itemNumbers": [1],
            },
        ),
        allowed_senders=("scott@example.com",),
        memory_path=tmp_path / "memory.duckdb",
    )

    assert result.status == "unsupported_action"
    assert "not enabled yet" in result.response_text


def _recent_action_result(memory_path):
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        return store.recent_actions()[0].result
    finally:
        store.close()


def _payload(*, text="show pending approvals", sender="scott@example.com", action=None):
    return {
        "schemaVersion": 1,
        "source": "teams",
        "commandId": "cmd-1",
        "receivedAt": "2026-08-03T15:30:00Z",
        "from": {
            "displayName": "Scott Sexton",
            "email": sender,
        },
        "conversation": {
            "team": "AI Workspace",
            "channel": "Clarity",
        },
        "text": text,
        "action": action,
    }


class RecordingTeamsTransport:
    def __init__(self):
        self.calls: list[tuple[str, Mapping[str, Any], Mapping[str, str]]] = []

    def post(
        self,
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
    ) -> TeamsWebhookResponse:
        self.calls.append((url, payload, headers))
        return TeamsWebhookResponse(status_code=202)
