"""Enqueue Teams-style relay messages for Clarity testing."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import uuid4

from assistant.src.process_teams_relay import build_azure_teams_relay_queue_from_config
from common.configuration import find_workspace_root
from common.teams_manifest import read_teams_manifest
from common.teams_relay import TeamsRelayQueue


SUPPORTED_ACTIONS = ("trash", "move_review", "move_noise")


@dataclass(frozen=True)
class EnqueueTeamsRelayResult:
    """Safe details for one enqueued Teams relay test message."""

    command_id: str
    text: str | None
    action_type: str | None
    item_numbers: tuple[int, ...]
    manifest_id: str | None


def enqueue_teams_relay_message(
    *,
    queue: TeamsRelayQueue,
    text: str | None = None,
    action_type: str | None = None,
    item_numbers: Sequence[int] = (),
    manifest_path: Path | str | None = None,
    root: Path | str | None = None,
    sender_email: str = "scott.sexton@sendthisfile.com",
    sender_name: str = "Scott Sexton",
    sender_object_id: str | None = None,
    team: str = "AI Workspace",
    channel: str = "Clarity",
    command_id: str | None = None,
) -> EnqueueTeamsRelayResult:
    """Enqueue a Teams relay text command or manifest-backed action."""

    if text and action_type:
        raise ValueError("text and action_type are mutually exclusive.")
    if not text and not action_type:
        raise ValueError("text or action_type is required.")
    manifest_id = None
    clean_item_numbers: tuple[int, ...] = ()
    if action_type:
        if action_type not in SUPPORTED_ACTIONS:
            raise ValueError(
                "action_type must be one of: " + ", ".join(SUPPORTED_ACTIONS)
            )
        clean_item_numbers = tuple(item_numbers)
        if not clean_item_numbers or any(number < 1 for number in clean_item_numbers):
            raise ValueError("item_numbers must contain positive integers.")
        if manifest_path is None:
            raise ValueError("manifest_path is required for actions.")
        workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
        manifest = read_teams_manifest(_resolve_path(workspace_root, Path(manifest_path)))
        manifest_id = manifest.manifest_id

    resolved_command_id = command_id or f"teams-relay-test-{uuid4().hex[:12]}"
    payload = _payload(
        command_id=resolved_command_id,
        text=text,
        action_type=action_type,
        item_numbers=clean_item_numbers,
        manifest_id=manifest_id,
        sender_email=sender_email,
        sender_name=sender_name,
        sender_object_id=sender_object_id,
        team=team,
        channel=channel,
    )
    queue.enqueue(payload)
    return EnqueueTeamsRelayResult(
        command_id=resolved_command_id,
        text=text,
        action_type=action_type,
        item_numbers=clean_item_numbers,
        manifest_id=manifest_id,
    )


def _payload(
    *,
    command_id: str,
    text: str | None,
    action_type: str | None,
    item_numbers: tuple[int, ...],
    manifest_id: str | None,
    sender_email: str,
    sender_name: str,
    sender_object_id: str | None,
    team: str,
    channel: str,
) -> Mapping[str, Any]:
    return {
        "schemaVersion": 1,
        "source": "teams",
        "commandId": command_id,
        "receivedAt": datetime.now(timezone.utc).isoformat(),
        "from": {
            "displayName": sender_name,
            "email": sender_email,
            "aadObjectId": sender_object_id,
        },
        "conversation": {
            "team": team,
            "channel": channel,
        },
        "text": text,
        "action": (
            None
            if action_type is None
            else {
                "type": action_type,
                "manifestId": manifest_id,
                "itemNumbers": list(item_numbers),
            }
        ),
    }


def _resolve_path(workspace_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return workspace_root / path


def main(argv: Sequence[str] | None = None) -> None:
    """Enqueue a Teams relay message into the configured Azure queue."""

    args = _parse_args(argv)
    result = enqueue_teams_relay_message(
        queue=build_azure_teams_relay_queue_from_config(),
        text=args.text,
        action_type=args.action,
        item_numbers=args.item,
        manifest_path=args.manifest,
        sender_email=args.sender,
        sender_name=args.sender_name,
        sender_object_id=args.sender_object_id,
        team=args.team,
        channel=args.channel,
    )
    print(json.dumps(result.__dict__, indent=2, sort_keys=True))


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enqueue a Teams-style Clarity relay test message."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--text", help="Teams text command to enqueue.")
    input_group.add_argument(
        "--action",
        choices=SUPPORTED_ACTIONS,
        help="Manifest-backed Teams card action to enqueue.",
    )
    parser.add_argument(
        "--item",
        action="append",
        type=int,
        default=[],
        help="Manifest item number for --action. Repeat for multiple items.",
    )
    parser.add_argument(
        "--manifest",
        default=str(Path("reports") / "teams-gmail-manifest.json"),
        help="Teams manifest path for action messages.",
    )
    parser.add_argument("--sender", default="scott.sexton@sendthisfile.com")
    parser.add_argument("--sender-name", default="Scott Sexton")
    parser.add_argument("--sender-object-id")
    parser.add_argument("--team", default="AI Workspace")
    parser.add_argument("--channel", default="Clarity")
    args = parser.parse_args(argv)
    if args.action and not args.item:
        parser.error("--action requires at least one --item.")
    return args


if __name__ == "__main__":
    main()
