from __future__ import annotations

from assistant.src.run_calendar_review import main, run_calendar_review
from common.calendar import StaticCalendarTransport
from common.memory import DuckDbMemoryStore


def test_run_calendar_review_records_events_and_generates_brief(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    brief_path = tmp_path / "reports" / "brief.md"

    result = run_calendar_review(
        root=tmp_path,
        calendar="family",
        review_date="2026-07-10",
        memory_path=memory_path,
        brief_output_path=brief_path,
        transport=StaticCalendarTransport(
            (
                {
                    "event_id": "family-1",
                    "calendar": "family",
                    "title": "School pickup",
                    "starts_at": "2026-07-10T15:00:00-05:00",
                    "ends_at": "2026-07-10T15:30:00-05:00",
                    "location": "School",
                },
            )
        ),
    )

    assert result.calendar == "family"
    assert result.review_date == "2026-07-10"
    assert result.event_count == 1
    assert brief_path.is_file()
    assert "# Calendar Items" in brief_path.read_text(encoding="utf-8")

    store = DuckDbMemoryStore(memory_path)
    try:
        latest_run = store.latest_run(workflow="calendar-review")
        calendar_items = [
            item
            for item in store.recent_memory()
            if item.source_type == "calendar"
        ]
    finally:
        store.close()

    assert latest_run is not None
    assert "Read 1 event(s) from family for 2026-07-10." in latest_run.summary
    assert calendar_items[0].subject == "School pickup"
    assert calendar_items[0].label == "calendar"


def test_main_prints_calendar_result(tmp_path, monkeypatch, capsys):
    _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    main(
        [
            "--calendar",
            "family",
            "--date",
            "2026-07-10",
            "--memory",
            str(tmp_path / "logs" / "memory.duckdb"),
            "--brief",
            str(tmp_path / "reports" / "brief.md"),
        ]
    )

    output = capsys.readouterr().out
    assert "Read 2 calendar event(s) from family for 2026-07-10" in output
    assert "Wrote brief" in output


def test_main_can_use_graph_calendar_transport(tmp_path, monkeypatch, capsys):
    _write_graph_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    def fake_build_graph_calendar_read_transport_from_config(
        *,
        use_bearer_auth=False,
        **_,
    ):
        calls.append(use_bearer_auth)
        return StaticCalendarTransport(
            (
                {
                    "event_id": "work-1",
                    "calendar": "scott.sexton@example.invalid",
                    "title": "Work review",
                    "starts_at": "2026-07-10T09:00:00-05:00",
                },
            )
        )

    monkeypatch.setattr(
        "assistant.src.run_calendar_review."
        "build_graph_calendar_read_transport_from_config",
        fake_build_graph_calendar_read_transport_from_config,
    )

    main(
        [
            "--calendar",
            "work",
            "--date",
            "2026-07-10",
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
    assert "Read 1 calendar event(s) from work for 2026-07-10" in output


def _write_config(root):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "calendar": {
              "approvedCalendars": [
                {
                  "label": "family",
                  "provider": "sample",
                  "source": "family",
                  "accessMode": "read"
                }
              ],
              "defaultCalendar": "family",
              "maxEvents": 25
            }
          }
        }
        """,
        encoding="utf-8",
    )


def _write_graph_config(root):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "calendar": {
              "approvedCalendars": [
                {
                  "label": "work",
                  "provider": "graph",
                  "source": "scott.sexton@example.invalid",
                  "accessMode": "read"
                }
              ],
              "defaultCalendar": "work",
              "maxEvents": 25
            }
          }
        }
        """,
        encoding="utf-8",
    )
