"""Print local Windows scheduling commands for Clarity."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Sequence

from common.configuration import find_workspace_root


DEFAULT_TASK_NAME = "Clarity Email Cycle"
DEFAULT_TASK_TIME = "07:30"


def build_windows_task_scheduler_script(
    *,
    root: Path | str | None = None,
    task_name: str = DEFAULT_TASK_NAME,
    at: str = DEFAULT_TASK_TIME,
    mailbox: str | None = None,
    use_graph: bool = False,
    use_graph_bearer: bool = False,
    use_sample_graph: bool = False,
    memory_path: Path | str | None = None,
    brief_path: Path | str | None = None,
) -> str:
    """Return PowerShell commands that register one local scheduled task."""

    if use_graph_bearer and not use_graph:
        raise ValueError("use_graph_bearer requires use_graph.")
    if use_graph and use_sample_graph:
        raise ValueError("use_graph and use_sample_graph are mutually exclusive.")
    if not _is_valid_time(at):
        raise ValueError("at must be in HH:mm 24-hour format.")

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    cycle_command = _cycle_command(
        mailbox=mailbox,
        use_graph=use_graph,
        use_graph_bearer=use_graph_bearer,
        use_sample_graph=use_sample_graph,
        memory_path=memory_path,
        brief_path=brief_path,
    )
    scheduled_argument = (
        "-NoProfile -ExecutionPolicy Bypass -Command "
        + _ps_double_quote(
            "Set-Location -LiteralPath "
            + _ps_single_quote(str(workspace_root))
            + "; "
            + cycle_command
        )
    )
    lines = [
        "$Action = New-ScheduledTaskAction "
        + "-Execute "
        + _ps_double_quote("powershell.exe")
        + " -Argument "
        + _ps_double_quote(scheduled_argument),
        "$Trigger = New-ScheduledTaskTrigger -Daily -At "
        + _ps_double_quote(at),
        "Register-ScheduledTask "
        + "-TaskName "
        + _ps_double_quote(task_name)
        + " -Action $Action -Trigger $Trigger "
        + "-Description "
        + _ps_double_quote("Run one local Clarity email review cycle.")
        + " -Force",
    ]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> None:
    """Print Windows Task Scheduler registration commands."""

    args = _parse_args(argv)
    print(
        build_windows_task_scheduler_script(
            task_name=args.task_name,
            at=args.at,
            mailbox=args.mailbox,
            use_graph=args.graph,
            use_graph_bearer=args.graph_bearer,
            use_sample_graph=args.sample_graph,
            memory_path=args.memory,
            brief_path=args.brief,
        ),
        end="",
    )


def _cycle_command(
    *,
    mailbox: str | None,
    use_graph: bool,
    use_graph_bearer: bool,
    use_sample_graph: bool,
    memory_path: Path | str | None,
    brief_path: Path | str | None,
) -> str:
    parts = ["python", "-m", "assistant.src.run_clarity_cycle"]
    if mailbox:
        parts.extend(("--mailbox", _ps_single_quote(mailbox)))
    if use_graph:
        parts.append("--graph")
    if use_graph_bearer:
        parts.append("--graph-bearer")
    if use_sample_graph:
        parts.append("--sample-graph")
    if memory_path is not None:
        parts.extend(("--memory", _ps_single_quote(str(memory_path))))
    if brief_path is not None:
        parts.extend(("--brief", _ps_single_quote(str(brief_path))))
    return " ".join(parts)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print PowerShell commands for scheduling Clarity locally."
    )
    parser.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    parser.add_argument(
        "--at",
        default=DEFAULT_TASK_TIME,
        help="Daily start time in HH:mm 24-hour format.",
    )
    parser.add_argument(
        "--mailbox",
        default=None,
        help="Approved mailbox to refresh. Defaults to the configured mailbox.",
    )
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--sample-graph",
        action="store_true",
        help="Schedule the local Graph-shaped sample cycle; no network calls.",
    )
    source_group.add_argument(
        "--graph",
        action="store_true",
        help="Schedule live Microsoft Graph metadata reads.",
    )
    parser.add_argument(
        "--graph-bearer",
        action="store_true",
        help="Use GRAPH_ACCESS_TOKEN instead of app-only client credentials.",
    )
    parser.add_argument("--memory", default=None)
    parser.add_argument("--brief", default=None)
    args = parser.parse_args(argv)
    if args.graph_bearer and not args.graph:
        parser.error("--graph-bearer requires --graph.")
    if not _is_valid_time(args.at):
        parser.error("--at must be in HH:mm 24-hour format.")
    return args


def _is_valid_time(value: str) -> bool:
    if not re.fullmatch(r"\d{2}:\d{2}", value):
        return False
    hour, minute = (int(part) for part in value.split(":", 1))
    return 0 <= hour <= 23 and 0 <= minute <= 59


def _ps_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _ps_double_quote(value: str) -> str:
    return '"' + value.replace("`", "``").replace('"', '`"') + '"'


if __name__ == "__main__":
    main()
