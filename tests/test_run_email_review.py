from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pytest

from assistant.src.run_email_review import (
    build_gmail_read_transport_from_config,
    build_graph_read_transport_from_config,
    run_email_review,
    main,
)
from common.configuration import ConfigurationError
from common.email import StaticEmailTransport
from common.memory import DuckDbMemoryStore


@dataclass
class FakeGraphResponse:
    status_code: int
    payload: Mapping[str, Any]

    def json(self) -> Mapping[str, Any]:
        return self.payload


class FakeGraphTransport:
    def get(self, url: str, headers: Mapping[str, str]) -> FakeGraphResponse:
        raise AssertionError("Unexpected Graph GET in factory test.")

    def post(
        self,
        url: str,
        headers: Mapping[str, str],
        body: Mapping[str, Any],
    ) -> FakeGraphResponse:
        raise AssertionError("Unexpected Graph POST in factory test.")


class FakeGraphTokenTransport:
    def __init__(self):
        self.calls: list[tuple[str, Mapping[str, str], Mapping[str, str]]] = []

    def post_form(
        self,
        url: str,
        headers: Mapping[str, str],
        form: Mapping[str, str],
    ) -> FakeGraphResponse:
        self.calls.append((url, headers, form))
        return FakeGraphResponse(200, {"access_token": "acquired-token"})


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


def test_build_graph_read_transport_from_config_uses_client_credentials(tmp_path):
    _write_graph_env(
        tmp_path,
        "GRAPH_TENANT_ID=tenant\n"
        "GRAPH_CLIENT_ID=client-id\n"
        "GRAPH_CLIENT_SECRET=super-secret\n",
    )
    token_transport = FakeGraphTokenTransport()

    transport = build_graph_read_transport_from_config(
        root=tmp_path,
        graph_transport=FakeGraphTransport(),
        token_transport=token_transport,
    )

    assert "acquired-token" not in repr(transport)
    assert len(token_transport.calls) == 1
    _, _, form = token_transport.calls[0]
    assert form["client_id"] == "client-id"
    assert form["client_secret"] == "super-secret"


def test_build_graph_read_transport_from_config_can_use_bearer_token(tmp_path):
    _write_graph_env(tmp_path, "GRAPH_ACCESS_TOKEN=direct-token\n")
    token_transport = FakeGraphTokenTransport()

    transport = build_graph_read_transport_from_config(
        root=tmp_path,
        graph_transport=FakeGraphTransport(),
        token_transport=token_transport,
        use_bearer_auth=True,
    )

    assert "direct-token" not in repr(transport)
    assert token_transport.calls == []


def test_build_gmail_read_transport_from_config_can_use_bearer_token(tmp_path):
    _write_graph_env(tmp_path, "GOOGLE_ACCESS_TOKEN=direct-token\n")
    token_transport = FakeGraphTokenTransport()

    transport = build_gmail_read_transport_from_config(
        root=tmp_path,
        gmail_transport=FakeGraphTransport(),
        token_transport=token_transport,
        use_bearer_auth=True,
    )

    assert "direct-token" not in repr(transport)
    assert token_transport.calls == []


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


def test_main_can_use_graph_read_transport(tmp_path, monkeypatch, capsys):
    _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    def fake_build_graph_read_transport_from_config(*, use_bearer_auth=False, **_):
        calls.append(use_bearer_auth)
        return StaticEmailTransport(
            (
                {
                    "message_id": "graph-live-1",
                    "mailbox": "inbox@example.invalid",
                    "subject": "Live Graph review",
                    "sender": "sender@example.invalid",
                },
            )
        )

    monkeypatch.setattr(
        "assistant.src.run_email_review.build_graph_read_transport_from_config",
        fake_build_graph_read_transport_from_config,
    )

    main(
        [
            "--graph",
            "--graph-bearer",
            "--memory",
            str(tmp_path / "logs" / "memory.duckdb"),
            "--brief",
            str(tmp_path / "reports" / "brief.md"),
        ]
    )

    output = capsys.readouterr().out
    assert calls == [True]
    assert "Read 1 email message(s) from inbox@example.invalid" in output
    assert "Review: 1" in output
    assert "Live Graph review" not in output


def test_main_can_use_gmail_read_transport(tmp_path, monkeypatch, capsys):
    _write_config(
        tmp_path,
        approved_mailboxes=("sesexton@gmail.com",),
        default_mailbox="sesexton@gmail.com",
        access_mode="read_write",
    )
    monkeypatch.chdir(tmp_path)
    calls = []

    def fake_build_gmail_read_transport_from_config(*, use_bearer_auth=False, **_):
        calls.append(use_bearer_auth)
        return StaticEmailTransport(
            (
                {
                    "message_id": "gmail-live-1",
                    "mailbox": "sesexton@gmail.com",
                    "subject": "Live Gmail review",
                    "sender": "friend@example.invalid",
                },
            )
        )

    monkeypatch.setattr(
        "assistant.src.run_email_review.build_gmail_read_transport_from_config",
        fake_build_gmail_read_transport_from_config,
    )

    main(
        [
            "--gmail",
            "--gmail-bearer",
            "--mailbox",
            "sesexton@gmail.com",
            "--memory",
            str(tmp_path / "logs" / "memory.duckdb"),
            "--brief",
            str(tmp_path / "reports" / "brief.md"),
        ]
    )

    output = capsys.readouterr().out
    assert calls == [True]
    assert "Read 1 email message(s) from sesexton@gmail.com" in output
    assert "Review: 1" in output
    assert "Live Gmail review" not in output


def test_main_rejects_graph_bearer_without_graph():
    with pytest.raises(SystemExit):
        main(["--graph-bearer"])


def test_main_rejects_gmail_bearer_without_gmail():
    with pytest.raises(SystemExit):
        main(["--gmail-bearer"])


def test_main_rejects_sample_graph_with_live_graph():
    with pytest.raises(SystemExit):
        main(["--sample-graph", "--graph"])


def _write_config(
    root,
    *,
    approved_mailboxes=("inbox@example.invalid",),
    default_mailbox="inbox@example.invalid",
    max_messages=25,
    allowed_senders=None,
    access_mode="read",
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
            f'{{"address": "{mailbox}", "accessMode": "{access_mode}"{allowed}}}'
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


def _write_graph_env(root, content):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    (config_dir / ".env").write_text(content, encoding="utf-8")
