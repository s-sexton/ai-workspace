from __future__ import annotations

import pytest

from assistant.src.enqueue_teams_relay import enqueue_teams_relay_message
from common.teams_manifest import TeamsManifestItem, create_teams_manifest, write_teams_manifest
from common.teams_relay import InMemoryTeamsRelayQueue


def test_enqueue_teams_relay_message_enqueues_text_command():
    queue = InMemoryTeamsRelayQueue()

    result = enqueue_teams_relay_message(
        queue=queue,
        text="show pending approvals",
        sender_email="scott@example.com",
        command_id="cmd-1",
    )

    messages = queue.receive()
    assert result.command_id == "cmd-1"
    assert messages[0].payload["text"] == "show pending approvals"
    assert messages[0].payload["action"] is None
    assert messages[0].payload["from"]["email"] == "scott@example.com"


def test_enqueue_teams_relay_message_enqueues_manifest_action(tmp_path):
    manifest_path = tmp_path / "reports" / "teams-gmail-manifest.json"
    manifest = create_teams_manifest(
        created_at="2026-08-03T15:30:00Z",
        manifest_id="manifest-1",
        items=(
            TeamsManifestItem(
                number=1,
                source_type="gmail",
                mailbox="sesexton@gmail.com",
                external_id="gmail-message-1",
                subject="Test message",
                allowed_actions=("trash", "move_review", "move_noise"),
            ),
        ),
    )
    write_teams_manifest(manifest_path, manifest)
    queue = InMemoryTeamsRelayQueue()

    result = enqueue_teams_relay_message(
        queue=queue,
        action_type="move_review",
        item_numbers=(1,),
        manifest_path=manifest_path,
        root=tmp_path,
        command_id="cmd-2",
    )

    messages = queue.receive()
    assert result.manifest_id == "manifest-1"
    assert messages[0].payload["text"] is None
    assert messages[0].payload["action"] == {
        "type": "move_review",
        "manifestId": "manifest-1",
        "itemNumbers": [1],
    }


def test_enqueue_teams_relay_message_rejects_action_without_items(tmp_path):
    queue = InMemoryTeamsRelayQueue()

    with pytest.raises(ValueError):
        enqueue_teams_relay_message(
            queue=queue,
            action_type="move_review",
            manifest_path=tmp_path / "missing.json",
        )
