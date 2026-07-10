from __future__ import annotations

from assistant.src.email_preferences import (
    record_email_sender_preference,
    remove_email_sender_preference,
)
from common.memory import DuckDbMemoryStore


def test_records_email_sender_preference(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"

    message = record_email_sender_preference(
        root=tmp_path,
        mailbox="inbox@example.invalid",
        memory_path=memory_path,
        match_type="sender",
        pattern="Promo@Example.Invalid",
        label="noise",
    )

    store = DuckDbMemoryStore(memory_path)
    try:
        preferences = store.list_email_sender_preferences()
        actions = store.recent_actions()
    finally:
        store.close()

    assert "Recorded noise email preference" in message
    assert preferences[0].mailbox == "inbox@example.invalid"
    assert preferences[0].match_type == "sender"
    assert preferences[0].pattern == "promo@example.invalid"
    assert preferences[0].label == "noise"
    assert actions[0].action_type == "record_email_sender_preference"


def test_rejects_unapproved_mailbox(tmp_path):
    _write_config(tmp_path)

    message = record_email_sender_preference(
        root=tmp_path,
        mailbox="other@example.invalid",
        memory_path=tmp_path / "logs" / "memory.duckdb",
        match_type="sender",
        pattern="promo@example.invalid",
        label="noise",
    )

    assert message == "Email mailbox is not approved: other@example.invalid"


def test_removes_email_sender_preference(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    record_email_sender_preference(
        root=tmp_path,
        mailbox="inbox@example.invalid",
        memory_path=memory_path,
        match_type="sender",
        pattern="promo@example.invalid",
        label="noise",
    )
    store = DuckDbMemoryStore(memory_path)
    try:
        preference = store.list_email_sender_preferences()[0]
    finally:
        store.close()

    message = remove_email_sender_preference(
        root=tmp_path,
        memory_path=memory_path,
        preference_id=preference.preference_id,
    )

    store = DuckDbMemoryStore(memory_path)
    try:
        preferences = store.list_email_sender_preferences()
        actions = store.recent_actions(limit=5)
    finally:
        store.close()

    assert "Removed noise email preference" in message
    assert preferences == ()
    assert actions[0].action_type == "remove_email_sender_preference"


def test_remove_reports_unknown_preference(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    record_email_sender_preference(
        root=tmp_path,
        mailbox="inbox@example.invalid",
        memory_path=memory_path,
        match_type="sender",
        pattern="promo@example.invalid",
        label="noise",
    )

    message = remove_email_sender_preference(
        root=tmp_path,
        memory_path=memory_path,
        preference_id="missing",
    )

    assert message == "Unknown email preference: missing"


def _write_config(root):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "email": {
              "approvedMailboxes": [
                {"address": "inbox@example.invalid", "accessMode": "read_write"}
              ],
              "defaultMailbox": "inbox@example.invalid",
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
