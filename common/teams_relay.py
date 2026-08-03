"""Teams Workflow relay message primitives."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol
from uuid import uuid4


class TeamsRelayError(RuntimeError):
    """Raised when a Teams relay message or queue operation is invalid."""


@dataclass(frozen=True)
class TeamsSenderIdentity:
    """Identity details for the Teams user who sent a command."""

    display_name: str
    email: str
    aad_object_id: str | None = None


@dataclass(frozen=True)
class TeamsConversationRef:
    """Teams conversation details carried through the relay."""

    team: str
    channel: str
    message_id: str | None = None
    reply_to_id: str | None = None


@dataclass(frozen=True)
class TeamsRelayAction:
    """Action details from a Teams card button or submit payload."""

    action_type: str
    manifest_id: str | None = None
    item_numbers: tuple[int, ...] = ()


@dataclass(frozen=True)
class TeamsRelayMessage:
    """Validated Teams Workflow relay message."""

    schema_version: int
    source: str
    command_id: str
    received_at: str
    sender: TeamsSenderIdentity
    conversation: TeamsConversationRef
    text: str | None = None
    action: TeamsRelayAction | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> TeamsRelayMessage:
        """Create a relay message from a JSON-like mapping."""

        schema_version = payload.get("schemaVersion")
        if schema_version != 1:
            raise TeamsRelayError("Unsupported Teams relay schemaVersion.")
        source = _required_text(payload.get("source"), "source")
        if source != "teams":
            raise TeamsRelayError("Teams relay source must be 'teams'.")
        text = _optional_text(payload.get("text"))
        action = _action_from_mapping(payload.get("action"))
        if text is None and action is None:
            raise TeamsRelayError("Teams relay message requires text or action.")
        return cls(
            schema_version=schema_version,
            source=source,
            command_id=_required_text(payload.get("commandId"), "commandId"),
            received_at=_required_text(payload.get("receivedAt"), "receivedAt"),
            sender=_sender_from_mapping(payload.get("from")),
            conversation=_conversation_from_mapping(payload.get("conversation")),
            text=text,
            action=action,
        )

    def to_mapping(self) -> Mapping[str, Any]:
        """Return a JSON-safe mapping."""

        return {
            "schemaVersion": self.schema_version,
            "source": self.source,
            "commandId": self.command_id,
            "receivedAt": self.received_at,
            "from": {
                "displayName": self.sender.display_name,
                "email": self.sender.email,
                "aadObjectId": self.sender.aad_object_id,
            },
            "conversation": {
                "team": self.conversation.team,
                "channel": self.conversation.channel,
                "messageId": self.conversation.message_id,
                "replyToId": self.conversation.reply_to_id,
            },
            "text": self.text,
            "action": (
                None
                if self.action is None
                else {
                    "type": self.action.action_type,
                    "manifestId": self.action.manifest_id,
                    "itemNumbers": list(self.action.item_numbers),
                }
            ),
        }


@dataclass(frozen=True)
class TeamsQueueMessage:
    """One received relay queue message."""

    queue_message_id: str
    payload: Mapping[str, Any]
    dequeue_count: int = 1


class TeamsRelayQueue(Protocol):
    """Minimal queue boundary for Teams relay commands."""

    def enqueue(self, payload: Mapping[str, Any]) -> TeamsQueueMessage:
        """Add a message to the queue."""

    def receive(self, *, limit: int = 1) -> tuple[TeamsQueueMessage, ...]:
        """Receive visible messages from the queue."""

    def complete(self, queue_message_id: str) -> None:
        """Mark a message as processed."""

    def dead_letter(self, queue_message_id: str, *, reason: str) -> None:
        """Move a failed message to a dead-letter collection."""


@dataclass
class InMemoryTeamsRelayQueue:
    """Test-friendly in-memory Teams relay queue."""

    _pending: list[TeamsQueueMessage] = field(default_factory=list)
    completed: list[TeamsQueueMessage] = field(default_factory=list)
    dead_letters: list[tuple[TeamsQueueMessage, str]] = field(default_factory=list)

    def enqueue(self, payload: Mapping[str, Any]) -> TeamsQueueMessage:
        message = TeamsQueueMessage(queue_message_id=uuid4().hex, payload=dict(payload))
        self._pending.append(message)
        return message

    def receive(self, *, limit: int = 1) -> tuple[TeamsQueueMessage, ...]:
        if limit < 1:
            raise TeamsRelayError("limit must be positive.")
        return tuple(self._pending[:limit])

    def complete(self, queue_message_id: str) -> None:
        message = self._pop_pending(queue_message_id)
        self.completed.append(message)

    def dead_letter(self, queue_message_id: str, *, reason: str) -> None:
        message = self._pop_pending(queue_message_id)
        self.dead_letters.append((message, _required_text(reason, "reason")))

    def _pop_pending(self, queue_message_id: str) -> TeamsQueueMessage:
        for index, message in enumerate(self._pending):
            if message.queue_message_id == queue_message_id:
                return self._pending.pop(index)
        raise TeamsRelayError(f"Unknown queue message: {queue_message_id}")


def relay_message_json(payload: Mapping[str, Any]) -> str:
    """Serialize a relay payload deterministically for local fixtures."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _sender_from_mapping(value: Any) -> TeamsSenderIdentity:
    if not isinstance(value, Mapping):
        raise TeamsRelayError("Teams relay from must be an object.")
    return TeamsSenderIdentity(
        display_name=_required_text(value.get("displayName"), "from.displayName"),
        email=_required_text(value.get("email"), "from.email").lower(),
        aad_object_id=_optional_text(value.get("aadObjectId")),
    )


def _conversation_from_mapping(value: Any) -> TeamsConversationRef:
    if not isinstance(value, Mapping):
        raise TeamsRelayError("Teams relay conversation must be an object.")
    return TeamsConversationRef(
        team=_required_text(value.get("team"), "conversation.team"),
        channel=_required_text(value.get("channel"), "conversation.channel"),
        message_id=_optional_text(value.get("messageId")),
        reply_to_id=_optional_text(value.get("replyToId")),
    )


def _action_from_mapping(value: Any) -> TeamsRelayAction | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise TeamsRelayError("Teams relay action must be an object.")
    item_numbers = value.get("itemNumbers", ())
    if item_numbers is None:
        item_numbers = ()
    if not isinstance(item_numbers, list) or any(
        not isinstance(item, int) or item < 1 for item in item_numbers
    ):
        raise TeamsRelayError("Teams relay action itemNumbers must be positive integers.")
    return TeamsRelayAction(
        action_type=_required_text(value.get("type"), "action.type"),
        manifest_id=_optional_text(value.get("manifestId")),
        item_numbers=tuple(item_numbers),
    )


def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TeamsRelayError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TeamsRelayError("Optional Teams relay text values must be strings.")
    stripped = value.strip()
    return stripped or None
