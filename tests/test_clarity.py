from __future__ import annotations

from assistant.src.clarity import answer_clarity_request, main
from common.memory import DuckDbMemoryStore


def test_clarity_answers_emails_needing_attention(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_clarity_request(
        "What emails need immediate attention?",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Items Marked For Review" in answer
    assert "Review vendor terms [review]" in answer


def test_clarity_answers_pending_approval_question(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_clarity_request(
        "What needs approval?",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Pending Actions" in answer
    assert "propose_email_move_review - Review vendor terms [required]" in answer
    assert "Action:" in answer


def test_clarity_answers_what_did_you_do(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_clarity_request(
        "What did you do?",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Recent Actions" in answer
    assert "read_email_metadata [not_required]" in answer


def test_clarity_answers_email_move_plan(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_clarity_request(
        "Show my email move plan",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Email Move Plan" in answer
    assert "email-noise-1 to Clarity/Noise" in answer


def test_clarity_returns_unsupported_response_for_unwired_calendar_question(tmp_path):
    answer = answer_clarity_request(
        "What is on my family calendar today?",
        root=tmp_path,
        memory_path=tmp_path / "logs" / "memory.duckdb",
    )

    assert "do not know how to answer that yet" in answer
    assert "What emails need immediate attention?" in answer


def test_main_prints_clarity_answer(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)
    monkeypatch.chdir(tmp_path)

    main(["What emails need immediate attention?", "--memory", str(memory_path)])

    output = capsys.readouterr().out
    assert "# Items Marked For Review" in output


def test_main_runs_local_prompt(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)
    requests = iter(["What did you do?", "quit"])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(requests))

    main(["--memory", str(memory_path)])

    output = capsys.readouterr().out
    assert "Clarity local prompt" in output
    assert "# Recent Actions" in output


def _seed_memory(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="email-review")
        source = store.record_source(
            source_type="email",
            display_name="clarity@sendthisfile.ai",
            scope_label="clarity@sendthisfile.ai",
        )
        item = store.record_item_seen(
            source_id=source.source_id,
            external_id="email-review-1",
            item_type="email_message",
            subject="Review vendor terms",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=item.item_id,
            run_id=run.run_id,
            label="review",
            reason="No safe noise rule matched; keep for human review.",
        )
        store.record_assistant_action(
            run_id=run.run_id,
            item_id=item.item_id,
            action_type="propose_email_move_review",
            approval_status="required",
            action_target="Clarity/Review",
            result="Proposed moving message metadata to Clarity/Review.",
        )
        approved_item = store.record_item_seen(
            source_id=source.source_id,
            external_id="email-noise-1",
            item_type="email_message",
            subject="Monthly newsletter",
            first_seen_run_id=run.run_id,
        )
        store.record_assistant_action(
            run_id=run.run_id,
            item_id=approved_item.item_id,
            action_type="propose_email_move_noise",
            approval_status="approved",
            action_target="Clarity/Noise",
            result="Proposed moving message metadata to Clarity/Noise.",
        )
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="read_email_metadata",
            approval_status="not_required",
            result="Read 2 message(s) from clarity@sendthisfile.ai.",
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary="Reviewed 2 email message(s).",
        )
    finally:
        store.close()
