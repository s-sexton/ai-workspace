from __future__ import annotations

from assistant.src.approve_email_moves import approve_email_moves, main
from common.memory import DuckDbMemoryStore


def test_approve_email_moves_dry_run_lists_matching_pending_moves(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    action_id = _seed_email_move(
        memory_path,
        mailbox="sesexton@gmail.com",
        message_id="pending-1",
        action_type="propose_email_move_noise",
    )

    result = approve_email_moves(root=tmp_path, memory_path=memory_path)

    assert "# Email Move Bulk Approval" in result
    assert "- Mode: Dry Run" in result
    assert "- Matching pending moves: 1" in result
    assert "No approvals were changed." in result
    assert "python -m assistant.src.approve_email_moves --execute" in result
    assert "pending-1 in sesexton@gmail.com to Clarity/Noise" in result
    assert f"Action: {action_id}" in result

    store = DuckDbMemoryStore(memory_path)
    try:
        pending = store.pending_actions()
    finally:
        store.close()

    assert pending[0].action_id == action_id


def test_approve_email_moves_can_filter_by_mailbox_and_classification(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    target_action = _seed_email_move(
        memory_path,
        mailbox="sesexton@gmail.com",
        message_id="gmail-noise",
        action_type="propose_email_move_noise",
    )
    _seed_email_move(
        memory_path,
        mailbox="other@example.invalid",
        message_id="other-noise",
        action_type="propose_email_move_noise",
    )
    _seed_email_move(
        memory_path,
        mailbox="sesexton@gmail.com",
        message_id="gmail-review",
        action_type="propose_email_move_review",
        target_folder="Clarity/Review",
    )

    result = approve_email_moves(
        root=tmp_path,
        memory_path=memory_path,
        mailbox="sesexton@gmail.com",
        classification="noise",
    )

    assert "- Mailbox: sesexton@gmail.com" in result
    assert "- Classification: noise" in result
    assert "- Matching pending moves: 1" in result
    assert f"Action: {target_action}" in result
    assert "other-noise" not in result
    assert "gmail-review" not in result


def test_approve_email_moves_execute_updates_matching_actions(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    action_id = _seed_email_move(
        memory_path,
        mailbox="sesexton@gmail.com",
        message_id="pending-1",
        action_type="propose_email_move_noise",
    )

    result = approve_email_moves(
        root=tmp_path,
        memory_path=memory_path,
        mailbox="sesexton@gmail.com",
        execute=True,
    )

    assert "- Mode: Executed" in result
    assert "- Matching pending moves: 1" in result
    assert f"Action: {action_id}" in result

    store = DuckDbMemoryStore(memory_path)
    try:
        pending = store.pending_actions()
        approved = store.actions_by_approval_status("approved")
        latest_run = store.latest_run(workflow="approve-email-moves")
        recent_actions = store.recent_actions()
    finally:
        store.close()

    assert pending == ()
    assert approved[0].action_id == action_id
    assert latest_run is not None
    assert latest_run.summary == "Approved 1 pending email move suggestion(s)."
    assert recent_actions[0].action_type == "approve_email_moves"


def test_approve_email_moves_can_preview_one_batch(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_email_move(
        memory_path,
        mailbox="sesexton@gmail.com",
        message_id="pending-1",
        action_type="propose_email_move_noise",
    )
    _seed_email_move(
        memory_path,
        mailbox="sesexton@gmail.com",
        message_id="pending-2",
        action_type="propose_email_move_noise",
    )
    _seed_email_move(
        memory_path,
        mailbox="sesexton@gmail.com",
        message_id="pending-3",
        action_type="propose_email_move_noise",
    )

    result = approve_email_moves(
        root=tmp_path,
        memory_path=memory_path,
        mailbox="sesexton@gmail.com",
        batch_size=2,
        batch=1,
    )

    assert "- Matching pending moves: 3" in result
    assert "- Batch: 1" in result
    assert "- Batch size: 2" in result
    assert "- Moves in this batch: 2" in result
    assert "--batch-size 2 --batch 1" in result
    assert "pending-3" in result
    assert "pending-2" in result
    assert "pending-1" not in result


def test_approve_email_moves_execute_only_selected_batch(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    first_action = _seed_email_move(
        memory_path,
        mailbox="sesexton@gmail.com",
        message_id="pending-1",
        action_type="propose_email_move_noise",
    )
    _seed_email_move(
        memory_path,
        mailbox="sesexton@gmail.com",
        message_id="pending-2",
        action_type="propose_email_move_noise",
    )
    _seed_email_move(
        memory_path,
        mailbox="sesexton@gmail.com",
        message_id="pending-3",
        action_type="propose_email_move_noise",
    )

    result = approve_email_moves(
        root=tmp_path,
        memory_path=memory_path,
        mailbox="sesexton@gmail.com",
        batch_size=1,
        batch=3,
        execute=True,
    )

    assert "- Matching pending moves: 3" in result
    assert "- Moves in this batch: 1" in result
    assert f"Action: {first_action}" in result

    store = DuckDbMemoryStore(memory_path)
    try:
        pending = store.pending_actions()
        approved = store.actions_by_approval_status("approved")
    finally:
        store.close()

    assert len(pending) == 2
    assert approved[0].action_id == first_action


def test_approve_email_moves_rejects_invalid_batch_options(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_email_move(
        memory_path,
        mailbox="sesexton@gmail.com",
        message_id="pending-1",
        action_type="propose_email_move_noise",
    )

    assert (
        approve_email_moves(root=tmp_path, memory_path=memory_path, batch_size=0)
        == "batch_size must be positive."
    )
    assert (
        approve_email_moves(root=tmp_path, memory_path=memory_path, batch=0)
        == "batch must be positive."
    )


def test_approve_email_moves_reports_empty(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    memory_path.parent.mkdir(parents=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
    finally:
        store.close()

    result = approve_email_moves(root=tmp_path, memory_path=memory_path)

    assert "- Matching pending moves: 0" in result
    assert "No matching pending email move suggestions found." in result


def test_main_prints_bulk_approval_plan(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_email_move(
        memory_path,
        mailbox="sesexton@gmail.com",
        message_id="pending-1",
        action_type="propose_email_move_noise",
    )
    monkeypatch.chdir(tmp_path)

    main(
        [
            "--memory",
            str(memory_path),
            "--mailbox",
            "sesexton@gmail.com",
            "--batch-size",
            "10",
        ]
    )

    output = capsys.readouterr().out
    assert "# Email Move Bulk Approval" in output
    assert "pending-1" in output
    assert "- Batch size: 10" in output


def _seed_email_move(
    memory_path,
    *,
    mailbox,
    message_id,
    action_type,
    target_folder="Clarity/Noise",
    approval_status="required",
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
            subject="Cleanup message",
            first_seen_run_id=run.run_id,
        )
        action = store.record_assistant_action(
            run_id=run.run_id,
            item_id=item.item_id,
            action_type=action_type,
            approval_status=approval_status,
            action_target=target_folder,
            result=f"Proposed moving message metadata to {target_folder}.",
        )
        store.finish_run(run.run_id, status="completed")
        return action.action_id
    finally:
        store.close()
