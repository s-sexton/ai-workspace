"""Process numbered directions for an email cleanup batch."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from assistant.src.email_cleanup_batch import DEFAULT_EMAIL_CLEANUP_BATCH_PATH
from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import find_workspace_root, load_workspace_config
from common.memory import DuckDbMemoryStore


DEFAULT_EMAIL_CLEANUP_MANIFEST_PATH = DEFAULT_EMAIL_CLEANUP_BATCH_PATH.with_suffix(
    ".json"
)


@dataclass(frozen=True)
class CleanupCommandPlanItem:
    """One parsed cleanup direction."""

    item_number: int
    label: str
    target_folder: str | None
    item_id: str | None
    subject: str | None
    result: str
    executed: bool
    feedback_recorded: bool = False


def process_email_cleanup_batch(
    directions: str,
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    manifest_path: Path | str = DEFAULT_EMAIL_CLEANUP_MANIFEST_PATH,
    execute: bool = False,
) -> str:
    """Parse and optionally record approved actions from cleanup directions."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    resolved_manifest_path = _resolve_path(workspace_root, Path(manifest_path))
    resolved_memory_path = _resolve_path(workspace_root, Path(memory_path))
    if not resolved_manifest_path.is_file():
        return f"No email cleanup manifest found at {resolved_manifest_path}."
    if not resolved_memory_path.is_file():
        return f"No Clarity memory found at {resolved_memory_path}."

    commands = _parse_directions(directions)
    if not commands:
        return "# Email Cleanup Batch Plan\n\nNo supported cleanup directions found."

    manifest = _load_manifest(resolved_manifest_path)
    email_settings = load_workspace_config(
        workspace_root,
        include_process_env=False,
    ).email_settings
    store = DuckDbMemoryStore(resolved_memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="email-cleanup-batch-directions")
        plan: list[CleanupCommandPlanItem] = []
        for command in commands:
            plan.append(
                _plan_or_record_command(
                    command,
                    manifest=manifest,
                    store=store,
                    run_id=run.run_id,
                    folder_policy=email_settings.folder_policy,
                    folder_namespace=email_settings.folder_namespace,
                    execute=execute,
                )
            )
        summary = _summary(plan, execute=execute)
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="process_email_cleanup_batch",
            approval_status="not_required",
            result=summary,
        )
        store.finish_run(run.run_id, status="completed", summary=summary)
    finally:
        store.close()

    return _format_result(tuple(plan), execute=execute)


def main(argv: Sequence[str] | None = None) -> None:
    """Process numbered email cleanup batch directions."""

    args = _parse_args(argv)
    directions = (
        Path(args.directions_file).read_text(encoding="utf-8")
        if args.directions_file
        else args.directions
    )
    print(
        process_email_cleanup_batch(
            directions,
            memory_path=args.memory,
            manifest_path=args.manifest,
            execute=args.execute,
        )
    )


def _parse_directions(directions: str) -> tuple[dict[str, Any], ...]:
    commands: list[dict[str, Any]] = []
    for raw_line in directions.splitlines():
        for raw_command in re.split(
            r";+|[,.](?=\s*(?:move|file|delete|trash)\b)",
            raw_line,
            flags=re.IGNORECASE,
        ):
            line = " ".join(raw_command.strip().split())
            if not line:
                continue
            command = _parse_direction_line(line)
            if command is not None:
                commands.extend(command)
    return tuple(commands)


def _parse_direction_line(line: str) -> tuple[dict[str, Any], ...] | None:
    move_match = re.search(
        r"^(?:move|file)\s+(?:items?\s+)?(?P<numbers>.+?)\s+to\s+(?P<target>.+)$",
        line,
        flags=re.IGNORECASE,
    )
    if move_match:
        numbers = _parse_number_list(move_match.group("numbers"))
        target = move_match.group("target").strip()
        return tuple(
            {"type": "move_item", "number": number, "target": target}
            for number in numbers
        )

    delete_match = re.search(
        r"^(?:delete|trash)\s+(?:items?\s+)?(?P<numbers>.+)$",
        line,
        flags=re.IGNORECASE,
    )
    if delete_match:
        numbers = _parse_number_list(delete_match.group("numbers"))
        return tuple(
            {"type": "move_item", "number": number, "target": "trash"}
            for number in numbers
        )
    return None


def _parse_number_list(value: str) -> tuple[int, ...]:
    normalized = (
        value.lower()
        .replace("items", "")
        .replace("item", "")
        .replace(" and ", ",")
        .replace("&", ",")
    )
    numbers: list[int] = []
    for part in normalized.split(","):
        clean_part = part.strip()
        if not clean_part:
            continue
        range_match = re.fullmatch(r"(\d+)\s*(?:-|through|to)\s*(\d+)", clean_part)
        if range_match:
            numbers.extend(_number_range(int(range_match.group(1)), int(range_match.group(2))))
            continue
        if not clean_part.isdigit():
            continue
        numbers.append(int(clean_part))
    return tuple(dict.fromkeys(numbers))


def _number_range(start: int, end: int) -> range:
    if start <= end:
        return range(start, end + 1)
    return range(start, end - 1, -1)


def _plan_or_record_command(
    command: dict[str, Any],
    *,
    manifest: dict[str, Any],
    store: DuckDbMemoryStore,
    run_id: str,
    folder_policy,
    folder_namespace: str,
    execute: bool,
) -> CleanupCommandPlanItem:
    item = _manifest_item(manifest, number=command["number"])
    if item is None:
        return _failed_item(command, "Batch item was not found.")
    target_folder = _target_folder(
        command["target"],
        folder_policy=folder_policy,
        folder_namespace=folder_namespace,
    )
    if target_folder is None:
        return _failed_item(command, "Target folder is not allowed.")
    label = _target_label(command["target"], target_folder=target_folder)
    if execute:
        store.record_assistant_action(
            run_id=run_id,
            item_id=item["itemId"],
            action_type=f"propose_email_move_{label}",
            approval_status="approved",
            action_target=target_folder,
            result=(
                "Email cleanup batch requested moving "
                f"{item['externalId']} to {target_folder}."
            ),
        )
        _record_cleanup_feedback(
            store,
            run_id=run_id,
            item_id=item["itemId"],
            target_folder=target_folder,
        )
    return CleanupCommandPlanItem(
        item_number=command["number"],
        label=label,
        target_folder=target_folder,
        item_id=item["itemId"],
        subject=item.get("subject"),
        result=(
            ("Recorded approved move action" if execute else "Would record approved move action")
            + f" to {target_folder}."
        ),
        executed=execute,
        feedback_recorded=execute,
    )


def _target_folder(
    value: str,
    *,
    folder_policy,
    folder_namespace: str,
) -> str | None:
    clean_value = " ".join(value.strip().split())
    label = clean_value.lower()
    if label in {"delete", "deleted", "deleted items", "trash"}:
        return folder_policy.get("trash")
    if label in {"noise", "review"}:
        return folder_policy.get(label)
    normalized_path = clean_value.replace("\\", "/").strip("/")
    if not normalized_path:
        return None
    namespace_prefix = f"{folder_namespace}/"
    if normalized_path.lower() == folder_namespace.lower():
        return None
    if normalized_path.lower().startswith(namespace_prefix.lower()):
        folder_path = normalized_path
    else:
        folder_path = f"{folder_namespace}/{normalized_path}"
    if not _is_allowed_folder_path(folder_path, folder_namespace=folder_namespace):
        return None
    return folder_path


def _is_allowed_folder_path(folder_path: str, *, folder_namespace: str) -> bool:
    segments = folder_path.split("/")
    if not segments or segments[0].lower() != folder_namespace.lower():
        return False
    if len(segments) < 2:
        return False
    for segment in segments:
        clean_segment = segment.strip()
        if (
            not clean_segment
            or clean_segment in {".", ".."}
            or any(character in clean_segment for character in '<>:"|?*')
        ):
            return False
    return True


def _target_label(value: str, *, target_folder: str) -> str:
    label = value.strip().lower().replace(" ", "_").replace("/", "_")
    if label in {"delete", "deleted", "deleted_items"}:
        return "trash"
    if label in {"noise", "review", "trash"}:
        return label
    safe_label = re.sub(r"[^a-z0-9_]+", "_", label).strip("_")
    if safe_label:
        return f"custom_{safe_label}"
    return f"custom_{re.sub(r'[^a-z0-9_]+', '_', target_folder.lower()).strip('_')}"


def _record_cleanup_feedback(
    store: DuckDbMemoryStore,
    *,
    run_id: str,
    item_id: str,
    target_folder: str,
) -> None:
    feedback_type = (
        "noise"
        if target_folder == "Deleted Items" or target_folder.lower().endswith("/noise")
        else "review"
    )
    feedback_text = (
        "Deleted during email cleanup."
        if target_folder == "Deleted Items"
        else f"Filed to {target_folder} during email cleanup."
    )
    store.record_feedback(
        item_id=item_id,
        run_id=run_id,
        feedback_type=feedback_type,
        feedback_text=feedback_text,
    )
    store.record_assistant_action(
        run_id=run_id,
        item_id=item_id,
        action_type="record_email_cleanup_feedback",
        approval_status="not_required",
        action_target=target_folder,
        result=f"Recorded {feedback_type} cleanup feedback for {target_folder}.",
    )


def _failed_item(command: dict[str, Any], result: str) -> CleanupCommandPlanItem:
    return CleanupCommandPlanItem(
        item_number=command["number"],
        label=str(command.get("target") or ""),
        target_folder=None,
        item_id=None,
        subject=None,
        result=result,
        executed=False,
    )


def _manifest_item(manifest: dict[str, Any], *, number: int) -> dict[str, Any] | None:
    raw_items = manifest.get("items", [])
    if not isinstance(raw_items, list):
        return None
    for item in raw_items:
        if isinstance(item, dict) and item.get("number") == number:
            return item
    return None


def _load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Email cleanup manifest must be a JSON object.")
    return payload


def _summary(plan: Sequence[CleanupCommandPlanItem], *, execute: bool) -> str:
    verb = "Recorded" if execute else "Prepared"
    feedback_count = sum(1 for item in plan if item.feedback_recorded)
    if execute:
        return (
            f"{verb} {len(plan)} email cleanup batch command(s); "
            f"learned from {feedback_count} item(s)."
        )
    return f"{verb} {len(plan)} email cleanup batch command(s)."


def _format_result(plan: tuple[CleanupCommandPlanItem, ...], *, execute: bool) -> str:
    title = "# Email Cleanup Batch Execution" if execute else "# Email Cleanup Batch Plan"
    lines = [title, "", "## Summary", "", f"- Commands: {len(plan)}"]
    lines.append(f"- Mode: {'execute' if execute else 'dry-run'}")
    if execute:
        lines.append(
            "- Learning feedback recorded: "
            f"{sum(1 for item in plan if item.feedback_recorded)}"
        )
    lines.extend(("", "## Commands", ""))
    for item in plan:
        subject = f": {item.subject}" if item.subject else ""
        target = f" -> {item.target_folder}" if item.target_folder else ""
        lines.append(f"- Item {item.item_number}{target}{subject}")
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
        description="Process numbered directions from an email cleanup batch."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--directions", help="Cleanup directions to process.")
    input_group.add_argument("--directions-file", help="Path to cleanup directions.")
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_EMAIL_CLEANUP_MANIFEST_PATH),
        help="Email cleanup manifest path.",
    )
    parser.add_argument(
        "--memory",
        default=str(DEFAULT_MEMORY_PATH),
        help="Local Clarity memory path.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Record approved cleanup actions.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
