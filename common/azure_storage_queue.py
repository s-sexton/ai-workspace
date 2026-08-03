"""Azure Storage Queue transport for Teams relay messages."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen
from uuid import uuid4
from xml.etree import ElementTree

from common.teams_relay import TeamsQueueMessage, TeamsRelayError, TeamsRelayQueue


class AzureQueueError(RuntimeError):
    """Raised when Azure Storage Queue operations fail."""


class AzureQueueHttpTransport(Protocol):
    """Minimal HTTP transport used by Azure Storage Queue client."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes | None = None,
    ) -> AzureQueueHttpResponse:
        """Send an HTTP request."""


@dataclass(frozen=True)
class AzureQueueHttpResponse:
    """Small HTTP response for Azure Queue operations."""

    status_code: int
    body: bytes = field(default=b"", repr=False)


@dataclass(frozen=True)
class UrllibAzureQueueHttpTransport:
    """Azure Queue HTTP transport backed by Python's standard library."""

    timeout_seconds: float = 30.0

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes | None = None,
    ) -> AzureQueueHttpResponse:
        """Send an HTTP request to Azure Queue Storage."""

        request = Request(url, data=body, headers=dict(headers), method=method)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return AzureQueueHttpResponse(
                    status_code=int(response.status),
                    body=response.read(),
                )
        except HTTPError as exc:
            return AzureQueueHttpResponse(status_code=int(exc.code), body=exc.read())
        except URLError as exc:
            raise AzureQueueError("Azure Queue request failed.") from exc


@dataclass(frozen=True)
class AzureStorageTeamsRelayQueue(TeamsRelayQueue):
    """Teams relay queue backed by Azure Storage Queue SAS URLs."""

    inbound_queue_url: str
    deadletter_queue_url: str
    transport: AzureQueueHttpTransport = field(
        default_factory=UrllibAzureQueueHttpTransport,
        repr=False,
    )
    visibility_timeout_seconds: int = 60

    def enqueue(self, payload: Mapping[str, Any]) -> TeamsQueueMessage:
        """Add a message to the inbound queue."""

        return self._enqueue_to(self.inbound_queue_url, payload)

    def receive(self, *, limit: int = 1) -> tuple[TeamsQueueMessage, ...]:
        """Receive visible messages from the inbound queue."""

        if limit < 1:
            raise TeamsRelayError("limit must be positive.")
        response = self.transport.request(
            "GET",
            _with_query(
                _append_path(self.inbound_queue_url, "messages"),
                {
                    "numofmessages": str(limit),
                    "visibilitytimeout": str(self.visibility_timeout_seconds),
                },
            ),
            headers=_headers(),
        )
        if response.status_code != 200:
            raise AzureQueueError(
                f"Azure Queue receive failed with status {response.status_code}."
            )
        return _parse_received_messages(response.body)

    def complete(self, queue_message_id: str) -> None:
        """Delete a processed message from the inbound queue."""

        message_id, pop_receipt = _split_queue_message_id(queue_message_id)
        encoded_message_id = quote(message_id, safe="")
        response = self.transport.request(
            "DELETE",
            _with_query(
                _append_path(self.inbound_queue_url, f"messages/{encoded_message_id}"),
                {"popreceipt": pop_receipt},
            ),
            headers=_headers(),
        )
        if response.status_code not in (202, 204):
            raise AzureQueueError(
                f"Azure Queue delete failed with status {response.status_code}."
            )

    def dead_letter(self, queue_message_id: str, *, reason: str) -> None:
        """Copy a failed message to dead-letter queue and complete it."""

        payload = {
            "schemaVersion": 1,
            "source": "teams-relay-deadletter",
            "deadletterId": uuid4().hex,
            "queueMessageId": queue_message_id,
            "reason": reason,
        }
        self._enqueue_to(self.deadletter_queue_url, payload)
        self.complete(queue_message_id)

    def _enqueue_to(
        self,
        queue_url: str,
        payload: Mapping[str, Any],
    ) -> TeamsQueueMessage:
        body = _queue_message_body(payload)
        response = self.transport.request(
            "POST",
            _append_path(queue_url, "messages"),
            headers={**_headers(), "Content-Type": "application/xml"},
            body=body,
        )
        if response.status_code not in (201, 202):
            raise AzureQueueError(
                f"Azure Queue enqueue failed with status {response.status_code}."
            )
        return TeamsQueueMessage(
            queue_message_id="queued",
            payload=dict(payload),
            dequeue_count=0,
        )


def _queue_message_body(payload: Mapping[str, Any]) -> bytes:
    raw_json = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    encoded = base64.b64encode(raw_json).decode("ascii")
    return (
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
        f"<QueueMessage><MessageText>{encoded}</MessageText></QueueMessage>"
    ).encode("utf-8")


def _parse_received_messages(body: bytes) -> tuple[TeamsQueueMessage, ...]:
    if not body.strip():
        return ()
    root = ElementTree.fromstring(body)
    messages: list[TeamsQueueMessage] = []
    for raw_message in root.findall("QueueMessage"):
        message_id = _xml_text(raw_message, "MessageId")
        pop_receipt = _xml_text(raw_message, "PopReceipt")
        message_text = _xml_text(raw_message, "MessageText")
        dequeue_count = _optional_xml_int(raw_message, "DequeueCount") or 1
        payload = _decode_message_payload(message_text)
        if not isinstance(payload, Mapping):
            raise AzureQueueError("Azure Queue message payload must be a JSON object.")
        messages.append(
            TeamsQueueMessage(
                queue_message_id=f"{message_id}|{pop_receipt}",
                payload=dict(payload),
                dequeue_count=dequeue_count,
            )
        )
    return tuple(messages)


def _split_queue_message_id(queue_message_id: str) -> tuple[str, str]:
    parts = queue_message_id.split("|", 1)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise AzureQueueError("Azure Queue message id must include pop receipt.")
    return parts[0], parts[1]


def _decode_message_payload(message_text: str) -> Any:
    try:
        return json.loads(base64.b64decode(message_text).decode("utf-8"))
    except (ValueError, TypeError, json.JSONDecodeError):
        try:
            return json.loads(message_text)
        except json.JSONDecodeError as exc:
            raise AzureQueueError("Azure Queue message payload must be JSON.") from exc


def _xml_text(raw_message: ElementTree.Element, tag: str) -> str:
    value = raw_message.findtext(tag)
    if value is None or not value.strip():
        raise AzureQueueError(f"Azure Queue message missing {tag}.")
    return value.strip()


def _optional_xml_int(raw_message: ElementTree.Element, tag: str) -> int | None:
    value = raw_message.findtext(tag)
    if value is None or not value.strip():
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise AzureQueueError(f"Azure Queue message {tag} must be an integer.") from exc


def _headers() -> dict[str, str]:
    return {
        "Accept": "application/xml",
        "x-ms-version": "2023-11-03",
    }


def _append_path(url: str, path: str) -> str:
    parsed = urlparse(_required_https_url(url))
    base_path = parsed.path.rstrip("/")
    clean_path = path.strip("/")
    return urlunparse(parsed._replace(path=f"{base_path}/{clean_path}"))


def _with_query(url: str, values: Mapping[str, str]) -> str:
    parsed = urlparse(_required_https_url(url))
    extra_query = urlencode(values)
    query = parsed.query
    combined_query = f"{extra_query}&{query}" if query else extra_query
    return urlunparse(parsed._replace(query=combined_query))


def _required_https_url(url: str) -> str:
    clean_url = url.strip()
    if not clean_url.startswith("https://"):
        raise AzureQueueError("Azure Queue URL must start with https://.")
    return clean_url
