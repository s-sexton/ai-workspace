from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from common.memory import DuckDbMemoryStore
from common.azure_storage_queue import RELAY_PAYLOAD_ERROR_KEY
from common.teams import TeamsWebhookResponse
from common.teams_manifest import (
    TeamsManifestItem,
    create_teams_manifest,
    write_teams_manifest,
)
from common.teams_relay import InMemoryTeamsRelayQueue, TeamsRelayMessage
from assistant.src.process_teams_relay import (
    MAX_TEAMS_RELAY_REPLY_CHARS,
    TeamsCommandResult,
    _format_teams_relay_result,
    _text_action_requests_execution,
    default_teams_command_handlers,
    extract_learning_request,
    process_teams_relay_queue,
    process_next_teams_relay_message,
    process_teams_relay_payload,
    parse_teams_text_action,
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
    assert route_teams_text_command("Clarity show email move plan") == "email_move_plan"
    assert (
        route_teams_text_command("Clarity execute Gmail email moves")
        == "execute_gmail_email_moves"
    )
    assert (
        route_teams_text_command("Clarity apply Outlook email moves")
        == "execute_graph_email_moves"
    )
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


def test_parse_teams_text_action_supports_numbered_email_actions():
    action = parse_teams_text_action("Clarity trash 1 2, 3")

    assert action is not None
    assert action.action_type == "trash"
    assert action.item_numbers == (1, 2, 3)
    assert parse_teams_text_action("Clarity move 4 to review").action_type == "move_review"
    assert parse_teams_text_action("Clarity noise 5").action_type == "move_noise"
    assert parse_teams_text_action("Clarity trash") is None
    assert parse_teams_text_action("show pending approvals") is None


def test_text_action_requests_execution_only_for_explicit_phrasing():
    assert _text_action_requests_execution("Clarity delete 1 and execute")
    assert _text_action_requests_execution("Clarity review 2 then apply")
    assert not _text_action_requests_execution("Clarity delete 1")
    assert not _text_action_requests_execution("Clarity show email move plan")


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


def test_process_teams_relay_text_action_uses_latest_manifest(tmp_path):
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
        for external_id, subject in (
            ("gmail-message-1", "First message"),
            ("gmail-message-2", "Second message"),
        ):
            store.record_item_seen(
                source_id=source.source_id,
                external_id=external_id,
                item_type="email_message",
                subject=subject,
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
                subject="First message",
                allowed_actions=("trash", "move_review", "move_noise"),
            ),
            TeamsManifestItem(
                number=2,
                source_type="gmail",
                mailbox="sesexton@gmail.com",
                external_id="gmail-message-2",
                subject="Second message",
                allowed_actions=("trash", "move_review", "move_noise"),
            ),
        ),
    )
    write_teams_manifest(manifest_path, manifest)

    result = process_teams_relay_payload(
        _payload(text="Clarity trash 1 2"),
        allowed_senders=("scott@example.com",),
        root=root,
        memory_path=memory_path,
        action_manifest_path=manifest_path,
    )

    assert result.status == "completed"
    assert "Recorded 2 approved local email action(s)" in result.response_text
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        approved = store.actions_by_approval_status("approved", limit=10)
    finally:
        store.close()
    assert [action.action_type for action in approved[:2]] == [
        "propose_email_move_trash",
        "propose_email_move_trash",
    ]


def test_process_teams_relay_text_action_can_execute_new_action_only(
    tmp_path,
    monkeypatch,
):
    root = tmp_path
    memory_path = root / "memory.duckdb"
    manifest_path = root / "reports" / "teams-gmail-manifest.json"
    _write_multi_mailbox_config(root)
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
        old_item = store.record_item_seen(
            source_id=source.source_id,
            external_id="old-gmail-message",
            item_type="email_message",
            subject="Old approved message",
            first_seen_run_id=run.run_id,
        )
        store.record_assistant_action(
            run_id=run.run_id,
            item_id=old_item.item_id,
            action_type="propose_email_move_review",
            approval_status="approved",
            action_target="Clarity/Review",
            result="Previously approved.",
        )
        store.record_item_seen(
            source_id=source.source_id,
            external_id="new-gmail-message",
            item_type="email_message",
            subject="New message",
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
                external_id="new-gmail-message",
                subject="New message",
                allowed_actions=("trash", "move_review", "move_noise"),
            ),
        ),
    )
    write_teams_manifest(manifest_path, manifest)
    transport = object()
    build_calls = []
    execute_calls = []

    def fake_build_gmail_move_transport_from_config(**kwargs):
        build_calls.append(kwargs)
        return transport

    def fake_execute_email_moves(**kwargs):
        execute_calls.append(kwargs)
        return "# Email Move Execution\n\nMoved one message"

    monkeypatch.setattr(
        "assistant.src.process_teams_relay.build_gmail_move_transport_from_config",
        fake_build_gmail_move_transport_from_config,
    )
    monkeypatch.setattr(
        "assistant.src.process_teams_relay.execute_email_moves",
        fake_execute_email_moves,
    )

    result = process_teams_relay_payload(
        _payload(text="Clarity delete 1 and execute"),
        allowed_senders=("scott@example.com",),
        root=root,
        memory_path=memory_path,
        action_manifest_path=manifest_path,
    )

    assert result.status == "completed"
    assert "Recorded 1 approved local email action" in result.response_text
    assert "Moved one message" in result.response_text
    assert build_calls == [{"root": root}]
    assert execute_calls[0]["mailboxes"] == ("sesexton@gmail.com",)
    assert execute_calls[0]["include_gmail_spam_cleanup"] is False
    assert len(execute_calls[0]["action_ids"]) == 1


def test_process_teams_relay_email_move_plan_returns_dry_run(tmp_path):
    root = tmp_path
    memory_path = root / "memory.duckdb"
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
        item = store.record_item_seen(
            source_id=source.source_id,
            external_id="gmail-message-1",
            item_type="email_message",
            subject="Move me",
            first_seen_run_id=run.run_id,
        )
        store.record_assistant_action(
            run_id=run.run_id,
            item_id=item.item_id,
            action_type="propose_email_move_review",
            approval_status="approved",
            action_target="Clarity/Review",
            result="Approved from Teams.",
        )
        store.finish_run(run.run_id, status="completed")
    finally:
        store.close()

    result = process_teams_relay_payload(
        _payload(text="Clarity show email move plan"),
        allowed_senders=("scott@example.com",),
        root=root,
        memory_path=memory_path,
    )

    assert result.status == "completed"
    assert "# Email Move Dry Run" in result.response_text
    assert "Would move message gmail-message-1" in result.response_text


def test_execute_gmail_email_moves_handler_filters_to_gmail_mailboxes(
    tmp_path,
    monkeypatch,
):
    _write_multi_mailbox_config(tmp_path)
    calls = []

    def fake_build_gmail_move_transport_from_config(**kwargs):
        calls.append(("build_gmail", kwargs))
        return object()

    def fake_execute_email_moves(**kwargs):
        calls.append(("execute", kwargs))
        return "Executed Gmail moves"

    monkeypatch.setattr(
        "assistant.src.process_teams_relay.build_gmail_move_transport_from_config",
        fake_build_gmail_move_transport_from_config,
    )
    monkeypatch.setattr(
        "assistant.src.process_teams_relay.execute_email_moves",
        fake_execute_email_moves,
    )

    response = default_teams_command_handlers(root=tmp_path)[
        "execute_gmail_email_moves"
    ](_message())

    assert response == "Executed Gmail moves"
    assert calls[0] == ("build_gmail", {"root": tmp_path})
    assert calls[1][1]["dry_run"] is False
    assert calls[1][1]["mailboxes"] == ("sesexton@gmail.com",)
    assert calls[1][1]["include_gmail_spam_cleanup"] is True


def test_execute_gmail_email_moves_handler_requires_provider_write_opt_in(
    tmp_path,
    monkeypatch,
):
    _write_multi_mailbox_config(tmp_path, allow_provider_writes=False)

    def fake_execute_email_moves(**_):
        raise AssertionError("Provider execution should not be called.")

    monkeypatch.setattr(
        "assistant.src.process_teams_relay.execute_email_moves",
        fake_execute_email_moves,
    )

    response = default_teams_command_handlers(root=tmp_path)[
        "execute_gmail_email_moves"
    ](_message())

    assert "Teams provider writes are disabled" in response


def test_execute_graph_email_moves_handler_filters_to_non_gmail_mailboxes(
    tmp_path,
    monkeypatch,
):
    _write_multi_mailbox_config(tmp_path)
    calls = []

    def fake_build_graph_move_transport_from_config(**kwargs):
        calls.append(("build_graph", kwargs))
        return object()

    def fake_execute_email_moves(**kwargs):
        calls.append(("execute", kwargs))
        return "Executed Graph moves"

    monkeypatch.setattr(
        "assistant.src.process_teams_relay.build_graph_move_transport_from_config",
        fake_build_graph_move_transport_from_config,
    )
    monkeypatch.setattr(
        "assistant.src.process_teams_relay.execute_email_moves",
        fake_execute_email_moves,
    )

    response = default_teams_command_handlers(root=tmp_path)[
        "execute_graph_email_moves"
    ](_message())

    assert response == "Executed Graph moves"
    assert calls[0] == ("build_graph", {"root": tmp_path})
    assert calls[1][1]["dry_run"] is False
    assert calls[1][1]["mailboxes"] == ("scott.sexton@sendthisfile.com",)


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


def test_watch_teams_relay_queue_continues_after_receive_error(tmp_path, capsys):
    queue = ReceiveFailsOnceQueue()
    queue.enqueue(_payload(text="show Gmail inbox"))
    sleep_values: list[float] = []

    result = watch_teams_relay_queue(
        queue=queue,
        allowed_senders=("scott@example.com",),
        memory_path=tmp_path / "memory.duckdb",
        handlers={"gmail_inbox": lambda _: "Gmail handled"},
        active_interval_seconds=30,
        idle_interval_seconds=3600,
        now_fn=lambda: datetime(2026, 8, 3, 9, 0, tzinfo=ZoneInfo("America/Chicago")),
        sleep_fn=sleep_values.append,
        max_iterations=2,
    )

    assert result.iterations == 2
    assert result.receive_error_count == 1
    assert result.processed_count == 1
    assert result.completed_count == 1
    assert sleep_values == [30]
    output = capsys.readouterr().out
    assert "Queue receive failed: temporary queue timeout" in output
    assert "Processed: 1" in output


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


def test_format_teams_relay_result_includes_context_header():
    result = _format_teams_relay_result(
        TeamsCommandResult(
            command_id="cmd-1",
            status="completed",
            response_text="Handled",
        )
    )

    assert "**Clarity Response**" in result
    assert "Command: `cmd-1`" in result
    assert "Status: **completed**" in result
    assert "Time:" in result


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


def _message():
    return TeamsRelayMessage.from_mapping(_payload())


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


def _write_multi_mailbox_config(root, *, allow_provider_writes=True):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        json.dumps(
            {
                "assistant": {
                    "teamsRelay": {
                        "allowProviderWrites": allow_provider_writes,
                    },
                    "email": {
                        "approvedMailboxes": [
                            {
                                "address": "sesexton@gmail.com",
                                "accessMode": "read_write",
                            },
                            {
                                "address": "scott.sexton@sendthisfile.com",
                                "accessMode": "read_write",
                            },
                            {
                                "address": "read-only@example.invalid",
                                "accessMode": "read",
                            },
                        ],
                        "defaultMailbox": "sesexton@gmail.com",
                        "folderNamespace": "Clarity",
                        "folderPolicy": {
                            "review": "Clarity/Review",
                            "noise": "Clarity/Noise",
                            "trash": "Deleted Items",
                        },
                        "gmailCleanupPolicy": {
                            "trashSpam": True,
                            "mailboxes": ["sesexton@gmail.com"],
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


class ReceiveFailsOnceQueue(InMemoryTeamsRelayQueue):
    def __init__(self):
        super().__init__()
        self.fail_next_receive = True

    def receive(self, *, limit: int = 1):
        if self.fail_next_receive:
            self.fail_next_receive = False
            raise RuntimeError("temporary queue timeout")
        return super().receive(limit=limit)
