from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import parse_qs, urlparse

import pytest

from common.configuration import GoogleCredentials
from common.google_gmail import (
    GoogleGmailClientError,
    GoogleGmailMoveTransport,
    GoogleGmailReadTransport,
    build_google_gmail_move_transport,
    build_google_gmail_read_transport,
    gmail_message_to_email_payload,
)


@dataclass
class FakeGoogleResponse:
    status_code: int
    payload: Mapping[str, Any]

    def json(self) -> Mapping[str, Any]:
        return self.payload


class FakeGoogleTransport:
    def __init__(self, responses: Mapping[str, FakeGoogleResponse]):
        self.responses = responses
        self.get_calls: list[tuple[str, Mapping[str, str]]] = []
        self.post_calls: list[tuple[str, Mapping[str, str], Mapping[str, Any]]] = []

    def get(self, url: str, headers: Mapping[str, str]) -> FakeGoogleResponse:
        self.get_calls.append((url, headers))
        return self.responses[url]

    def post(
        self,
        url: str,
        headers: Mapping[str, str],
        body: Mapping[str, Any],
    ) -> FakeGoogleResponse:
        self.post_calls.append((url, headers, body))
        return self.responses[url]


class FakeGoogleTokenTransport:
    def __init__(self, response: FakeGoogleResponse):
        self.response = response
        self.calls: list[tuple[str, Mapping[str, str], Mapping[str, str]]] = []

    def post_form(
        self,
        url: str,
        headers: Mapping[str, str],
        form: Mapping[str, str],
    ) -> FakeGoogleResponse:
        self.calls.append((url, headers, form))
        return self.response


def test_build_google_gmail_read_transport_can_use_direct_access_token():
    gmail_transport = FakeGoogleTransport({})
    token_transport = FakeGoogleTokenTransport(
        FakeGoogleResponse(200, {"access_token": "should-not-be-used"})
    )

    transport = build_google_gmail_read_transport(
        GoogleCredentials(access_token="direct-token"),
        gmail_transport=gmail_transport,
        token_transport=token_transport,
        use_bearer_auth=True,
    )

    assert "direct-token" not in repr(transport)
    assert token_transport.calls == []


def test_build_google_gmail_move_transport_can_refresh_token():
    gmail_transport = FakeGoogleTransport({})
    token_transport = FakeGoogleTokenTransport(
        FakeGoogleResponse(200, {"access_token": "acquired-token"})
    )

    transport = build_google_gmail_move_transport(
        GoogleCredentials(
            client_id="client-id",
            client_secret="super-secret",
            refresh_token="refresh-secret",
        ),
        gmail_transport=gmail_transport,
        token_transport=token_transport,
    )

    assert "super-secret" not in repr(transport)
    assert len(token_transport.calls) == 1


def test_google_gmail_read_transport_lists_inbox_metadata():
    base_url = "https://gmail.example/gmail/v1"
    list_url = (
        "https://gmail.example/gmail/v1/users/sesexton%40gmail.com/messages?"
        "maxResults=2&labelIds=INBOX&includeSpamTrash=false"
    )
    metadata_url = (
        "https://gmail.example/gmail/v1/users/sesexton%40gmail.com/messages/msg-1?"
        "format=metadata&metadataHeaders=From&metadataHeaders=Subject&"
        "metadataHeaders=Date&fields=id%2CthreadId%2ClabelIds%2Csnippet%2Cpayload%2Fheaders"
    )
    transport = FakeGoogleTransport(
        {
            list_url: FakeGoogleResponse(200, {"messages": [{"id": "msg-1"}]}),
            metadata_url: FakeGoogleResponse(
                200,
                {
                    "id": "msg-1",
                    "labelIds": ["INBOX", "CATEGORY_PRIMARY"],
                    "snippet": "Please review this.",
                    "payload": {
                        "headers": [
                            {"name": "From", "value": "Scott <sesexton@gmail.com>"},
                            {"name": "Subject", "value": "Review this"},
                            {"name": "Date", "value": "Fri, 10 Jul 2026 09:00:00 -0500"},
                        ]
                    },
                },
            ),
        }
    )
    client = GoogleGmailReadTransport(
        access_token="access-token",
        transport=transport,
        base_url=base_url,
    )

    messages = client.list_messages("sesexton@gmail.com", 2)

    assert len(messages) == 1
    message = messages[0]
    assert message["message_id"] == "msg-1"
    assert message["mailbox"] == "sesexton@gmail.com"
    assert message["subject"] == "Review this"
    assert message["sender"] == "Scott <sesexton@gmail.com>"
    assert message["categories"] == ("INBOX", "CATEGORY_PRIMARY")
    assert transport.get_calls[0][1]["Authorization"] == "Bearer access-token"
    parsed = urlparse(transport.get_calls[0][0])
    assert parse_qs(parsed.query)["labelIds"] == ["INBOX"]


def test_google_gmail_move_transport_trashes_deleted_items():
    trash_url = (
        "https://gmail.example/gmail/v1/users/sesexton%40gmail.com/"
        "messages/msg-1/trash"
    )
    transport = FakeGoogleTransport(
        {trash_url: FakeGoogleResponse(200, {"id": "msg-1"})}
    )
    client = GoogleGmailMoveTransport(
        access_token="access-token",
        transport=transport,
        base_url="https://gmail.example/gmail/v1",
    )

    client.move_message(
        mailbox="sesexton@gmail.com",
        message_id="msg-1",
        target_folder="Deleted Items",
    )

    assert transport.get_calls == []
    assert len(transport.post_calls) == 1
    assert transport.post_calls[0][2] == {}


def test_google_gmail_move_transport_creates_label_and_archives():
    labels_url = "https://gmail.example/gmail/v1/users/sesexton%40gmail.com/labels"
    modify_url = (
        "https://gmail.example/gmail/v1/users/sesexton%40gmail.com/"
        "messages/msg-1/modify"
    )
    transport = FakeGoogleTransport(
        {
            labels_url: FakeGoogleResponse(200, {"labels": []}),
            modify_url: FakeGoogleResponse(200, {"id": "msg-1"}),
        }
    )
    transport.responses[labels_url] = FakeGoogleResponse(200, {"labels": []})
    transport.responses[labels_url + "#create"] = FakeGoogleResponse(
        200,
        {"id": "Label_123", "name": "Clarity/Noise"},
    )

    def fake_post(url, headers, body):
        transport.post_calls.append((url, headers, body))
        if url == labels_url:
            return FakeGoogleResponse(200, {"id": "Label_123"})
        return transport.responses[url]

    transport.post = fake_post
    client = GoogleGmailMoveTransport(
        access_token="access-token",
        transport=transport,
        base_url="https://gmail.example/gmail/v1",
    )

    client.move_message(
        mailbox="sesexton@gmail.com",
        message_id="msg-1",
        target_folder="Clarity/Noise",
    )

    assert len(transport.get_calls) == 1
    assert len(transport.post_calls) == 2
    assert transport.post_calls[0][2]["name"] == "Clarity/Noise"
    assert transport.post_calls[1][2] == {
        "removeLabelIds": ["INBOX"],
        "addLabelIds": ["Label_123"],
    }


def test_gmail_message_to_email_payload_requires_headers_list():
    with pytest.raises(GoogleGmailClientError):
        gmail_message_to_email_payload(
            {"id": "msg-1", "payload": {"headers": {}}},
            mailbox="sesexton@gmail.com",
        )
