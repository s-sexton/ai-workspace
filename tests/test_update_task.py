from __future__ import annotations

from assistant.src.delegate_task import delegate_task
from assistant.src.update_task import main, update_task
from common.memory import DuckDbMemoryStore


def test_updates_delegated_task_status(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    task_id = _create_task(memory_path, tmp_path)

    message = update_task(
        task_id=task_id,
        status="in_progress",
        next_step="Draft the design note.",
        root=tmp_path,
        memory_path=memory_path,
    )

    store = DuckDbMemoryStore(memory_path)
    try:
        task = store.get_delegated_task(task_id)
        actions = store.recent_actions()
    finally:
        store.close()

    assert message == f"Updated delegated task {task_id}: in_progress."
    assert task.status == "in_progress"
    assert task.next_step == "Draft the design note."
    assert task.completed_at is None
    assert actions[0].action_type == "update_task"
    assert actions[0].approval_status == "not_required"
    assert actions[0].result == f"Updated delegated task {task_id} to in_progress."


def test_completed_task_is_no_longer_open(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    task_id = _create_task(memory_path, tmp_path)

    update_task(
        task_id=task_id,
        status="completed",
        root=tmp_path,
        memory_path=memory_path,
    )

    store = DuckDbMemoryStore(memory_path)
    try:
        task = store.get_delegated_task(task_id)
        open_tasks = store.list_open_delegated_tasks()
    finally:
        store.close()

    assert task.status == "completed"
    assert task.completed_at is not None
    assert open_tasks == ()


def test_reports_missing_task(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _create_task(memory_path, tmp_path)

    message = update_task(
        task_id="missing",
        status="blocked",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert message == "Unknown delegated task: missing"


def test_reports_missing_memory(tmp_path):
    message = update_task(
        task_id="task",
        status="completed",
        root=tmp_path,
        memory_path=tmp_path / "logs" / "missing.duckdb",
    )

    assert "No Clarity memory found" in message


def test_main_prints_update_result(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    task_id = _create_task(memory_path, tmp_path)
    monkeypatch.chdir(tmp_path)

    main([task_id, "waiting_for_approval", "--memory", str(memory_path)])

    output = capsys.readouterr().out
    assert f"Updated delegated task {task_id}: waiting_for_approval." in output


def _create_task(memory_path, root):
    delegate_task(
        title="Prepare Exchange plan",
        request="Draft the smallest safe Exchange read-only plan.",
        next_step="Write a design note.",
        root=root,
        memory_path=memory_path,
    )
    store = DuckDbMemoryStore(memory_path)
    try:
        return store.list_open_delegated_tasks()[0].task_id
    finally:
        store.close()
