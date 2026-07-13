from __future__ import annotations

import pytest

from assistant.src.print_clarity_schedule import (
    build_windows_task_scheduler_script,
    main,
)


def test_build_windows_task_scheduler_script_uses_workspace_root(tmp_path):
    script = build_windows_task_scheduler_script(
        root=tmp_path,
        task_name="Clarity Test",
        at="06:45",
        mailbox="clarity@sendthisfile.ai",
        use_graph=True,
        memory_path="logs/clarity-memory.duckdb",
        brief_path="reports/clarity-brief.md",
        cycle_report_path="reports/clarity-cycle.md",
        log_path="logs/clarity-cycle.log",
    )

    assert "New-ScheduledTaskAction" in script
    assert "Register-ScheduledTask" in script
    assert '-TaskName "Clarity Test"' in script
    assert '-At "06:45"' in script
    assert f"Set-Location -LiteralPath '{tmp_path}'" in script
    assert "python -m assistant.src.run_clarity_cycle" in script
    assert "--mailbox 'clarity@sendthisfile.ai'" in script
    assert "--graph" in script
    assert "--memory 'logs/clarity-memory.duckdb'" in script
    assert "--brief 'reports/clarity-brief.md'" in script
    assert "--cycle-report 'reports/clarity-cycle.md'" in script
    assert "$ClarityLog = 'logs/clarity-cycle.log'" in script
    assert "New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ClarityLog)" in script
    assert "*>> 'logs/clarity-cycle.log'" in script


def test_build_windows_task_scheduler_script_escapes_single_quotes(tmp_path):
    script = build_windows_task_scheduler_script(
        root=tmp_path / "Scott's Workspace",
        mailbox="scott's-mailbox@example.invalid",
        use_sample_graph=True,
    )

    assert "Scott''s Workspace" in script
    assert "--mailbox 'scott''s-mailbox@example.invalid'" in script
    assert "--sample-graph" in script


def test_build_windows_task_scheduler_script_can_disable_log_redirection(tmp_path):
    script = build_windows_task_scheduler_script(
        root=tmp_path,
        mailbox="clarity@sendthisfile.ai",
        use_sample_graph=True,
        log_path=None,
    )

    assert "$ClarityLog" not in script
    assert "*>>" not in script
    assert "--sample-graph" in script


def test_build_windows_task_scheduler_script_can_include_calendar_refresh(tmp_path):
    script = build_windows_task_scheduler_script(
        root=tmp_path,
        mailbox="clarity@sendthisfile.ai",
        use_graph=True,
        refresh_calendar=True,
        calendar="google-family",
        calendar_date="2026-07-10",
        use_google_calendar=True,
        use_google_bearer=True,
    )

    assert "--mailbox 'clarity@sendthisfile.ai'" in script
    assert "--graph" in script
    assert "--refresh-calendar" in script
    assert "--calendar 'google-family'" in script
    assert "--calendar-date '2026-07-10'" in script
    assert "--google-calendar" in script
    assert "--google-bearer" in script


def test_build_windows_task_scheduler_script_rejects_invalid_flags(tmp_path):
    with pytest.raises(ValueError):
        build_windows_task_scheduler_script(root=tmp_path, use_graph_bearer=True)

    with pytest.raises(ValueError):
        build_windows_task_scheduler_script(
            root=tmp_path,
            use_graph=True,
            use_sample_graph=True,
        )

    with pytest.raises(ValueError):
        build_windows_task_scheduler_script(root=tmp_path, at="25:00")

    with pytest.raises(ValueError):
        build_windows_task_scheduler_script(root=tmp_path, use_google_bearer=True)

    with pytest.raises(ValueError):
        build_windows_task_scheduler_script(
            root=tmp_path,
            refresh_calendar=True,
            use_graph_calendar=True,
            use_google_calendar=True,
        )

    with pytest.raises(ValueError):
        build_windows_task_scheduler_script(root=tmp_path, calendar="family")

    with pytest.raises(ValueError):
        build_windows_task_scheduler_script(root=tmp_path, use_google_calendar=True)


def test_main_prints_schedule_script(tmp_path, monkeypatch, capsys):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    main(["--mailbox", "clarity@sendthisfile.ai", "--sample-graph", "--at", "08:15"])

    output = capsys.readouterr().out
    assert "Register-ScheduledTask" in output
    assert '-At "08:15"' in output
    assert "--mailbox 'clarity@sendthisfile.ai'" in output
    assert "--sample-graph" in output
    assert "--cycle-report 'reports/clarity-cycle.md'" in output
    assert "*>> 'logs/clarity-cycle.log'" in output


def test_main_prints_schedule_script_with_calendar_refresh(
    tmp_path,
    monkeypatch,
    capsys,
):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    main(
        [
            "--mailbox",
            "clarity@sendthisfile.ai",
            "--graph",
            "--refresh-calendar",
            "--calendar",
            "google-family",
            "--calendar-date",
            "2026-07-10",
            "--google-calendar",
        ]
    )

    output = capsys.readouterr().out
    assert "--mailbox 'clarity@sendthisfile.ai'" in output
    assert "--graph" in output
    assert "--refresh-calendar" in output
    assert "--calendar 'google-family'" in output
    assert "--calendar-date '2026-07-10'" in output
    assert "--google-calendar" in output


def test_main_can_disable_schedule_log(tmp_path, monkeypatch, capsys):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    main(["--mailbox", "clarity@sendthisfile.ai", "--sample-graph", "--no-log"])

    output = capsys.readouterr().out
    assert "$ClarityLog" not in output
    assert "*>>" not in output


def test_main_rejects_graph_bearer_without_graph():
    with pytest.raises(SystemExit):
        main(["--graph-bearer"])


def test_main_rejects_calendar_provider_without_refresh_calendar():
    with pytest.raises(SystemExit):
        main(["--google-calendar"])


def test_main_rejects_google_bearer_without_google_calendar():
    with pytest.raises(SystemExit):
        main(["--refresh-calendar", "--google-bearer"])


def test_main_rejects_invalid_time():
    with pytest.raises(SystemExit):
        main(["--at", "8:15"])
