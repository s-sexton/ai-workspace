from __future__ import annotations

from typing import Any, Mapping

import pytest

from common.teams import (
    TeamsWebhookError,
    TeamsWebhookResponse,
    post_lightweight_card_to_teams,
    post_text_to_teams,
)


def test_post_text_to_teams_sends_lightweight_text_payload():
    transport = RecordingTeamsTransport(status_code=202)

    response = post_text_to_teams(
        webhook_url="https://example.webhook.office.com/test",
        text="Hello Teams",
        transport=transport,
    )

    assert response.status_code == 202
    assert transport.calls == [
        (
            "https://example.webhook.office.com/test",
            {"text": "Hello Teams"},
            {"Content-Type": "application/json"},
        )
    ]


def test_post_lightweight_card_to_teams_sends_minimal_adaptive_card():
    transport = RecordingTeamsTransport(status_code=202)

    response = post_lightweight_card_to_teams(
        webhook_url="https://example.webhook.office.com/test",
        text="Hello Teams",
        transport=transport,
    )

    assert response.status_code == 202
    _, payload, headers = transport.calls[0]
    assert headers == {"Content-Type": "application/json"}
    assert payload["type"] == "message"
    attachment = payload["attachments"][0]
    assert attachment["contentType"] == "application/vnd.microsoft.card.adaptive"
    assert attachment["content"]["body"][0]["text"] == "Hello Teams"
    assert attachment["content"]["msteams"]["width"] == "Full"


def test_post_text_to_teams_requires_https_webhook_url():
    with pytest.raises(TeamsWebhookError):
        post_text_to_teams(webhook_url="http://example.invalid", text="Hello")


def test_post_text_to_teams_raises_for_non_success_status():
    transport = RecordingTeamsTransport(status_code=400)

    with pytest.raises(TeamsWebhookError) as exc_info:
        post_text_to_teams(
            webhook_url="https://example.webhook.office.com/test",
            text="Hello",
            transport=transport,
        )

    assert "400" in str(exc_info.value)


class RecordingTeamsTransport:
    def __init__(self, *, status_code: int):
        self.status_code = status_code
        self.calls: list[tuple[str, Mapping[str, Any], Mapping[str, str]]] = []

    def post(
        self,
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
    ) -> TeamsWebhookResponse:
        self.calls.append((url, payload, headers))
        return TeamsWebhookResponse(status_code=self.status_code)
