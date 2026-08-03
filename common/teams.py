"""Small Microsoft Teams webhook notification boundary."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class TeamsWebhookError(RuntimeError):
    """Raised when a Teams webhook notification cannot be sent."""


class TeamsWebhookTransport(Protocol):
    """Minimal HTTP transport used by the Teams webhook client."""

    def post(
        self,
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
    ) -> TeamsWebhookResponse:
        """Send a webhook POST request and return a response."""


@dataclass(frozen=True)
class TeamsWebhookResponse:
    """Safe Teams webhook response details."""

    status_code: int
    body: str = field(default="", repr=False)


@dataclass(frozen=True)
class UrllibTeamsWebhookTransport:
    """Teams webhook transport backed by Python's standard library."""

    timeout_seconds: float = 30.0

    def post(
        self,
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
    ) -> TeamsWebhookResponse:
        """Send a Teams webhook POST request."""

        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=dict(headers),
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return TeamsWebhookResponse(
                    status_code=int(response.status),
                    body=response.read().decode("utf-8", errors="replace"),
                )
        except HTTPError as exc:
            return TeamsWebhookResponse(
                status_code=int(exc.code),
                body=exc.read().decode("utf-8", errors="replace"),
            )
        except URLError as exc:
            raise TeamsWebhookError("Teams webhook request failed.") from exc


def post_text_to_teams(
    *,
    webhook_url: str,
    text: str,
    transport: TeamsWebhookTransport | None = None,
) -> TeamsWebhookResponse:
    """Post a lightweight text notification to a Teams incoming webhook."""

    clean_url = _validated_webhook_url(webhook_url)
    clean_text = text.strip()
    if not clean_text:
        raise TeamsWebhookError("Teams message text is required.")

    response = (transport or UrllibTeamsWebhookTransport()).post(
        clean_url,
        payload={"text": clean_text},
        headers={"Content-Type": "application/json"},
    )
    if response.status_code < 200 or response.status_code >= 300:
        raise TeamsWebhookError(
            f"Teams webhook POST failed with status {response.status_code}."
        )
    return response


def post_lightweight_card_to_teams(
    *,
    webhook_url: str,
    text: str,
    transport: TeamsWebhookTransport | None = None,
) -> TeamsWebhookResponse:
    """Post a minimal Adaptive Card for Teams Workflows webhook rendering."""

    clean_url = _validated_webhook_url(webhook_url)
    clean_text = text.strip()
    if not clean_text:
        raise TeamsWebhookError("Teams message text is required.")

    response = (transport or UrllibTeamsWebhookTransport()).post(
        clean_url,
        payload=_lightweight_card_payload(clean_text),
        headers={"Content-Type": "application/json"},
    )
    if response.status_code < 200 or response.status_code >= 300:
        raise TeamsWebhookError(
            f"Teams webhook POST failed with status {response.status_code}."
        )
    return response


def _lightweight_card_payload(text: str) -> Mapping[str, Any]:
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "msteams": {
                        "width": "Full",
                    },
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": text,
                            "wrap": True,
                        }
                    ],
                },
            }
        ],
    }


def _validated_webhook_url(webhook_url: str) -> str:
    clean_url = webhook_url.strip()
    if not clean_url:
        raise TeamsWebhookError("Teams webhook URL is required.")
    if not clean_url.startswith("https://"):
        raise TeamsWebhookError("Teams webhook URL must start with https://.")
    return clean_url
