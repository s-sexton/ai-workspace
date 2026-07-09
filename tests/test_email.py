from __future__ import annotations

import pytest

from common.email import (
    EmailClient,
    EmailClientError,
    StaticEmailTransport,
    classify_email_message,
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
        {"review": "Clarity/Review", "noise": "Clarity/Noise"},
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
