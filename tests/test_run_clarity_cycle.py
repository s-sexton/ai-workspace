from __future__ import annotations

import pytest

from assistant.src.run_clarity_cycle import main, run_clarity_cycle
from common.email import StaticEmailTransport
from common.memory import DuckDbMemoryStore


def test_run_clarity_cycle_refreshes_email_and_returns_answers(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    brief_path = tmp_path / "reports" / "brief.md"
    cycle_report_path = tmp_path / "reports" / "cycle.md"

    result = run_clarity_cycle(
        root=tmp_path,
        mailbox="inbox@example.invalid",
        memory_path=memory_path,
        brief_path=brief_path,
        cycle_report_path=cycle_report_path,
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "review-1",
                    "mailbox": "inbox@example.invalid",
                    "subject": "Please review this",
                    "sender": "sender@example.invalid",
                },
                {
                    "message_id": "noise-1",
                    "mailbox": "inbox@example.invalid",
                    "subject": "Monthly newsletter",
                    "sender": "marketing@example.invalid",
                    "preview": "Unsubscribe here.",
                },
            )
        ),
    )

    assert result.mailbox == "inbox@example.invalid"
    assert result.message_count == 2
    assert result.review_count == 1
    assert result.noise_count == 1
    assert "# Clarity Command Center" in result.focus_answer
    assert "# Items Marked For Review" in result.review_answer
    assert "Please review this [review]" in result.review_answer
    assert "# Pending Actions" in result.pending_answer
    assert result.brief_path == brief_path
    assert result.cycle_report_path == cycle_report_path
    report = cycle_report_path.read_text(encoding="utf-8")
    assert "# Clarity Cycle" in report
    assert "Mailbox: inbox@example.invalid" in report
    assert "# Clarity Command Center" in report
    assert "Please review this [review]" in report
    store = DuckDbMemoryStore(memory_path)
    try:
        latest_cycle = store.latest_run(workflow="clarity-cycle")
        artifacts = store.list_generated_artifacts(run_id=latest_cycle.run_id)
        actions = store.recent_actions()
    finally:
        store.close()

    assert latest_cycle is not None
    assert "Read 2 message(s) from inbox@example.invalid" in latest_cycle.summary
    assert artifacts[0].path == str(cycle_report_path)
    assert any(action.action_type == "run_clarity_cycle" for action in actions)


def test_main_prints_safe_cycle_summary(tmp_path, monkeypatch, capsys):
    _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    main(
        [
            "--memory",
            str(tmp_path / "logs" / "memory.duckdb"),
            "--brief",
            str(tmp_path / "reports" / "brief.md"),
            "--cycle-report",
            str(tmp_path / "reports" / "cycle.md"),
        ]
    )

    output = capsys.readouterr().out
    assert "# Clarity Cycle" in output
    assert "Mailbox: inbox@example.invalid" in output
    assert "Read: 2" in output
    assert "Proposed actions: 2" in output
    assert "Cycle report:" in output
    assert "# Clarity Command Center" in output
    assert "# Items Marked For Review" in output
    assert "# Pending Actions" in output
    cycle_report = (tmp_path / "reports" / "cycle.md").read_text(encoding="utf-8")
    assert "# Clarity Cycle" in cycle_report


def test_main_can_use_graph_read_transport(tmp_path, monkeypatch, capsys):
    _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    def fake_build_graph_read_transport_from_config(*, use_bearer_auth=False, **_):
        calls.append(use_bearer_auth)
        return StaticEmailTransport(
            (
                {
                    "message_id": "graph-1",
                    "mailbox": "inbox@example.invalid",
                    "subject": "Graph review item",
                },
            )
        )

    monkeypatch.setattr(
        "assistant.src.run_clarity_cycle.build_graph_read_transport_from_config",
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
            "--cycle-report",
            str(tmp_path / "reports" / "cycle.md"),
        ]
    )

    output = capsys.readouterr().out
    assert calls == [True]
    assert "Read: 1" in output
    assert "Graph review item [review]" in output


def test_main_writes_failure_report_and_memory(tmp_path, monkeypatch, capsys):
    _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    def fake_build_graph_read_transport_from_config(**_):
        raise RuntimeError("GRAPH_CLIENT_SECRET=super-secret")

    monkeypatch.setattr(
        "assistant.src.run_clarity_cycle.build_graph_read_transport_from_config",
        fake_build_graph_read_transport_from_config,
    )

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "--graph",
                "--memory",
                str(tmp_path / "logs" / "memory.duckdb"),
                "--cycle-report",
                str(tmp_path / "reports" / "cycle.md"),
            ]
        )

    assert exc_info.value.code == 1
    output = capsys.readouterr().out
    assert "# Clarity Cycle Failed" in output
    assert "GRAPH_CLIENT_SECRET=<redacted>" in output
    assert "super-secret" not in output

    report = (tmp_path / "reports" / "cycle.md").read_text(encoding="utf-8")
    assert "# Clarity Cycle Failed" in report
    assert "GRAPH_CLIENT_SECRET=<redacted>" in report
    assert "super-secret" not in report

    store = DuckDbMemoryStore(tmp_path / "logs" / "memory.duckdb")
    try:
        latest_cycle = store.latest_run(workflow="clarity-cycle")
        artifacts = store.list_generated_artifacts(run_id=latest_cycle.run_id)
    finally:
        store.close()

    assert latest_cycle.status == "failed"
    assert "super-secret" not in latest_cycle.summary
    assert artifacts[0].path == str(tmp_path / "reports" / "cycle.md")


def test_main_rejects_graph_bearer_without_graph():
    with pytest.raises(SystemExit):
        main(["--graph-bearer"])


def _write_config(root):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "email": {
              "approvedMailboxes": [
                {"address": "inbox@example.invalid", "accessMode": "read"}
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
