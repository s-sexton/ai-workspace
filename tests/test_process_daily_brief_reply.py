from __future__ import annotations

from datetime import datetime

from assistant.src.generate_daily_brief import generate_daily_brief
from assistant.src.process_daily_brief_reply import main, process_daily_brief_reply
from common.memory import DuckDbMemoryStore


def test_process_daily_brief_reply_dry_run_plans_supported_commands(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path)
    brief = generate_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-16",
        generated_at=datetime(2026, 7, 16, 7, 30),
    )

    result = process_daily_brief_reply(
        "Move item 1 to Noise\nMark sender from item 1 as noise",
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=brief.manifest_path,
    )

    assert "# Daily Brief Reply Plan" in result
    assert "move_item item 1 (outlook) -> noise" in result
    assert "Would record pending move action to Clarity/Noise." in result
    assert "sender_preference item 1 (outlook) -> noise" in result
    assert "Would record noise sender preference" in result

    store = DuckDbMemoryStore(memory_path)
    try:
        pending = store.pending_actions(limit=10)
        preferences = store.list_email_sender_preferences(limit=10)
    finally:
        store.close()

    assert not any(action.action_type == "propose_email_move_noise" for action in pending)
    assert preferences == ()


def test_process_daily_brief_reply_execute_records_local_actions(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path)
    brief = generate_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-16",
    )

    result = process_daily_brief_reply(
        "Move item 1 to Noise\nMark sender from item 1 as noise",
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=brief.manifest_path,
        execute=True,
    )

    assert "# Daily Brief Reply Execution" in result
    assert "Recorded pending move action to Clarity/Noise." in result
    assert "Recorded noise sender preference" in result

    store = DuckDbMemoryStore(memory_path)
    try:
        pending = store.pending_actions(limit=10)
        preferences = store.list_email_sender_preferences(limit=10)
        latest_run = store.latest_run(workflow="daily-brief-reply")
    finally:
        store.close()

    assert any(action.action_type == "propose_email_move_noise" for action in pending)
    assert pending[0].action_target == "Clarity/Noise"
    assert preferences[0].mailbox == "scott.sexton@sendthisfile.com"
    assert preferences[0].pattern == "customer@example.invalid"
    assert preferences[0].label == "noise"
    assert latest_run is not None
    assert "Executed 2 daily brief reply command" in latest_run.summary


def test_process_daily_brief_reply_can_approve_pending_cleanup(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path, pending_move=True)
    brief = generate_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-16",
    )

    result = process_daily_brief_reply(
        "Approve pending cleanup actions",
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=brief.manifest_path,
        execute=True,
    )

    assert "Approved 1 pending cleanup action" in result
    store = DuckDbMemoryStore(memory_path)
    try:
        approved = store.actions_by_approval_status("approved", limit=10)
    finally:
        store.close()

    assert len(approved) == 1
    assert approved[0].action_type == "propose_email_move_review"


def test_main_prints_reply_plan(tmp_path, monkeypatch, capsys):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path)
    brief = generate_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-16",
    )
    monkeypatch.chdir(tmp_path)

    main(
        [
            "--reply",
            "Move item 1 to Review",
            "--memory",
            str(memory_path),
            "--manifest",
            str(brief.manifest_path),
        ]
    )

    output = capsys.readouterr().out
    assert "# Daily Brief Reply Plan" in output
    assert "move_item item 1" in output


def _write_config(root):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "email": {
              "approvedMailboxes": [
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


def _seed_memory(memory_path, *, pending_move=False):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="reply-fixture")
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
            updated_at="2026-07-16T06:45:00-05:00",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=item.item_id,
            run_id=run.run_id,
            label="review",
            reason="Potentially important operational message.",
        )
        if pending_move:
            store.record_assistant_action(
                run_id=run.run_id,
                item_id=item.item_id,
                action_type="propose_email_move_review",
                approval_status="required",
                action_target="Clarity/Review",
                result="Proposed moving message metadata to Clarity/Review.",
            )
        store.finish_run(run.run_id, status="completed")
    finally:
        store.close()
