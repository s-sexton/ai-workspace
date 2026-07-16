"""Google Gmail transport boundary for AI Workspace."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping
from urllib.parse import quote, urlencode

from common.configuration import GoogleCredentials
from common.email import EmailClientError, SequenceEmailMessages
from common.google_calendar import (
    GoogleCalendarClientError,
    GoogleCalendarTransport,
    GoogleTokenTransport,
    GoogleRefreshTokenProvider,
    UrllibGoogleCalendarTransport,
    UrllibGoogleTokenTransport,
)


GOOGLE_GMAIL_BASE_URL = "https://gmail.googleapis.com/gmail/v1"


class GoogleGmailClientError(RuntimeError):
    """Raised when Gmail operations fail."""


def build_google_gmail_read_transport(
    credentials: GoogleCredentials,
    *,
    gmail_transport: GoogleCalendarTransport | None = None,
    token_transport: GoogleTokenTransport | None = None,
    use_bearer_auth: bool = False,
) -> GoogleGmailReadTransport:
    """Build a Gmail read transport from local credentials."""

    access_token = _google_access_token(
        credentials,
        token_transport=token_transport,
        use_bearer_auth=use_bearer_auth,
    )
    return GoogleGmailReadTransport(
        access_token=access_token,
        transport=gmail_transport or UrllibGoogleCalendarTransport(),
    )


def build_google_gmail_move_transport(
    credentials: GoogleCredentials,
    *,
    gmail_transport: GoogleCalendarTransport | None = None,
    token_transport: GoogleTokenTransport | None = None,
    use_bearer_auth: bool = False,
) -> GoogleGmailMoveTransport:
    """Build a Gmail move/trash transport from local credentials."""

    access_token = _google_access_token(
        credentials,
        token_transport=token_transport,
        use_bearer_auth=use_bearer_auth,
    )
    return GoogleGmailMoveTransport(
        access_token=access_token,
        transport=gmail_transport or UrllibGoogleCalendarTransport(),
    )


@dataclass(frozen=True)
class GoogleGmailReadTransport:
    """Read Gmail message metadata."""

    access_token: str = field(repr=False)
    transport: GoogleCalendarTransport = field(repr=False)
    base_url: str = GOOGLE_GMAIL_BASE_URL

    def list_messages(self, mailbox: str, limit: int) -> SequenceEmailMessages:
        """Return normalized Gmail payloads for inbox messages."""

        clean_mailbox = _required_text(mailbox, "mailbox")
        if limit < 1:
            raise EmailClientError("limit must be positive.")

        payload = self._get_json(self._message_list_url(clean_mailbox, limit=limit))
        raw_messages = payload.get("messages", [])
        if not isinstance(raw_messages, list):
            raise GoogleGmailClientError("Gmail messages response missing messages.")

        messages = []
        for raw_message in raw_messages:
            if not isinstance(raw_message, Mapping):
                raise GoogleGmailClientError(
                    "Gmail messages response item must be an object."
                )
            message_id = raw_message.get("id")
            if not isinstance(message_id, str) or not message_id.strip():
                raise GoogleGmailClientError("Gmail message missing id.")
            messages.append(
                gmail_message_to_email_payload(
                    self._message_metadata(clean_mailbox, message_id),
                    mailbox=clean_mailbox,
                )
            )
        return tuple(messages)

    def _message_metadata(
        self,
        mailbox: str,
        message_id: str,
    ) -> Mapping[str, Any]:
        return self._get_json(self._message_metadata_url(mailbox, message_id))

    def _get_json(self, url: str) -> Mapping[str, Any]:
        response = self.transport.get(url, headers=self._json_headers())
        if response.status_code != 200:
            raise GoogleGmailClientError(
                f"Gmail read failed with status {response.status_code}"
            )
        return response.json()

    def _json_headers(self) -> dict[str, str]:
        token = _required_text(self.access_token, "access_token")
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def _message_list_url(self, mailbox: str, *, limit: int) -> str:
        encoded_mailbox = quote(mailbox, safe="")
        query = urlencode(
            {
                "maxResults": str(limit),
                "labelIds": "INBOX",
                "includeSpamTrash": "false",
            }
        )
        return f"{self._base_url()}/users/{encoded_mailbox}/messages?{query}"

    def _message_metadata_url(self, mailbox: str, message_id: str) -> str:
        encoded_mailbox = quote(mailbox, safe="")
        encoded_message_id = quote(message_id, safe="")
        query = urlencode(
            {
                "format": "metadata",
                "metadataHeaders": ("From", "Subject", "Date"),
                "fields": "id,threadId,labelIds,snippet,payload/headers",
            },
            doseq=True,
        )
        return (
            f"{self._base_url()}/users/{encoded_mailbox}/messages/"
            f"{encoded_message_id}?{query}"
        )

    def _base_url(self) -> str:
        return self.base_url.rstrip("/")


@dataclass(frozen=True)
class GoogleGmailMoveTransport:
    """Archive, label, or trash Gmail messages."""

    access_token: str = field(repr=False)
    transport: GoogleCalendarTransport = field(repr=False)
    base_url: str = GOOGLE_GMAIL_BASE_URL

    def move_message(
        self,
        *,
        mailbox: str,
        message_id: str,
        target_folder: str,
    ) -> None:
        """Move one Gmail message according to the configured target."""

        clean_mailbox = _required_text(mailbox, "mailbox")
        clean_message_id = _required_text(message_id, "message_id")
        clean_target = _required_text(target_folder, "target_folder")
        if clean_target == "Deleted Items":
            self._trash_message(clean_mailbox, clean_message_id)
            return

        label_id = self._label_id(clean_mailbox, clean_target)
        self._modify_message(
            clean_mailbox,
            clean_message_id,
            body={
                "removeLabelIds": ["INBOX"],
                "addLabelIds": [label_id],
            },
        )

    def trash_spam_messages(self, mailbox: str) -> tuple[str, ...]:
        """Move all current Gmail Spam messages to Trash."""

        clean_mailbox = _required_text(mailbox, "mailbox")
        trashed_message_ids: list[str] = []
        page_token: str | None = None
        while True:
            payload = self._get_json(
                self._message_list_url(
                    clean_mailbox,
                    label_id="SPAM",
                    include_spam_trash=True,
                    page_token=page_token,
                )
            )
            raw_messages = payload.get("messages", [])
            if not isinstance(raw_messages, list):
                raise GoogleGmailClientError("Gmail messages response missing messages.")
            for raw_message in raw_messages:
                if not isinstance(raw_message, Mapping):
                    raise GoogleGmailClientError(
                        "Gmail messages response item must be an object."
                    )
                message_id = raw_message.get("id")
                if not isinstance(message_id, str) or not message_id.strip():
                    raise GoogleGmailClientError("Gmail message missing id.")
                clean_message_id = message_id.strip()
                self._trash_message(clean_mailbox, clean_message_id)
                trashed_message_ids.append(clean_message_id)

            next_page_token = payload.get("nextPageToken")
            if next_page_token is None:
                break
            if not isinstance(next_page_token, str) or not next_page_token.strip():
                raise GoogleGmailClientError("Gmail nextPageToken must be a string.")
            page_token = next_page_token.strip()

        return tuple(trashed_message_ids)

    def _label_id(self, mailbox: str, label_name: str) -> str:
        existing = self._find_label_id(mailbox, label_name)
        if existing is not None:
            return existing
        return self._create_label(mailbox, label_name)

    def _get_json(self, url: str) -> Mapping[str, Any]:
        response = self.transport.get(url, headers=self._json_headers())
        if response.status_code != 200:
            raise GoogleGmailClientError(
                f"Gmail read failed with status {response.status_code}"
            )
        return response.json()

    def _find_label_id(self, mailbox: str, label_name: str) -> str | None:
        response = self.transport.get(self._labels_url(mailbox), headers=self._json_headers())
        if response.status_code != 200:
            raise GoogleGmailClientError(
                f"Gmail label lookup failed with status {response.status_code}"
            )
        payload = response.json()
        raw_labels = payload.get("labels")
        if not isinstance(raw_labels, list):
            raise GoogleGmailClientError("Gmail labels response missing labels.")
        for raw_label in raw_labels:
            if not isinstance(raw_label, Mapping):
                raise GoogleGmailClientError("Gmail label response item must be an object.")
            if raw_label.get("name") == label_name:
                label_id = raw_label.get("id")
                if not isinstance(label_id, str) or not label_id.strip():
                    raise GoogleGmailClientError("Gmail label missing id.")
                return label_id
        return None

    def _create_label(self, mailbox: str, label_name: str) -> str:
        response = self.transport.post(
            self._labels_url(mailbox),
            headers=self._json_headers(),
            body={
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        )
        if response.status_code != 200:
            raise GoogleGmailClientError(
                f"Gmail label create failed with status {response.status_code}"
            )
        payload = response.json()
        label_id = payload.get("id")
        if not isinstance(label_id, str) or not label_id.strip():
            raise GoogleGmailClientError("Gmail label create response missing id.")
        return label_id

    def _trash_message(self, mailbox: str, message_id: str) -> None:
        response = self.transport.post(
            self._trash_url(mailbox, message_id),
            headers=self._json_headers(),
            body={},
        )
        if response.status_code != 200:
            raise GoogleGmailClientError(
                f"Gmail trash failed with status {response.status_code}"
            )

    def _modify_message(
        self,
        mailbox: str,
        message_id: str,
        *,
        body: Mapping[str, Any],
    ) -> None:
        response = self.transport.post(
            self._modify_url(mailbox, message_id),
            headers=self._json_headers(),
            body=body,
        )
        if response.status_code != 200:
            raise GoogleGmailClientError(
                f"Gmail modify failed with status {response.status_code}"
            )

    def _json_headers(self) -> dict[str, str]:
        token = _required_text(self.access_token, "access_token")
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def _labels_url(self, mailbox: str) -> str:
        encoded_mailbox = quote(mailbox, safe="")
        return f"{self._base_url()}/users/{encoded_mailbox}/labels"

    def _trash_url(self, mailbox: str, message_id: str) -> str:
        encoded_mailbox = quote(mailbox, safe="")
        encoded_message_id = quote(message_id, safe="")
        return (
            f"{self._base_url()}/users/{encoded_mailbox}/messages/"
            f"{encoded_message_id}/trash"
        )

    def _modify_url(self, mailbox: str, message_id: str) -> str:
        encoded_mailbox = quote(mailbox, safe="")
        encoded_message_id = quote(message_id, safe="")
        return (
            f"{self._base_url()}/users/{encoded_mailbox}/messages/"
            f"{encoded_message_id}/modify"
        )

    def _message_list_url(
        self,
        mailbox: str,
        *,
        label_id: str,
        include_spam_trash: bool,
        page_token: str | None = None,
    ) -> str:
        encoded_mailbox = quote(mailbox, safe="")
        query_values = {
            "maxResults": "100",
            "labelIds": label_id,
            "includeSpamTrash": "true" if include_spam_trash else "false",
        }
        if page_token is not None:
            query_values["pageToken"] = page_token
        query = urlencode(query_values)
        return f"{self._base_url()}/users/{encoded_mailbox}/messages?{query}"

    def _base_url(self) -> str:
        return self.base_url.rstrip("/")


def gmail_message_to_email_payload(
    payload: Mapping[str, Any],
    *,
    mailbox: str,
) -> Mapping[str, Any]:
    """Convert Gmail message metadata into Clarity email payload shape."""

    headers = _gmail_headers(payload)
    label_ids = _string_tuple(payload.get("labelIds", ()))
    return {
        "message_id": _required_mapping_text(payload, "id"),
        "mailbox": mailbox,
        "subject": _first_header(headers, "subject") or "(no subject)",
        "sender": _first_header(headers, "from"),
        "received_at": _first_header(headers, "date"),
        "preview": _optional_text(payload.get("snippet")),
        "categories": label_ids,
    }


def _google_access_token(
    credentials: GoogleCredentials,
    *,
    token_transport: GoogleTokenTransport | None,
    use_bearer_auth: bool,
) -> str:
    if use_bearer_auth:
        return _required_text(credentials.access_token, "access_token")
    provider = GoogleRefreshTokenProvider(
        credentials=credentials,
        transport=token_transport or UrllibGoogleTokenTransport(),
    )
    return provider.access_token()


def _gmail_headers(payload: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    raw_payload = payload.get("payload", {})
    if not isinstance(raw_payload, Mapping):
        raise GoogleGmailClientError("Gmail payload must be an object.")
    raw_headers = raw_payload.get("headers", [])
    if not isinstance(raw_headers, list):
        raise GoogleGmailClientError("Gmail payload headers must be a list.")

    headers: list[tuple[str, str]] = []
    for index, header in enumerate(raw_headers, 1):
        if not isinstance(header, Mapping):
            raise GoogleGmailClientError(
                f"Gmail header entry must be an object: {index}"
            )
        name = header.get("name")
        value = header.get("value")
        if not isinstance(name, str) or not name.strip():
            raise GoogleGmailClientError(f"Gmail header name missing: {index}")
        if not isinstance(value, str):
            raise GoogleGmailClientError(f"Gmail header value missing: {index}")
        headers.append((name.strip().lower(), value))
    return tuple(headers)


def _first_header(headers: tuple[tuple[str, str], ...], name: str) -> str | None:
    clean_name = name.lower()
    for header_name, value in headers:
        if header_name == clean_name:
            return value
    return None


def _required_mapping_text(payload: Mapping[str, Any], key: str) -> str:
    return _required_text(payload.get(key), key)


def _required_text(value: Any, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EmailClientError(f"Gmail value is required: {key}")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    stripped = value.strip()
    return stripped or None


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise GoogleGmailClientError("Gmail labelIds must be a list.")
    if any(not isinstance(item, str) for item in value):
        raise GoogleGmailClientError("Gmail labelIds must contain only strings.")
    return tuple(value)
