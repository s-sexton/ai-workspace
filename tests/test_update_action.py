from __future__ import annotations

from assistant.src.update_action import main, update_action
from common.memory import DuckDbMemoryStore


def test_update_action_approval_status(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    action_id = _seed_action(memory_path)

    result = update_action(
        root=tmp_path,
        memory_path=memory_path,
        action_id=action_id,
        approval_status="approved",
    )

    assert result == f"Updated assistant action {action_id}: approved."

    store = DuckDbMemoryStore(memory_path)
    try:
        pending_actions = store.pending_actions()
        recent_actions = store.recent_actions()
        latest_run = store.latest_run(workflow="update-action")
    finally:
        store.close()

    assert pending_actions == ()
    assert latest_run is not None
    assert latest_run.summary == f"Updated assistant action approval: {action_id}"
    assert recent_actions[0].action_type == "update_action_approval"
    assert recent_actions[0].approval_status == "not_required"


def test_update_action_reports_missing_memory(tmp_path):
    result = update_action(
        root=tmp_path,
        memory_path=tmp_path / "logs" / "missing.duckdb",
        action_id="missing",
        approval_status="approved",
    )

    assert "No Clarity memory found" in result


def test_update_action_reports_unknown_action(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_action(memory_path)

    result = update_action(
        root=tmp_path,
        memory_path=memory_path,
        action_id="missing",
        approval_status="approved",
    )

    assert "Unknown assistant action" in result


def test_main_prints_result(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    action_id = _seed_action(memory_path)
    monkeypatch.chdir(tmp_path)

    main([action_id, "rejected", "--memory", str(memory_path)])

    output = capsys.readouterr().out
    assert f"Updated assistant action {action_id}: rejected." in output


def _seed_action(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="email-review")
        action = store.record_assistant_action(
            run_id=run.run_id,
            action_type="propose_email_move_noise",
            approval_status="required",
            result="Proposed moving message metadata to Clarity/Noise.",
        )
        store.finish_run(run.run_id, status="completed")
        return action.action_id
    finally:
        store.close()
