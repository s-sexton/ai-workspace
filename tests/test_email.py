from __future__ import annotations

import pytest

from common.email import (
    EmailClient,
    EmailClientError,
    EmailMoveClient,
    StaticGraphEmailTransport,
    StaticEmailTransport,
    StaticEmailMoveTransport,
    classify_email_message,
    graph_message_to_email_payload,
    propose_email_folder_action,
)


def test_email_client_reads_and_normalizes_metadata():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "msg-1",
                    "mailbox": "inbox@example.invalid",
                    "subject": "Legal review needed",
                    "sender": "legal@example.invalid",
                    "return_path": "bounce@example.invalid",
                    "spf": "pass",
                    "dkim": "pass",
                    "dmarc": "pass",
                    "received_at": "2026-07-09T08:00:00-05:00",
                    "preview": "Please review.",
                    "categories": ["legal"],
                },
            )
        )
    )

    result = client.list_messages(mailbox="inbox@example.invalid", limit=10)

    assert result.mailbox == "inbox@example.invalid"
    assert len(result.messages) == 1
    message = result.messages[0]
    assert message.message_id == "msg-1"
    assert message.subject == "Legal review needed"
    assert message.sender == "legal@example.invalid"
    assert message.return_path == "bounce@example.invalid"
    assert message.spf == "pass"
    assert message.dkim == "pass"
    assert message.dmarc == "pass"
    assert message.categories == ("legal",)


def test_email_client_filters_by_mailbox_and_limit():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {"message_id": "msg-1", "mailbox": "a@example.invalid", "subject": "A"},
                {"message_id": "msg-2", "mailbox": "b@example.invalid", "subject": "B"},
                {"message_id": "msg-3", "mailbox": "a@example.invalid", "subject": "C"},
            )
        )
    )

    result = client.list_messages(mailbox="a@example.invalid", limit=1)

    assert [message.message_id for message in result.messages] == ["msg-1"]


def test_classifies_marketing_as_noise_and_sensitive_work_as_review():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "marketing",
                    "mailbox": "inbox@example.invalid",
                    "subject": "Monthly newsletter",
                    "preview": "Unsubscribe here.",
                },
                {
                    "message_id": "legal",
                    "mailbox": "inbox@example.invalid",
                    "subject": "Legal review needed",
                },
            )
        )
    )
    result = client.list_messages(mailbox="inbox@example.invalid")

    assert classify_email_message(result.messages[0]).label == "noise"
    assert classify_email_message(result.messages[1]).label == "review"


def test_restricted_mailbox_sender_allow_list_classifies_unauthorized_as_trash():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "allowed",
                    "mailbox": "clarity@sendthisfile.ai",
                    "subject": "Review this",
                    "sender": "SCOTT.SEXTON@sendthisfile.com",
                    "spf": "pass",
                    "dkim": "pass",
                    "dmarc": "pass",
                },
                {
                    "message_id": "blocked",
                    "mailbox": "clarity@sendthisfile.ai",
                    "subject": "Act on this",
                    "sender": "external@example.invalid",
                },
            )
        )
    )
    result = client.list_messages(mailbox="clarity@sendthisfile.ai")

    assert (
        classify_email_message(
            result.messages[0],
            allowed_senders=(
                "scott.sexton@sendthisfile.com",
                "sesexton@gmail.com",
            ),
        ).label
        == "review"
    )
    classification = classify_email_message(
        result.messages[1],
        allowed_senders=(
            "scott.sexton@sendthisfile.com",
            "sesexton@gmail.com",
        ),
    )
    assert classification.label == "trash"
    assert "unauthorized sender" in classification.reason


def test_restricted_mailbox_requires_authentication_pass_for_allowed_sender():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "spoofed",
                    "mailbox": "clarity@sendthisfile.ai",
                    "subject": "Spoof attempt",
                    "sender": "scott.sexton@sendthisfile.com",
                    "spf": "fail",
                    "dkim": "fail",
                    "dmarc": "fail",
                },
                {
                    "message_id": "missing-auth",
                    "mailbox": "clarity@sendthisfile.ai",
                    "subject": "Missing authentication headers",
                    "sender": "sesexton@gmail.com",
                },
            )
        )
    )
    result = client.list_messages(mailbox="clarity@sendthisfile.ai")

    for message in result.messages:
        classification = classify_email_message(
            message,
            allowed_senders=(
                "scott.sexton@sendthisfile.com",
                "sesexton@gmail.com",
            ),
        )
        assert classification.label == "trash"
        assert "authentication checks" in classification.reason


def test_parses_authentication_results_header_metadata():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "header-auth",
                    "mailbox": "clarity@sendthisfile.ai",
                    "subject": "Header auth",
                    "sender": "scott.sexton@sendthisfile.com",
                    "authentication_results": (
                        "mx.example; spf=pass smtp.mailfrom=sendthisfile.com; "
                        "dkim=fail header.d=sendthisfile.com; "
                        "dmarc=pass action=none header.from=sendthisfile.com"
                    ),
                },
            )
        )
    )

    message = client.list_messages(mailbox="clarity@sendthisfile.ai").messages[0]
    classification = classify_email_message(
        message,
        allowed_senders=(
            "scott.sexton@sendthisfile.com",
            "sesexton@gmail.com",
        ),
    )

    assert message.spf == "pass"
    assert message.dkim == "fail"
    assert message.dmarc == "pass"
    assert classification.label == "review"


def test_parses_authentication_results_header_list():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "header-list-auth",
                    "mailbox": "clarity@sendthisfile.ai",
                    "subject": "Header auth",
                    "sender": "sesexton@gmail.com",
                    "authentication_results": [
                        "mx.example; spf=fail smtp.mailfrom=example.invalid",
                        "mx.example; dkim=pass header.d=gmail.com; dmarc=pass",
                    ],
                },
            )
        )
    )

    message = client.list_messages(mailbox="clarity@sendthisfile.ai").messages[0]
    classification = classify_email_message(
        message,
        allowed_senders=(
            "scott.sexton@sendthisfile.com",
            "sesexton@gmail.com",
        ),
    )

    assert message.spf == "fail"
    assert message.dkim == "pass"
    assert message.dmarc == "pass"
    assert classification.label == "review"


def test_explicit_authentication_values_override_parsed_header_metadata():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "explicit-auth",
                    "mailbox": "clarity@sendthisfile.ai",
                    "subject": "Explicit auth",
                    "sender": "scott.sexton@sendthisfile.com",
                    "spf": "pass",
                    "authentication_results": "mx.example; spf=fail; dmarc=pass",
                },
            )
        )
    )

    message = client.list_messages(mailbox="clarity@sendthisfile.ai").messages[0]

    assert message.spf == "pass"
    assert message.dmarc == "pass"


def test_invalid_authentication_results_metadata_raises_error():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "bad-header-auth",
                    "mailbox": "clarity@sendthisfile.ai",
                    "subject": "Bad header auth",
                    "authentication_results": [123],
                },
            )
        )
    )

    with pytest.raises(EmailClientError):
        client.list_messages(mailbox="clarity@sendthisfile.ai")


def test_graph_message_payload_maps_headers_into_email_metadata():
    payload = graph_message_to_email_payload(
        {
            "id": "graph-1",
            "subject": "Review from Graph",
            "from": {
                "emailAddress": {
                    "address": "scott.sexton@sendthisfile.com",
                }
            },
            "receivedDateTime": "2026-07-09T15:30:00Z",
            "bodyPreview": "Please review this.",
            "categories": ["clarity"],
            "internetMessageHeaders": [
                {
                    "name": "Return-Path",
                    "value": "<bounce@sendthisfile.com>",
                },
                {
                    "name": "Authentication-Results",
                    "value": (
                        "mx.example; spf=pass smtp.mailfrom=sendthisfile.com; "
                        "dkim=pass header.d=sendthisfile.com; dmarc=pass"
                    ),
                },
            ],
        },
        mailbox="clarity@sendthisfile.ai",
    )
    client = EmailClient(transport=StaticEmailTransport((payload,)))

    message = client.list_messages(mailbox="clarity@sendthisfile.ai").messages[0]
    classification = classify_email_message(
        message,
        allowed_senders=(
            "scott.sexton@sendthisfile.com",
            "sesexton@gmail.com",
        ),
    )

    assert message.message_id == "graph-1"
    assert message.sender == "scott.sexton@sendthisfile.com"
    assert message.return_path == "<bounce@sendthisfile.com>"
    assert message.received_at == "2026-07-09T15:30:00Z"
    assert message.preview == "Please review this."
    assert message.categories == ("clarity",)
    assert message.spf == "pass"
    assert message.dkim == "pass"
    assert message.dmarc == "pass"
    assert classification.label == "review"


def test_static_graph_email_transport_reads_graph_payloads_through_email_client():
    client = EmailClient(
        transport=StaticGraphEmailTransport(
            {
                "clarity@sendthisfile.ai": (
                    {
                        "id": "graph-1",
                        "subject": "First",
                        "from": {
                            "emailAddress": {
                                "address": "scott.sexton@sendthisfile.com",
                            }
                        },
                        "internetMessageHeaders": [
                            {
                                "name": "Authentication-Results",
                                "value": "mx.example; spf=pass; dkim=pass; dmarc=pass",
                            },
                        ],
                    },
                    {
                        "id": "graph-2",
                        "subject": "Second",
                        "from": {
                            "emailAddress": {
                                "address": "sesexton@gmail.com",
                            }
                        },
                    },
                ),
                "other@example.invalid": (
                    {
                        "id": "other-1",
                        "subject": "Other",
                    },
                ),
            }
        )
    )

    result = client.list_messages(mailbox="clarity@sendthisfile.ai", limit=1)

    assert result.mailbox == "clarity@sendthisfile.ai"
    assert len(result.messages) == 1
    assert result.messages[0].message_id == "graph-1"
    assert result.messages[0].sender == "scott.sexton@sendthisfile.com"
    assert result.messages[0].dmarc == "pass"


def test_graph_message_payload_can_use_sender_when_from_is_missing():
    payload = graph_message_to_email_payload(
        {
            "id": "graph-2",
            "subject": "Sender fallback",
            "sender": {
                "emailAddress": {
                    "address": "sesexton@gmail.com",
                }
            },
        },
        mailbox="clarity@sendthisfile.ai",
    )

    assert payload["sender"] == "sesexton@gmail.com"


def test_invalid_graph_header_payload_raises_error():
    with pytest.raises(EmailClientError):
        graph_message_to_email_payload(
            {
                "id": "graph-3",
                "subject": "Invalid header",
                "internetMessageHeaders": [{"name": "Return-Path"}],
            },
            mailbox="clarity@sendthisfile.ai",
        )


def test_invalid_authentication_status_raises_error():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "bad-auth",
                    "mailbox": "clarity@sendthisfile.ai",
                    "subject": "Bad auth",
                    "spf": "wat",
                },
            )
        )
    )

    with pytest.raises(EmailClientError):
        client.list_messages(mailbox="clarity@sendthisfile.ai")


def test_proposes_folder_action_from_classification():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "marketing",
                    "mailbox": "inbox@example.invalid",
                    "subject": "Monthly newsletter",
                    "preview": "Unsubscribe here.",
                },
            )
        )
    )
    classification = classify_email_message(
        client.list_messages(mailbox="inbox@example.invalid").messages[0]
    )

    proposal = propose_email_folder_action(
        classification,
        {"review": "Clarity/Review", "noise": "Clarity/Noise", "trash": "Deleted Items"},
    )

    assert proposal.action_type == "propose_email_move_noise"
    assert proposal.target_folder == "Clarity/Noise"


def test_missing_folder_policy_for_classification_raises_error():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "marketing",
                    "mailbox": "inbox@example.invalid",
                    "subject": "Monthly newsletter",
                    "preview": "Unsubscribe here.",
                },
            )
        )
    )
    classification = classify_email_message(
        client.list_messages(mailbox="inbox@example.invalid").messages[0]
    )

    with pytest.raises(EmailClientError):
        propose_email_folder_action(classification, {"review": "Clarity/Review"})


def test_email_move_client_moves_message_inside_mailbox():
    transport = StaticEmailMoveTransport(moved_messages=[])
    client = EmailMoveClient(transport=transport)

    result = client.move_message(
        mailbox="scott.sexton@sendthisfile.com",
        message_id="graph-message-1",
        target_folder="Clarity/Review",
    )

    assert result.mailbox == "scott.sexton@sendthisfile.com"
    assert result.message_id == "graph-message-1"
    assert result.target_folder == "Clarity/Review"
    assert transport.moved_messages[0].mailbox == "scott.sexton@sendthisfile.com"
    assert transport.moved_messages[0].message_id == "graph-message-1"
    assert transport.moved_messages[0].target_folder == "Clarity/Review"


def test_email_move_client_requires_complete_request():
    transport = StaticEmailMoveTransport(moved_messages=[])
    client = EmailMoveClient(transport=transport)

    with pytest.raises(EmailClientError):
        client.move_message(
            mailbox="scott.sexton@sendthisfile.com",
            message_id="",
            target_folder="Clarity/Review",
        )

    assert transport.moved_messages == []


def test_invalid_email_payload_raises_error():
    client = EmailClient(
        transport=StaticEmailTransport(
            ({"message_id": "missing-subject", "mailbox": "inbox@example.invalid"},)
        )
    )

    with pytest.raises(EmailClientError):
        client.list_messages(mailbox="inbox@example.invalid")


def test_email_limit_must_be_positive():
    client = EmailClient(transport=StaticEmailTransport(()))

    with pytest.raises(EmailClientError):
        client.list_messages(mailbox="inbox@example.invalid", limit=0)
