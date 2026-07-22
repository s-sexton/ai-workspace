from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import parse_qs, urlparse

import pytest

from common.configuration import GraphCredentials
from common.email import EmailClientError
from common.graph_email import (
    GraphClientError,
    GraphClientCredentialsTokenProvider,
    GraphEmailFolderTransport,
    GraphEmailReadTransport,
    GraphEmailMoveTransport,
    GraphEmailRuleTransport,
    GraphEmailSendTransport,
    UrllibGraphResponse,
    build_graph_email_folder_transport,
    build_graph_email_read_transport,
    build_graph_email_move_transport,
    build_graph_email_rule_transport,
    build_graph_email_send_transport,
)


@dataclass
class FakeGraphResponse:
    status_code: int
    payload: Mapping[str, Any]

    def json(self) -> Mapping[str, Any]:
        return self.payload


class FakeGraphTransport:
    def __init__(self, responses: Mapping[str, FakeGraphResponse]):
        self.responses = responses
        self.get_calls: list[tuple[str, Mapping[str, str]]] = []
        self.post_calls: list[tuple[str, Mapping[str, str], Mapping[str, Any]]] = []

    def get(self, url: str, headers: Mapping[str, str]) -> FakeGraphResponse:
        self.get_calls.append((url, headers))
        return self.responses[url]

    def post(
        self,
        url: str,
        headers: Mapping[str, str],
        body: Mapping[str, Any],
    ) -> FakeGraphResponse:
        self.post_calls.append((url, headers, body))
        return self.responses[url]


class FakeGraphTokenTransport:
    def __init__(self, response: FakeGraphResponse):
        self.response = response
        self.calls: list[tuple[str, Mapping[str, str], Mapping[str, str]]] = []

    def post_form(
        self,
        url: str,
        headers: Mapping[str, str],
        form: Mapping[str, str],
    ) -> FakeGraphResponse:
        self.calls.append((url, headers, form))
        return self.response


def test_graph_client_credentials_token_provider_posts_expected_form():
    transport = FakeGraphTokenTransport(
        FakeGraphResponse(200, {"access_token": "access-token"})
    )
    provider = GraphClientCredentialsTokenProvider(
        credentials=GraphCredentials(
            tenant_id="tenant id",
            client_id="client-id",
            client_secret="super-secret",
        ),
        transport=transport,
        authority_base_url="https://login.example",
    )

    token = provider.access_token()

    assert token == "access-token"
    assert len(transport.calls) == 1
    url, headers, form = transport.calls[0]
    assert url == "https://login.example/tenant%20id/oauth2/v2.0/token"
    assert headers["Accept"] == "application/json"
    assert form == {
        "client_id": "client-id",
        "client_secret": "super-secret",
        "grant_type": "client_credentials",
        "scope": "https://graph.microsoft.com/.default",
    }
    assert "super-secret" not in repr(provider)


def test_graph_client_credentials_token_provider_rejects_error_status():
    provider = GraphClientCredentialsTokenProvider(
        credentials=GraphCredentials(
            tenant_id="tenant",
            client_id="client-id",
            client_secret="super-secret",
        ),
        transport=FakeGraphTokenTransport(FakeGraphResponse(401, {})),
    )

    with pytest.raises(GraphClientError) as exc_info:
        provider.access_token()

    assert "401" in str(exc_info.value)
    assert "super-secret" not in str(exc_info.value)


def test_graph_client_credentials_token_provider_requires_access_token_response():
    provider = GraphClientCredentialsTokenProvider(
        credentials=GraphCredentials(
            tenant_id="tenant",
            client_id="client-id",
            client_secret="super-secret",
        ),
        transport=FakeGraphTokenTransport(FakeGraphResponse(200, {})),
    )

    with pytest.raises(GraphClientError):
        provider.access_token()


def test_build_graph_email_move_transport_can_use_direct_access_token():
    graph_transport = FakeGraphTransport({})
    token_transport = FakeGraphTokenTransport(
        FakeGraphResponse(200, {"access_token": "should-not-be-used"})
    )

    transport = build_graph_email_move_transport(
        GraphCredentials(access_token="direct-token"),
        graph_transport=graph_transport,
        token_transport=token_transport,
        use_bearer_auth=True,
    )

    assert isinstance(transport, GraphEmailMoveTransport)
    assert "direct-token" not in repr(transport)
    assert token_transport.calls == []


def test_build_graph_email_move_transport_can_acquire_client_credentials_token():
    graph_transport = FakeGraphTransport({})
    token_transport = FakeGraphTokenTransport(
        FakeGraphResponse(200, {"access_token": "acquired-token"})
    )

    transport = build_graph_email_move_transport(
        GraphCredentials(
            tenant_id="tenant",
            client_id="client-id",
            client_secret="super-secret",
        ),
        graph_transport=graph_transport,
        token_transport=token_transport,
    )

    assert isinstance(transport, GraphEmailMoveTransport)
    assert len(token_transport.calls) == 1
    _, _, form = token_transport.calls[0]
    assert form["grant_type"] == "client_credentials"
    assert form["scope"] == "https://graph.microsoft.com/.default"
    assert "super-secret" not in repr(transport)


def test_build_graph_email_move_transport_requires_direct_access_token():
    with pytest.raises(EmailClientError):
        build_graph_email_move_transport(
            GraphCredentials(),
            graph_transport=FakeGraphTransport({}),
            use_bearer_auth=True,
        )


def test_build_graph_email_read_transport_can_use_direct_access_token():
    graph_transport = FakeGraphTransport({})
    token_transport = FakeGraphTokenTransport(
        FakeGraphResponse(200, {"access_token": "should-not-be-used"})
    )

    transport = build_graph_email_read_transport(
        GraphCredentials(access_token="direct-token"),
        graph_transport=graph_transport,
        token_transport=token_transport,
        use_bearer_auth=True,
    )

    assert isinstance(transport, GraphEmailReadTransport)
    assert "direct-token" not in repr(transport)
    assert token_transport.calls == []


def test_build_graph_email_read_transport_can_acquire_client_credentials_token():
    graph_transport = FakeGraphTransport({})
    token_transport = FakeGraphTokenTransport(
        FakeGraphResponse(200, {"access_token": "acquired-token"})
    )

    transport = build_graph_email_read_transport(
        GraphCredentials(
            tenant_id="tenant",
            client_id="client-id",
            client_secret="super-secret",
        ),
        graph_transport=graph_transport,
        token_transport=token_transport,
    )

    assert isinstance(transport, GraphEmailReadTransport)
    assert len(token_transport.calls) == 1
    assert "super-secret" not in repr(transport)


def test_build_graph_email_folder_transport_can_use_direct_access_token():
    graph_transport = FakeGraphTransport({})
    token_transport = FakeGraphTokenTransport(
        FakeGraphResponse(200, {"access_token": "should-not-be-used"})
    )

    transport = build_graph_email_folder_transport(
        GraphCredentials(access_token="direct-token"),
        graph_transport=graph_transport,
        token_transport=token_transport,
        use_bearer_auth=True,
    )

    assert isinstance(transport, GraphEmailFolderTransport)
    assert "direct-token" not in repr(transport)
    assert token_transport.calls == []


def test_build_graph_email_folder_transport_can_acquire_client_credentials_token():
    graph_transport = FakeGraphTransport({})
    token_transport = FakeGraphTokenTransport(
        FakeGraphResponse(200, {"access_token": "acquired-token"})
    )

    transport = build_graph_email_folder_transport(
        GraphCredentials(
            tenant_id="tenant",
            client_id="client-id",
            client_secret="super-secret",
        ),
        graph_transport=graph_transport,
        token_transport=token_transport,
    )

    assert isinstance(transport, GraphEmailFolderTransport)
    assert len(token_transport.calls) == 1
    assert "super-secret" not in repr(transport)


def test_build_graph_email_rule_transport_can_use_direct_access_token():
    graph_transport = FakeGraphTransport({})
    token_transport = FakeGraphTokenTransport(
        FakeGraphResponse(200, {"access_token": "should-not-be-used"})
    )

    transport = build_graph_email_rule_transport(
        GraphCredentials(access_token="direct-token"),
        graph_transport=graph_transport,
        token_transport=token_transport,
        use_bearer_auth=True,
    )

    assert isinstance(transport, GraphEmailRuleTransport)
    assert token_transport.calls == []


def test_build_graph_email_rule_transport_can_acquire_client_credentials_token():
    graph_transport = FakeGraphTransport({})
    token_transport = FakeGraphTokenTransport(
        FakeGraphResponse(200, {"access_token": "acquired-token"})
    )

    transport = build_graph_email_rule_transport(
        GraphCredentials(
            tenant_id="tenant-id",
            client_id="client-id",
            client_secret="client-secret",
        ),
        graph_transport=graph_transport,
        token_transport=token_transport,
    )

    assert isinstance(transport, GraphEmailRuleTransport)
    assert len(token_transport.calls) == 1
    assert "client-secret" not in repr(transport)


def test_build_graph_email_send_transport_can_acquire_client_credentials_token():
    graph_transport = FakeGraphTransport({})
    token_transport = FakeGraphTokenTransport(
        FakeGraphResponse(200, {"access_token": "acquired-token"})
    )

    transport = build_graph_email_send_transport(
        GraphCredentials(
            tenant_id="tenant-id",
            client_id="client-id",
            client_secret="client-secret",
        ),
        graph_transport=graph_transport,
        token_transport=token_transport,
    )

    assert isinstance(transport, GraphEmailSendTransport)
    assert len(token_transport.calls) == 1
    assert "client-secret" not in repr(transport)


def test_graph_email_send_transport_sends_plain_text_mail():
    send_url = "https://graph.example/v1.0/users/clarity%40example.invalid/sendMail"
    transport = FakeGraphTransport({send_url: FakeGraphResponse(202, {})})
    client = GraphEmailSendTransport(
        access_token="access-token",
        transport=transport,
        base_url="https://graph.example/v1.0",
    )

    client.send_mail(
        sender="clarity@example.invalid",
        recipients=("scott@example.invalid",),
        subject="Clarity Day in a Glance - 2026-07-16",
        body_text="# Clarity Daily Brief\n",
    )

    assert len(transport.post_calls) == 1
    url, headers, body = transport.post_calls[0]
    assert url == send_url
    assert headers["Authorization"] == "Bearer access-token"
    assert body["message"]["subject"] == "Clarity Day in a Glance - 2026-07-16"
    assert body["message"]["body"] == {
        "contentType": "Text",
        "content": "# Clarity Daily Brief\n",
    }
    assert body["message"]["toRecipients"] == [
        {"emailAddress": {"address": "scott@example.invalid"}}
    ]
    assert body["saveToSentItems"] is True


def test_graph_email_send_transport_sends_html_mail_when_supplied():
    send_url = "https://graph.example/v1.0/users/clarity%40example.invalid/sendMail"
    transport = FakeGraphTransport({send_url: FakeGraphResponse(202, {})})
    client = GraphEmailSendTransport(
        access_token="access-token",
        transport=transport,
        base_url="https://graph.example/v1.0",
    )

    client.send_mail(
        sender="clarity@example.invalid",
        recipients=("scott@example.invalid",),
        subject="Clarity Day in a Glance - 2026-07-16",
        body_text="# Clarity Daily Brief\n",
        body_html="<h1>Clarity Daily Brief</h1>",
    )

    _, _, body = transport.post_calls[0]
    assert body["message"]["body"] == {
        "contentType": "HTML",
        "content": "<h1>Clarity Daily Brief</h1>",
    }


def test_graph_email_send_transport_reports_graph_error_detail():
    send_url = "https://graph.example/v1.0/users/clarity%40example.invalid/sendMail"
    transport = FakeGraphTransport(
        {
            send_url: FakeGraphResponse(
                403,
                {
                    "error": {
                        "code": "ErrorAccessDenied",
                        "message": "Access is denied. Check credentials.",
                    }
                },
            )
        }
    )
    client = GraphEmailSendTransport(
        access_token="access-token",
        transport=transport,
        base_url="https://graph.example/v1.0",
    )

    with pytest.raises(GraphClientError) as exc_info:
        client.send_mail(
            sender="clarity@example.invalid",
            recipients=("scott@example.invalid",),
            subject="Clarity Day in a Glance - 2026-07-16",
            body_text="# Clarity Daily Brief\n",
        )

    error = str(exc_info.value)
    assert "403" in error
    assert "ErrorAccessDenied" in error
    assert "Access is denied" in error
    assert "access-token" not in error


def test_graph_email_folder_transport_creates_missing_folder_path():
    base_url = "https://graph.example/v1.0"
    root_list_url = (
        "https://graph.example/v1.0/users/clarity%40sendthisfile.ai/"
        "mailFolders?%24top=100"
    )
    root_create_url = (
        "https://graph.example/v1.0/users/clarity%40sendthisfile.ai/mailFolders"
    )
    child_list_url = (
        "https://graph.example/v1.0/users/clarity%40sendthisfile.ai/"
        "mailFolders/folder-clarity/childFolders?%24top=100"
    )
    child_create_url = (
        "https://graph.example/v1.0/users/clarity%40sendthisfile.ai/"
        "mailFolders/folder-clarity/childFolders"
    )
    transport = FakeGraphTransport(
        {
            root_list_url: FakeGraphResponse(200, {"value": []}),
            root_create_url: FakeGraphResponse(
                201,
                {"id": "folder-clarity", "displayName": "Clarity"},
            ),
            child_list_url: FakeGraphResponse(200, {"value": []}),
            child_create_url: FakeGraphResponse(
                201,
                {"id": "folder-review", "displayName": "Review"},
            ),
        }
    )
    client = GraphEmailFolderTransport(
        access_token="access-token",
        transport=transport,
        base_url=base_url,
    )

    result = client.ensure_folder_path(
        mailbox="clarity@sendthisfile.ai",
        folder_path="Clarity/Review",
    )

    assert result.mailbox == "clarity@sendthisfile.ai"
    assert result.folder_path == "Clarity/Review"
    assert result.folder_id == "folder-review"
    assert result.created
    assert len(transport.post_calls) == 2
    assert transport.post_calls[0][2] == {"displayName": "Clarity"}
    assert transport.post_calls[1][2] == {"displayName": "Review"}


def test_graph_email_folder_transport_leaves_existing_folder_path_unchanged():
    base_url = "https://graph.example/v1.0"
    root_list_url = (
        "https://graph.example/v1.0/users/clarity%40sendthisfile.ai/"
        "mailFolders?%24top=100"
    )
    child_list_url = (
        "https://graph.example/v1.0/users/clarity%40sendthisfile.ai/"
        "mailFolders/folder-clarity/childFolders?%24top=100"
    )
    transport = FakeGraphTransport(
        {
            root_list_url: FakeGraphResponse(
                200,
                {"value": [{"id": "folder-clarity", "displayName": "Clarity"}]},
            ),
            child_list_url: FakeGraphResponse(
                200,
                {"value": [{"id": "folder-noise", "displayName": "Noise"}]},
            ),
        }
    )
    client = GraphEmailFolderTransport(
        access_token="access-token",
        transport=transport,
        base_url=base_url,
    )

    result = client.ensure_folder_path(
        mailbox="clarity@sendthisfile.ai",
        folder_path="Clarity/Noise",
    )

    assert result.folder_id == "folder-noise"
    assert not result.created
    assert transport.post_calls == []


def test_graph_email_folder_transport_checks_folder_path_existence():
    base_url = "https://graph.example/v1.0"
    root_list_url = (
        "https://graph.example/v1.0/users/clarity%40sendthisfile.ai/"
        "mailFolders?%24top=100"
    )
    child_list_url = (
        "https://graph.example/v1.0/users/clarity%40sendthisfile.ai/"
        "mailFolders/folder-clarity/childFolders?%24top=100"
    )
    transport = FakeGraphTransport(
        {
            root_list_url: FakeGraphResponse(
                200,
                {"value": [{"id": "folder-clarity", "displayName": "Clarity"}]},
            ),
            child_list_url: FakeGraphResponse(200, {"value": []}),
        }
    )
    client = GraphEmailFolderTransport(
        access_token="access-token",
        transport=transport,
        base_url=base_url,
    )

    assert not client.folder_path_exists(
        mailbox="clarity@sendthisfile.ai",
        folder_path="Clarity/Review",
    )


def test_graph_email_folder_transport_does_not_create_deleted_items():
    client = GraphEmailFolderTransport(
        access_token="access-token",
        transport=FakeGraphTransport({}),
        base_url="https://graph.example/v1.0",
    )

    result = client.ensure_folder_path(
        mailbox="clarity@sendthisfile.ai",
        folder_path="Deleted Items",
    )

    assert result.folder_id == "deleteditems"
    assert not result.created


def test_graph_email_move_resolves_folder_path_and_moves_message():
    base_url = "https://graph.example/v1.0"
    root_url = (
        "https://graph.example/v1.0/users/scott.sexton%40sendthisfile.com/"
        "mailFolders?%24top=100"
    )
    child_url = (
        "https://graph.example/v1.0/users/scott.sexton%40sendthisfile.com/"
        "mailFolders/folder-clarity/childFolders?%24top=100"
    )
    move_url = (
        "https://graph.example/v1.0/users/scott.sexton%40sendthisfile.com/"
        "messages/graph-message-1/move"
    )
    transport = FakeGraphTransport(
        {
            root_url: FakeGraphResponse(
                200,
                {"value": [{"id": "folder-clarity", "displayName": "Clarity"}]},
            ),
            child_url: FakeGraphResponse(
                200,
                {"value": [{"id": "folder-review", "displayName": "Review"}]},
            ),
            move_url: FakeGraphResponse(201, {"id": "new-message-id"}),
        }
    )
    client = GraphEmailMoveTransport(
        access_token="access-token",
        transport=transport,
        base_url=base_url,
    )

    client.move_message(
        mailbox="scott.sexton@sendthisfile.com",
        message_id="graph-message-1",
        target_folder="Clarity/Review",
    )

    assert len(transport.get_calls) == 2
    assert len(transport.post_calls) == 1
    _, headers, body = transport.post_calls[0]
    assert headers["Authorization"] == "Bearer access-token"
    assert body == {"destinationId": "folder-review"}


def test_graph_email_move_uses_deleted_items_well_known_folder():
    move_url = (
        "https://graph.example/v1.0/users/scott.sexton%40sendthisfile.com/"
        "messages/graph-message-1/move"
    )
    transport = FakeGraphTransport(
        {move_url: FakeGraphResponse(201, {"id": "deleted-message-id"})}
    )
    client = GraphEmailMoveTransport(
        access_token="access-token",
        transport=transport,
        base_url="https://graph.example/v1.0",
    )

    client.move_message(
        mailbox="scott.sexton@sendthisfile.com",
        message_id="graph-message-1",
        target_folder="Deleted Items",
    )

    assert transport.get_calls == []
    _, _, body = transport.post_calls[0]
    assert body == {"destinationId": "deleteditems"}


def test_graph_email_move_uses_mailbox_identity_override():
    move_url = (
        "https://graph.example/v1.0/users/scott.dk%40sendthisfile1.onmicrosoft.com/"
        "messages/graph-message-1/move"
    )
    transport = FakeGraphTransport(
        {move_url: FakeGraphResponse(201, {"id": "moved-message"})}
    )
    client = GraphEmailMoveTransport(
        access_token="access-token",
        transport=transport,
        base_url="https://graph.example/v1.0",
        mailbox_identity_overrides={
            "scott@developkansas.com": "scott.dk@sendthisfile1.onmicrosoft.com",
        },
    )

    client.move_message(
        mailbox="scott@developkansas.com",
        message_id="graph-message-1",
        target_folder="Deleted Items",
    )

    assert transport.post_calls[0][0] == move_url


def test_graph_email_move_url_encodes_mailbox_and_message_id():
    root_url = (
        "https://graph.example/v1.0/users/scott.sexton%40sendthisfile.com/"
        "mailFolders?%24top=100"
    )
    child_url = (
        "https://graph.example/v1.0/users/scott.sexton%40sendthisfile.com/"
        "mailFolders/folder-clarity/childFolders?%24top=100"
    )
    move_url = (
        "https://graph.example/v1.0/users/scott.sexton%40sendthisfile.com/"
        "messages/AAMkADhAAATs28OAAA%3D%2Fpart/move"
    )
    transport = FakeGraphTransport(
        {
            root_url: FakeGraphResponse(
                200,
                {"value": [{"id": "folder-clarity", "displayName": "Clarity"}]},
            ),
            child_url: FakeGraphResponse(
                200,
                {"value": [{"id": "folder-review", "displayName": "Review"}]},
            ),
            move_url: FakeGraphResponse(201, {}),
        }
    )
    client = GraphEmailMoveTransport(
        access_token="access-token",
        transport=transport,
        base_url="https://graph.example/v1.0",
    )

    client.move_message(
        mailbox="scott.sexton@sendthisfile.com",
        message_id="AAMkADhAAATs28OAAA=/part",
        target_folder="Clarity/Review",
    )

    parsed = urlparse(transport.post_calls[0][0])
    assert parsed.path.endswith("/messages/AAMkADhAAATs28OAAA%3D%2Fpart/move")
    assert parse_qs(urlparse(transport.get_calls[0][0]).query) == {"$top": ["100"]}


def test_graph_email_move_creates_missing_folder_path_before_move():
    root_url = (
        "https://graph.example/v1.0/users/scott.sexton%40sendthisfile.com/"
        "mailFolders?%24top=100"
    )
    create_root_url = (
        "https://graph.example/v1.0/users/scott.sexton%40sendthisfile.com/"
        "mailFolders"
    )
    child_url = (
        "https://graph.example/v1.0/users/scott.sexton%40sendthisfile.com/"
        "mailFolders/folder-clarity/childFolders?%24top=100"
    )
    create_child_url = (
        "https://graph.example/v1.0/users/scott.sexton%40sendthisfile.com/"
        "mailFolders/folder-clarity/childFolders"
    )
    move_url = (
        "https://graph.example/v1.0/users/scott.sexton%40sendthisfile.com/"
        "messages/graph-message-1/move"
    )
    transport = FakeGraphTransport(
        {
            root_url: FakeGraphResponse(200, {"value": []}),
            create_root_url: FakeGraphResponse(
                201,
                {"id": "folder-clarity", "displayName": "Clarity"},
            ),
            child_url: FakeGraphResponse(200, {"value": []}),
            create_child_url: FakeGraphResponse(
                201,
                {"id": "folder-review", "displayName": "Review"},
            ),
            move_url: FakeGraphResponse(201, {"id": "moved-message"}),
        }
    )
    client = GraphEmailMoveTransport(
        access_token="access-token",
        transport=transport,
        base_url="https://graph.example/v1.0",
    )

    client.move_message(
        mailbox="scott.sexton@sendthisfile.com",
        message_id="graph-message-1",
        target_folder="Clarity/Review",
    )

    assert len(transport.get_calls) == 2
    assert len(transport.post_calls) == 3
    assert transport.post_calls[0][2] == {"displayName": "Clarity"}
    assert transport.post_calls[1][2] == {"displayName": "Review"}
    assert transport.post_calls[2][2] == {"destinationId": "folder-review"}


def test_graph_email_move_raises_for_non_successful_move_status():
    move_url = (
        "https://graph.example/v1.0/users/scott.sexton%40sendthisfile.com/"
        "messages/graph-message-1/move"
    )
    transport = FakeGraphTransport({move_url: FakeGraphResponse(403, {})})
    client = GraphEmailMoveTransport(
        access_token="access-token",
        transport=transport,
        base_url="https://graph.example/v1.0",
    )

    with pytest.raises(GraphClientError) as exc_info:
        client.move_message(
            mailbox="scott.sexton@sendthisfile.com",
            message_id="graph-message-1",
            target_folder="Deleted Items",
        )

    assert "403" in str(exc_info.value)
    assert "access-token" not in str(exc_info.value)
    assert "access-token" not in repr(client)


def test_graph_email_rule_transport_lists_inbox_rules():
    base_url = "https://graph.example/v1.0"
    rules_url = (
        "https://graph.example/v1.0/users/scott.sexton%40sendthisfile.com/"
        "mailFolders/inbox/messageRules"
    )
    transport = FakeGraphTransport(
        {
            rules_url: FakeGraphResponse(
                200,
                {
                    "value": [
                        {
                            "id": "rule-1",
                            "displayName": "Suspicious activity",
                            "sequence": 1,
                            "isEnabled": True,
                            "hasError": False,
                            "isReadOnly": False,
                            "conditions": {
                                "subjectContains": ["Suspicious Activities Report"]
                            },
                            "actions": {
                                "moveToFolder": "folder-id",
                                "stopProcessingRules": True,
                            },
                        }
                    ]
                },
            )
        }
    )
    client = GraphEmailRuleTransport(
        access_token="access-token",
        transport=transport,
        base_url=base_url,
    )

    rules = client.list_inbox_rules("scott.sexton@sendthisfile.com")

    assert len(rules) == 1
    assert rules[0]["displayName"] == "Suspicious activity"
    assert rules[0]["conditions"] == {
        "subjectContains": ["Suspicious Activities Report"]
    }
    assert len(transport.get_calls) == 1
    assert transport.get_calls[0][0] == rules_url
    assert transport.get_calls[0][1]["Authorization"] == "Bearer access-token"


def test_graph_email_rule_transport_uses_mailbox_identity_override():
    rules_url = (
        "https://graph.example/v1.0/users/scott.dk%40sendthisfile1.onmicrosoft.com/"
        "mailFolders/inbox/messageRules"
    )
    transport = FakeGraphTransport({rules_url: FakeGraphResponse(200, {"value": []})})
    client = GraphEmailRuleTransport(
        access_token="access-token",
        transport=transport,
        base_url="https://graph.example/v1.0",
        mailbox_identity_overrides={
            "scott@developkansas.com": "scott.dk@sendthisfile1.onmicrosoft.com",
        },
    )

    rules = client.list_inbox_rules("scott@developkansas.com")

    assert rules == ()
    assert transport.get_calls[0][0] == rules_url


def test_graph_email_rule_transport_rejects_missing_value_list():
    rules_url = (
        "https://graph.example/v1.0/users/scott.sexton%40sendthisfile.com/"
        "mailFolders/inbox/messageRules"
    )
    client = GraphEmailRuleTransport(
        access_token="access-token",
        transport=FakeGraphTransport({rules_url: FakeGraphResponse(200, {})}),
        base_url="https://graph.example/v1.0",
    )

    with pytest.raises(GraphClientError):
        client.list_inbox_rules("scott.sexton@sendthisfile.com")


def test_graph_email_read_transport_lists_messages_and_fetches_headers():
    base_url = "https://graph.example/v1.0"
    list_url = (
        "https://graph.example/v1.0/users/clarity%40sendthisfile.ai/"
        "mailFolders/inbox/messages?"
        "%24top=2&%24orderby=receivedDateTime+desc&%24select="
        "id%2Csubject%2Cfrom%2Csender%2CreceivedDateTime%2CbodyPreview%2Ccategories"
    )
    headers_url = (
        "https://graph.example/v1.0/users/clarity%40sendthisfile.ai/messages/"
        "graph-1?%24select=internetMessageHeaders"
    )
    transport = FakeGraphTransport(
        {
            list_url: FakeGraphResponse(
                200,
                {
                    "value": [
                        {
                            "id": "graph-1",
                            "subject": "Please review",
                            "from": {
                                "emailAddress": {
                                    "address": "scott.sexton@sendthisfile.com",
                                }
                            },
                            "receivedDateTime": "2026-07-09T15:30:00Z",
                            "bodyPreview": "Review this.",
                            "categories": ["clarity"],
                        }
                    ]
                },
            ),
            headers_url: FakeGraphResponse(
                200,
                {
                    "internetMessageHeaders": [
                        {
                            "name": "Authentication-Results",
                            "value": "mx.example; spf=pass; dkim=pass; dmarc=pass",
                        }
                    ]
                },
            ),
        }
    )
    client = GraphEmailReadTransport(
        access_token="access-token",
        transport=transport,
        base_url=base_url,
    )

    messages = client.list_messages("clarity@sendthisfile.ai", 2)

    assert len(messages) == 1
    message = messages[0]
    assert message["message_id"] == "graph-1"
    assert message["mailbox"] == "clarity@sendthisfile.ai"
    assert message["subject"] == "Please review"
    assert message["sender"] == "scott.sexton@sendthisfile.com"
    assert message["authentication_results"] == (
        "mx.example; spf=pass; dkim=pass; dmarc=pass",
    )
    assert len(transport.get_calls) == 2
    assert "/mailFolders/inbox/messages?" in transport.get_calls[0][0]
    assert transport.get_calls[0][1]["Authorization"] == "Bearer access-token"


def test_graph_email_read_transport_uses_mailbox_identity_override():
    base_url = "https://graph.example/v1.0"
    list_url = (
        "https://graph.example/v1.0/users/scott.dk%40sendthisfile1.onmicrosoft.com/"
        "mailFolders/inbox/messages?"
        "%24top=1&%24orderby=receivedDateTime+desc&%24select="
        "id%2Csubject%2Cfrom%2Csender%2CreceivedDateTime%2CbodyPreview%2Ccategories"
    )
    headers_url = (
        "https://graph.example/v1.0/users/scott.dk%40sendthisfile1.onmicrosoft.com/"
        "messages/graph-1?%24select=internetMessageHeaders"
    )
    transport = FakeGraphTransport(
        {
            list_url: FakeGraphResponse(
                200,
                {
                    "value": [
                        {
                            "id": "graph-1",
                            "subject": "Please review",
                            "from": {
                                "emailAddress": {
                                    "address": "sender@example.invalid",
                                }
                            },
                            "receivedDateTime": "2026-07-20T15:30:00Z",
                            "bodyPreview": "Review this.",
                        }
                    ]
                },
            ),
            headers_url: FakeGraphResponse(200, {"internetMessageHeaders": []}),
        }
    )
    client = GraphEmailReadTransport(
        access_token="access-token",
        transport=transport,
        base_url=base_url,
        mailbox_identity_overrides={
            "scott@developkansas.com": "scott.dk@sendthisfile1.onmicrosoft.com",
        },
    )

    messages = client.list_messages("scott@developkansas.com", 1)

    assert messages[0]["mailbox"] == "scott@developkansas.com"
    assert transport.get_calls[0][0] == list_url
    assert transport.get_calls[1][0] == headers_url


def test_graph_email_read_transport_can_include_body_text():
    base_url = "https://graph.example/v1.0"
    list_url = (
        "https://graph.example/v1.0/users/clarity%40sendthisfile.ai/"
        "mailFolders/inbox/messages?"
        "%24top=1&%24orderby=receivedDateTime+desc&%24select="
        "id%2Csubject%2Cfrom%2Csender%2CreceivedDateTime%2C"
        "bodyPreview%2Ccategories%2Cbody"
    )
    headers_url = (
        "https://graph.example/v1.0/users/clarity%40sendthisfile.ai/messages/"
        "graph-1?%24select=internetMessageHeaders"
    )
    transport = FakeGraphTransport(
        {
            list_url: FakeGraphResponse(
                200,
                {
                    "value": [
                        {
                            "id": "graph-1",
                            "subject": "RE: Clarity Day in a Glance",
                            "from": {
                                "emailAddress": {
                                    "address": "scott.sexton@sendthisfile.com",
                                }
                            },
                            "receivedDateTime": "2026-07-20T15:30:00Z",
                            "bodyPreview": "Delete items 1-8",
                            "body": {
                                "contentType": "html",
                                "content": (
                                    "<div>Delete items 1-8</div>"
                                    "<div>Delete gmail item 9</div>"
                                    "<div>Mark Jira item 1 as done</div>"
                                ),
                            },
                            "categories": [],
                        }
                    ]
                },
            ),
            headers_url: FakeGraphResponse(200, {"internetMessageHeaders": []}),
        }
    )
    client = GraphEmailReadTransport(
        access_token="access-token",
        transport=transport,
        base_url=base_url,
        include_body_text=True,
    )

    messages = client.list_messages("clarity@sendthisfile.ai", 1)

    assert messages[0]["preview"] == (
        "Delete items 1-8\n"
        "Delete gmail item 9\n"
        "Mark Jira item 1 as done"
    )


def test_graph_email_read_transport_requires_positive_limit():
    client = GraphEmailReadTransport(
        access_token="access-token",
        transport=FakeGraphTransport({}),
        base_url="https://graph.example/v1.0",
    )

    with pytest.raises(EmailClientError):
        client.list_messages("clarity@sendthisfile.ai", 0)


def test_graph_email_read_transport_rejects_missing_value_list():
    list_url = (
        "https://graph.example/v1.0/users/clarity%40sendthisfile.ai/"
        "mailFolders/inbox/messages?"
        "%24top=1&%24orderby=receivedDateTime+desc&%24select="
        "id%2Csubject%2Cfrom%2Csender%2CreceivedDateTime%2CbodyPreview%2Ccategories"
    )
    client = GraphEmailReadTransport(
        access_token="access-token",
        transport=FakeGraphTransport({list_url: FakeGraphResponse(200, {})}),
        base_url="https://graph.example/v1.0",
    )

    with pytest.raises(GraphClientError):
        client.list_messages("clarity@sendthisfile.ai", 1)


def test_urllib_graph_response_rejects_non_object_json():
    response = UrllibGraphResponse(status_code=200, body=b"[]")

    with pytest.raises(GraphClientError):
        response.json()
