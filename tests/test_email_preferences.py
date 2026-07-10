from __future__ import annotations

from assistant.src.email_preferences import record_email_sender_preference
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
