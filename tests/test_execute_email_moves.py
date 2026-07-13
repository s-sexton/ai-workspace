from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pytest

from assistant.src.execute_email_moves import (
    build_gmail_move_transport_from_config,
    build_graph_move_transport_from_config,
    execute_email_moves,
    main,
)
from common.email import StaticEmailMoveTransport
from common.memory import DuckDbMemoryStore


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


def test_execute_email_moves_dry_run_lists_approved_moves(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path, "scott.sexton@sendthisfile.com", "read_write")
    action_id = _seed_approved_email_move(memory_path)

    result = execute_email_moves(root=tmp_path, memory_path=memory_path)

    assert "# Email Move Dry Run" in result
    assert "## Summary" in result
    assert "- Ready to move: 1" in result
    assert "- Blocked/skipped: 0" in result
    assert "- Mailbox scott.sexton@sendthisfile.com: 1 move(s)" in result
    assert "- Destination Clarity/Review: 1 move(s)" in result
    assert "## Moves" in result
    assert (
        "Would move message graph-message-1 in mailbox "
        "scott.sexton@sendthisfile.com to Clarity/Review"
    ) in result
    assert "Subject: Review this" in result
    assert f"Action: {action_id}" in result

    store = DuckDbMemoryStore(memory_path)
    try:
        latest_run = store.latest_run(workflow="execute-email-moves")
        actions = store.recent_actions()
        executed_actions = store.actions_by_approval_status("executed")
    finally:
        store.close()

    assert latest_run is not None
    assert (
        latest_run.summary
        == "Dry-run email move plan for 1 approved email move(s); 0 blocked/skipped."
    )
    assert actions[0].action_type == "dry_run_email_moves"
    assert actions[0].result == (
        "Prepared dry-run plan for 1 approved email move(s); 0 blocked/skipped."
    )


def test_execute_email_moves_reports_no_plan(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    memory_path.parent.mkdir(parents=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
    finally:
        store.close()

    result = execute_email_moves(root=tmp_path, memory_path=memory_path)

    assert result == "No approved email moves found."


def test_execute_email_moves_blocks_read_only_mailbox(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path, "scott.sexton@sendthisfile.com", "read")
    action_id = _seed_approved_email_move(memory_path)

    result = execute_email_moves(root=tmp_path, memory_path=memory_path)

    assert "# Email Move Dry Run" in result
    assert "- Ready to move: 0" in result
    assert "- Blocked/skipped: 1" in result
    assert "No executable approved email moves found." in result
    assert "Blocked message graph-message-1" in result
    assert "scott.sexton@sendthisfile.com" in result
    assert "not approved for read_write" in result
    assert f"Action: {action_id}" in result


def test_execute_email_moves_blocks_unconfigured_target_folder(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path, "scott.sexton@sendthisfile.com", "read_write")
    action_id = _seed_approved_email_move(
        memory_path,
        target_folder="Clarity/Unconfigured",
    )

    result = execute_email_moves(root=tmp_path, memory_path=memory_path)

    assert "No executable approved email moves found." in result
    assert "target folder is not in the current email folder policy" in result
    assert f"Action: {action_id}" in result


def test_execute_email_moves_blocks_non_email_source_item(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path, "scott.sexton@sendthisfile.com", "read_write")
    action_id = _seed_approved_email_move(
        memory_path,
        source_type="jira",
        source_scope_label="project = ACCT",
        item_type="jira_issue",
        message_id="ACCT-101",
    )

    result = execute_email_moves(root=tmp_path, memory_path=memory_path)

    assert "No executable approved email moves found." in result
    assert "action is not attached to an email message source" in result
    assert "Blocked message ACCT-101 in mailbox project = ACCT" in result
    assert f"Action: {action_id}" in result


def test_execute_email_moves_reports_missing_memory(tmp_path):
    result = execute_email_moves(
        root=tmp_path,
        memory_path=tmp_path / "logs" / "missing.duckdb",
    )

    assert "No Clarity memory found" in result


def test_execute_email_moves_rejects_live_execution(tmp_path):
    result = execute_email_moves(root=tmp_path, dry_run=False)

    assert result == "Live email moves are not implemented. Run without --execute."


def test_build_graph_move_transport_from_config_uses_client_credentials(tmp_path):
    _write_graph_env(
        tmp_path,
        "GRAPH_TENANT_ID=tenant\n"
        "GRAPH_CLIENT_ID=client-id\n"
        "GRAPH_CLIENT_SECRET=super-secret\n",
    )
    token_transport = FakeGraphTokenTransport()

    transport = build_graph_move_transport_from_config(
        root=tmp_path,
        graph_transport=FakeGraphTransport(),
        token_transport=token_transport,
    )

    assert "acquired-token" not in repr(transport)
    assert len(token_transport.calls) == 1
    _, _, form = token_transport.calls[0]
    assert form["client_id"] == "client-id"
    assert form["client_secret"] == "super-secret"


def test_build_graph_move_transport_from_config_can_use_bearer_token(tmp_path):
    _write_graph_env(tmp_path, "GRAPH_ACCESS_TOKEN=direct-token\n")
    token_transport = FakeGraphTokenTransport()

    transport = build_graph_move_transport_from_config(
        root=tmp_path,
        graph_transport=FakeGraphTransport(),
        token_transport=token_transport,
        use_bearer_auth=True,
    )

    assert "direct-token" not in repr(transport)
    assert token_transport.calls == []


def test_build_gmail_move_transport_from_config_can_use_bearer_token(tmp_path):
    _write_graph_env(tmp_path, "GOOGLE_ACCESS_TOKEN=direct-token\n")
    token_transport = FakeGraphTokenTransport()

    transport = build_gmail_move_transport_from_config(
        root=tmp_path,
        gmail_transport=FakeGraphTransport(),
        token_transport=token_transport,
        use_bearer_auth=True,
    )

    assert "direct-token" not in repr(transport)
    assert token_transport.calls == []


def test_execute_email_moves_can_execute_with_injected_transport(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path, "scott.sexton@sendthisfile.com", "read_write")
    action_id = _seed_approved_email_move(memory_path)
    transport = StaticEmailMoveTransport(moved_messages=[])

    result = execute_email_moves(
        root=tmp_path,
        memory_path=memory_path,
        dry_run=False,
        move_transport=transport,
    )

    assert "# Email Move Execution" in result
    assert "## Summary" in result
    assert "- Moved: 1" in result
    assert "- Blocked/skipped: 0" in result
    assert "- Mailbox scott.sexton@sendthisfile.com: 1 move(s)" in result
    assert "- Destination Clarity/Review: 1 move(s)" in result
    assert (
        "Moved message graph-message-1 in mailbox "
        "scott.sexton@sendthisfile.com to Clarity/Review"
    ) in result
    assert f"Action: {action_id}" in result
    assert len(transport.moved_messages) == 1
    assert transport.moved_messages[0].mailbox == "scott.sexton@sendthisfile.com"
    assert transport.moved_messages[0].message_id == "graph-message-1"
    assert transport.moved_messages[0].target_folder == "Clarity/Review"

    store = DuckDbMemoryStore(memory_path)
    try:
        latest_run = store.latest_run(workflow="execute-email-moves")
        actions = store.recent_actions()
        executed_actions = store.actions_by_approval_status("executed")
    finally:
        store.close()

    assert latest_run is not None
    assert (
        latest_run.summary
        == "Executed email move plan for 1 approved email move(s); 0 blocked/skipped."
    )
    assert actions[0].action_type == "execute_email_moves"
    assert actions[0].result == (
        "Executed for 1 approved email move(s); 0 blocked/skipped."
    )
    assert executed_actions[0].action_id == action_id


def test_execute_email_moves_does_not_repeat_executed_actions(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path, "scott.sexton@sendthisfile.com", "read_write")
    _seed_approved_email_move(memory_path)
    first_transport = StaticEmailMoveTransport(moved_messages=[])

    execute_email_moves(
        root=tmp_path,
        memory_path=memory_path,
        dry_run=False,
        move_transport=first_transport,
    )
    second_transport = StaticEmailMoveTransport(moved_messages=[])
    result = execute_email_moves(
        root=tmp_path,
        memory_path=memory_path,
        dry_run=False,
        move_transport=second_transport,
    )

    assert len(first_transport.moved_messages) == 1
    assert second_transport.moved_messages == []
    assert result == "No approved email moves found."


def test_main_prints_dry_run(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path, "scott.sexton@sendthisfile.com", "read_write")
    _seed_approved_email_move(memory_path)
    monkeypatch.chdir(tmp_path)

    main(["--memory", str(memory_path)])

    output = capsys.readouterr().out
    assert "# Email Move Dry Run" in output
    assert (
        "Would move message graph-message-1 in mailbox "
        "scott.sexton@sendthisfile.com to Clarity/Review"
    ) in output


def test_main_execute_without_graph_still_fails_closed(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path, "scott.sexton@sendthisfile.com", "read_write")
    _seed_approved_email_move(memory_path)
    monkeypatch.chdir(tmp_path)

    main(["--memory", str(memory_path), "--execute"])

    output = capsys.readouterr().out
    assert "Live email moves are not implemented" in output


def test_main_rejects_graph_without_execute():
    with pytest.raises(SystemExit):
        main(["--graph"])


def test_main_rejects_gmail_without_execute():
    with pytest.raises(SystemExit):
        main(["--gmail"])


def test_main_rejects_graph_bearer_without_graph():
    with pytest.raises(SystemExit):
        main(["--graph-bearer"])


def test_main_rejects_gmail_bearer_without_gmail():
    with pytest.raises(SystemExit):
        main(["--gmail-bearer"])


def test_main_can_execute_with_graph_transport(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path, "scott.sexton@sendthisfile.com", "read_write")
    action_id = _seed_approved_email_move(memory_path)
    transport = StaticEmailMoveTransport(moved_messages=[])
    calls = []

    def fake_build_graph_move_transport_from_config(*, use_bearer_auth=False, **_):
        calls.append(use_bearer_auth)
        return transport

    monkeypatch.setattr(
        "assistant.src.execute_email_moves.build_graph_move_transport_from_config",
        fake_build_graph_move_transport_from_config,
    )
    monkeypatch.chdir(tmp_path)

    main(["--memory", str(memory_path), "--graph", "--graph-bearer", "--execute"])

    output = capsys.readouterr().out
    assert calls == [True]
    assert "# Email Move Execution" in output
    assert f"Action: {action_id}" in output
    assert len(transport.moved_messages) == 1


def test_main_can_execute_with_gmail_transport(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path, "sesexton@gmail.com", "read_write")
    action_id = _seed_approved_email_move(
        memory_path,
        source_scope_label="sesexton@gmail.com",
        message_id="gmail-message-1",
        target_folder="Deleted Items",
    )
    transport = StaticEmailMoveTransport(moved_messages=[])
    calls = []

    def fake_build_gmail_move_transport_from_config(*, use_bearer_auth=False, **_):
        calls.append(use_bearer_auth)
        return transport

    monkeypatch.setattr(
        "assistant.src.execute_email_moves.build_gmail_move_transport_from_config",
        fake_build_gmail_move_transport_from_config,
    )
    monkeypatch.chdir(tmp_path)

    main(["--memory", str(memory_path), "--gmail", "--gmail-bearer", "--execute"])

    output = capsys.readouterr().out
    assert calls == [True]
    assert "# Email Move Execution" in output
    assert f"Action: {action_id}" in output
    assert len(transport.moved_messages) == 1


def _seed_approved_email_move(
    memory_path,
    *,
    target_folder="Clarity/Review",
    source_type="email",
    source_scope_label="scott.sexton@sendthisfile.com",
    item_type="email_message",
    message_id="graph-message-1",
):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="email-review")
        source = store.record_source(
            source_type=source_type,
            display_name=source_scope_label,
            scope_label=source_scope_label,
        )
        item = store.record_item_seen(
            source_id=source.source_id,
            external_id=message_id,
            item_type=item_type,
            subject="Review this",
            first_seen_run_id=run.run_id,
        )
        action = store.record_assistant_action(
            run_id=run.run_id,
            item_id=item.item_id,
            action_type="propose_email_move_review",
            approval_status="approved",
            action_target=target_folder,
            result=f"Proposed moving message metadata to {target_folder}.",
        )
        store.finish_run(run.run_id, status="completed")
        return action.action_id
    finally:
        store.close()


def _write_config(root, mailbox, access_mode):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        f"""
        {{
          "assistant": {{
            "email": {{
              "approvedMailboxes": [
                {{"address": "{mailbox}", "accessMode": "{access_mode}"}}
              ],
              "defaultMailbox": "{mailbox}",
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
