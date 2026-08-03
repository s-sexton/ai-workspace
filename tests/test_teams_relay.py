from __future__ import annotations

import pytest

from common.teams_relay import (
    InMemoryTeamsRelayQueue,
    TeamsRelayError,
    TeamsRelayMessage,
)


def test_teams_relay_message_validates_text_payload():
    message = TeamsRelayMessage.from_mapping(_payload(text="show pending approvals"))

    assert message.command_id == "cmd-1"
    assert message.sender.email == "scott@example.com"
    assert message.conversation.team == "AI Workspace"
    assert message.text == "show pending approvals"


def test_teams_relay_message_validates_action_payload():
    message = TeamsRelayMessage.from_mapping(
        _payload(
            text=None,
            action={
                "type": "gmail_trash",
                "manifestId": "manifest-1",
                "itemNumbers": [1, 4],
            },
        )
    )

    assert message.action is not None
    assert message.action.action_type == "gmail_trash"
    assert message.action.item_numbers == (1, 4)


def test_teams_relay_message_requires_text_or_action():
    with pytest.raises(TeamsRelayError):
        TeamsRelayMessage.from_mapping(_payload(text=None, action=None))


def test_in_memory_teams_relay_queue_completes_messages():
    queue = InMemoryTeamsRelayQueue()
    queued = queue.enqueue(_payload())

    assert queue.receive()[0].queue_message_id == queued.queue_message_id

    queue.complete(queued.queue_message_id)

    assert queue.receive() == ()
    assert queue.completed[0].queue_message_id == queued.queue_message_id


def test_in_memory_teams_relay_queue_dead_letters_messages():
    queue = InMemoryTeamsRelayQueue()
    queued = queue.enqueue(_payload())

    queue.dead_letter(queued.queue_message_id, reason="bad sender")

    assert queue.receive() == ()
    assert queue.dead_letters[0][1] == "bad sender"


def _payload(*, text="show COMP tickets", action=None):
    return {
        "schemaVersion": 1,
        "source": "teams",
        "commandId": "cmd-1",
        "receivedAt": "2026-08-03T15:30:00Z",
        "from": {
            "displayName": "Scott Sexton",
            "email": "scott@example.com",
        },
        "conversation": {
            "team": "AI Workspace",
            "channel": "Clarity",
        },
        "text": text,
        "action": action,
    }
