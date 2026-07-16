from __future__ import annotations

import json
from datetime import datetime

from assistant.src.generate_daily_brief import generate_daily_brief, main
from common.memory import DuckDbMemoryStore


def test_generate_daily_brief_renders_email_ready_sections(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_daily_memory(memory_path)

    result = generate_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-16",
        generated_at=datetime(2026, 7, 16, 7, 30),
    )

    brief = output_path.read_text(encoding="utf-8")
    manifest = json.loads(output_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert result.output_path == output_path
    assert result.manifest_path == output_path.with_suffix(".json")
    assert result.outlook_attention_count == 1
    assert result.calendar_event_count == 1
    assert result.jira_ticket_count == 1
    assert result.pending_action_count == 1
    assert "# Clarity Daily Brief" in brief
    assert "Date: 2026-07-16" in brief
    assert "Generated: 2026-07-16T07:30:00" in brief
    assert "## At A Glance" in brief
    assert "- Outlook items that may need attention: 1" in brief
    assert "- Calendar events today: 1" in brief
    assert "- Open Jira tickets: 1" in brief
    assert "## Outlook Inbox Attention" in brief
    assert "1. Review customer invoice" in brief
    assert "Source: scott.sexton@sendthisfile.com" in brief
    assert "## Day In A Glance" in brief
    assert "09:00-09:30 Morning standup" in brief
    assert "## Open Jira Tickets" in brief
    assert "ACCT-101: Finish reconciliation" in brief
    assert "## Reply To Clarity" in brief
    assert "authenticated replies from approved senders" in brief
    assert manifest["briefDate"] == "2026-07-16"
    assert manifest["sections"]["outlook"][0]["number"] == 1
    assert manifest["sections"]["outlook"][0]["itemId"]
    assert manifest["sections"]["outlook"][0]["externalId"] == "message-1"
    assert manifest["sections"]["calendar"][0]["externalId"] == "event-1"
    assert manifest["sections"]["jira"][0]["externalId"] == "ACCT-101"

    store = DuckDbMemoryStore(memory_path)
    try:
        latest_run = store.latest_run(workflow="daily-brief")
        actions = store.recent_actions()
        artifacts = store.list_generated_artifacts(run_id=latest_run.run_id)
    finally:
        store.close()

    assert latest_run is not None
    assert "outlook=1, calendar=1, jira=1, pending=1" in latest_run.summary
    assert actions[0].action_type == "generate_daily_brief"
    artifact_types = {artifact.artifact_type for artifact in artifacts}
    assert "markdown_daily_brief" in artifact_types
    assert "json_daily_brief_manifest" in artifact_types


def test_generate_daily_brief_handles_missing_memory(tmp_path):
    memory_path = tmp_path / "logs" / "missing.duckdb"
    output_path = tmp_path / "reports" / "daily.md"

    result = generate_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-16",
    )

    brief = output_path.read_text(encoding="utf-8")
    manifest = json.loads(output_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert result.outlook_attention_count == 0
    assert "No Clarity memory found" in brief
    assert manifest["sections"]["outlook"] == []
    assert not memory_path.exists()


def test_main_prints_daily_brief_summary(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_daily_memory(memory_path)
    monkeypatch.chdir(tmp_path)

    main(
        [
            "--memory",
            str(memory_path),
            "--output",
            str(output_path),
            "--date",
            "2026-07-16",
        ]
    )

    output = capsys.readouterr().out
    assert f"Wrote {output_path}" in output
    assert f"Manifest: {output_path.with_suffix('.json')}" in output
    assert "Outlook attention: 1" in output
    assert "Calendar events: 1" in output
    assert "Open Jira tickets: 1" in output
    assert "Pending approvals: 1" in output


def _seed_daily_memory(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="daily-brief-fixture")
        email_source = store.record_source(
            source_type="email",
            display_name="scott.sexton@sendthisfile.com",
            scope_label="scott.sexton@sendthisfile.com",
        )
        email_item = store.record_item_seen(
            source_id=email_source.source_id,
            external_id="message-1",
            item_type="email_message",
            subject="Review customer invoice",
            sender_or_owner="customer@example.invalid",
            updated_at="2026-07-16T06:45:00-05:00",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=email_item.item_id,
            run_id=run.run_id,
            label="review",
            reason="Potentially important operational message.",
        )
        gmail_source = store.record_source(
            source_type="email",
            display_name="sesexton@gmail.com",
            scope_label="sesexton@gmail.com",
        )
        gmail_item = store.record_item_seen(
            source_id=gmail_source.source_id,
            external_id="gmail-1",
            item_type="email_message",
            subject="Personal review item",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=gmail_item.item_id,
            run_id=run.run_id,
            label="review",
            reason="Should not appear in Outlook section.",
        )
        calendar_source = store.record_source(
            source_type="calendar",
            display_name="work calendar",
            scope_label="work",
        )
        calendar_item = store.record_item_seen(
            source_id=calendar_source.source_id,
            external_id="event-1",
            item_type="calendar_event",
            subject="Morning standup",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=calendar_item.item_id,
            run_id=run.run_id,
            label="calendar",
            reason=(
                "Calendar event starts at 2026-07-16T09:00:00-05:00. "
                "Ends at 2026-07-16T09:30:00-05:00. Location: Teams."
            ),
        )
        old_calendar_item = store.record_item_seen(
            source_id=calendar_source.source_id,
            external_id="event-old",
            item_type="calendar_event",
            subject="Yesterday event",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=old_calendar_item.item_id,
            run_id=run.run_id,
            label="calendar",
            reason="Calendar event starts at 2026-07-15T09:00:00-05:00.",
        )
        jira_source = store.record_source(
            source_type="jira",
            display_name="Jira Cloud",
            scope_label="project = ACCT",
        )
        jira_item = store.record_item_seen(
            source_id=jira_source.source_id,
            external_id="ACCT-101",
            item_type="jira_issue",
            subject="Finish reconciliation",
            sender_or_owner="Scott Sexton",
            updated_at="2026-07-16T06:00:00-05:00",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=jira_item.item_id,
            run_id=run.run_id,
            label="review",
            reason="Included in the Jira report for human review.",
        )
        store.record_assistant_action(
            run_id=run.run_id,
            item_id=email_item.item_id,
            action_type="propose_email_move_review",
            approval_status="required",
            action_target="Clarity/Review",
            result="Proposed moving message metadata to Clarity/Review.",
        )
        store.finish_run(run.run_id, status="completed")
    finally:
        store.close()
