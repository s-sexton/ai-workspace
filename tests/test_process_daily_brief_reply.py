from __future__ import annotations

import json
from datetime import datetime

from assistant.src.generate_daily_brief import generate_daily_brief
from assistant.src.process_daily_brief_reply import main, process_daily_brief_reply
from common.memory import DuckDbMemoryStore


def test_process_daily_brief_reply_dry_run_plans_supported_commands(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path)
    brief = generate_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-16",
        generated_at=datetime(2026, 7, 16, 7, 30),
    )

    result = process_daily_brief_reply(
        "Move item 1 to Noise\nMark sender from item 1 as noise",
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=brief.manifest_path,
    )

    assert "# Daily Brief Reply Plan" in result
    assert "move_item item 1 (outlook) -> noise" in result
    assert "Would record pending move action to Clarity/Noise." in result
    assert "sender_preference item 1 (outlook) -> noise" in result
    assert "Would record noise sender preference" in result

    store = DuckDbMemoryStore(memory_path)
    try:
        pending = store.pending_actions(limit=10)
        preferences = store.list_email_sender_preferences(limit=10)
    finally:
        store.close()

    assert not any(action.action_type == "propose_email_move_noise" for action in pending)
    assert preferences == ()


def test_process_daily_brief_reply_execute_records_local_actions(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path)
    brief = generate_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-16",
    )

    result = process_daily_brief_reply(
        "Move item 1 to Noise\nMark sender from item 1 as noise",
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=brief.manifest_path,
        execute=True,
    )

    assert "# Daily Brief Reply Execution" in result
    assert "Recorded pending move action to Clarity/Noise." in result
    assert "Recorded noise sender preference" in result

    store = DuckDbMemoryStore(memory_path)
    try:
        pending = store.pending_actions(limit=10)
        preferences = store.list_email_sender_preferences(limit=10)
        latest_run = store.latest_run(workflow="daily-brief-reply")
    finally:
        store.close()

    assert any(action.action_type == "propose_email_move_noise" for action in pending)
    assert pending[0].action_target == "Clarity/Noise"
    assert preferences[0].mailbox == "scott.sexton@sendthisfile.com"
    assert preferences[0].pattern == "customer@example.invalid"
    assert preferences[0].label == "noise"
    assert latest_run is not None
    assert "Executed 2 daily brief reply command" in latest_run.summary


def test_process_daily_brief_reply_can_approve_pending_cleanup(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path, pending_move=True)
    brief = generate_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-16",
    )

    result = process_daily_brief_reply(
        "Approve pending cleanup actions",
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=brief.manifest_path,
        execute=True,
    )

    assert "Approved 1 pending cleanup action" in result
    store = DuckDbMemoryStore(memory_path)
    try:
        approved = store.actions_by_approval_status("approved", limit=10)
    finally:
        store.close()

    assert len(approved) == 1
    assert approved[0].action_type == "propose_email_move_review"


def test_process_daily_brief_reply_can_approve_specific_pending_action(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path, pending_move=True)
    brief = generate_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-16",
    )
    store = DuckDbMemoryStore(memory_path)
    try:
        action_id = store.pending_actions(limit=10)[0].action_id
    finally:
        store.close()

    result = process_daily_brief_reply(
        f"Approve action {action_id}",
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=brief.manifest_path,
        execute=True,
    )

    assert "action_approval (pendingApprovals) -> approved" in result
    assert f"Updated action {action_id} to approved" in result
    store = DuckDbMemoryStore(memory_path)
    try:
        approved = store.actions_by_approval_status("approved", limit=10)
        pending = store.pending_actions(limit=10)
    finally:
        store.close()

    assert approved[0].action_id == action_id
    assert pending == ()


def test_process_daily_brief_reply_can_reject_specific_pending_action(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path, pending_move=True)
    brief = generate_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-16",
    )
    store = DuckDbMemoryStore(memory_path)
    try:
        action_id = store.pending_actions(limit=10)[0].action_id
    finally:
        store.close()

    result = process_daily_brief_reply(
        f"Reject action {action_id}",
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=brief.manifest_path,
        execute=True,
    )

    assert "action_approval (pendingApprovals) -> rejected" in result
    store = DuckDbMemoryStore(memory_path)
    try:
        rejected = store.actions_by_approval_status("rejected", limit=10)
    finally:
        store.close()

    assert rejected[0].action_id == action_id


def test_process_daily_brief_reply_supports_move_item_ranges(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path, extra_items=3)
    brief = generate_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-16",
    )

    result = process_daily_brief_reply(
        "Move items 1 - 4 to Trash",
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=brief.manifest_path,
    )

    assert "- Commands: 4" in result
    assert "move_item item 1 (outlook) -> trash" in result
    assert "move_item item 4 (outlook) -> trash" in result


def test_process_daily_brief_reply_supports_delete_ranges_and_move_shorthand(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path, extra_items=5)
    brief = generate_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-16",
    )

    result = process_daily_brief_reply(
        "Delete 1 - 5. Move 6 to review",
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=brief.manifest_path,
    )

    assert "- Commands: 6" in result
    assert "move_item item 1 (outlook) -> trash" in result
    assert "move_item item 5 (outlook) -> trash" in result
    assert "move_item item 6 (outlook) -> review" in result


def test_process_daily_brief_reply_ignores_quoted_original_message(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path, extra_items=1)
    brief = generate_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-16",
    )

    result = process_daily_brief_reply(
        "Move items 1 - 2 to Trash\n\n"
        "-----Original Message-----\n"
        "Reply with short directions such as:\n"
        "- Move item 1 to Review\n",
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=brief.manifest_path,
    )

    assert "- Commands: 2" in result
    assert "move_item item 1 (outlook) -> trash" in result
    assert "move_item item 2 (outlook) -> trash" in result
    assert "-> review" not in result.lower()


def test_process_daily_brief_reply_supports_gmail_section_alias(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    manifest_path = tmp_path / "reports" / "daily.json"
    gmail_item_id = _seed_manifest_item_memory(
        memory_path,
        source_type="email",
        source_scope="sesexton@gmail.com",
        item_type="email_message",
        external_id="gmail-message-1",
        subject="Gmail review item",
    )
    second_gmail_item_id = _seed_manifest_item_memory(
        memory_path,
        source_type="email",
        source_scope="sesexton@gmail.com",
        item_type="email_message",
        external_id="gmail-message-2",
        subject="Capitol Federal item",
    )
    _write_manifest(
        manifest_path,
        section="outlook",
        items=[
            {
                "number": 9,
                "itemId": gmail_item_id,
                "externalId": "gmail-message-1",
                "sourceType": "email",
                "sourceScope": "sesexton@gmail.com",
                "itemType": "email_message",
                "subject": "Gmail review item",
                "senderOrOwner": "sender@example.invalid",
            },
            {
                "number": 10,
                "itemId": second_gmail_item_id,
                "externalId": "gmail-message-2",
                "sourceType": "email",
                "sourceScope": "sesexton@gmail.com",
                "itemType": "email_message",
                "subject": "Capitol Federal item",
                "senderOrOwner": "sender@example.invalid",
            },
        ],
    )

    result = process_daily_brief_reply(
        "For sesexton@gmail.com mailbox, delete 9 and move 10 to Capitol Federal folder",
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=manifest_path,
        execute=True,
    )

    assert "move_item item 9 (outlook) -> trash: Gmail review item" in result
    assert "Recorded pending move action to Deleted Items." in result
    assert "move_item item 10 (outlook) -> folder: Capitol Federal item" in result
    assert "Recorded pending move action to Clarity/Capitol Federal." in result
    store = DuckDbMemoryStore(memory_path)
    try:
        pending = store.pending_actions(limit=10)
    finally:
        store.close()

    assert {action.action_type for action in pending} == {
        "propose_email_move_trash",
        "propose_email_move_folder",
    }
    assert {action.action_target for action in pending} == {
        "Deleted Items",
        "Clarity/Capitol Federal",
    }
    assert {action.source_scope_label for action in pending} == {"sesexton@gmail.com"}


def test_process_daily_brief_reply_records_jira_transition_requests(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    manifest_path = tmp_path / "reports" / "daily.json"
    jira_item_id = _seed_manifest_item_memory(
        memory_path,
        source_type="jira",
        source_scope="project in (STF, ACCT)",
        item_type="jira_issue",
        external_id="ACCT-6546",
        subject="Receipt summary",
    )
    _write_manifest(
        manifest_path,
        section="jira",
        item={
            "number": 1,
            "itemId": jira_item_id,
            "externalId": "ACCT-6546",
            "sourceType": "jira",
            "sourceScope": "project in (STF, ACCT)",
            "itemType": "jira_issue",
            "subject": "Receipt summary",
            "senderOrOwner": None,
        },
    )

    result = process_daily_brief_reply(
        "Mark Jira item 1 as done",
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=manifest_path,
        execute=True,
    )

    assert "jira_transition item 1 (jira) -> done: ACCT-6546: Receipt summary" in result
    assert "Recorded pending Jira transition request to done" in result
    assert "No Jira write" in result
    store = DuckDbMemoryStore(memory_path)
    try:
        pending = store.pending_actions(limit=10)
    finally:
        store.close()

    assert pending[0].action_type == "propose_jira_transition_done"
    assert pending[0].action_target == "done"


def test_process_daily_brief_reply_records_jira_key_delete_requests(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    manifest_path = tmp_path / "reports" / "daily.json"
    first_jira_item_id = _seed_manifest_item_memory(
        memory_path,
        source_type="jira",
        source_scope="project in (STF, ACCT)",
        item_type="jira_issue",
        external_id="ACCT-6546",
        subject="Receipt summary",
    )
    second_jira_item_id = _seed_manifest_item_memory(
        memory_path,
        source_type="jira",
        source_scope="project in (STF, ACCT)",
        item_type="jira_issue",
        external_id="ACCT-6543",
        subject="Another receipt summary",
    )
    _write_manifest(
        manifest_path,
        section="jira",
        items=[
            {
                "number": 1,
                "itemId": first_jira_item_id,
                "externalId": "ACCT-6546",
                "sourceType": "jira",
                "sourceScope": "project in (STF, ACCT)",
                "itemType": "jira_issue",
                "subject": "Receipt summary",
                "senderOrOwner": None,
            },
            {
                "number": 4,
                "itemId": second_jira_item_id,
                "externalId": "ACCT-6543",
                "sourceType": "jira",
                "sourceScope": "project in (STF, ACCT)",
                "itemType": "jira_issue",
                "subject": "Another receipt summary",
                "senderOrOwner": None,
            },
        ],
    )

    result = process_daily_brief_reply(
        "For the Jira tickets, delete ACCT-6546, ACCT-6543.",
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=manifest_path,
        execute=True,
    )

    assert "jira_key_action item 1 (jira) -> delete: ACCT-6546: Receipt summary" in result
    assert "jira_key_action item 4 (jira) -> delete: ACCT-6543: Another receipt summary" in result
    assert "No Jira write" in result
    store = DuckDbMemoryStore(memory_path)
    try:
        pending = store.pending_actions(limit=10)
    finally:
        store.close()

    assert len(pending) == 2
    assert {action.action_type for action in pending} == {"propose_jira_delete"}
    assert {action.item_external_id for action in pending} == {"ACCT-6546", "ACCT-6543"}


def test_main_prints_reply_plan(tmp_path, monkeypatch, capsys):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path)
    brief = generate_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-16",
    )
    monkeypatch.chdir(tmp_path)

    main(
        [
            "--reply",
            "Move item 1 to Review",
            "--memory",
            str(memory_path),
            "--manifest",
            str(brief.manifest_path),
        ]
    )

    output = capsys.readouterr().out
    assert "# Daily Brief Reply Plan" in output
    assert "move_item item 1" in output


def _write_config(root):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "email": {
              "approvedMailboxes": [
                {
                  "address": "scott.sexton@sendthisfile.com",
                  "accessMode": "read_write"
                }
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


def _seed_memory(memory_path, *, pending_move=False, extra_items=0):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="email-review")
        source = store.record_source(
            source_type="email",
            display_name="scott.sexton@sendthisfile.com",
            scope_label="scott.sexton@sendthisfile.com",
        )
        item = store.record_item_seen(
            source_id=source.source_id,
            external_id="message-1",
            item_type="email_message",
            subject="Review customer invoice",
            sender_or_owner="customer@example.invalid",
            updated_at="2026-07-16T06:45:00-05:00",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=item.item_id,
            run_id=run.run_id,
            label="review",
            reason="Potentially important operational message.",
        )
        for index in range(extra_items):
            extra_item = store.record_item_seen(
                source_id=source.source_id,
                external_id=f"message-extra-{index + 1}",
                item_type="email_message",
                subject=f"Review customer invoice {index + 2}",
                sender_or_owner=f"customer{index + 2}@example.invalid",
                updated_at=f"2026-07-16T06:4{index}:00-05:00",
                first_seen_run_id=run.run_id,
            )
            store.record_classification(
                item_id=extra_item.item_id,
                run_id=run.run_id,
                label="review",
                reason="Potentially important operational message.",
            )
        if pending_move:
            store.record_assistant_action(
                run_id=run.run_id,
                item_id=item.item_id,
                action_type="propose_email_move_review",
                approval_status="required",
                action_target="Clarity/Review",
                result="Proposed moving message metadata to Clarity/Review.",
            )
        store.finish_run(run.run_id, status="completed")
    finally:
        store.close()


def _seed_manifest_item_memory(
    memory_path,
    *,
    source_type,
    source_scope,
    item_type,
    external_id,
    subject,
):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="manifest-fixture")
        source = store.record_source(
            source_type=source_type,
            display_name=source_scope,
            scope_label=source_scope,
        )
        item = store.record_item_seen(
            source_id=source.source_id,
            external_id=external_id,
            item_type=item_type,
            subject=subject,
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=item.item_id,
            run_id=run.run_id,
            label="review",
            reason="Fixture item for reply parser.",
        )
        store.finish_run(run.run_id, status="completed")
        return item.item_id
    finally:
        store.close()


def _write_manifest(path, *, section, item=None, items=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest_items = items if items is not None else [item]
    path.write_text(
        json.dumps(
            {
                "briefDate": "2026-07-20",
                "generatedAt": "2026-07-20T07:30:00",
                "sections": {
                    section: manifest_items,
                },
            }
        ),
        encoding="utf-8",
    )
