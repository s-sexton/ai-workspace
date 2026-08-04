from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from common.memory import DuckDbMemoryStore
from common.azure_storage_queue import RELAY_PAYLOAD_ERROR_KEY
from common.teams import TeamsWebhookResponse
from common.teams_manifest import TeamsManifestItem, create_teams_manifest, write_teams_manifest
from common.teams_relay import InMemoryTeamsRelayQueue
from assistant.src.process_teams_relay import (
    MAX_TEAMS_RELAY_REPLY_CHARS,
    TeamsCommandResult,
    _format_teams_relay_result,
    extract_learning_request,
    process_teams_relay_queue,
    process_next_teams_relay_message,
    process_teams_relay_payload,
    remove_watcher_pid_file_if_current,
    render_teams_relay_health,
    route_teams_text_command,
    teams_relay_poll_interval_seconds,
    watch_teams_relay_queue,
    write_watcher_pid_file,
)


def test_route_teams_text_command_supports_read_only_commands():
    assert route_teams_text_command("show open COMP tickets") == "open_comp_tickets"
    assert route_teams_text_command("show Gmail inbox") == "gmail_inbox"
    assert route_teams_text_command("what needs approval?") == "pending_approvals"
    assert route_teams_text_command("Clarity health") == "health"
    assert (
        route_teams_text_command(
            "Clarity add this to your learning list: remember this syntax"
        )
        == "learning_request"
    )


def test_extract_learning_request_returns_requested_content():
    assert (
        extract_learning_request(
            "Clarity to add this to your learning list: summarize noisy vendors"
        )
        == "summarize noisy vendors"
    )
    assert extract_learning_request("Clarity add this to your learning list:") is None


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


def test_process_teams_relay_payload_rejects_unapproved_sender_object_id(tmp_path):
    result = process_teams_relay_payload(
        _payload(aad_object_id="wrong-object-id"),
        allowed_senders=("scott@example.com",),
        allowed_sender_object_ids=("approved-object-id",),
        require_sender_object_id=True,
        memory_path=tmp_path / "memory.duckdb",
    )

    assert result.status == "rejected"
    assert "object ID is not approved" in result.response_text


def test_process_teams_relay_payload_accepts_approved_sender_object_id(tmp_path):
    result = process_teams_relay_payload(
        _payload(aad_object_id="approved-object-id"),
        allowed_senders=("scott@example.com",),
        allowed_sender_object_ids=("approved-object-id",),
        require_sender_object_id=True,
        memory_path=tmp_path / "memory.duckdb",
        handlers={"pending_approvals": lambda _: "Pending handled"},
    )

    assert result.status == "completed"
    assert result.response_text == "Pending handled"


def test_process_teams_relay_payload_returns_health_summary(tmp_path):
    _write_teams_relay_config(tmp_path)

    result = process_teams_relay_payload(
        _payload(text="Clarity health", aad_object_id="approved-object-id"),
        allowed_senders=("scott@example.com",),
        allowed_sender_object_ids=("approved-object-id",),
        require_sender_object_id=True,
        root=tmp_path,
        memory_path=tmp_path / "memory.duckdb",
    )

    assert result.status == "completed"
    assert "Clarity Teams Relay Health" in result.response_text
    assert "Sender object ID required: True" in result.response_text
    assert "Approved sender emails: 1" in result.response_text
    assert "Approved sender object IDs: 1" in result.response_text


def test_process_teams_relay_payload_uses_injected_handler(tmp_path):
    result = process_teams_relay_payload(
        _payload(text="show open COMP tickets"),
        allowed_senders=("scott@example.com",),
        memory_path=tmp_path / "memory.duckdb",
        handlers={"open_comp_tickets": lambda message: f"Handled {message.command_id}"},
    )

    assert result.status == "completed"
    assert result.response_text == "Handled cmd-1"


def test_process_teams_relay_payload_records_learning_request(tmp_path):
    memory_path = tmp_path / "memory.duckdb"

    result = process_teams_relay_payload(
        _payload(
            text=(
                "Clarity add this to your learning list: "
                "recognize portal renewal reminders"
            )
        ),
        allowed_senders=("scott@example.com",),
        root=tmp_path,
        memory_path=memory_path,
    )

    assert result.status == "completed"
    assert "Recorded delegated task" in result.response_text
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        tasks = store.list_open_delegated_tasks()
    finally:
        store.close()
    assert tasks[0].title == "Clarity learning request"
    assert tasks[0].request == "recognize portal renewal reminders"
    assert tasks[0].approval_required is True


def test_process_teams_relay_payload_replies_when_command_is_unsupported(tmp_path):
    result = process_teams_relay_payload(
        _payload(text="Clarity please do something mysterious"),
        allowed_senders=("scott@example.com",),
        memory_path=tmp_path / "memory.duckdb",
    )

    assert result.status == "unsupported"
    assert "I don't understand what you are asking yet" in result.response_text


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
    assert _recent_action_result(memory_path=tmp_path / "memory.duckdb").startswith(
        "Teams relay reply posted with status 202."
    )


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


def test_process_teams_relay_queue_can_continue_after_malformed_message(tmp_path):
    queue = InMemoryTeamsRelayQueue()
    malformed = queue.enqueue(
        {
            "schemaVersion": 1,
            "source": "teams",
            "commandId": "bad",
            "receivedAt": "2026-08-03T15:30:00Z",
            "from": {"displayName": "Scott Sexton", "email": ""},
            "conversation": {"team": "AI Workspace", "channel": "Clarity"},
            "text": "show pending approvals",
            "action": None,
        }
    )
    good = queue.enqueue(_payload(text="show Gmail inbox"))

    result = process_teams_relay_queue(
        queue=queue,
        allowed_senders=("scott@example.com",),
        memory_path=tmp_path / "memory.duckdb",
        handlers={"gmail_inbox": lambda _: "Gmail handled"},
        limit=2,
        raise_on_error=False,
    )

    assert result.processed_count == 2
    assert result.completed_count == 1
    assert result.deadletter_count == 1
    assert queue.completed[0].queue_message_id == good.queue_message_id
    dead_lettered, reason = queue.dead_letters[0]
    assert dead_lettered.queue_message_id == malformed.queue_message_id
    assert "from.email" in reason


def test_process_teams_relay_queue_deadletters_malformed_azure_payload(tmp_path):
    queue = InMemoryTeamsRelayQueue()
    malformed = queue.enqueue(
        {RELAY_PAYLOAD_ERROR_KEY: "Azure Queue message payload must be JSON."}
    )
    good = queue.enqueue(_payload(text="show Gmail inbox"))

    result = process_teams_relay_queue(
        queue=queue,
        allowed_senders=("scott@example.com",),
        memory_path=tmp_path / "memory.duckdb",
        handlers={"gmail_inbox": lambda _: "Gmail handled"},
        limit=2,
        raise_on_error=False,
    )

    assert result.processed_count == 2
    assert result.completed_count == 1
    assert result.deadletter_count == 1
    assert queue.completed[0].queue_message_id == good.queue_message_id
    dead_lettered, reason = queue.dead_letters[0]
    assert dead_lettered.queue_message_id == malformed.queue_message_id
    assert reason == "Azure Queue message payload must be JSON."


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
    assert "not supported yet" in result.response_text


def test_process_teams_relay_action_records_approved_email_action(tmp_path):
    root = tmp_path
    memory_path = root / "memory.duckdb"
    manifest_path = root / "reports" / "teams-gmail-manifest.json"
    _write_email_config(root)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="test")
        source = store.record_source(
            source_type="email",
            display_name="Gmail",
            scope_label="sesexton@gmail.com",
            access_mode="read_write",
        )
        store.record_item_seen(
            source_id=source.source_id,
            external_id="gmail-message-1",
            item_type="email_message",
            subject="Test message",
            first_seen_run_id=run.run_id,
        )
        store.finish_run(run.run_id, status="completed")
    finally:
        store.close()
    manifest = create_teams_manifest(
        created_at="2026-08-03T15:30:00Z",
        manifest_id="manifest-1",
        items=(
            TeamsManifestItem(
                number=1,
                source_type="gmail",
                mailbox="sesexton@gmail.com",
                external_id="gmail-message-1",
                subject="Test message",
                allowed_actions=("trash", "move_review", "move_noise"),
            ),
        ),
    )
    write_teams_manifest(manifest_path, manifest)

    result = process_teams_relay_payload(
        _payload(
            text=None,
            action={
                "type": "trash",
                "manifestId": "manifest-1",
                "itemNumbers": [1],
            },
        ),
        allowed_senders=("scott@example.com",),
        root=root,
        memory_path=memory_path,
        action_manifest_path=manifest_path,
    )

    assert result.status == "completed"
    assert "Run the email move executor" in result.response_text
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        approved = store.actions_by_approval_status("approved", limit=10)
    finally:
        store.close()
    assert approved[0].action_type == "propose_email_move_trash"
    assert approved[0].action_target == "Deleted Items"


def test_teams_relay_poll_interval_uses_active_weekday_window():
    central = ZoneInfo("America/Chicago")

    assert (
        teams_relay_poll_interval_seconds(
            now=datetime(2026, 8, 3, 5, 0, tzinfo=central),
            active_interval_seconds=30,
            idle_interval_seconds=3600,
        )
        == 30
    )
    assert (
        teams_relay_poll_interval_seconds(
            now=datetime(2026, 8, 3, 18, 59, tzinfo=central),
            active_interval_seconds=30,
            idle_interval_seconds=3600,
        )
        == 30
    )
    assert (
        teams_relay_poll_interval_seconds(
            now=datetime(2026, 8, 3, 19, 0, tzinfo=central),
            active_interval_seconds=30,
            idle_interval_seconds=3600,
        )
        == 3600
    )
    assert (
        teams_relay_poll_interval_seconds(
            now=datetime(2026, 8, 8, 10, 0, tzinfo=central),
            active_interval_seconds=30,
            idle_interval_seconds=3600,
        )
        == 3600
    )


def test_watch_teams_relay_queue_sleeps_between_bounded_iterations(tmp_path, capsys):
    queue = InMemoryTeamsRelayQueue()
    sleep_values: list[float] = []

    result = watch_teams_relay_queue(
        queue=queue,
        allowed_senders=("scott@example.com",),
        memory_path=tmp_path / "memory.duckdb",
        limit=5,
        active_interval_seconds=30,
        idle_interval_seconds=3600,
        now_fn=lambda: datetime(2026, 8, 3, 9, 0, tzinfo=ZoneInfo("America/Chicago")),
        sleep_fn=sleep_values.append,
        max_iterations=2,
    )

    assert result.iterations == 2
    assert result.processed_count == 0
    assert sleep_values == [30]
    output = capsys.readouterr().out
    assert "Processed: 0" in output


def test_watcher_pid_file_is_removed_only_for_matching_pid(tmp_path):
    pid_path = tmp_path / "logs" / "clarity-teams-relay.pid"

    written_path = write_watcher_pid_file(pid_path, pid=1234)

    assert written_path == pid_path
    assert pid_path.read_text(encoding="utf-8") == "1234\n"
    assert remove_watcher_pid_file_if_current(pid_path, pid=9999) is False
    assert pid_path.exists()
    assert remove_watcher_pid_file_if_current(pid_path, pid=1234) is True
    assert not pid_path.exists()


def test_render_teams_relay_health_includes_pid_file_and_last_reply(tmp_path):
    memory_path = tmp_path / "memory.duckdb"
    pid_path = tmp_path / "logs" / "clarity-teams-relay.pid"
    write_watcher_pid_file(pid_path, pid=1234)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="test")
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="post_teams_relay_reply",
            approval_status="executed",
            result="Teams relay reply posted with status 202.",
        )
        store.finish_run(run.run_id, status="completed")
    finally:
        store.close()

    result = render_teams_relay_health(
        root=tmp_path,
        memory_path=memory_path,
        pid_file=pid_path,
        require_sender_object_id=True,
        approved_sender_count=1,
        approved_sender_object_id_count=1,
    )

    assert "Watcher PID file: 1234" in result
    assert "Sender object ID required: True" in result
    assert "Last Teams reply: Teams relay reply posted with status 202." in result


def test_format_teams_relay_result_truncates_long_replies():
    result = _format_teams_relay_result(
        TeamsCommandResult(
            command_id="cmd-1",
            status="completed",
            response_text="x" * (MAX_TEAMS_RELAY_REPLY_CHARS + 100),
        )
    )

    assert len(result) <= MAX_TEAMS_RELAY_REPLY_CHARS
    assert "Response truncated for Teams" in result


def _recent_action_result(memory_path):
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        return store.recent_actions()[0].result
    finally:
        store.close()


def _payload(
    *,
    text="show pending approvals",
    sender="scott@example.com",
    aad_object_id=None,
    action=None,
):
    return {
        "schemaVersion": 1,
        "source": "teams",
        "commandId": "cmd-1",
        "receivedAt": "2026-08-03T15:30:00Z",
        "from": {
            "displayName": "Scott Sexton",
            "email": sender,
            "aadObjectId": aad_object_id,
        },
        "conversation": {
            "team": "AI Workspace",
            "channel": "Clarity",
        },
        "text": text,
        "action": action,
    }


def _write_email_config(root):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        json.dumps(
            {
                "assistant": {
                    "email": {
                        "approvedMailboxes": [
                            {
                                "address": "sesexton@gmail.com",
                                "accessMode": "read_write",
                            }
                        ],
                        "defaultMailbox": "sesexton@gmail.com",
                        "folderNamespace": "Clarity",
                        "folderPolicy": {
                            "review": "Clarity/Review",
                            "noise": "Clarity/Noise",
                            "trash": "Deleted Items",
                        },
                        "maxMessages": 25,
                    }
                }
            }
        ),
        encoding="utf-8",
    )


def _write_teams_relay_config(root):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        json.dumps(
            {
                "assistant": {
                    "teamsRelay": {
                        "requireAadObjectId": True,
                        "approvedSenders": [
                            {
                                "email": "scott@example.com",
                                "aadObjectId": "approved-object-id",
                            }
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )


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
