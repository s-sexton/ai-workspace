from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pytest

from assistant.src.ensure_email_folders import (
    build_graph_folder_transport_from_config,
    ensure_email_folders,
    main,
)
from common.configuration import ConfigurationError


@dataclass(frozen=True)
class FakeFolderResult:
    created: bool


class FakeFolderTransport:
    def __init__(self, existing=()):
        self.existing = set(existing)
        self.ensure_calls: list[tuple[str, str]] = []
        self.exists_calls: list[tuple[str, str]] = []

    def ensure_folder_path(self, *, mailbox: str, folder_path: str):
        self.ensure_calls.append((mailbox, folder_path))
        created = folder_path not in self.existing
        self.existing.add(folder_path)
        return FakeFolderResult(created=created)

    def folder_path_exists(self, *, mailbox: str, folder_path: str) -> bool:
        self.exists_calls.append((mailbox, folder_path))
        return folder_path in self.existing


@dataclass
class FakeGraphResponse:
    status_code: int
    payload: Mapping[str, Any]

    def json(self) -> Mapping[str, Any]:
        return self.payload


class FakeGraphTransport:
    def get(self, url: str, headers: Mapping[str, str]) -> FakeGraphResponse:
        raise AssertionError("Unexpected Graph GET in factory test.")

    def post(
        self,
        url: str,
        headers: Mapping[str, str],
        body: Mapping[str, Any],
    ) -> FakeGraphResponse:
        raise AssertionError("Unexpected Graph POST in factory test.")


class FakeGraphTokenTransport:
    def __init__(self):
        self.calls: list[tuple[str, Mapping[str, str], Mapping[str, str]]] = []

    def post_form(
        self,
        url: str,
        headers: Mapping[str, str],
        form: Mapping[str, str],
    ) -> FakeGraphResponse:
        self.calls.append((url, headers, form))
        return FakeGraphResponse(200, {"access_token": "acquired-token"})


def test_ensure_email_folders_dry_run_checks_configured_non_trash_folders(tmp_path):
    _write_config(tmp_path, access_mode="read_write")
    transport = FakeFolderTransport(existing=("Clarity/Review",))

    results = ensure_email_folders(
        root=tmp_path,
        mailbox="clarity@sendthisfile.ai",
        folder_transport=transport,
    )

    assert [(result.folder_path, result.status) for result in results] == [
        ("Clarity/Review", "exists"),
        ("Clarity/Noise", "missing"),
    ]
    assert transport.exists_calls == [
        ("clarity@sendthisfile.ai", "Clarity/Review"),
        ("clarity@sendthisfile.ai", "Clarity/Noise"),
    ]
    assert transport.ensure_calls == []


def test_ensure_email_folders_execute_creates_missing_configured_folders(tmp_path):
    _write_config(tmp_path, access_mode="read_write")
    transport = FakeFolderTransport(existing=("Clarity/Review",))

    results = ensure_email_folders(
        root=tmp_path,
        mailbox="clarity@sendthisfile.ai",
        execute=True,
        folder_transport=transport,
    )

    assert [(result.folder_path, result.status) for result in results] == [
        ("Clarity/Review", "exists"),
        ("Clarity/Noise", "created"),
    ]
    assert transport.ensure_calls == [
        ("clarity@sendthisfile.ai", "Clarity/Review"),
        ("clarity@sendthisfile.ai", "Clarity/Noise"),
    ]


def test_ensure_email_folders_requires_read_write_mailbox(tmp_path):
    _write_config(tmp_path, access_mode="read")

    with pytest.raises(ConfigurationError) as exc_info:
        ensure_email_folders(
            root=tmp_path,
            mailbox="clarity@sendthisfile.ai",
            folder_transport=FakeFolderTransport(),
        )

    assert "folder writes" in str(exc_info.value)


def test_ensure_email_folders_rejects_unapproved_mailbox(tmp_path):
    _write_config(tmp_path, access_mode="read_write")

    with pytest.raises(ConfigurationError):
        ensure_email_folders(
            root=tmp_path,
            mailbox="missing@example.invalid",
            folder_transport=FakeFolderTransport(),
        )


def test_build_graph_folder_transport_from_config_uses_client_credentials(tmp_path):
    _write_graph_env(
        tmp_path,
        "GRAPH_TENANT_ID=tenant\n"
        "GRAPH_CLIENT_ID=client-id\n"
        "GRAPH_CLIENT_SECRET=super-secret\n",
    )
    token_transport = FakeGraphTokenTransport()

    transport = build_graph_folder_transport_from_config(
        root=tmp_path,
        graph_transport=FakeGraphTransport(),
        token_transport=token_transport,
    )

    assert "acquired-token" not in repr(transport)
    assert len(token_transport.calls) == 1
    _, _, form = token_transport.calls[0]
    assert form["client_id"] == "client-id"
    assert form["client_secret"] == "super-secret"


def test_main_prints_dry_run_summary(tmp_path, monkeypatch, capsys):
    _write_config(tmp_path, access_mode="read_write")
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        "assistant.src.ensure_email_folders.build_graph_folder_transport_from_config",
        lambda **_: FakeFolderTransport(existing=("Clarity/Review",)),
    )

    main(["--mailbox", "clarity@sendthisfile.ai"])

    output = capsys.readouterr().out
    assert "# Email Folder Check" in output
    assert "Clarity/Review [exists]" in output
    assert "Clarity/Noise [missing]" in output


def test_main_prints_execute_summary(tmp_path, monkeypatch, capsys):
    _write_config(tmp_path, access_mode="read_write")
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        "assistant.src.ensure_email_folders.build_graph_folder_transport_from_config",
        lambda **_: FakeFolderTransport(existing=("Clarity/Review",)),
    )

    main(["--mailbox", "clarity@sendthisfile.ai", "--execute"])

    output = capsys.readouterr().out
    assert "# Email Folder Creation" in output
    assert "Clarity/Review [exists]" in output
    assert "Clarity/Noise [created]" in output


def _write_config(root, *, access_mode):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        f"""
        {{
          "assistant": {{
            "email": {{
              "approvedMailboxes": [
                {{"address": "clarity@sendthisfile.ai", "accessMode": "{access_mode}"}}
              ],
              "defaultMailbox": "clarity@sendthisfile.ai",
              "folderNamespace": "Clarity",
              "folderPolicy": {{
                "review": "Clarity/Review",
                "noise": "Clarity/Noise",
                "trash": "Deleted Items"
              }},
              "maxMessages": 25
            }}
          }}
        }}
        """,
        encoding="utf-8",
    )


def _write_graph_env(root, content):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    (config_dir / ".env").write_text(content, encoding="utf-8")
