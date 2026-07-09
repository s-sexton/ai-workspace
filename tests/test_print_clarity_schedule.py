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


def test_build_windows_task_scheduler_script_escapes_single_quotes(tmp_path):
    script = build_windows_task_scheduler_script(
        root=tmp_path / "Scott's Workspace",
        mailbox="scott's-mailbox@example.invalid",
        use_sample_graph=True,
    )

    assert "Scott''s Workspace" in script
    assert "--mailbox 'scott''s-mailbox@example.invalid'" in script
    assert "--sample-graph" in script


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


def test_main_rejects_graph_bearer_without_graph():
    with pytest.raises(SystemExit):
        main(["--graph-bearer"])


def test_main_rejects_invalid_time():
    with pytest.raises(SystemExit):
        main(["--at", "8:15"])
