from __future__ import annotations

from assistant.src.email_cleanup_plan import build_email_cleanup_plan, main
from common.memory import DuckDbMemoryStore


def test_build_email_cleanup_plan_groups_ready_pending_and_blocked(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path, "sesexton@gmail.com", "read_write")
    approved_action = _seed_email_move(
        memory_path,
        mailbox="sesexton@gmail.com",
        message_id="ready-1",
        approval_status="approved",
        target_folder="Clarity/Noise",
        subject="Promo ready",
    )
    pending_action = _seed_email_move(
        memory_path,
        mailbox="sesexton@gmail.com",
        message_id="pending-1",
        approval_status="required",
        target_folder="Clarity/Noise",
        subject="Promo pending",
    )
    blocked_action = _seed_email_move(
        memory_path,
        mailbox="sesexton@gmail.com",
        message_id="blocked-1",
        approval_status="approved",
        target_folder="Clarity/Unknown",
        subject="Promo blocked",
    )

    plan = build_email_cleanup_plan(root=tmp_path, memory_path=memory_path)

    assert "# Email Cleanup Plan" in plan
    assert "- Ready to execute: 1" in plan
    assert "- Needs approval: 1" in plan
    assert "- Blocked approved moves: 1" in plan
    assert "## Ready To Execute" in plan
    assert "- 1 message(s) to Clarity/Noise" in plan
    assert f"Action: {approved_action}" in plan
    assert "python -m assistant.src.execute_email_moves --gmail --execute" in plan
    assert "## Needs Approval" in plan
    assert f"Action: {pending_action}" in plan
    assert f"python -m assistant.src.update_action {pending_action} approved" in plan
    assert "python -m assistant.src.approve_email_moves" in plan
    assert "python -m assistant.src.approve_email_moves --execute" in plan
    assert "## Blocked Approved Moves" in plan
    assert f"Action: {blocked_action}" in plan
    assert "target folder is not in the current email folder policy" in plan


def test_build_email_cleanup_plan_can_filter_by_mailbox(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path, "sesexton@gmail.com", "read_write")
    _seed_email_move(
        memory_path,
        mailbox="sesexton@gmail.com",
        message_id="gmail-1",
        approval_status="approved",
        target_folder="Clarity/Noise",
    )
    _seed_email_move(
        memory_path,
        mailbox="other@example.invalid",
        message_id="other-1",
        approval_status="approved",
        target_folder="Clarity/Noise",
    )

    plan = build_email_cleanup_plan(
        root=tmp_path,
        memory_path=memory_path,
        mailbox="sesexton@gmail.com",
    )

    assert "- Mailbox: sesexton@gmail.com" in plan
    assert "gmail-1" in plan
    assert "other-1" not in plan


def test_build_email_cleanup_plan_reports_empty(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path, "sesexton@gmail.com", "read_write")
    memory_path.parent.mkdir(parents=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
    finally:
        store.close()

    plan = build_email_cleanup_plan(root=tmp_path, memory_path=memory_path)

    assert "No email cleanup actions found." in plan


def test_main_prints_cleanup_plan(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path, "sesexton@gmail.com", "read_write")
    _seed_email_move(
        memory_path,
        mailbox="sesexton@gmail.com",
        message_id="ready-1",
        approval_status="approved",
        target_folder="Clarity/Noise",
    )
    monkeypatch.chdir(tmp_path)

    main(["--memory", str(memory_path)])

    output = capsys.readouterr().out
    assert "# Email Cleanup Plan" in output
    assert "ready-1" in output


def _seed_email_move(
    memory_path,
    *,
    mailbox,
    message_id,
    approval_status,
    target_folder,
    subject="Cleanup message",
):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="email-review")
        source = store.record_source(
            source_type="email",
            display_name=mailbox,
            scope_label=mailbox,
        )
        item = store.record_item_seen(
            source_id=source.source_id,
            external_id=message_id,
            item_type="email_message",
            subject=subject,
            first_seen_run_id=run.run_id,
        )
        action = store.record_assistant_action(
            run_id=run.run_id,
            item_id=item.item_id,
            action_type="propose_email_move_noise",
            approval_status=approval_status,
            action_target=target_folder,
            result=f"Proposed moving message metadata to {target_folder}.",
        )
        store.finish_run(run.run_id, status="completed")
        return action.action_id
    finally:
        store.close()


def _write_config(root, mailbox, access_mode):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        f"""
        {{
          "assistant": {{
            "email": {{
              "approvedMailboxes": [
                {{"address": "{mailbox}", "accessMode": "{access_mode}"}}
              ],
              "defaultMailbox": "{mailbox}",
              "folderNamespace": "Clarity",
              "folderPolicy": {{
                "review": "Clarity/Review",
                "noise": "Clarity/Noise",
                "trash": "Deleted Items"
              }},
              "maxMessages": 25
            }}
          }}
        }}
        """,
        encoding="utf-8",
    )
