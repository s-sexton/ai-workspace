"""Record local email sender/domain preferences."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import find_workspace_root, load_workspace_config
from common.console import print_text
from common.memory import DuckDbMemoryStore, MemoryStoreError


PREFERENCE_LABELS = ("noise", "review")
PREFERENCE_MATCH_TYPES = ("sender", "domain")


def record_email_sender_preference(
    *,
    mailbox: str | None,
    match_type: str,
    pattern: str,
    label: str,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
) -> str:
    """Record a local mailbox-scoped sender/domain classification preference."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    config = load_workspace_config(workspace_root, include_process_env=False)
    email_settings = config.email_settings
    resolved_mailbox = mailbox or email_settings.default_mailbox
    if resolved_mailbox not in email_settings.approved_mailboxes:
        return f"Email mailbox is not approved: {resolved_mailbox}"
    if match_type not in PREFERENCE_MATCH_TYPES:
        return f"Unsupported preference match type: {match_type}."
    if label not in PREFERENCE_LABELS:
        return f"Unsupported preference label: {label}."

    resolved_memory_path = _resolve_memory_path(workspace_root, Path(memory_path))
    resolved_memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(resolved_memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="email-preference")
        preference = store.record_email_sender_preference(
            mailbox=resolved_mailbox,
            match_type=match_type,
            pattern=pattern,
            label=label,
            created_run_id=run.run_id,
        )
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="record_email_sender_preference",
            approval_status="not_required",
            action_target=f"{preference.mailbox}:{preference.match_type}:{preference.pattern}",
            result=(
                f"Recorded {preference.label} preference for "
                f"{preference.match_type} {preference.pattern} in {preference.mailbox}."
            ),
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary=(
                f"Recorded {preference.label} email preference for "
                f"{preference.match_type} {preference.pattern}."
            ),
        )
    except MemoryStoreError as exc:
        return str(exc)
    finally:
        store.close()

    return (
        f"Recorded {preference.label} email preference for "
        f"{preference.match_type} {preference.pattern} in {preference.mailbox}."
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Record a local email sender/domain preference from the command line."""

    args = _parse_args(argv)
    print_text(
        record_email_sender_preference(
            mailbox=args.mailbox,
            match_type=args.match_type,
            pattern=args.pattern,
            label=args.label,
            memory_path=args.memory,
        )
    )


def _resolve_memory_path(workspace_root: Path, memory_path: Path) -> Path:
    if memory_path.is_absolute():
        return memory_path
    return workspace_root / memory_path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record a local mailbox-scoped email sender/domain preference."
    )
    parser.add_argument("match_type", choices=PREFERENCE_MATCH_TYPES)
    parser.add_argument("pattern", help="Sender email address or domain.")
    parser.add_argument("label", choices=PREFERENCE_LABELS)
    parser.add_argument("--mailbox", default=None, help="Approved mailbox scope.")
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
