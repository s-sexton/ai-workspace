"""Read-only email metadata boundary for AI Workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol


class EmailClientError(RuntimeError):
    """Raised when email retrieval or normalization fails."""


class EmailTransport(Protocol):
    """Minimal read-only email transport interface."""

    def list_messages(self, mailbox: str, limit: int) -> SequenceEmailMessages:
        """Return raw mailbox messages."""


SequenceEmailMessages = tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class EmailMessage:
    """Normalized email metadata used by Clarity."""

    message_id: str
    mailbox: str
    subject: str
    sender: str | None = None
    received_at: str | None = None
    preview: str | None = None
    categories: tuple[str, ...] = ()


@dataclass(frozen=True)
class EmailClassification:
    """Deterministic first-pass email classification."""

    label: str
    reason: str


@dataclass(frozen=True)
class EmailFolderProposal:
    """A local proposal for where an email should be reviewed."""

    action_type: str
    target_folder: str
    reason: str


@dataclass(frozen=True)
class EmailReadResult:
    """Normalized read-only mailbox result."""

    mailbox: str
    messages: tuple[EmailMessage, ...]


@dataclass(frozen=True)
class StaticEmailTransport:
    """Fake read-only email transport for local workflow tests."""

    messages: tuple[Mapping[str, Any], ...]

    def list_messages(self, mailbox: str, limit: int) -> SequenceEmailMessages:
        """Return fake messages for a mailbox."""

        if limit < 1:
            raise EmailClientError("limit must be positive.")
        return tuple(
            message for message in self.messages if message.get("mailbox") == mailbox
        )[:limit]


@dataclass(frozen=True)
class EmailClient:
    """Small read-only email client for metadata normalization."""

    transport: EmailTransport

    def list_messages(self, *, mailbox: str, limit: int = 25) -> EmailReadResult:
        """Read and normalize mailbox message metadata."""

        if not mailbox.strip():
            raise EmailClientError("mailbox must be a non-empty string.")
        if limit < 1:
            raise EmailClientError("limit must be positive.")

        messages = tuple(
            _normalize_message(message, mailbox=mailbox)
            for message in self.transport.list_messages(mailbox, limit)
        )
        return EmailReadResult(mailbox=mailbox, messages=messages)


def classify_email_message(message: EmailMessage) -> EmailClassification:
    """Classify email metadata with deterministic first-pass rules."""

    combined_text = " ".join(
        value.lower()
        for value in (message.subject, message.sender or "", message.preview or "")
    )
    if any(token in combined_text for token in ("unsubscribe", "newsletter", "webinar")):
        return EmailClassification(
            label="noise",
            reason="Marketing or subscription-style message.",
        )
    if any(token in combined_text for token in ("legal", "accounting", "dpo", "urgent")):
        return EmailClassification(
            label="review",
            reason="Potentially important operational or risk-related message.",
        )
    return EmailClassification(
        label="review",
        reason="No safe noise rule matched; keep for human review.",
    )


def propose_email_folder_action(
    classification: EmailClassification,
    folder_policy: Mapping[str, str],
) -> EmailFolderProposal:
    """Create a local folder move proposal from a classification."""

    target_folder = folder_policy.get(classification.label)
    if target_folder is None:
        raise EmailClientError(
            f"No email folder policy configured for label: {classification.label}"
        )
    action_suffix = classification.label.replace("_", "-")
    return EmailFolderProposal(
        action_type=f"propose_email_move_{action_suffix}",
        target_folder=target_folder,
        reason=(
            f"Classification '{classification.label}' maps to "
            f"folder '{target_folder}'."
        ),
    )


def _normalize_message(payload: Mapping[str, Any], *, mailbox: str) -> EmailMessage:
    message_id = _required_string(payload, "message_id")
    subject = _required_string(payload, "subject")
    return EmailMessage(
        message_id=message_id,
        mailbox=mailbox,
        subject=subject,
        sender=_optional_string(payload.get("sender")),
        received_at=_optional_string(payload.get("received_at")),
        preview=_optional_string(payload.get("preview")),
        categories=_string_tuple(payload.get("categories", ())),
    )


def _required_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EmailClientError(f"Email message missing {key}.")
    return value.strip()


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise EmailClientError("Email metadata value must be a string when present.")
    return value


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise EmailClientError("Email categories must be a list of strings.")
    if any(not isinstance(item, str) for item in value):
        raise EmailClientError("Email categories must be a list of strings.")
    return tuple(value)
