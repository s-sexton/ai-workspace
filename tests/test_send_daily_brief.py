from __future__ import annotations

from dataclasses import dataclass

import pytest

from assistant.src.send_daily_brief import main, send_daily_brief
from common.memory import DuckDbMemoryStore


@dataclass
class FakeSendTransport:
    calls: list[tuple[str, tuple[str, ...], str, str]]

    def send_mail(
        self,
        *,
        sender: str,
        recipients: tuple[str, ...],
        subject: str,
        body_text: str,
    ) -> None:
        self.calls.append((sender, recipients, subject, body_text))


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
    sender, recipients, subject, body_text = transport.calls[0]
    assert sender == "clarity@example.invalid"
    assert recipients == ("scott@example.invalid",)
    assert subject == "Clarity Day in a Glance - 2026-07-16"
    assert "# Clarity Daily Brief" in body_text
    assert body_text == output_path.read_text(encoding="utf-8")

    store = DuckDbMemoryStore(memory_path)
    try:
        latest_run = store.latest_run(workflow="send-daily-brief")
        actions = store.recent_actions()
    finally:
        store.close()

    assert latest_run is not None
    assert any(action.action_type == "send_daily_brief_email" for action in actions)


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
    assert "Sent: no" in output
    assert "Dry run only" in output


def test_main_rejects_execute_without_graph():
    with pytest.raises(SystemExit):
        main(["--execute"])


def test_main_rejects_graph_without_execute():
    with pytest.raises(SystemExit):
        main(["--graph"])


def _write_config(root):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "dailyBrief": {
              "sender": "clarity@example.invalid",
              "recipients": ["scott@example.invalid"],
              "subjectPrefix": "Clarity Day in a Glance"
            }
          }
        }
        """,
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
