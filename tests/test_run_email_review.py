from __future__ import annotations

import pytest

from assistant.src.run_email_review import run_email_review, main
from common.configuration import ConfigurationError
from common.email import StaticEmailTransport
from common.memory import DuckDbMemoryStore


def test_run_email_review_records_metadata_and_generates_brief(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    brief_path = tmp_path / "reports" / "brief.md"
    _write_config(tmp_path)

    result = run_email_review(
        root=tmp_path,
        mailbox="inbox@example.invalid",
        memory_path=memory_path,
        brief_output_path=brief_path,
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "legal-1",
                    "mailbox": "inbox@example.invalid",
                    "subject": "Legal review needed",
                    "sender": "legal@example.invalid",
                    "received_at": "2026-07-09T08:00:00-05:00",
                    "preview": "Please review the vendor terms.",
                },
                {
                    "message_id": "marketing-1",
                    "mailbox": "inbox@example.invalid",
                    "subject": "Monthly newsletter",
                    "sender": "marketing@example.invalid",
                    "preview": "Unsubscribe here.",
                },
            )
        ),
    )

    assert result.message_count == 2
    assert result.review_count == 1
    assert result.noise_count == 1
    assert result.proposed_action_count == 2
    assert result.brief_path == brief_path
    brief = brief_path.read_text(encoding="utf-8")
    assert "# Clarity Brief" in brief
    assert "# Items Marked As Noise" in brief
    assert "Monthly newsletter [noise]" in brief

    store = DuckDbMemoryStore(memory_path)
    try:
        recent = store.recent_memory()
        review_items = store.recent_memory_by_label("review")
        noise_items = store.recent_memory_by_label("noise")
        actions = store.recent_actions()
        run = store.get_run(result.run_id)
    finally:
        store.close()

    assert run.workflow == "email-review"
    assert run.summary == "Reviewed 2 email message(s) from inbox@example.invalid."
    assert {record.subject for record in recent} == {
        "Legal review needed",
        "Monthly newsletter",
    }
    assert review_items[0].subject == "Legal review needed"
    assert noise_items[0].subject == "Monthly newsletter"
    assert any(action.action_type == "read_email_metadata" for action in actions)
    assert any(action.action_type == "generate_clarity_brief" for action in actions)
    proposals = [
        action
        for action in actions
        if action.action_type.startswith("propose_email_move_")
    ]
    assert {action.action_type for action in proposals} == {
        "propose_email_move_review",
        "propose_email_move_noise",
    }
    assert {action.approval_status for action in proposals} == {"required"}
    assert {action.action_target for action in proposals} == {
        "Clarity/Review",
        "Clarity/Noise",
    }
    assert any("Clarity/Review" in (action.result or "") for action in proposals)
    assert any("Clarity/Noise" in (action.result or "") for action in proposals)


def test_run_email_review_is_mailbox_scoped(tmp_path):
    _write_config(
        tmp_path,
        approved_mailboxes=("legal@example.invalid", "personal@example.invalid"),
        default_mailbox="legal@example.invalid",
    )

    result = run_email_review(
        root=tmp_path,
        mailbox="legal@example.invalid",
        memory_path=tmp_path / "logs" / "memory.duckdb",
        brief_output_path=tmp_path / "reports" / "brief.md",
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "legal-1",
                    "mailbox": "legal@example.invalid",
                    "subject": "Legal question",
                },
                {
                    "message_id": "personal-1",
                    "mailbox": "personal@example.invalid",
                    "subject": "Family calendar",
                },
            )
        ),
    )

    assert result.mailbox == "legal@example.invalid"
    assert result.message_count == 1
    assert result.review_count == 1
    assert result.noise_count == 0
    assert result.proposed_action_count == 1


def test_run_email_review_trashes_unauthorized_clarity_mailbox_sender(tmp_path):
    _write_config(
        tmp_path,
        approved_mailboxes=("clarity@sendthisfile.ai",),
        default_mailbox="clarity@sendthisfile.ai",
        allowed_senders={
            "clarity@sendthisfile.ai": (
                "scott.sexton@sendthisfile.com",
                "sesexton@gmail.com",
            )
        },
    )

    result = run_email_review(
        root=tmp_path,
        mailbox="clarity@sendthisfile.ai",
        memory_path=tmp_path / "logs" / "memory.duckdb",
        brief_output_path=tmp_path / "reports" / "brief.md",
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "allowed-1",
                    "mailbox": "clarity@sendthisfile.ai",
                    "subject": "Please review this",
                    "sender": "scott.sexton@sendthisfile.com",
                    "spf": "pass",
                    "dkim": "pass",
                    "dmarc": "pass",
                },
                {
                    "message_id": "blocked-1",
                    "mailbox": "clarity@sendthisfile.ai",
                    "subject": "Ignore this",
                    "sender": "external@example.invalid",
                },
            )
        ),
    )

    assert result.message_count == 2
    assert result.review_count == 1
    assert result.trash_count == 1

    store = DuckDbMemoryStore(tmp_path / "logs" / "memory.duckdb")
    try:
        trash_items = store.recent_memory_by_label("trash")
        actions = store.recent_actions()
    finally:
        store.close()

    assert trash_items[0].subject == "Ignore this"
    assert any(
        action.action_type == "propose_email_move_trash"
        and action.action_target == "Deleted Items"
        and "Deleted Items" in (action.result or "")
        for action in actions
    )


def test_run_email_review_trashes_spoofed_clarity_mailbox_sender(tmp_path):
    _write_config(
        tmp_path,
        approved_mailboxes=("clarity@sendthisfile.ai",),
        default_mailbox="clarity@sendthisfile.ai",
        allowed_senders={
            "clarity@sendthisfile.ai": (
                "scott.sexton@sendthisfile.com",
                "sesexton@gmail.com",
            )
        },
    )

    result = run_email_review(
        root=tmp_path,
        mailbox="clarity@sendthisfile.ai",
        memory_path=tmp_path / "logs" / "memory.duckdb",
        brief_output_path=tmp_path / "reports" / "brief.md",
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "spoofed-1",
                    "mailbox": "clarity@sendthisfile.ai",
                    "subject": "Spoofed command",
                    "sender": "scott.sexton@sendthisfile.com",
                    "spf": "fail",
                    "dkim": "fail",
                    "dmarc": "fail",
                },
            )
        ),
    )

    assert result.message_count == 1
    assert result.review_count == 0
    assert result.trash_count == 1

    store = DuckDbMemoryStore(tmp_path / "logs" / "memory.duckdb")
    try:
        trash_items = store.recent_memory_by_label("trash")
    finally:
        store.close()

    assert trash_items[0].subject == "Spoofed command"
    assert "authentication checks" in trash_items[0].reason


def test_run_email_review_can_use_sample_graph_transport(tmp_path):
    _write_config(
        tmp_path,
        approved_mailboxes=("clarity@sendthisfile.ai",),
        default_mailbox="clarity@sendthisfile.ai",
        allowed_senders={
            "clarity@sendthisfile.ai": (
                "scott.sexton@sendthisfile.com",
                "sesexton@gmail.com",
            )
        },
    )

    result = run_email_review(
        root=tmp_path,
        mailbox="clarity@sendthisfile.ai",
        memory_path=tmp_path / "logs" / "memory.duckdb",
        brief_output_path=tmp_path / "reports" / "brief.md",
        use_sample_graph=True,
    )

    assert result.message_count == 2
    assert result.review_count == 1
    assert result.trash_count == 1

    store = DuckDbMemoryStore(tmp_path / "logs" / "memory.duckdb")
    try:
        review_items = store.recent_memory_by_label("review")
        trash_items = store.recent_memory_by_label("trash")
    finally:
        store.close()

    assert review_items[0].subject == "Please review my Clarity note"
    assert trash_items[0].subject == "Spoofed Clarity command"


def test_run_email_review_rejects_unapproved_mailbox(tmp_path):
    _write_config(tmp_path)

    with pytest.raises(ConfigurationError):
        run_email_review(
            root=tmp_path,
            mailbox="not-approved@example.invalid",
            memory_path=tmp_path / "logs" / "memory.duckdb",
            brief_output_path=tmp_path / "reports" / "brief.md",
        )


def test_run_email_review_uses_default_mailbox_and_configured_limit(tmp_path):
    _write_config(tmp_path, max_messages=1)

    result = run_email_review(
        root=tmp_path,
        mailbox="inbox@example.invalid",
        memory_path=tmp_path / "logs" / "memory.duckdb",
        brief_output_path=tmp_path / "reports" / "brief.md",
    )

    assert result.mailbox == "inbox@example.invalid"
    assert result.message_count == 1


def test_main_prints_safe_summary(tmp_path, monkeypatch, capsys):
    _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    main(
        [
            "--memory",
            str(tmp_path / "logs" / "memory.duckdb"),
            "--brief",
            str(tmp_path / "reports" / "brief.md"),
        ]
    )

    output = capsys.readouterr().out
    assert "Read 2 email message(s) from inbox@example.invalid" in output
    assert "Review: 1" in output
    assert "Noise: 1" in output
    assert "Trash: 0" in output
    assert "Proposed actions: 2" in output
    assert "Wrote brief" in output
    assert "Legal review needed" not in output


def test_main_can_use_sample_graph_transport(tmp_path, monkeypatch, capsys):
    _write_config(
        tmp_path,
        approved_mailboxes=("clarity@sendthisfile.ai",),
        default_mailbox="clarity@sendthisfile.ai",
        allowed_senders={
            "clarity@sendthisfile.ai": (
                "scott.sexton@sendthisfile.com",
                "sesexton@gmail.com",
            )
        },
    )
    monkeypatch.chdir(tmp_path)

    main(
        [
            "--mailbox",
            "clarity@sendthisfile.ai",
            "--sample-graph",
            "--memory",
            str(tmp_path / "logs" / "memory.duckdb"),
            "--brief",
            str(tmp_path / "reports" / "brief.md"),
        ]
    )

    output = capsys.readouterr().out
    assert "Read 2 email message(s) from clarity@sendthisfile.ai" in output
    assert "Review: 1" in output
    assert "Trash: 1" in output


def _write_config(
    root,
    *,
    approved_mailboxes=("inbox@example.invalid",),
    default_mailbox="inbox@example.invalid",
    max_messages=25,
    allowed_senders=None,
):
    config_dir = root / "config"
    config_dir.mkdir()
    allowed_senders = allowed_senders or {}
    approved_entries = []
    for mailbox in approved_mailboxes:
        senders = allowed_senders.get(mailbox, ())
        allowed = ""
        if senders:
            sender_values = ", ".join(f'"{sender}"' for sender in senders)
            allowed = f', "allowedSenders": [{sender_values}]'
        approved_entries.append(
            f'{{"address": "{mailbox}", "accessMode": "read"{allowed}}}'
        )
    approved = ", ".join(approved_entries)
    (config_dir / "config.json").write_text(
        f"""
        {{
          "assistant": {{
            "email": {{
              "approvedMailboxes": [{approved}],
              "defaultMailbox": "{default_mailbox}",
              "folderNamespace": "Clarity",
              "folderPolicy": {{
                "review": "Clarity/Review",
                "noise": "Clarity/Noise",
                "trash": "Deleted Items"
              }},
              "maxMessages": {max_messages}
            }}
          }}
        }}
        """,
        encoding="utf-8",
    )
