from __future__ import annotations

import pytest

from common.teams_manifest import (
    TeamsManifestError,
    TeamsManifestItem,
    create_teams_manifest,
    read_teams_manifest,
    resolve_manifest_items,
    write_teams_manifest,
)


def test_create_write_and_read_teams_manifest(tmp_path):
    manifest = create_teams_manifest(
        manifest_id="manifest-1",
        created_at="2026-08-03T15:30:00-05:00",
        items=(
            TeamsManifestItem(
                number=1,
                source_type="gmail",
                mailbox="sesexton@gmail.com",
                external_id="gmail-1",
                subject="Message one",
                allowed_actions=("trash", "move_review"),
            ),
        ),
    )

    path = write_teams_manifest(tmp_path / "manifest.json", manifest)
    loaded = read_teams_manifest(path)

    assert loaded.manifest_id == "manifest-1"
    assert loaded.items[0].external_id == "gmail-1"
    assert loaded.items[0].allowed_actions == ("trash", "move_review")


def test_create_teams_manifest_requires_sequential_numbers():
    with pytest.raises(TeamsManifestError):
        create_teams_manifest(
            created_at="2026-08-03T15:30:00-05:00",
            items=(
                TeamsManifestItem(
                    number=2,
                    source_type="gmail",
                    external_id="gmail-2",
                    subject="Message two",
                ),
            ),
        )


def test_resolve_manifest_items_validates_action():
    manifest = create_teams_manifest(
        created_at="2026-08-03T15:30:00-05:00",
        items=(
            TeamsManifestItem(
                number=1,
                source_type="gmail",
                external_id="gmail-1",
                subject="Message one",
                allowed_actions=("trash",),
            ),
        ),
    )

    resolved = resolve_manifest_items(
        manifest,
        item_numbers=(1,),
        required_action="trash",
    )

    assert resolved[0].subject == "Message one"


def test_resolve_manifest_items_rejects_disallowed_action():
    manifest = create_teams_manifest(
        created_at="2026-08-03T15:30:00-05:00",
        items=(
            TeamsManifestItem(
                number=1,
                source_type="gmail",
                external_id="gmail-1",
                subject="Message one",
                allowed_actions=("trash",),
            ),
        ),
    )

    with pytest.raises(TeamsManifestError):
        resolve_manifest_items(
            manifest,
            item_numbers=(1,),
            required_action="move_review",
        )
