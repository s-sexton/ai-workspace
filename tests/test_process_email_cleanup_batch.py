from __future__ import annotations

import json

from assistant.src.process_email_cleanup_batch import (
    process_email_cleanup_batch,
)
from common.memory import DuckDbMemoryStore


def test_process_email_cleanup_batch_dry_run_parses_numbered_directions(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    manifest_path = tmp_path / "reports" / "email-cleanup-batch.json"
    _write_config(tmp_path)
    items = _seed_email_memory(memory_path)
    _write_manifest(manifest_path, items)

    result = process_email_cleanup_batch(
        "delete 1, 3. move 2 to Authorize.net",
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=manifest_path,
    )

    assert "# Email Cleanup Batch Plan" in result
    assert "- Commands: 3" in result
    assert "Item 1 -> Deleted Items: First item" in result
    assert "Item 2 -> Clarity/Authorize.net: Second item" in result
    assert "Item 3 -> Deleted Items: Third item" in result
    assert "Would record approved move action" in result
    assert "Learning feedback recorded" not in result

    store = DuckDbMemoryStore(memory_path)
    try:
        approved_actions = store.actions_by_approval_status("approved")
        feedback = store.recent_feedback()
    finally:
        store.close()

    assert approved_actions == ()
    assert feedback == ()


def test_process_email_cleanup_batch_execute_records_approved_actions(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    manifest_path = tmp_path / "reports" / "email-cleanup-batch.json"
    _write_config(tmp_path)
    items = _seed_email_memory(memory_path)
    _write_manifest(manifest_path, items)

    result = process_email_cleanup_batch(
        "move 1-2 to Noise; move 3 to Clarity/Authorize.net",
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=manifest_path,
        execute=True,
    )

    assert "# Email Cleanup Batch Execution" in result
    assert "- Commands: 3" in result
    assert "- Learning feedback recorded: 3" in result
    assert "Recorded approved move action to Clarity/Noise" in result
    assert "Recorded approved move action to Clarity/Authorize.net" in result

    store = DuckDbMemoryStore(memory_path)
    try:
        approved_actions = store.actions_by_approval_status("approved")
        feedback = store.recent_feedback()
        latest_run = store.latest_run(workflow="email-cleanup-batch-directions")
    finally:
        store.close()

    targets = sorted(action.action_target for action in approved_actions)
    assert targets == [
        "Clarity/Authorize.net",
        "Clarity/Noise",
        "Clarity/Noise",
    ]
    assert all(action.action_type.startswith("propose_email_move_") for action in approved_actions)
    assert len(feedback) == 3
    assert sorted(record.feedback_type for record in feedback) == [
        "noise",
        "noise",
        "review",
    ]
    assert any(
        record.feedback_text == "Filed to Clarity/Authorize.net during email cleanup."
        for record in feedback
    )
    assert "learned from 3 item(s)" in latest_run.summary


def test_process_email_cleanup_batch_splits_comma_before_command_verb(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    manifest_path = tmp_path / "reports" / "email-cleanup-batch.json"
    _write_config(tmp_path)
    items = _seed_email_memory(memory_path)
    _write_manifest(manifest_path, items)

    result = process_email_cleanup_batch(
        "delete 1, move 2 to Review",
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=manifest_path,
        execute=True,
    )

    assert "# Email Cleanup Batch Execution" in result
    assert "- Commands: 2" in result

    store = DuckDbMemoryStore(memory_path)
    try:
        approved_actions = store.actions_by_approval_status("approved")
    finally:
        store.close()

    targets = {
        action.item_external_id: action.action_target
        for action in approved_actions
    }
    assert targets["message-1"] == "Deleted Items"
    assert targets["message-2"] == "Clarity/Review"


def test_process_email_cleanup_batch_rejects_folder_outside_namespace(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    manifest_path = tmp_path / "reports" / "email-cleanup-batch.json"
    _write_config(tmp_path)
    items = _seed_email_memory(memory_path)
    _write_manifest(manifest_path, items)

    result = process_email_cleanup_batch(
        "move 1 to Clarity/../Archive",
        root=tmp_path,
        memory_path=memory_path,
        manifest_path=manifest_path,
        execute=True,
    )

    assert "Target folder is not allowed." in result

    store = DuckDbMemoryStore(memory_path)
    try:
        approved_actions = store.actions_by_approval_status("approved")
        feedback = store.recent_feedback()
    finally:
        store.close()

    assert approved_actions == ()
    assert feedback == ()


def _write_config(root):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "email": {
              "approvedMailboxes": [
                {"address": "scott.sexton@sendthisfile.com", "accessMode": "read_write"}
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


def _seed_email_memory(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="email-cleanup-fixture")
        source = store.record_source(
            source_type="email",
            display_name="scott.sexton@sendthisfile.com",
            scope_label="scott.sexton@sendthisfile.com",
        )
        items = []
        for index, subject in enumerate(("First item", "Second item", "Third item"), 1):
            item = store.record_item_seen(
                source_id=source.source_id,
                external_id=f"message-{index}",
                item_type="email_message",
                subject=subject,
                sender_or_owner=f"sender{index}@example.invalid",
                first_seen_run_id=run.run_id,
            )
            store.record_classification(
                item_id=item.item_id,
                run_id=run.run_id,
                label="review",
                reason="Fixture item.",
            )
            items.append(item)
        return tuple(items)
    finally:
        store.close()


def _write_manifest(path, items):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "mailbox": "scott.sexton@sendthisfile.com",
                "items": [
                    {
                        "number": index,
                        "itemId": item.item_id,
                        "externalId": item.external_id,
                        "sourceType": "email",
                        "sourceScope": "scott.sexton@sendthisfile.com",
                        "itemType": "email_message",
                        "subject": item.subject,
                        "senderOrOwner": item.sender_or_owner,
                        "updatedAt": item.updated_at,
                        "label": "review",
                        "reason": "Fixture item.",
                    }
                    for index, item in enumerate(items, 1)
                ],
            }
        ),
        encoding="utf-8",
    )
