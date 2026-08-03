"""Local Teams message manifest helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import uuid4


class TeamsManifestError(RuntimeError):
    """Raised when a Teams message manifest is invalid."""


@dataclass(frozen=True)
class TeamsManifestItem:
    """One actionable item shown in a Teams message."""

    number: int
    source_type: str
    external_id: str
    subject: str
    mailbox: str | None = None
    allowed_actions: tuple[str, ...] = ()

    def to_mapping(self) -> Mapping[str, Any]:
        """Return a JSON-safe mapping."""

        return {
            "number": self.number,
            "sourceType": self.source_type,
            "mailbox": self.mailbox,
            "externalId": self.external_id,
            "subject": self.subject,
            "allowedActions": list(self.allowed_actions),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> TeamsManifestItem:
        """Create an item from a JSON-like mapping."""

        number = payload.get("number")
        if not isinstance(number, int) or number < 1:
            raise TeamsManifestError("Manifest item number must be a positive integer.")
        allowed_actions = payload.get("allowedActions", ())
        if not isinstance(allowed_actions, list) or any(
            not isinstance(action, str) or not action.strip()
            for action in allowed_actions
        ):
            raise TeamsManifestError("Manifest allowedActions must be strings.")
        return cls(
            number=number,
            source_type=_required_text(payload.get("sourceType"), "sourceType"),
            mailbox=_optional_text(payload.get("mailbox")),
            external_id=_required_text(payload.get("externalId"), "externalId"),
            subject=_required_text(payload.get("subject"), "subject"),
            allowed_actions=tuple(action.strip() for action in allowed_actions),
        )


@dataclass(frozen=True)
class TeamsMessageManifest:
    """Local manifest for a Teams message with numbered items."""

    manifest_id: str
    surface: str
    created_at: str
    items: tuple[TeamsManifestItem, ...]

    def to_mapping(self) -> Mapping[str, Any]:
        """Return a JSON-safe mapping."""

        return {
            "manifestId": self.manifest_id,
            "surface": self.surface,
            "createdAt": self.created_at,
            "items": [item.to_mapping() for item in self.items],
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> TeamsMessageManifest:
        """Create a manifest from a JSON-like mapping."""

        raw_items = payload.get("items")
        if not isinstance(raw_items, list):
            raise TeamsManifestError("Manifest items must be a list.")
        items = tuple(
            TeamsManifestItem.from_mapping(item)
            for item in raw_items
            if isinstance(item, Mapping)
        )
        if len(items) != len(raw_items):
            raise TeamsManifestError("Manifest items must be objects.")
        return cls(
            manifest_id=_required_text(payload.get("manifestId"), "manifestId"),
            surface=_required_text(payload.get("surface"), "surface"),
            created_at=_required_text(payload.get("createdAt"), "createdAt"),
            items=items,
        )


def create_teams_manifest(
    *,
    created_at: str,
    items: Sequence[TeamsManifestItem],
    manifest_id: str | None = None,
    surface: str = "teams",
) -> TeamsMessageManifest:
    """Create a Teams manifest and validate item numbering."""

    manifest_items = tuple(items)
    expected_numbers = tuple(range(1, len(manifest_items) + 1))
    actual_numbers = tuple(item.number for item in manifest_items)
    if actual_numbers != expected_numbers:
        raise TeamsManifestError("Manifest item numbers must be sequential from 1.")
    return TeamsMessageManifest(
        manifest_id=manifest_id or uuid4().hex,
        surface=_required_text(surface, "surface"),
        created_at=_required_text(created_at, "created_at"),
        items=manifest_items,
    )


def write_teams_manifest(path: Path | str, manifest: TeamsMessageManifest) -> Path:
    """Write a Teams manifest JSON file."""

    resolved_path = Path(path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(
        json.dumps(manifest.to_mapping(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return resolved_path


def read_teams_manifest(path: Path | str) -> TeamsMessageManifest:
    """Read a Teams manifest JSON file."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TeamsManifestError("Manifest file must contain a JSON object.")
    return TeamsMessageManifest.from_mapping(payload)


def resolve_manifest_items(
    manifest: TeamsMessageManifest,
    *,
    item_numbers: Sequence[int],
    required_action: str | None = None,
) -> tuple[TeamsManifestItem, ...]:
    """Resolve numbered manifest items and optionally validate an action."""

    by_number = {item.number: item for item in manifest.items}
    resolved: list[TeamsManifestItem] = []
    for number in item_numbers:
        item = by_number.get(number)
        if item is None:
            raise TeamsManifestError(f"Unknown manifest item number: {number}")
        if required_action is not None and required_action not in item.allowed_actions:
            raise TeamsManifestError(
                f"Action {required_action} is not allowed for item {number}."
            )
        resolved.append(item)
    return tuple(resolved)


def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TeamsManifestError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TeamsManifestError("Optional manifest text values must be strings.")
    stripped = value.strip()
    return stripped or None
