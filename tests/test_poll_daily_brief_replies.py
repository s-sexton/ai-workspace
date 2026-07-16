from __future__ import annotations

from datetime import datetime

import pytest

from assistant.src.generate_daily_brief import generate_daily_brief
from assistant.src.poll_daily_brief_replies import main, poll_daily_brief_replies
from common.email import StaticEmailTransport
from common.memory import DuckDbMemoryStore


def test_poll_daily_brief_replies_dry_run_processes_authenticated_reply(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    manifest_path = _seed_daily_brief(tmp_path, memory_path)

    result = poll_daily_brief_replies(
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=manifest_path,
        transport=StaticEmailTransport(
            (
                _reply_message(
                    message_id="reply-1",
                    preview="Move item 1 to Noise",
                ),
            )
        ),
    )

    assert result.mailbox == "clarity@example.invalid"
    assert result.read_count == 1
    assert result.selected_count == 1
    assert result.skipped_count == 0
    assert result.processed_count == 1
    assert "# Daily Brief Reply Plan" in result.replies[0].result

    store = DuckDbMemoryStore(memory_path)
    try:
        processed_replies = [
            record
            for record in store.recent_memory_by_source_type("email", limit=100)
            if record.item_type == "daily_brief_reply"
        ]
        pending_noise = [
            action
            for action in store.pending_actions(limit=100)
            if action.action_type == "propose_email_move_noise"
        ]
    finally:
        store.close()

    assert processed_replies == []
    assert pending_noise == []


def test_poll_daily_brief_replies_execute_records_processed_reply(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    manifest_path = _seed_daily_brief(tmp_path, memory_path)

    result = poll_daily_brief_replies(
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=manifest_path,
        transport=StaticEmailTransport(
            (
                _reply_message(
                    message_id="reply-1",
                    preview="Move item 1 to Noise",
                ),
            )
        ),
        execute=True,
    )

    assert result.selected_count == 1
    assert result.processed_count == 1

    store = DuckDbMemoryStore(memory_path)
    try:
        processed_replies = [
            record
            for record in store.recent_memory_by_source_type("email", limit=100)
            if record.item_type == "daily_brief_reply"
        ]
        pending_noise = [
            action
            for action in store.pending_actions(limit=100)
            if action.action_type == "propose_email_move_noise"
        ]
    finally:
        store.close()

    assert len(processed_replies) == 1
    assert processed_replies[0].external_id == "reply-1"
    assert len(pending_noise) == 1
    assert pending_noise[0].action_target == "Clarity/Noise"


def test_poll_daily_brief_replies_skips_duplicate_processed_reply(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    manifest_path = _seed_daily_brief(tmp_path, memory_path)
    transport = StaticEmailTransport(
        (
            _reply_message(
                message_id="reply-1",
                preview="Move item 1 to Noise",
            ),
        )
    )

    poll_daily_brief_replies(
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=manifest_path,
        transport=transport,
        execute=True,
    )
    result = poll_daily_brief_replies(
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=manifest_path,
        transport=transport,
        execute=True,
    )

    assert result.selected_count == 0
    assert result.skipped_count == 1
    assert result.replies[0].result == "Skipped: reply already processed."


def test_poll_daily_brief_replies_skips_unauthorized_or_failed_auth(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    manifest_path = _seed_daily_brief(tmp_path, memory_path)

    result = poll_daily_brief_replies(
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=manifest_path,
        transport=StaticEmailTransport(
            (
                _reply_message(
                    message_id="reply-unauthorized",
                    sender="intruder@example.invalid",
                    preview="Move item 1 to Noise",
                ),
                _reply_message(
                    message_id="reply-auth-fail",
                    dmarc="fail",
                    preview="Move item 1 to Noise",
                ),
            )
        ),
    )

    assert result.selected_count == 0
    assert result.skipped_count == 2
    assert result.replies[0].result == "Skipped: sender is not allowed."
    assert result.replies[1].result == "Skipped: message authentication did not pass."


def test_poll_daily_brief_replies_skips_allowed_sender_without_daily_brief_subject(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    manifest_path = _seed_daily_brief(tmp_path, memory_path)

    result = poll_daily_brief_replies(
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=manifest_path,
        transport=StaticEmailTransport(
            (
                _reply_message(
                    message_id="reply-random",
                    subject="Please do this thing",
                    preview="Move item 1 to Noise",
                ),
            )
        ),
    )

    assert result.selected_count == 0
    assert result.skipped_count == 1
    assert result.replies[0].result == (
        "Skipped: message is not tied to a Clarity daily brief."
    )


def test_main_can_poll_with_graph_transport(tmp_path, monkeypatch, capsys):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    manifest_path = _seed_daily_brief(tmp_path, memory_path)

    def fake_build_graph_read_transport_from_config(*, use_bearer_auth=False, **_):
        assert use_bearer_auth is True
        return StaticEmailTransport(
            (
                _reply_message(
                    message_id="reply-1",
                    preview="Move item 1 to Noise",
                ),
            )
        )

    monkeypatch.setattr(
        "assistant.src.poll_daily_brief_replies.build_graph_read_transport_from_config",
        fake_build_graph_read_transport_from_config,
    )
    monkeypatch.chdir(tmp_path)

    main(
        [
            "--graph",
            "--graph-bearer",
            "--memory",
            str(memory_path),
            "--manifest",
            str(manifest_path),
        ]
    )

    output = capsys.readouterr().out
    assert "# Daily Brief Reply Poll" in output
    assert "Selected: 1" in output


def test_main_requires_graph():
    with pytest.raises(SystemExit):
        main([])


def _write_config(root):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "dailyBrief": {
              "sender": "clarity@example.invalid",
              "recipients": ["scott@example.invalid"],
              "subjectPrefix": "Clarity Day in a Glance"
            },
            "email": {
              "approvedMailboxes": [
                {
                  "address": "clarity@example.invalid",
                  "accessMode": "read_write",
                  "allowedSenders": ["scott@example.invalid"]
                },
                {
                  "address": "scott.sexton@sendthisfile.com",
                  "accessMode": "read_write"
                }
              ],
              "defaultMailbox": "scott.sexton@sendthisfile.com",
              "folderNamespace": "Clarity",
              "folderPolicy": {
                "review": "Clarity/Review",
                "noise": "Clarity/Noise",
                "trash": "Deleted Items"
              },
              "maxMessages": 25
            }
          }
        }
        """,
        encoding="utf-8",
    )


def _seed_daily_brief(root, memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="poll-fixture")
        source = store.record_source(
            source_type="email",
            display_name="scott.sexton@sendthisfile.com",
            scope_label="scott.sexton@sendthisfile.com",
        )
        item = store.record_item_seen(
            source_id=source.source_id,
            external_id="message-1",
            item_type="email_message",
            subject="Review customer invoice",
            sender_or_owner="customer@example.invalid",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=item.item_id,
            run_id=run.run_id,
            label="review",
            reason="Potentially important operational message.",
        )
        store.finish_run(run.run_id, status="completed")
    finally:
        store.close()

    result = generate_daily_brief(
        root=root,
        memory_path=memory_path,
        output_path=root / "reports" / "daily.md",
        brief_date="2026-07-16",
        generated_at=datetime(2026, 7, 16, 7, 30),
    )
    return result.manifest_path


def _reply_message(
    *,
    message_id,
    sender="scott@example.invalid",
    subject="Re: Clarity Day in a Glance - 2026-07-16",
    preview,
    dmarc="pass",
    spf="pass",
    dkim=None,
):
    return {
        "message_id": message_id,
        "mailbox": "clarity@example.invalid",
        "subject": subject,
        "sender": sender,
        "received_at": "2026-07-16T08:00:00-05:00",
        "preview": preview,
        "dmarc": dmarc,
        "spf": spf,
        "dkim": dkim,
    }
