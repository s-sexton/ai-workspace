"""Read-only email metadata boundary for AI Workspace."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Protocol


class EmailClientError(RuntimeError):
    """Raised when email retrieval or normalization fails."""


class EmailTransport(Protocol):
    """Minimal read-only email transport interface."""

    def list_messages(self, mailbox: str, limit: int) -> SequenceEmailMessages:
        """Return raw mailbox messages."""


class EmailMoveTransport(Protocol):
    """Minimal email move transport interface."""

    def move_message(
        self,
        *,
        mailbox: str,
        message_id: str,
        target_folder: str,
    ) -> None:
        """Move one message inside a mailbox."""


SequenceEmailMessages = tuple[Mapping[str, Any], ...]
AUTH_STATUS_VALUES = (
    "pass",
    "fail",
    "softfail",
    "neutral",
    "none",
    "temperror",
    "permerror",
)
REVIEW_SIGNAL_TOKENS = (
    "accounting",
    "approval",
    "approve",
    "billing",
    "calendar",
    "contract",
    "decision",
    "dpo",
    "family",
    "invoice",
    "legal",
    "meeting",
    "payment",
    "password",
    "security",
    "statement",
    "urgent",
)
NOISE_SIGNAL_TOKENS = (
    "% off",
    "all bottoms",
    "birthday fun",
    "boost your nutrition",
    "buy 1",
    "credit card recommendations",
    "daily digest",
    "deal",
    "exclusive offer",
    "free shipping",
    "grab a",
    "introducing the new",
    "member savings",
    "newsletter",
    "points",
    "sale",
    "savings",
    "sports extra",
    "start watching",
    "summer colors",
    "today only",
    "unsubscribe",
    "vacation from",
    "webinar",
    "wiper refresh",
)


@dataclass(frozen=True)
class EmailMessage:
    """Normalized email metadata used by Clarity."""

    message_id: str
    mailbox: str
    subject: str
    sender: str | None = None
    return_path: str | None = None
    spf: str | None = None
    dkim: str | None = None
    dmarc: str | None = None
    received_at: str | None = None
    preview: str | None = None
    categories: tuple[str, ...] = ()


@dataclass(frozen=True)
class EmailClassification:
    """Deterministic first-pass email classification."""

    label: str
    reason: str


@dataclass(frozen=True)
class EmailFeedbackRule:
    """A local human feedback rule for future email classification."""

    label: str
    subject: str
    sender: str | None
    content_terms: tuple[str, ...] = ()


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
class EmailMoveRequest:
    """A request to move one message inside a mailbox."""

    mailbox: str
    message_id: str
    target_folder: str


@dataclass(frozen=True)
class EmailMoveResult:
    """Result metadata for an email move request."""

    mailbox: str
    message_id: str
    target_folder: str


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
class StaticGraphEmailTransport:
    """Fake Microsoft Graph-shaped read-only email transport."""

    messages_by_mailbox: Mapping[str, tuple[Mapping[str, Any], ...]]

    def list_messages(self, mailbox: str, limit: int) -> SequenceEmailMessages:
        """Return fake Microsoft Graph messages normalized to Clarity payloads."""

        if limit < 1:
            raise EmailClientError("limit must be positive.")
        graph_messages = self.messages_by_mailbox.get(mailbox, ())
        return tuple(
            graph_message_to_email_payload(message, mailbox=mailbox)
            for message in graph_messages[:limit]
        )


@dataclass
class StaticEmailMoveTransport:
    """Fake email move transport for local workflow tests."""

    moved_messages: list[EmailMoveRequest]

    def move_message(
        self,
        *,
        mailbox: str,
        message_id: str,
        target_folder: str,
    ) -> None:
        """Record a fake email move request."""

        self.moved_messages.append(
            EmailMoveRequest(
                mailbox=_required_non_empty_text(mailbox, "mailbox"),
                message_id=_required_non_empty_text(message_id, "message_id"),
                target_folder=_required_non_empty_text(
                    target_folder,
                    "target_folder",
                ),
            )
        )


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


@dataclass(frozen=True)
class EmailMoveClient:
    """Small email move client for validated move requests."""

    transport: EmailMoveTransport

    def move_message(
        self,
        *,
        mailbox: str,
        message_id: str,
        target_folder: str,
    ) -> EmailMoveResult:
        """Move one message inside a mailbox through the configured transport."""

        request = EmailMoveRequest(
            mailbox=_required_non_empty_text(mailbox, "mailbox"),
            message_id=_required_non_empty_text(message_id, "message_id"),
            target_folder=_required_non_empty_text(target_folder, "target_folder"),
        )
        self.transport.move_message(
            mailbox=request.mailbox,
            message_id=request.message_id,
            target_folder=request.target_folder,
        )
        return EmailMoveResult(
            mailbox=request.mailbox,
            message_id=request.message_id,
            target_folder=request.target_folder,
        )


def classify_email_message(
    message: EmailMessage,
    *,
    allowed_senders: tuple[str, ...] = (),
    feedback_rules: tuple[EmailFeedbackRule, ...] = (),
) -> EmailClassification:
    """Classify email metadata with deterministic first-pass rules."""

    if allowed_senders and not _sender_is_allowed(message.sender, allowed_senders):
        return EmailClassification(
            label="trash",
            reason="Message sent to a restricted mailbox by an unauthorized sender.",
        )
    if allowed_senders and not _message_authentication_passes(message):
        return EmailClassification(
            label="trash",
            reason=(
                "Message sent to a restricted mailbox without passing required "
                "SPF/DKIM/DMARC authentication checks."
            ),
        )

    feedback_rule = _matching_feedback_rule(message, feedback_rules)
    if feedback_rule is not None:
        return EmailClassification(
            label=feedback_rule.label,
            reason="Matched prior human email feedback.",
        )

    combined_text = _combined_lower_text(message)
    if _contains_any(combined_text, REVIEW_SIGNAL_TOKENS):
        return EmailClassification(
            label="review",
            reason="Potentially important operational or risk-related message.",
        )
    if _contains_any(combined_text, NOISE_SIGNAL_TOKENS):
        return EmailClassification(
            label="noise",
            reason="Marketing, digest, or subscription-style message.",
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


def graph_message_to_email_payload(
    payload: Mapping[str, Any],
    *,
    mailbox: str,
) -> Mapping[str, Any]:
    """Convert Microsoft Graph message metadata into Clarity email payload shape."""

    headers = _graph_headers(payload.get("internetMessageHeaders"))
    return {
        "message_id": _required_string(payload, "id"),
        "mailbox": mailbox,
        "subject": _required_string(payload, "subject"),
        "sender": _graph_sender(payload),
        "return_path": _first_header(headers, "return-path"),
        "authentication_results": _header_values(headers, "authentication-results"),
        "received_at": _optional_string(payload.get("receivedDateTime")),
        "preview": _optional_string(payload.get("bodyPreview")),
        "categories": _string_tuple(payload.get("categories", ())),
    }


def _sender_is_allowed(sender: str | None, allowed_senders: tuple[str, ...]) -> bool:
    if sender is None:
        return False
    clean_sender = sender.strip().lower()
    return clean_sender in {allowed_sender.lower() for allowed_sender in allowed_senders}


def _message_authentication_passes(message: EmailMessage) -> bool:
    return (
        _auth_status_passes(message.dmarc)
        and (_auth_status_passes(message.spf) or _auth_status_passes(message.dkim))
    )


def _auth_status_passes(status: str | None) -> bool:
    return status is not None and status.strip().lower() == "pass"


def _combined_lower_text(message: EmailMessage) -> str:
    return " ".join(
        value.lower()
        for value in (message.subject, message.sender or "", message.preview or "")
    )


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def _matching_feedback_rule(
    message: EmailMessage,
    feedback_rules: tuple[EmailFeedbackRule, ...],
) -> EmailFeedbackRule | None:
    message_subject = _normalize_feedback_text(message.subject)
    message_sender = _normalize_optional_feedback_text(message.sender)
    message_terms = set(email_learning_terms(message))
    for rule in feedback_rules:
        if rule.label not in ("noise", "review"):
            continue
        rule_sender = _normalize_optional_feedback_text(rule.sender)
        if rule_sender is not None and rule_sender != message_sender:
            continue
        if _normalize_feedback_text(rule.subject) == message_subject:
            return rule
        if _has_learning_term_match(message_terms, set(rule.content_terms)):
            return rule
    return None


def email_learning_terms(message: EmailMessage) -> tuple[str, ...]:
    """Return sanitized content terms that can guide future email feedback."""

    combined_text = _combined_lower_text(message)
    terms: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[a-z][a-z0-9']{2,}", combined_text):
        clean_token = token.strip("'")
        if clean_token in _EMAIL_LEARNING_STOP_WORDS:
            continue
        if any(marker.strip() in clean_token for marker in ("token", "password")):
            continue
        if clean_token not in seen:
            terms.append(clean_token)
            seen.add(clean_token)
        if len(terms) >= 20:
            break
    return tuple(terms)


def _has_learning_term_match(
    message_terms: set[str],
    rule_terms: set[str],
) -> bool:
    if len(rule_terms) < 3:
        return False
    shared_terms = message_terms & rule_terms
    return len(shared_terms) >= 3


_EMAIL_LEARNING_STOP_WORDS = {
    "about",
    "after",
    "again",
    "ahead",
    "also",
    "and",
    "are",
    "because",
    "been",
    "before",
    "but",
    "can",
    "com",
    "for",
    "from",
    "has",
    "have",
    "here",
    "into",
    "more",
    "not",
    "now",
    "off",
    "our",
    "out",
    "the",
    "this",
    "to",
    "with",
    "you",
    "your",
}


def _normalize_feedback_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _normalize_optional_feedback_text(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return _normalize_feedback_text(value)


def _graph_sender(payload: Mapping[str, Any]) -> str | None:
    sender = payload.get("from")
    if sender is None:
        sender = payload.get("sender")
    if sender is None:
        return None
    if not isinstance(sender, Mapping):
        raise EmailClientError("Graph sender must be an object when present.")
    email_address = sender.get("emailAddress")
    if not isinstance(email_address, Mapping):
        raise EmailClientError("Graph sender emailAddress must be an object.")
    address = email_address.get("address")
    return _optional_string(address)


def _graph_headers(value: Any) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise EmailClientError("Graph internetMessageHeaders must be a list.")

    headers: list[tuple[str, str]] = []
    for index, header in enumerate(value, 1):
        if not isinstance(header, Mapping):
            raise EmailClientError(
                f"Graph internetMessageHeaders entry must be an object: {index}"
            )
        name = header.get("name")
        header_value = header.get("value")
        if not isinstance(name, str) or not name.strip():
            raise EmailClientError(
                f"Graph internetMessageHeaders name must be a string: {index}"
            )
        if not isinstance(header_value, str):
            raise EmailClientError(
                f"Graph internetMessageHeaders value must be a string: {index}"
            )
        headers.append((name.strip().lower(), header_value))
    return tuple(headers)


def _header_values(headers: tuple[tuple[str, str], ...], name: str) -> tuple[str, ...]:
    clean_name = name.lower()
    return tuple(value for header_name, value in headers if header_name == clean_name)


def _first_header(headers: tuple[tuple[str, str], ...], name: str) -> str | None:
    values = _header_values(headers, name)
    return values[0] if values else None


def _normalize_message(payload: Mapping[str, Any], *, mailbox: str) -> EmailMessage:
    message_id = _required_string(payload, "message_id")
    subject = _required_string(payload, "subject")
    parsed_auth = _parse_authentication_results(
        payload.get("authentication_results")
    )
    return EmailMessage(
        message_id=message_id,
        mailbox=mailbox,
        subject=subject,
        sender=_optional_string(payload.get("sender")),
        return_path=_optional_string(payload.get("return_path")),
        spf=_optional_auth_status(payload.get("spf"), "spf")
        or parsed_auth.get("spf"),
        dkim=_optional_auth_status(payload.get("dkim"), "dkim")
        or parsed_auth.get("dkim"),
        dmarc=_optional_auth_status(payload.get("dmarc"), "dmarc")
        or parsed_auth.get("dmarc"),
        received_at=_optional_string(payload.get("received_at")),
        preview=_optional_string(payload.get("preview")),
        categories=_string_tuple(payload.get("categories", ())),
    )


def _required_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EmailClientError(f"Email message missing {key}.")
    return value.strip()


def _required_non_empty_text(value: str, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EmailClientError(f"Email move missing {key}.")
    return value.strip()


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise EmailClientError("Email metadata value must be a string when present.")
    return value


def _optional_auth_status(value: Any, key: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise EmailClientError(f"Email authentication value must be a string: {key}")
    clean_value = value.strip().lower()
    if clean_value not in AUTH_STATUS_VALUES:
        raise EmailClientError(f"Unsupported email authentication value: {key}")
    return clean_value


def _parse_authentication_results(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if isinstance(value, str):
        header_values = (value,)
    elif isinstance(value, (list, tuple)):
        if any(not isinstance(item, str) for item in value):
            raise EmailClientError(
                "Email authentication_results must be a string or list of strings."
            )
        header_values = tuple(value)
    else:
        raise EmailClientError(
            "Email authentication_results must be a string or list of strings."
        )

    parsed: dict[str, str] = {}
    for header_value in header_values:
        for auth_type, status in re.findall(
            r"\b(spf|dkim|dmarc)\s*=\s*([a-zA-Z]+)\b",
            header_value,
            flags=re.IGNORECASE,
        ):
            clean_auth_type = auth_type.lower()
            clean_status = status.lower()
            if clean_status in AUTH_STATUS_VALUES:
                parsed.setdefault(clean_auth_type, clean_status)
    return parsed


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise EmailClientError("Email categories must be a list of strings.")
    if any(not isinstance(item, str) for item in value):
        raise EmailClientError("Email categories must be a list of strings.")
    return tuple(value)
