"""Process deterministic directions from a Clarity daily brief reply."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import find_workspace_root, load_workspace_config
from common.memory import DuckDbMemoryStore


DEFAULT_DAILY_BRIEF_MANIFEST_PATH = Path("reports") / "clarity-daily-brief.json"
_SECTION_PATTERN = r"(outlook|inbox|gmail|jira|calendar)"


@dataclass(frozen=True)
class ReplyPlanItem:
    """One deterministic instruction parsed from a daily brief reply."""

    command_type: str
    item_number: int | None
    section: str | None
    label: str | None
    item_id: str | None
    subject: str | None
    result: str
    executed: bool


@dataclass(frozen=True)
class ReplyProcessResult:
    """Result from processing a daily brief reply."""

    plan: tuple[ReplyPlanItem, ...]
    executed: bool


def process_daily_brief_reply(
    reply_text: str,
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    manifest_path: Path | str = DEFAULT_DAILY_BRIEF_MANIFEST_PATH,
    execute: bool = False,
) -> str:
    """Parse and optionally apply deterministic daily brief reply commands."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    resolved_manifest_path = _resolve_path(workspace_root, Path(manifest_path))
    resolved_memory_path = _resolve_path(workspace_root, Path(memory_path))
    if not resolved_manifest_path.is_file():
        return f"No daily brief manifest found at {resolved_manifest_path}."
    if not resolved_memory_path.is_file():
        return f"No Clarity memory found at {resolved_memory_path}."

    manifest = _load_manifest(resolved_manifest_path)
    commands = _parse_reply_commands(reply_text)
    if not commands:
        return "# Daily Brief Reply Plan\n\nNo supported reply commands found."

    config = load_workspace_config(workspace_root, include_process_env=False)
    store = DuckDbMemoryStore(resolved_memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="daily-brief-reply")
        plan: list[ReplyPlanItem] = []
        for command in commands:
            plan.append(
                _plan_or_execute_command(
                    command,
                    manifest=manifest,
                    store=store,
                    run_id=run.run_id,
                    folder_policy=config.email_settings.folder_policy,
                    folder_namespace=config.email_settings.folder_namespace,
                    root=workspace_root,
                    memory_path=resolved_memory_path,
                    execute=execute,
                )
            )
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="process_daily_brief_reply",
            approval_status="not_required",
            result=_summary(plan, execute=execute),
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary=_summary(plan, execute=execute),
        )
    finally:
        store.close()

    return _format_result(tuple(plan), execute=execute)


def main(argv: Sequence[str] | None = None) -> None:
    """Process deterministic directions from a Clarity daily brief reply."""

    args = _parse_args(argv)
    reply_text = (
        Path(args.reply_file).read_text(encoding="utf-8")
        if args.reply_file
        else args.reply
    )
    print(
        process_daily_brief_reply(
            reply_text,
            memory_path=args.memory,
            manifest_path=args.manifest,
            execute=args.execute,
        )
    )


def _parse_reply_commands(reply_text: str) -> tuple[dict[str, Any], ...]:
    commands: list[dict[str, Any]] = []
    for raw_line in _reply_instruction_text(reply_text).splitlines():
        line_context = _line_context(raw_line)
        normalized_line = " ".join(raw_line.strip().lower().split())
        jira_key_commands = _parse_jira_key_commands(normalized_line)
        if jira_key_commands:
            commands.extend(jira_key_commands)
            continue
        for raw_command in re.split(r"\s+and\s+|[.;]+", raw_line):
            line = " ".join(raw_command.strip().lower().split())
            line = _strip_reply_context(line)
            if not line:
                continue
            commands.extend(_parse_reply_command_line(line, default_section=line_context))
    return tuple(commands)


def _parse_reply_command_line(
    line: str,
    *,
    default_section: str = "outlook",
) -> tuple[dict[str, Any], ...]:
    commands: list[dict[str, Any]] = []
    jira_done_range_match = re.search(
        rf"\b(?:mark|set|move|transition)\s+jira\s+(?:items?\s+)?(\d+)\s*(?:-|through|to)\s*(\d+)\s+(?:as\s+|to\s+)?(done|closed|resolved)\b",
        line,
    )
    if jira_done_range_match:
        start = int(jira_done_range_match.group(1))
        end = int(jira_done_range_match.group(2))
        target_status = _clean_jira_status(jira_done_range_match.group(3))
        for number in _number_range(start, end):
            commands.append(
                {
                    "type": "jira_transition",
                    "section": "jira",
                    "number": number,
                    "label": target_status,
                }
            )
        return tuple(commands)

    jira_done_match = re.search(
        r"\b(?:mark|set|move|transition)\s+jira\s+(?:item\s+)?(\d+)\s+(?:as\s+|to\s+)?(done|closed|resolved)\b",
        line,
    )
    if jira_done_match:
        commands.append(
            {
                "type": "jira_transition",
                "section": "jira",
                "number": int(jira_done_match.group(1)),
                "label": _clean_jira_status(jira_done_match.group(2)),
            }
        )
        return tuple(commands)

    delete_range_match = re.search(
        rf"\b(?:delete|trash)\s+(?:{_SECTION_PATTERN}\s+)?(?:items?\s+)?(\d+)\s*(?:-|through|to)\s*(\d+)\b",
        line,
    )
    if delete_range_match:
        section = _clean_section(delete_range_match.group(1), default=default_section)
        start = int(delete_range_match.group(2))
        end = int(delete_range_match.group(3))
        for number in _number_range(start, end):
            commands.append(
                {
                    "type": "move_item",
                    "section": section,
                    "number": number,
                    "label": "trash",
                }
            )
        return tuple(commands)

    move_range_match = re.search(
        rf"\b(?:move|file)\s+(?:{_SECTION_PATTERN}\s+)?items\s+(\d+)\s*(?:-|through|to)\s*(\d+)\s+to\s+(review|noise|trash|deleted items)\b",
        line,
    )
    if move_range_match:
        section = _clean_section(move_range_match.group(1), default=default_section)
        start = int(move_range_match.group(2))
        end = int(move_range_match.group(3))
        label = _clean_label(move_range_match.group(4))
        for number in _number_range(start, end):
            commands.append(
                {
                    "type": "move_item",
                    "section": section,
                    "number": number,
                    "label": label,
                }
            )
        return tuple(commands)

    move_match = re.search(
        rf"\b(?:move|file)\s+(?:{_SECTION_PATTERN}\s+)?item\s+(\d+)\s+to\s+(review|noise|trash|deleted items)\b",
        line,
    )
    if move_match:
        commands.append(
            {
                "type": "move_item",
                "section": _clean_section(move_match.group(1), default=default_section),
                "number": int(move_match.group(2)),
                "label": _clean_label(move_match.group(3)),
            }
        )
        return tuple(commands)

    move_shorthand_match = re.search(
        rf"\b(?:move|file)\s+(?:{_SECTION_PATTERN}\s+)?(\d+)\s+to\s+(review|noise|trash|deleted items)\b",
        line,
    )
    if move_shorthand_match:
        commands.append(
            {
                "type": "move_item",
                "section": _clean_section(
                    move_shorthand_match.group(1),
                    default=default_section,
                ),
                "number": int(move_shorthand_match.group(2)),
                "label": _clean_label(move_shorthand_match.group(3)),
            }
        )
        return tuple(commands)

    move_folder_match = re.search(
        rf"\b(?:move|file)\s+(?:{_SECTION_PATTERN}\s+)?(?:item\s+)?(\d+)\s+to\s+(.+?)\s+folder\b",
        line,
    )
    if move_folder_match:
        commands.append(
            {
                "type": "move_item",
                "section": _clean_section(
                    move_folder_match.group(1),
                    default=default_section,
                ),
                "number": int(move_folder_match.group(2)),
                "label": "folder",
                "target_folder": move_folder_match.group(3),
            }
        )
        return tuple(commands)

    trash_match = re.search(
        rf"\b(?:delete|trash)\s+(?:{_SECTION_PATTERN}\s+)?item\s+(\d+)\b",
        line,
    )
    if trash_match:
        commands.append(
            {
                "type": "move_item",
                "section": _clean_section(trash_match.group(1), default=default_section),
                "number": int(trash_match.group(2)),
                "label": "trash",
            }
        )
        return tuple(commands)

    trash_shorthand_match = re.search(
        rf"\b(?:delete|trash)\s+(?:{_SECTION_PATTERN}\s+)?(\d+)\b",
        line,
    )
    if trash_shorthand_match:
        commands.append(
            {
                "type": "move_item",
                "section": _clean_section(
                    trash_shorthand_match.group(1),
                    default=default_section,
                ),
                "number": int(trash_shorthand_match.group(2)),
                "label": "trash",
            }
        )
        return tuple(commands)

    preference_match = re.search(
        rf"\bmark\s+sender\s+from\s+(?:{_SECTION_PATTERN}\s+)?item\s+(\d+)\s+as\s+(noise|review)\b",
        line,
    )
    if preference_match:
        commands.append(
            {
                "type": "sender_preference",
                "section": _clean_section(
                    preference_match.group(1),
                    default=default_section,
                ),
                "number": int(preference_match.group(2)),
                "label": preference_match.group(3),
            }
        )
        return tuple(commands)

    if "approve pending cleanup actions" in line:
        commands.append({"type": "approve_pending_cleanup"})
        return tuple(commands)

    action_approval_match = re.search(
        r"\b(approve|reject)\s+action\s+([a-z0-9]{8,})\b",
        line,
    )
    if action_approval_match:
        commands.append(
            {
                "type": "action_approval",
                "label": (
                    "approved"
                    if action_approval_match.group(1) == "approve"
                    else "rejected"
                ),
                "action_id": action_approval_match.group(2),
            }
        )
    return tuple(commands)


def _reply_instruction_text(reply_text: str) -> str:
    lines: list[str] = []
    for raw_line in reply_text.splitlines():
        line = raw_line.strip()
        if line.startswith("-----Original Message-----"):
            break
        lines.append(raw_line)
    return "\n".join(lines)


def _number_range(start: int, end: int) -> range:
    if start <= end:
        return range(start, end + 1)
    return range(start, end - 1, -1)


def _plan_or_execute_command(
    command: dict[str, Any],
    *,
    manifest: dict[str, Any],
    store: DuckDbMemoryStore,
    run_id: str,
    folder_policy,
    folder_namespace: str,
    root: Path,
    memory_path: Path,
    execute: bool,
) -> ReplyPlanItem:
    command_type = command["type"]
    if command_type == "approve_pending_cleanup":
        pending_email_moves = [
            action
            for action in store.pending_actions(limit=100)
            if action.action_type.startswith("propose_email_move_")
            and action.item_external_id
            and action.action_target
        ]
        if execute:
            for action in pending_email_moves:
                store.update_assistant_action_approval(
                    action_id=action.action_id,
                    approval_status="approved",
                )
        result = (
            f"Approved {len(pending_email_moves)} pending cleanup action(s)."
            if execute
            else (
                "Would approve "
                f"{len(pending_email_moves)} pending cleanup action(s)."
            )
        )
        return ReplyPlanItem(
            command_type=command_type,
            item_number=None,
            section=None,
            label=None,
            item_id=None,
            subject=None,
            result=result,
            executed=execute,
        )

    if command_type == "action_approval":
        return _plan_or_execute_action_approval(
            command,
            store=store,
            execute=execute,
        )

    if command_type == "jira_key_action":
        return _plan_or_execute_jira_key_action(
            command,
            manifest=manifest,
            store=store,
            run_id=run_id,
            execute=execute,
        )

    item = _manifest_item(
        manifest,
        section=command["section"],
        number=command["number"],
    )
    if item is None:
        return _failed_item(command, "Brief item was not found.")
    if command_type == "move_item":
        return _plan_or_execute_move(
            command,
            item=item,
            store=store,
            run_id=run_id,
            folder_policy=folder_policy,
            folder_namespace=folder_namespace,
            execute=execute,
        )
    if command_type == "jira_transition":
        return _plan_or_execute_jira_transition(
            command,
            item=item,
            store=store,
            run_id=run_id,
            execute=execute,
        )
    if command_type == "sender_preference":
        return _plan_or_execute_sender_preference(
            command,
            item=item,
            root=root,
            memory_path=memory_path,
            store=store,
            run_id=run_id,
            execute=execute,
        )
    return ReplyPlanItem(
        command_type=command_type,
        item_number=command.get("number"),
        section=command.get("section"),
        label=command.get("label"),
        item_id=None,
        subject=None,
        result="Unsupported reply command.",
        executed=False,
    )


def _plan_or_execute_action_approval(
    command: dict[str, Any],
    *,
    store: DuckDbMemoryStore,
    execute: bool,
) -> ReplyPlanItem:
    action_id = command["action_id"]
    target_status = command["label"]
    action = _pending_action_by_id(store, action_id)
    if action is None:
        return ReplyPlanItem(
            command_type="action_approval",
            item_number=None,
            section="pendingApprovals",
            label=target_status,
            item_id=None,
            subject=None,
            result=f"Pending action was not found: {action_id}.",
            executed=False,
        )
    if execute:
        store.update_assistant_action_approval(
            action_id=action.action_id,
            approval_status=target_status,
        )
    return ReplyPlanItem(
        command_type="action_approval",
        item_number=None,
        section="pendingApprovals",
        label=target_status,
        item_id=action.item_id,
        subject=action.item_subject or action.item_external_id,
        result=(
            f"{'Updated' if execute else 'Would update'} action "
            f"{action.action_id} to {target_status}. No provider write was performed."
        ),
        executed=execute,
    )


def _pending_action_by_id(store: DuckDbMemoryStore, action_id: str):
    for action in store.pending_actions(limit=500):
        if action.action_id.lower() == action_id.lower():
            return action
    return None


def _plan_or_execute_move(
    command: dict[str, Any],
    *,
    item: dict[str, Any],
    store: DuckDbMemoryStore,
    run_id: str,
    folder_policy,
    folder_namespace: str,
    execute: bool,
) -> ReplyPlanItem:
    label = command["label"]
    if item.get("sourceType") != "email" or item.get("itemType") != "email_message":
        return _failed_item(command, "Only email brief items can be moved.")
    target_folder = (
        _custom_target_folder(command["target_folder"], folder_namespace)
        if label == "folder"
        else folder_policy.get(label)
    )
    if target_folder is None:
        return _failed_item(command, f"No folder policy for label: {label}.")
    if execute:
        store.record_assistant_action(
            run_id=run_id,
            item_id=item["itemId"],
            action_type=f"propose_email_move_{label}",
            approval_status="required",
            action_target=target_folder,
            result=(
                "Daily brief reply requested moving "
                f"{item['externalId']} to {target_folder}."
            ),
        )
    return ReplyPlanItem(
        command_type="move_item",
        item_number=command["number"],
        section=command["section"],
        label=label,
        item_id=item["itemId"],
        subject=item.get("subject"),
        result=(
            ("Recorded pending move action" if execute else "Would record pending move action")
            + f" to {target_folder}."
        ),
        executed=execute,
    )


def _plan_or_execute_sender_preference(
    command: dict[str, Any],
    *,
    item: dict[str, Any],
    root: Path,
    memory_path: Path,
    store: DuckDbMemoryStore,
    run_id: str,
    execute: bool,
) -> ReplyPlanItem:
    if item.get("sourceType") != "email" or item.get("itemType") != "email_message":
        return _failed_item(command, "Only email brief items can set sender preferences.")
    sender = item.get("senderOrOwner")
    if not isinstance(sender, str) or not sender.strip():
        return _failed_item(command, "Brief item does not include a sender.")
    if execute:
        preference = store.record_email_sender_preference(
            mailbox=item["sourceScope"],
            match_type="sender",
            pattern=sender,
            label=command["label"],
            created_run_id=run_id,
        )
        store.record_assistant_action(
            run_id=run_id,
            action_type="record_email_sender_preference",
            approval_status="not_required",
            action_target=(
                f"{preference.mailbox}:{preference.match_type}:{preference.pattern}"
            ),
            result=(
                f"Recorded {preference.label} preference for "
                f"{preference.match_type} {preference.pattern} in {preference.mailbox}."
            ),
        )
        result = (
            f"Recorded {preference.label} sender preference for "
            f"{preference.pattern}."
        )
    else:
        result = f"Would record {command['label']} sender preference for {sender}."
    return ReplyPlanItem(
        command_type="sender_preference",
        item_number=command["number"],
        section=command["section"],
        label=command["label"],
        item_id=item["itemId"],
        subject=item.get("subject"),
        result=result,
        executed=execute,
    )


def _plan_or_execute_jira_transition(
    command: dict[str, Any],
    *,
    item: dict[str, Any],
    store: DuckDbMemoryStore,
    run_id: str,
    execute: bool,
) -> ReplyPlanItem:
    if item.get("sourceType") != "jira" or item.get("itemType") != "jira_issue":
        return _failed_item(command, "Only Jira brief items can request Jira transitions.")
    target_status = command["label"]
    issue_key = item.get("externalId") or item.get("subject")
    if execute:
        store.record_assistant_action(
            run_id=run_id,
            item_id=item["itemId"],
            action_type=f"propose_jira_transition_{target_status}",
            approval_status="required",
            action_target=target_status,
            result=(
                "Daily brief reply requested Jira transition for "
                f"{issue_key} to {target_status}. No Jira write was performed."
            ),
        )
    return ReplyPlanItem(
        command_type="jira_transition",
        item_number=command["number"],
        section="jira",
        label=target_status,
        item_id=item["itemId"],
        subject=f"{issue_key}: {item.get('subject')}",
        result=(
            (
                "Recorded pending Jira transition request"
                if execute
                else "Would record pending Jira transition request"
            )
            + f" to {target_status}. No Jira write will be performed."
        ),
        executed=execute,
    )


def _plan_or_execute_jira_key_action(
    command: dict[str, Any],
    *,
    manifest: dict[str, Any],
    store: DuckDbMemoryStore,
    run_id: str,
    execute: bool,
) -> ReplyPlanItem:
    key = command["key"]
    item = _manifest_item_by_external_id(manifest, section="jira", external_id=key)
    if item is None:
        return _failed_item(command, f"Jira issue was not found in the brief: {key}.")
    action = command["label"]
    if execute:
        store.record_assistant_action(
            run_id=run_id,
            item_id=item["itemId"],
            action_type=f"propose_jira_{action}",
            approval_status="required",
            action_target=action,
            result=(
                "Daily brief reply requested Jira "
                f"{action} for {key}. No Jira write was performed."
            ),
        )
    return ReplyPlanItem(
        command_type="jira_key_action",
        item_number=item.get("number"),
        section="jira",
        label=action,
        item_id=item["itemId"],
        subject=f"{key}: {item.get('subject')}",
        result=(
            (
                f"Recorded pending Jira {action} request"
                if execute
                else f"Would record pending Jira {action} request"
            )
            + ". No Jira write will be performed."
        ),
        executed=execute,
    )


def _failed_item(command: dict[str, Any], result: str) -> ReplyPlanItem:
    return ReplyPlanItem(
        command_type=command["type"],
        item_number=command.get("number"),
        section=command.get("section"),
        label=command.get("label"),
        item_id=None,
        subject=None,
        result=result,
        executed=False,
    )


def _manifest_item(
    manifest: dict[str, Any],
    *,
    section: str,
    number: int,
) -> dict[str, Any] | None:
    raw_items = manifest.get("sections", {}).get(_clean_section(section), [])
    if not isinstance(raw_items, list):
        return None
    for item in raw_items:
        if isinstance(item, dict) and item.get("number") == number:
            return item
    return None


def _manifest_item_by_external_id(
    manifest: dict[str, Any],
    *,
    section: str,
    external_id: str,
) -> dict[str, Any] | None:
    raw_items = manifest.get("sections", {}).get(section, [])
    if not isinstance(raw_items, list):
        return None
    for item in raw_items:
        if isinstance(item, dict) and item.get("externalId") == external_id:
            return item
    return None


def _load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Daily brief manifest must be a JSON object.")
    return payload


def _clean_label(value: str) -> str:
    if value == "deleted items":
        return "trash"
    return value


def _clean_section(value: str | None, *, default: str = "outlook") -> str:
    if value in (None, ""):
        return default
    if value in ("outlook", "inbox", "gmail"):
        return "outlook"
    return value


def _clean_jira_status(value: str) -> str:
    if value in ("closed", "resolved"):
        return "done"
    return value


def _line_context(raw_line: str) -> str:
    line = raw_line.lower()
    if "jira" in line:
        return "jira"
    if "gmail" in line or "@gmail.com" in line or "mailbox" in line:
        return "outlook"
    return "outlook"


def _strip_reply_context(line: str) -> str:
    return re.sub(r"^for\s+.+?\s*,\s*", "", line)


def _parse_jira_key_commands(line: str) -> tuple[dict[str, Any], ...]:
    if "jira" not in line or not re.search(r"\b(?:delete|trash|remove)\b", line):
        return ()
    return tuple(
        {
            "type": "jira_key_action",
            "section": "jira",
            "key": key.upper(),
            "label": "delete",
        }
        for key in re.findall(r"\b[A-Z][A-Z0-9]+-\d+\b", line.upper())
    )


def _custom_target_folder(value: str, folder_namespace: str) -> str:
    clean_value = " ".join(value.split()).strip(" /")
    if not clean_value:
        raise RuntimeError("Custom email folder name cannot be empty.")
    if clean_value.lower().startswith(folder_namespace.lower() + "/"):
        return clean_value
    return f"{folder_namespace}/{clean_value.title()}"


def _summary(plan: Sequence[ReplyPlanItem], *, execute: bool) -> str:
    verb = "Executed" if execute else "Prepared"
    return f"{verb} {len(plan)} daily brief reply command(s)."


def _format_result(plan: tuple[ReplyPlanItem, ...], *, execute: bool) -> str:
    title = "# Daily Brief Reply Execution" if execute else "# Daily Brief Reply Plan"
    lines = [title, "", "## Summary", "", f"- Commands: {len(plan)}"]
    lines.append(f"- Mode: {'execute' if execute else 'dry-run'}")
    lines.extend(("", "## Commands", ""))
    for item in plan:
        subject = f": {item.subject}" if item.subject else ""
        label = f" -> {item.label}" if item.label else ""
        number = f" item {item.item_number}" if item.item_number is not None else ""
        section = f" ({item.section})" if item.section else ""
        lines.append(f"- {item.command_type}{number}{section}{label}{subject}")
        lines.append(f"  Result: {item.result}")
        if item.item_id:
            lines.append(f"  Clarity item: {item.item_id}")
    return "\n".join(lines)


def _resolve_path(workspace_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return workspace_root / path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process deterministic directions from a Clarity daily brief reply."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--reply", help="Reply text to process.")
    input_group.add_argument("--reply-file", help="Path to a reply text file.")
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_DAILY_BRIEF_MANIFEST_PATH),
        help="Daily brief manifest path.",
    )
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply supported local reply commands.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
