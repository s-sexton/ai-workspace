from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from assistant.src.send_daily_brief import main, render_daily_brief_html, send_daily_brief
from common.memory import DuckDbMemoryStore


@dataclass
class FakeSendTransport:
    calls: list[tuple[str, tuple[str, ...], str, str, str | None]]

    def send_mail(
        self,
        *,
        sender: str,
        recipients: tuple[str, ...],
        subject: str,
        body_text: str,
        body_html: str | None = None,
    ) -> None:
        self.calls.append((sender, recipients, subject, body_text, body_html))


def test_send_daily_brief_dry_run_generates_without_sending(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path)
    transport = FakeSendTransport(calls=[])

    result = send_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-16",
        send_transport=transport,
    )

    assert result.sent is False
    assert result.sender == "clarity@example.invalid"
    assert result.recipients == ("scott@example.invalid",)
    assert result.subject == "Clarity Day in a Glance - 2026-07-16"
    assert output_path.is_file()
    assert result.html_path == output_path.with_suffix(".html")
    assert result.html_path.is_file()
    assert transport.calls == []


def test_send_daily_brief_execute_sends_generated_body(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path)
    transport = FakeSendTransport(calls=[])

    result = send_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-16",
        execute=True,
        send_transport=transport,
    )

    assert result.sent is True
    assert len(transport.calls) == 1
    sender, recipients, subject, body_text, body_html = transport.calls[0]
    assert sender == "clarity@example.invalid"
    assert recipients == ("scott@example.invalid",)
    assert subject == "Clarity Day in a Glance - 2026-07-16"
    assert "# Clarity Daily Brief" in body_text
    assert body_text == output_path.read_text(encoding="utf-8")
    assert body_html is not None
    assert "<h1>Clarity Daily Brief</h1>" in body_html
    assert '<section class="section">' in body_html
    assert body_html == output_path.with_suffix(".html").read_text(encoding="utf-8")

    store = DuckDbMemoryStore(memory_path)
    try:
        latest_run = store.latest_run(workflow="send-daily-brief")
        actions = store.recent_actions()
    finally:
        store.close()

    assert latest_run is not None
    assert any(action.action_type == "send_daily_brief_email" for action in actions)


def test_send_daily_brief_can_refresh_google_calendar_window(tmp_path, monkeypatch):
    _write_config(tmp_path, include_calendar=True)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path)
    calls = []

    def fake_run_calendar_review(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(
        "assistant.src.send_daily_brief.run_calendar_review",
        fake_run_calendar_review,
    )

    result = send_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-20",
        calendar_window_days=3,
        refresh_calendars=True,
        use_google_calendars=True,
        google_calendar_transport=object(),
    )

    assert result.sent is False
    assert [call["calendar"] for call in calls] == [
        "sexton-family",
        "sexton-family",
        "sexton-family",
    ]
    assert [call["review_date"] for call in calls] == [
        "2026-07-20",
        "2026-07-21",
        "2026-07-22",
    ]
    assert all(call["use_google"] is True for call in calls)
    assert all(call["use_graph"] is False for call in calls)


def test_send_daily_brief_can_refresh_email_and_jira_before_generation(
    tmp_path,
    monkeypatch,
):
    _write_config(tmp_path, include_email=True)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path)
    email_calls = []
    jira_calls = []

    def fake_run_email_review(**kwargs):
        email_calls.append(kwargs)

    def fake_generate_local_jira_report(**kwargs):
        jira_calls.append(kwargs)

    monkeypatch.setattr(
        "assistant.src.send_daily_brief.run_email_review",
        fake_run_email_review,
    )
    monkeypatch.setattr(
        "assistant.src.send_daily_brief.generate_local_jira_report",
        fake_generate_local_jira_report,
    )

    result = send_daily_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        brief_date="2026-07-20",
        refresh_email=True,
        use_graph_email=True,
        use_gmail=True,
        graph_email_transport=object(),
        gmail_transport=object(),
        refresh_jira=True,
    )

    assert result.sent is False
    assert [call["mailbox"] for call in email_calls] == [
        "scott@example.invalid",
        "sesexton@gmail.com",
    ]
    assert email_calls[0]["use_gmail"] is False
    assert email_calls[1]["use_gmail"] is True
    assert len(jira_calls) == 1
    assert jira_calls[0]["use_live_jira"] is True
    assert jira_calls[0]["memory_path"] == memory_path


def test_send_daily_brief_names_mailbox_when_email_refresh_fails(
    tmp_path,
    monkeypatch,
):
    _write_config(tmp_path, include_email=True)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path)

    def fake_run_email_review(**kwargs):
        raise RuntimeError("provider denied")

    monkeypatch.setattr(
        "assistant.src.send_daily_brief.run_email_review",
        fake_run_email_review,
    )

    with pytest.raises(RuntimeError) as exc_info:
        send_daily_brief(
            root=tmp_path,
            memory_path=memory_path,
            output_path=output_path,
            brief_date="2026-07-20",
            refresh_email=True,
            use_graph_email=True,
            graph_email_transport=object(),
        )

    assert "Email refresh failed for mailbox scott@example.invalid" in str(exc_info.value)
    assert "provider denied" in str(exc_info.value)


def test_render_daily_brief_html_escapes_content_and_formats_sections():
    html_body = render_daily_brief_html(
        "# Clarity Daily Brief\n"
        "\n"
        "Date: 2026-07-20\n"
        "\n"
        "## At A Glance\n"
        "\n"
        "- Inbox items that may need attention: 3\n"
        "\n"
        "## Inbox Attention\n"
        "\n"
        "1. Date: 2026-07-20T07:00:00Z\n"
        "   From: bad<script>@example.invalid\n"
        "   Subject: Review & approve\n"
        "   Recommendation: Look at this.\n"
    )

    assert "<h1>Clarity Daily Brief</h1>" in html_body
    assert "<h2>At A Glance</h2>" in html_body
    assert '<div class="metric"><span>Inbox items that may need attention</span>' in html_body
    assert "font-size: 14px;" in html_body
    assert '<article class="item">' in html_body
    assert '<span class="item-number">1.</span> Date: 2026-07-20T07:00:00Z' in html_body
    assert "<span>From: </span><strong>bad&lt;script&gt;@example.invalid</strong>" in html_body
    assert "<span>Subject: </span><strong>Review &amp; approve</strong>" in html_body
    assert "bad&lt;script&gt;@example.invalid" in html_body
    assert "Review &amp; approve" in html_body


def test_render_daily_brief_html_formats_calendar_section_with_calendar_colors():
    html_body = render_daily_brief_html(
        "# Clarity Daily Brief\n"
        "\n"
        "## Calendar: 2026-07-20 through 2026-07-26\n"
        "\n"
        "1. 2026-07-20 7:00 PM-8:00 PM HOA Board Meeting\n"
        "   Calendar: sexton-family calendar\n"
        "\n"
        "2. 2026-07-21 2:00 PM-2:30 PM Touchbase\n"
        "   Calendar: stf-holiday-vacation calendar\n"
        "\n"
        "3. 2026-07-25 All day Pay Citi Double Points\n"
        "   Calendar: sexton-family calendar\n"
    )

    assert '<table class="calendar-table" role="presentation">' in html_body
    assert '<div class="calendar-legend">' in html_body
    assert '<span><i class="legend-swatch calendar-family"></i>Family</span>' in html_body
    assert (
        '<span><i class="legend-swatch calendar-sendthisfile"></i>SendThisFile</span>'
        in html_body
    )
    assert '<span class="calendar-day">Mon</span>' in html_body
    assert '<span class="calendar-day-date">2026-07-20</span>' in html_body
    assert '<span class="calendar-day">Sun</span>' in html_body
    assert '<span class="calendar-day-date">2026-07-26</span>' in html_body
    assert '<div class="calendar-block-time">7:00 PM-8:00 PM</div>' in html_body
    assert '<div class="calendar-block-time">All day</div>' in html_body
    assert "Pay Citi Double Points" in html_body
    assert "day Pay Citi" not in html_body
    assert "HOA Board Meeting" in html_body
    assert '<div class="calendar-block calendar-family">' in html_body
    assert '<div class="calendar-block calendar-sendthisfile">' in html_body


def test_main_prints_dry_run_summary(tmp_path, monkeypatch, capsys):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "daily.md"
    _seed_memory(memory_path)
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
    assert "# Clarity Daily Brief Email" in output
    assert "HTML:" in output
    assert "Sent: no" in output
    assert "Dry run only" in output


def test_main_rejects_execute_without_graph():
    with pytest.raises(SystemExit):
        main(["--execute"])


def test_main_rejects_graph_without_execute():
    with pytest.raises(SystemExit):
        main(["--graph"])


def test_main_rejects_refresh_calendars_without_provider():
    with pytest.raises(SystemExit):
        main(["--refresh-calendars"])


def test_main_rejects_refresh_email_without_provider():
    with pytest.raises(SystemExit):
        main(["--refresh-email"])


def _write_config(root, *, include_calendar=False, include_email=False):
    config_dir = root / "config"
    config_dir.mkdir()
    assistant_config = {
        "dailyBrief": {
            "sender": "clarity@example.invalid",
            "recipients": ["scott@example.invalid"],
            "subjectPrefix": "Clarity Day in a Glance",
        }
    }
    if include_calendar:
        assistant_config["calendar"] = {
            "approvedCalendars": [
                {
                    "label": "sexton-family",
                    "provider": "google",
                    "source": "family@example.invalid",
                    "accessMode": "read",
                }
            ],
            "defaultCalendar": "sexton-family",
            "maxEvents": 25,
        }
    if include_email:
        assistant_config["email"] = {
            "approvedMailboxes": [
                {"address": "scott@example.invalid", "accessMode": "read"},
                {"address": "sesexton@gmail.com", "accessMode": "read"},
            ],
            "defaultMailbox": "scott@example.invalid",
            "folderNamespace": "Clarity",
            "folderPolicy": {
                "review": "Clarity/Review",
                "noise": "Clarity/Noise",
                "trash": "Deleted Items",
            },
            "maxMessages": 25,
        }
    (config_dir / "config.json").write_text(
        json.dumps({"assistant": assistant_config}),
        encoding="utf-8",
    )


def _seed_memory(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="fixture")
        source = store.record_source(
            source_type="jira",
            display_name="Jira Cloud",
            scope_label="project = ACCT",
        )
        item = store.record_item_seen(
            source_id=source.source_id,
            external_id="ACCT-101",
            item_type="jira_issue",
            subject="Finish reconciliation",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=item.item_id,
            run_id=run.run_id,
            label="review",
            reason="Included in the Jira report.",
        )
        store.finish_run(run.run_id, status="completed")
    finally:
        store.close()
