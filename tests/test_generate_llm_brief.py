from __future__ import annotations

from assistant.src.generate_llm_brief import generate_fake_llm_brief, main
from common.memory import DuckDbMemoryStore


def test_generate_fake_llm_brief_writes_safe_report(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "llm.md"
    _seed_memory(memory_path)

    report = generate_fake_llm_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
    )

    assert "# Clarity Fake LLM Brief" in report
    assert "No LLM was called." in report
    assert "Review items: 1" in report
    assert "Pending approvals: 1" in report
    assert output_path.read_text(encoding="utf-8") == report


def test_generate_fake_llm_brief_can_skip_write(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "llm.md"
    _seed_memory(memory_path)

    report = generate_fake_llm_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        write=False,
    )

    assert "Clarity Fake LLM Brief" in report
    assert not output_path.exists()


def test_main_prints_and_writes_report(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "llm.md"
    _seed_memory(memory_path)
    monkeypatch.chdir(tmp_path)

    main(["--memory", str(memory_path), "--output", str(output_path)])

    output = capsys.readouterr().out
    assert "# Clarity Fake LLM Brief" in output
    assert "Wrote" in output
    assert output_path.is_file()


def _seed_memory(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="clarity-cycle")
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
            result="Proposed moving message metadata.",
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary="Read 1 message(s) from clarity@sendthisfile.ai.",
        )
    finally:
        store.close()
