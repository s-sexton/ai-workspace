from __future__ import annotations

import json
from datetime import datetime

from assistant.src.generate_daily_brief import generate_daily_brief, main
from common.memory import DuckDbMemoryStore


def test_generate_daily_brief_renders_email_ready_sections(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _write_config(tmp_path)
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
    assert result.outlook_attention_count == 3
    assert result.calendar_event_count == 3
    assert result.jira_ticket_count == 1
    assert result.open_task_count == 1
    assert result.pending_action_count == 1
    assert "# Clarity Daily Brief" in brief
    assert "Date: 2026-07-16 through 2026-07-22" in brief
    assert "Generated: 2026-07-16T07:30:00" in brief
    assert "## At A Glance" in brief
    assert "- Inbox items that may need attention: 3" in brief
    assert "- Calendar events next 7 days: 3" in brief
    assert "- Open Jira tickets: 1" in brief
    assert "- Open tasks: 1" in brief
    assert "## Inbox Attention" in brief
    assert "### scott.sexton@sendthisfile.com" in brief
    assert "1. Date: 2026-07-16 6:45 AM" in brief
    assert "From: customer@example.invalid" in brief
    assert "Subject: Review customer invoice" in brief
    assert "Recommendation: Potentially important operational message." in brief
    assert "### legal@example.invalid" in brief
    assert "2. Date: 2026-07-16 6:15 AM" in brief
    assert "From: counsel@example.invalid" in brief
    assert "Subject: Review legal notice" in brief
    assert "### sesexton@gmail.com" in brief
    assert "3. Date: 2026-07-16 6:05 AM" in brief
    assert "Subject: Personal review item" in brief
    assert "Clarity Day in a Glance - 2026-07-16" not in brief
    assert "Clarity item:" not in brief
    assert "## Calendar: 2026-07-16 through 2026-07-22" in brief
    assert "2026-07-16 9:00 AM-9:30 AM Morning standup" in brief
    assert "2026-07-18 All day Pay Citi Double Points" in brief
    assert "2026-07-20 11:00 AM-12:00 PM Weekly planning" in brief
    assert "## Open Jira Tickets" in brief
    assert "Subject: ACCT-101: Finish reconciliation" in brief
    assert "## Open Tasks" in brief
    assert "Prepare renewal packet" in brief
    assert "Next step: Draft owner summary." in brief
    assert "## Pending Approvals" in brief
    assert (
        "Move email to Clarity/Review: Review customer invoice "
        "(scott.sexton@sendthisfile.com)"
    ) in brief
    pending_section = brief.split("## Pending Approvals", maxsplit=1)[1].split(
        "## Reply To Clarity",
        maxsplit=1,
    )[0]
    assert "Action:" not in pending_section
    assert "Target: Clarity/Review" not in brief
    assert "Proposed moving message metadata to Clarity/Review." not in brief
    assert "## Reply To Clarity" in brief
    assert "authenticated replies from approved senders" in brief
    assert manifest["briefDate"] == "2026-07-16"
    assert manifest["sections"]["inbox"][0]["number"] == 1
    assert manifest["sections"]["inbox"][0]["itemId"]
    assert manifest["sections"]["inbox"][0]["externalId"] == "message-1"
    assert manifest["sections"]["inbox"][1]["number"] == 2
    assert manifest["sections"]["inbox"][1]["sourceScope"] == "legal@example.invalid"
    assert manifest["sections"]["inbox"][2]["sourceScope"] == "sesexton@gmail.com"
    assert manifest["sections"]["outlook"] == manifest["sections"]["inbox"]
    assert manifest["sections"]["calendar"][0]["externalId"] == "event-1"
    assert manifest["sections"]["jira"][0]["externalId"] == "ACCT-101"
    assert manifest["sections"]["tasks"][0]["title"] == "Prepare renewal packet"
    assert manifest["sections"]["pendingApprovals"][0]["number"] == 1
    assert manifest["sections"]["pendingApprovals"][0]["actionType"] == (
        "propose_email_move_review"
    )
    assert manifest["sections"]["pendingApprovals"][0]["target"] == "Clarity/Review"
    assert manifest["sections"]["pendingApprovals"][0]["subject"] == (
        "Review customer invoice"
    )

    store = DuckDbMemoryStore(memory_path)
    try:
        latest_run = store.latest_run(workflow="daily-brief")
        actions = store.recent_actions()
        artifacts = store.list_generated_artifacts(run_id=latest_run.run_id)
    finally:
        store.close()

    assert latest_run is not None
    assert "inbox=3, calendar=3, jira=1, tasks=1, pending=1" in latest_run.summary
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
    assert manifest["sections"]["inbox"] == []
    assert manifest["sections"]["tasks"] == []
    assert manifest["sections"]["pendingApprovals"] == []
    assert not memory_path.exists()


def test_generate_daily_brief_includes_latest_calendar_review_for_date(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _write_config(tmp_path)
    _seed_overnight_calendar_memory(memory_path)

    result = generate_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-20",
        generated_at=datetime(2026, 7, 20, 7, 30),
    )

    brief = output_path.read_text(encoding="utf-8")
    manifest = json.loads(output_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert result.calendar_event_count == 1
    assert "## Calendar: 2026-07-20 through 2026-07-26" in brief
    assert "Hotschedules: 55 PT Adult Part Time" in brief
    assert manifest["sections"]["calendar"][0]["externalId"] == "overnight-event"


def test_generate_daily_brief_uses_limit_per_inbox(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _write_config(tmp_path)
    _seed_many_mailbox_items(memory_path)

    result = generate_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-16",
        limit=2,
    )

    brief = output_path.read_text(encoding="utf-8")
    manifest = json.loads(output_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert result.outlook_attention_count == 6
    assert "- Inbox items that may need attention: 6" in brief
    assert "### scott.sexton@sendthisfile.com" in brief
    assert "### legal@example.invalid" in brief
    assert "### sesexton@gmail.com" in brief
    assert [item["sourceScope"] for item in manifest["sections"]["inbox"]] == [
        "scott.sexton@sendthisfile.com",
        "scott.sexton@sendthisfile.com",
        "legal@example.invalid",
        "legal@example.invalid",
        "sesexton@gmail.com",
        "sesexton@gmail.com",
    ]


def test_generate_daily_brief_does_not_globally_cap_calendar_window(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _write_config(tmp_path)
    _seed_many_calendar_items(memory_path)

    result = generate_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-20",
        limit=2,
    )

    brief = output_path.read_text(encoding="utf-8")
    manifest = json.loads(output_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert result.calendar_event_count == 7
    assert "- Calendar events next 7 days: 7" in brief
    assert "2026-07-20 9:00 AM-9:30 AM Calendar item 1" in brief
    assert "2026-07-26 9:00 AM-9:30 AM Calendar item 7" in brief
    assert len(manifest["sections"]["calendar"]) == 7


def test_main_prints_daily_brief_summary(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _write_config(tmp_path)
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
    assert "Inbox attention: 3" in output
    assert "Calendar events (7 days): 3" in output
    assert "Open Jira tickets: 1" in output
    assert "Open tasks: 1" in output
    assert "Pending approvals: 1" in output


def _write_config(root):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "dailyBrief": {
              "sender": "clarity@sendthisfile.ai",
              "recipients": ["scott@example.invalid"],
              "subjectPrefix": "Clarity Day in a Glance"
            },
            "email": {
              "approvedMailboxes": [
                {"address": "scott.sexton@sendthisfile.com", "accessMode": "read_write"},
                {"address": "legal@example.invalid", "accessMode": "read"},
                {"address": "sesexton@gmail.com", "accessMode": "read_write"}
              ],
              "defaultMailbox": "scott.sexton@sendthisfile.com",
              "folderNamespace": "Clarity",
              "folderPolicy": {
                "review": "Clarity/Review",
                "noise": "Clarity/Noise",
                "trash": "Deleted Items"
              },
              "maxMessages": 25
            }
          }
        }
        """,
        encoding="utf-8",
    )


def _seed_daily_memory(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="email-review")
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
        legal_source = store.record_source(
            source_type="email",
            display_name="legal@example.invalid",
            scope_label="legal@example.invalid",
        )
        legal_item = store.record_item_seen(
            source_id=legal_source.source_id,
            external_id="legal-message-1",
            item_type="email_message",
            subject="Review legal notice",
            sender_or_owner="counsel@example.invalid",
            updated_at="2026-07-16T06:15:00-05:00",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=legal_item.item_id,
            run_id=run.run_id,
            label="review",
            reason="Potentially important legal notice.",
        )
        clarity_item = store.record_item_seen(
            source_id=email_source.source_id,
            external_id="clarity-message-1",
            item_type="email_message",
            subject="Clarity Day in a Glance - 2026-07-16",
            sender_or_owner="clarity@sendthisfile.ai",
            updated_at="2026-07-16T07:30:00-05:00",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=clarity_item.item_id,
            run_id=run.run_id,
            label="review",
            reason="Generated daily brief should not appear as attention item.",
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
            sender_or_owner="family@example.invalid",
            updated_at="2026-07-16T06:05:00-05:00",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=gmail_item.item_id,
            run_id=run.run_id,
            label="review",
            reason="Personal inbox item that may need attention.",
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
        all_day_calendar_item = store.record_item_seen(
            source_id=calendar_source.source_id,
            external_id="event-all-day",
            item_type="calendar_event",
            subject="Pay Citi Double Points",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=all_day_calendar_item.item_id,
            run_id=run.run_id,
            label="calendar",
            reason=(
                "Calendar event starts at 2026-07-18. "
                "Ends at 2026-07-19."
            ),
        )
        future_calendar_item = store.record_item_seen(
            source_id=calendar_source.source_id,
            external_id="event-2",
            item_type="calendar_event",
            subject="Weekly planning",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=future_calendar_item.item_id,
            run_id=run.run_id,
            label="calendar",
            reason=(
                "Calendar event starts at 2026-07-20T11:00:00-05:00. "
                "Ends at 2026-07-20T12:00:00-05:00."
            ),
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
        store.create_delegated_task(
            created_run_id=run.run_id,
            title="Prepare renewal packet",
            request="Pull renewal context together.",
            status="in_progress",
            next_step="Draft owner summary.",
        )
        store.finish_run(run.run_id, status="completed")
    finally:
        store.close()


def _seed_overnight_calendar_memory(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(
            workflow="calendar-review",
            started_at="2026-07-20T12:00:00+00:00",
        )
        source = store.record_source(
            source_type="calendar",
            display_name="sexton-family calendar",
            scope_label="sexton-family",
        )
        item = store.record_item_seen(
            source_id=source.source_id,
            external_id="overnight-event",
            item_type="calendar_event",
            subject="Hotschedules: 55 PT Adult Part Time",
            updated_at="2026-07-19T23:00:00-05:00",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=item.item_id,
            run_id=run.run_id,
            label="calendar",
            reason=(
                "Calendar event starts at 2026-07-19T23:00:00-05:00. "
                "Ends at 2026-07-20T08:00:00-05:00."
            ),
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary="Read 1 event(s) from sexton-family for 2026-07-20.",
        )
    finally:
        store.close()


def _seed_many_mailbox_items(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="email-review")
        for mailbox in (
            "scott.sexton@sendthisfile.com",
            "legal@example.invalid",
            "sesexton@gmail.com",
        ):
            source = store.record_source(
                source_type="email",
                display_name=mailbox,
                scope_label=mailbox,
            )
            for index in range(3):
                item = store.record_item_seen(
                    source_id=source.source_id,
                    external_id=f"{mailbox}-message-{index + 1}",
                    item_type="email_message",
                    subject=f"{mailbox} review {index + 1}",
                    sender_or_owner=f"sender{index + 1}@example.invalid",
                    updated_at=f"2026-07-16T06:4{index}:00-05:00",
                    first_seen_run_id=run.run_id,
                )
                store.record_classification(
                    item_id=item.item_id,
                    run_id=run.run_id,
                    label="review",
                    reason="Needs attention.",
                )
        store.finish_run(run.run_id, status="completed")
    finally:
        store.close()


def _seed_many_calendar_items(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="calendar-review")
        source = store.record_source(
            source_type="calendar",
            display_name="work calendar",
            scope_label="work",
        )
        for index in range(7):
            item_date = f"2026-07-{20 + index:02d}"
            item = store.record_item_seen(
                source_id=source.source_id,
                external_id=f"event-{index + 1}",
                item_type="calendar_event",
                subject=f"Calendar item {index + 1}",
                first_seen_run_id=run.run_id,
            )
            store.record_classification(
                item_id=item.item_id,
                run_id=run.run_id,
                label="calendar",
                reason=(
                    f"Calendar event starts at {item_date}T09:00:00-05:00. "
                    f"Ends at {item_date}T09:30:00-05:00."
                ),
            )
        store.finish_run(run.run_id, status="completed")
    finally:
        store.close()
