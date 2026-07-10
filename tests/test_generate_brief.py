from __future__ import annotations

from datetime import datetime

from assistant.src.generate_brief import generate_memory_brief, main
from common.memory import DuckDbMemoryStore


def test_generates_memory_brief(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "brief.md"
    _seed_memory(memory_path)

    result = generate_memory_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        generated_at=datetime(2026, 7, 9, 12, 0),
    )

    brief = output_path.read_text(encoding="utf-8")
    assert result == output_path
    assert "# Clarity Brief" in brief
    assert "Generated: 2026-07-09T12:00:00" in brief
    assert "# Clarity Command Center" in brief
    assert "# Clarity Focus Plan" in brief
    assert "# Clarity Memory Summary" in brief
    assert "# Items Marked For Review" in brief
    assert "# Items Marked As Noise" in brief
    assert "# Open Delegated Tasks" in brief
    assert "# Pending Actions" in brief
    assert "# Approved Actions" in brief
    assert "# Email Move Plan" in brief
    assert "# Recent Actions" in brief
    assert "Review billing export [review]" in brief
    assert "propose_email_move_review - Review billing export" in brief
    assert "Target: Clarity/Review" in brief
    assert "propose_email_move_noise - Monthly newsletter [approved]" in brief
    assert "Target: Clarity/Noise" in brief
    assert (
        "In mailbox scott.sexton@sendthisfile.com, move message "
        "email-noise-1 to Clarity/Noise"
    ) in brief

    store = DuckDbMemoryStore(memory_path)
    try:
        latest_run = store.latest_run(workflow="clarity-brief")
        actions = store.recent_actions()
        artifacts = store.list_generated_artifacts(run_id=latest_run.run_id)
    finally:
        store.close()

    assert latest_run is not None
    assert latest_run.summary == "Generated local Clarity memory brief."
    assert actions[0].action_type == "generate_clarity_brief"
    assert actions[0].result == f"Wrote {output_path}"
    assert artifacts[0].artifact_type == "markdown_brief"
    assert artifacts[0].path == str(output_path)


def test_generates_missing_memory_brief_without_creating_memory(tmp_path):
    memory_path = tmp_path / "logs" / "missing.duckdb"
    output_path = tmp_path / "reports" / "brief.md"

    generate_memory_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        generated_at=datetime(2026, 7, 9, 12, 0),
    )

    brief = output_path.read_text(encoding="utf-8")
    assert "No Clarity memory found" in brief
    assert not memory_path.exists()


def test_main_prints_output_path(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "brief.md"
    _seed_memory(memory_path)
    monkeypatch.chdir(tmp_path)

    main(["--memory", str(memory_path), "--output", str(output_path)])

    output = capsys.readouterr().out
    assert f"Wrote {output_path}" in output


def _seed_memory(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="jira-report")
        source = store.record_source(
            source_type="jira",
            display_name="Jira Cloud",
            scope_label="project = ACCT",
        )
        item = store.record_item_seen(
            source_id=source.source_id,
            external_id="ACCT-101",
            item_type="jira_issue",
            subject="Review billing export",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=item.item_id,
            run_id=run.run_id,
            label="review",
            reason="Customer-impacting accounting work.",
        )
        store.create_delegated_task(
            created_run_id=run.run_id,
            title="Prepare ACCT review",
            request="Summarize billing tickets.",
            next_step="Run the Jira report.",
        )
        store.record_assistant_action(
            run_id=run.run_id,
            item_id=item.item_id,
            action_type="propose_email_move_review",
            approval_status="required",
            action_target="Clarity/Review",
            result="Proposed moving message metadata to Clarity/Review.",
        )
        email_source = store.record_source(
            source_type="email",
            display_name="scott.sexton@sendthisfile.com",
            scope_label="scott.sexton@sendthisfile.com",
        )
        approved_item = store.record_item_seen(
            source_id=email_source.source_id,
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
            action_type="generate_jira_report",
            approval_status="not_required",
            result="Wrote reports/jira-report.md",
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary="Generated Jira report with 1 issue(s).",
        )
    finally:
        store.close()
