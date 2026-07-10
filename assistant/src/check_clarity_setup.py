"""Preflight checks for local Clarity runs."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from assistant.src.run_clarity_cycle import DEFAULT_CYCLE_REPORT_PATH
from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import ConfigurationError, load_workspace_config


DEFAULT_CYCLE_LOG_PATH = "logs/clarity-cycle.log"


@dataclass(frozen=True)
class PreflightResult:
    """Result of a Clarity setup preflight."""

    ok: bool
    lines: tuple[str, ...]

    def format(self) -> str:
        return "\n".join(self.lines)


def check_clarity_setup(
    *,
    root: Path | str | None = None,
    mailbox: str | None = None,
    use_graph: bool = False,
    use_graph_bearer: bool = False,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    brief_path: Path | str | None = None,
    cycle_report_path: Path | str = DEFAULT_CYCLE_REPORT_PATH,
    log_path: Path | str | None = DEFAULT_CYCLE_LOG_PATH,
) -> PreflightResult:
    """Validate local Clarity setup without reading mail or writing files."""

    lines = ["# Clarity Setup Check", ""]
    errors: list[str] = []

    try:
        config = load_workspace_config(root)
        lines.append(f"- Workspace: {config.root}")
    except ConfigurationError as exc:
        return PreflightResult(
            ok=False,
            lines=(
                "# Clarity Setup Check",
                "",
                f"- FAILED: {exc}",
            ),
        )

    try:
        email_settings = config.email_settings
    except ConfigurationError as exc:
        return PreflightResult(
            ok=False,
            lines=(
                "# Clarity Setup Check",
                "",
                f"- Workspace: {config.root}",
                f"- FAILED: {exc}",
            ),
        )

    selected_mailbox = mailbox or email_settings.default_mailbox
    access_mode = email_settings.access_mode_for(selected_mailbox)
    if access_mode is None:
        errors.append(f"Mailbox is not approved: {selected_mailbox}")
    elif access_mode not in ("read", "read_write"):
        errors.append(f"Mailbox is not approved for read access: {selected_mailbox}")
    else:
        lines.append(f"- Mailbox: {selected_mailbox} [{access_mode}]")

    if selected_mailbox in email_settings.approved_mailboxes:
        allowed_senders = email_settings.allowed_senders_for(selected_mailbox)
        if allowed_senders:
            lines.append(f"- Allowed senders: {len(allowed_senders)} configured")
        else:
            lines.append("- Allowed senders: unrestricted")

    lines.append(f"- Max messages: {email_settings.max_messages}")
    lines.append(f"- Folder namespace: {email_settings.folder_namespace}")
    for label in ("review", "noise", "trash"):
        lines.append(f"- Folder {label}: {email_settings.folder_for_label(label)}")

    if use_graph_bearer and not use_graph:
        errors.append("--graph-bearer requires --graph")
    if use_graph:
        try:
            config.require_graph_credentials(use_bearer_auth=use_graph_bearer)
            graph_mode = "bearer token" if use_graph_bearer else "client credentials"
            lines.append(f"- Graph credentials: present ({graph_mode})")
        except ConfigurationError as exc:
            errors.append(str(exc))
    else:
        lines.append("- Graph credentials: not required for this check")

    lines.append(f"- Memory path: {_resolve_path(config.root, Path(memory_path))}")
    if brief_path is not None:
        lines.append(f"- Brief path: {_resolve_path(config.root, Path(brief_path))}")
    lines.append(
        f"- Cycle report path: {_resolve_path(config.root, Path(cycle_report_path))}"
    )
    if log_path is not None:
        lines.append(f"- Cycle log path: {_resolve_path(config.root, Path(log_path))}")

    lines.append("")
    if errors:
        lines.append("## Problems")
        lines.extend(f"- {error}" for error in errors)
        return PreflightResult(ok=False, lines=tuple(lines))

    lines.append("OK: Clarity setup preflight passed.")
    return PreflightResult(ok=True, lines=tuple(lines))


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    result = check_clarity_setup(
        mailbox=args.mailbox,
        use_graph=args.graph,
        use_graph_bearer=args.graph_bearer,
        memory_path=args.memory,
        brief_path=args.brief,
        cycle_report_path=args.cycle_report,
        log_path=args.log,
    )
    print(result.format())
    if not result.ok:
        raise SystemExit(1)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check local Clarity setup without reading mail or writing files."
    )
    parser.add_argument(
        "--mailbox",
        default=None,
        help="Approved mailbox to check. Defaults to the configured mailbox.",
    )
    parser.add_argument("--graph", action="store_true")
    parser.add_argument("--graph-bearer", action="store_true")
    parser.add_argument("--memory", default=str(DEFAULT_MEMORY_PATH))
    parser.add_argument("--brief", default=None)
    parser.add_argument("--cycle-report", default=str(DEFAULT_CYCLE_REPORT_PATH))
    parser.add_argument("--log", default=DEFAULT_CYCLE_LOG_PATH)
    args = parser.parse_args(argv)
    if args.graph_bearer and not args.graph:
        parser.error("--graph-bearer requires --graph.")
    return args


def _resolve_path(workspace_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return workspace_root / path


if __name__ == "__main__":
    main()
