from __future__ import annotations

from assistant.src.record_feedback import record_memory_feedback, main
from common.memory import DuckDbMemoryStore


def test_records_feedback_for_external_item_id(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    message = record_memory_feedback(
        item_reference="STF-1",
        feedback_type="noise",
        feedback_text="This was just an automated update.",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "Recorded feedback" in message
    assert "for STF-1: noise" in message

    store = DuckDbMemoryStore(memory_path)
    try:
        actions = store.recent_actions()
    finally:
        store.close()

    assert actions[0].action_type == "record_feedback"
    assert actions[0].approval_status == "not_required"
    assert actions[0].result == "Recorded noise feedback for STF-1."


def test_reports_missing_memory(tmp_path):
    message = record_memory_feedback(
        item_reference="STF-1",
        feedback_type="noise",
        feedback_text="No memory yet.",
        root=tmp_path,
        memory_path=tmp_path / "logs" / "missing.duckdb",
    )

    assert "No Clarity memory found" in message


def test_reports_missing_item(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    message = record_memory_feedback(
        item_reference="ACCT-404",
        feedback_type="review",
        feedback_text="Should be reviewed.",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert message == "No remembered item found for: ACCT-404."


def test_reports_unsupported_feedback_type(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    message = record_memory_feedback(
        item_reference="STF-1",
        feedback_type="maybe",
        feedback_text="Unclear.",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "Unsupported feedback type: maybe" in message


def test_main_prints_feedback_result(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)
    monkeypatch.chdir(tmp_path)

    main(
        [
            "STF-1",
            "useful",
            "Keep surfacing this.",
            "--memory",
            str(memory_path),
        ]
    )

    output = capsys.readouterr().out
    assert "Recorded feedback" in output
    assert "for STF-1: useful" in output


def _seed_memory(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="jira-report")
        source = store.record_source(
            source_type="jira",
            display_name="Jira Cloud",
            scope_label="project = STF",
        )
        store.record_item_seen(
            source_id=source.source_id,
            external_id="STF-1",
            item_type="jira_issue",
            subject="Build the first Jira report",
            first_seen_run_id=run.run_id,
        )
        store.finish_run(run.run_id, status="completed")
    finally:
        store.close()
