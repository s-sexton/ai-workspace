from __future__ import annotations

from common.memory import DuckDbMemoryStore
from common.email import EmailMessage
from assistant.src.send_gmail_teams_summary import (
    create_gmail_teams_manifest,
    _formatted_received_at,
    _sender_display_text,
    gmail_message_link,
    record_gmail_teams_summary_memory,
    render_gmail_teams_summary,
)


def test_render_gmail_teams_summary_links_subjects_to_gmail_messages():
    message = EmailMessage(
        message_id="abc123",
        mailbox="sesexton@gmail.com",
        subject="Test Gmail item",
        sender="sender@example.com",
        received_at="Mon, 3 Aug 2026 10:00:00 -0500",
    )

    text = render_gmail_teams_summary(
        [message],
        mailbox="sesexton@gmail.com",
        mention="Scott Sexton",
    )

    assert "Scott Sexton" in text
    assert "**Gmail Inbox: sesexton@gmail.com**" in text
    assert "[Test Gmail item](https://mail.google.com/mail/u/0/#inbox/abc123)" in text
    assert "**From:** sender at example.com" in text
    assert "**Date:** 08/03/2026 10:00 AM" in text


def test_gmail_message_link_uses_inbox_message_id():
    assert gmail_message_link(" abc123 ") == (
        "https://mail.google.com/mail/u/0/#inbox/abc123"
    )


def test_create_gmail_teams_manifest_allows_future_actions():
    manifest = create_gmail_teams_manifest(
        (
            EmailMessage(
                message_id="abc123",
                mailbox="sesexton@gmail.com",
                subject="Test Gmail item",
            ),
        ),
        mailbox="sesexton@gmail.com",
    )

    assert manifest.items[0].number == 1
    assert manifest.items[0].source_type == "gmail"
    assert manifest.items[0].allowed_actions == (
        "trash",
        "move_review",
        "move_noise",
    )


def test_record_gmail_teams_summary_memory_links_manifest_items(tmp_path):
    memory_path = tmp_path / "memory.duckdb"

    record_gmail_teams_summary_memory(
        (
            EmailMessage(
                message_id="abc123",
                mailbox="sesexton@gmail.com",
                subject="Test Gmail item",
                sender="sender@example.com",
                received_at="Mon, 3 Aug 2026 10:00:00 -0500",
            ),
        ),
        mailbox="sesexton@gmail.com",
        access_mode="read_write",
        memory_path=memory_path,
    )

    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        item = store.find_item_seen("abc123")
    finally:
        store.close()
    assert item is not None
    assert item.subject == "Test Gmail item"
    assert item.sender_or_owner == "sender@example.com"


def test_sender_display_text_prefers_display_name():
    assert _sender_display_text("Example Sender <sender@example.com>") == (
        "Example Sender"
    )


def test_sender_display_text_breaks_bare_email_autolinking():
    assert _sender_display_text("sender@example.com") == "sender at example.com"


def test_formatted_received_at_supports_iso_dates():
    assert _formatted_received_at("2026-08-03T15:30:00-05:00") == (
        "08/03/2026 03:30 PM"
    )


def test_formatted_received_at_converts_to_central_time():
    assert _formatted_received_at("2026-08-03T21:30:00Z") == (
        "08/03/2026 04:30 PM"
    )
