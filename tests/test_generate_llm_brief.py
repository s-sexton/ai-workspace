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
    store = DuckDbMemoryStore(memory_path)
    try:
        latest_run = store.latest_run(workflow="fake-llm-brief")
        artifacts = store.list_generated_artifacts(run_id=latest_run.run_id)
        actions = store.recent_actions()
    finally:
        store.close()

    assert latest_run is not None
    assert latest_run.status == "completed"
    assert latest_run.summary == "Generated local deterministic fake LLM brief."
    assert artifacts[0].path == str(output_path)
    assert artifacts[0].artifact_type == "markdown_fake_llm_brief"
    assert actions[0].action_type == "generate_fake_llm_brief"


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
    store = DuckDbMemoryStore(memory_path)
    try:
        latest_run = store.latest_run(workflow="fake-llm-brief")
    finally:
        store.close()

    assert latest_run is None


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
