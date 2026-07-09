from __future__ import annotations

from assistant.src.ask_memory import answer_memory_question
from assistant.src.delegate_task import delegate_task, main
from common.memory import DuckDbMemoryStore


def test_delegates_task_into_new_memory_file(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"

    message = delegate_task(
        title="Prepare Exchange plan",
        request="Draft the smallest safe Exchange read-only plan.",
        next_step="Write a design note.",
        root=tmp_path,
        memory_path=memory_path,
    )

    store = DuckDbMemoryStore(memory_path)
    try:
        open_tasks = store.list_open_delegated_tasks()
        latest_run = store.latest_run(workflow="delegated-task")
        actions = store.recent_actions()
    finally:
        store.close()

    assert "Recorded delegated task" in message
    assert len(open_tasks) == 1
    assert open_tasks[0].title == "Prepare Exchange plan"
    assert open_tasks[0].request == "Draft the smallest safe Exchange read-only plan."
    assert open_tasks[0].next_step == "Write a design note."
    assert open_tasks[0].approval_required is True
    assert latest_run is not None
    assert latest_run.summary == "Recorded delegated task: Prepare Exchange plan"
    assert actions[0].action_type == "delegate_task"
    assert actions[0].approval_status == "not_required"
    assert actions[0].result == f"Recorded delegated task {open_tasks[0].task_id}."


def test_delegated_task_appears_in_memory_questions(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"

    delegate_task(
        title="Review ACCT tickets",
        request="Find billing issues that need attention.",
        next_step="Run the Jira report.",
        root=tmp_path,
        memory_path=memory_path,
    )

    answer = answer_memory_question(
        "open-tasks",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "Review ACCT tickets [requested, approval required]" in answer
    assert "Next step: Run the Jira report." in answer


def test_can_record_task_without_approval_requirement(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"

    delegate_task(
        title="Local cleanup note",
        request="Remember to review old reports.",
        approval_required=False,
        root=tmp_path,
        memory_path=memory_path,
    )

    store = DuckDbMemoryStore(memory_path)
    try:
        open_tasks = store.list_open_delegated_tasks()
    finally:
        store.close()

    assert open_tasks[0].approval_required is False


def test_main_prints_delegated_task_result(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    monkeypatch.chdir(tmp_path)

    main(
        [
            "Prepare daily review",
            "Summarize what needs attention.",
            "--next-step",
            "Ask memory summary.",
            "--memory",
            str(memory_path),
        ]
    )

    output = capsys.readouterr().out
    assert "Recorded delegated task" in output
    assert "Prepare daily review" in output
