from __future__ import annotations

import pytest

from common.email import (
    EmailClient,
    EmailClientError,
    EmailFeedbackRule,
    EmailMoveClient,
    EmailSenderPreference,
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


@pytest.mark.parametrize(
    "subject",
    (
        "Scott, congrats! You have credit card recommendations!",
        "Introducing the new HOKA Clifton PRO",
        "Your Daily Digest for Fri, 7/10 is ready to view",
        "Exclusive Offer on JET JWL-1440VSK 14 In. x 40 In. Wood Lathe",
        "Keep the Birthday Fun Going with Your $5 Gift",
        "Boost Your Nutrition for Less",
        "Vacation From $37 Per Night - Where Will You Go?",
        "ALL Bottoms Buy 1, Get 1 50% OFF!",
        "K-State Sports Extra - July 10, 2026",
        "grab a li'l something fun for $2.95 today only.",
        "Wiper Refresh for the Sunny Days Ahead!",
        "Beat the Heat with Summer Colors and Styles",
        "Start watching I'm Not Afraid",
        "Fresh color starts now: Emerald and Duration are 35% off",
    ),
)
def test_classifies_common_promotional_subjects_as_noise(subject):
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "promo",
                    "mailbox": "inbox@example.invalid",
                    "subject": subject,
                    "sender": "marketing@example.invalid",
                },
            )
        )
    )

    classification = classify_email_message(
        client.list_messages(mailbox="inbox@example.invalid").messages[0]
    )

    assert classification.label == "noise"


def test_review_signals_take_precedence_over_promotional_language():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "billing-offer",
                    "mailbox": "inbox@example.invalid",
                    "subject": "Billing approval needed for exclusive offer",
                },
            )
        )
    )

    classification = classify_email_message(
        client.list_messages(mailbox="inbox@example.invalid").messages[0]
    )

    assert classification.label == "review"


def test_prior_feedback_can_override_content_rules():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "newsletter",
                    "mailbox": "inbox@example.invalid",
                    "subject": "Monthly newsletter",
                    "sender": "school@example.invalid",
                },
            )
        )
    )
    message = client.list_messages(mailbox="inbox@example.invalid").messages[0]

    classification = classify_email_message(
        message,
        feedback_rules=(
            EmailFeedbackRule(
                label="review",
                subject="monthly newsletter",
                sender="school@example.invalid",
            ),
        ),
    )

    assert classification.label == "review"
    assert classification.reason == "Matched prior human email feedback."


def test_sender_preference_takes_precedence_over_content_rules():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "sender-pref",
                    "mailbox": "inbox@example.invalid",
                    "subject": "Legal newsletter",
                    "sender": "promo@example.invalid",
                },
            )
        )
    )
    message = client.list_messages(mailbox="inbox@example.invalid").messages[0]

    classification = classify_email_message(
        message,
        sender_preferences=(
            EmailSenderPreference(
                mailbox="inbox@example.invalid",
                match_type="sender",
                pattern="promo@example.invalid",
                label="noise",
            ),
        ),
    )

    assert classification.label == "noise"
    assert classification.reason == "Matched mailbox-specific sender preference."


def test_domain_preference_matches_sender_domain():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "domain-pref",
                    "mailbox": "inbox@example.invalid",
                    "subject": "Weekly update",
                    "sender": "alerts@example.invalid",
                },
            )
        )
    )
    message = client.list_messages(mailbox="inbox@example.invalid").messages[0]

    classification = classify_email_message(
        message,
        sender_preferences=(
            EmailSenderPreference(
                mailbox="inbox@example.invalid",
                match_type="domain",
                pattern="example.invalid",
                label="review",
            ),
        ),
    )

    assert classification.label == "review"
    assert classification.reason == "Matched mailbox-specific domain preference."


def test_prior_feedback_can_match_sanitized_content_terms():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "new-promo",
                    "mailbox": "inbox@example.invalid",
                    "subject": "Another weekend update",
                    "sender": "store@example.invalid",
                    "preview": "Mystery savings and clearance deals are waiting.",
                },
            )
        )
    )
    message = client.list_messages(mailbox="inbox@example.invalid").messages[0]

    classification = classify_email_message(
        message,
        feedback_rules=(
            EmailFeedbackRule(
                label="noise",
                subject="Old promo",
                sender="store@example.invalid",
                content_terms=("mystery", "savings", "clearance", "deals"),
            ),
        ),
    )

    assert classification.label == "noise"
    assert classification.reason == "Matched prior human email feedback."


def test_prior_feedback_content_terms_do_not_match_different_sender():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "school-update",
                    "mailbox": "inbox@example.invalid",
                    "subject": "Classroom update",
                    "sender": "school@example.invalid",
                    "preview": "Classroom field trip permission slips are due tomorrow.",
                },
            )
        )
    )
    message = client.list_messages(mailbox="inbox@example.invalid").messages[0]

    classification = classify_email_message(
        message,
        feedback_rules=(
            EmailFeedbackRule(
                label="noise",
                subject="Old promo",
                sender="store@example.invalid",
                content_terms=("classroom", "field", "permission", "slips"),
            ),
        ),
    )

    assert classification.label == "review"


def test_restricted_mailbox_security_rules_take_precedence_over_feedback():
    client = EmailClient(
        transport=StaticEmailTransport(
            (
                {
                    "message_id": "spoofed",
                    "mailbox": "clarity@sendthisfile.ai",
                    "subject": "Monthly newsletter",
                    "sender": "scott.sexton@sendthisfile.com",
                    "spf": "fail",
                    "dkim": "fail",
                    "dmarc": "fail",
                },
            )
        )
    )
    message = client.list_messages(mailbox="clarity@sendthisfile.ai").messages[0]

    classification = classify_email_message(
        message,
        allowed_senders=("scott.sexton@sendthisfile.com",),
        feedback_rules=(
            EmailFeedbackRule(
                label="review",
                subject="Monthly newsletter",
                sender="scott.sexton@sendthisfile.com",
            ),
        ),
    )

    assert classification.label == "trash"
    assert "authentication checks" in classification.reason


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
                    "name": "X-MS-Exchange-Organization-AuthAs",
                    "value": "Internal",
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
    assert message.exchange_auth_as == "Internal"
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


def test_graph_message_payload_uses_placeholder_for_missing_subject():
    payload = graph_message_to_email_payload(
        {
            "id": "graph-no-subject",
            "subject": None,
        },
        mailbox="clarity@sendthisfile.ai",
    )

    assert payload["subject"] == "(No subject)"


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
