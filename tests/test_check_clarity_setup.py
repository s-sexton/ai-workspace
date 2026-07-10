from __future__ import annotations

import pytest

from assistant.src.check_clarity_setup import check_clarity_setup, main


def test_check_clarity_setup_passes_for_sample_mode(tmp_path):
    _write_config(tmp_path)

    result = check_clarity_setup(
        root=tmp_path,
        mailbox="clarity@sendthisfile.ai",
        memory_path="logs/memory.duckdb",
        brief_path="reports/brief.md",
        cycle_report_path="reports/cycle.md",
        log_path="logs/cycle.log",
    )

    output = result.format()
    assert result.ok
    assert "Mailbox: clarity@sendthisfile.ai [read_write]" in output
    assert "Allowed senders: 2 configured" in output
    assert "Graph credentials: not required" in output
    assert "OK: Clarity setup preflight passed." in output


def test_check_clarity_setup_requires_approved_mailbox(tmp_path):
    _write_config(tmp_path)

    result = check_clarity_setup(
        root=tmp_path,
        mailbox="missing@example.invalid",
    )

    output = result.format()
    assert not result.ok
    assert "Mailbox is not approved: missing@example.invalid" in output


def test_check_clarity_setup_reports_missing_graph_values_without_secrets(tmp_path):
    _write_config(tmp_path)
    _write_env(tmp_path, "GRAPH_TENANT_ID=tenant\nGRAPH_CLIENT_SECRET=super-secret\n")

    result = check_clarity_setup(
        root=tmp_path,
        mailbox="clarity@sendthisfile.ai",
        use_graph=True,
    )

    output = result.format()
    assert not result.ok
    assert "GRAPH_CLIENT_ID" in output
    assert "super-secret" not in output


def test_check_clarity_setup_accepts_graph_client_credentials(tmp_path):
    _write_config(tmp_path)
    _write_env(
        tmp_path,
        "GRAPH_TENANT_ID=tenant\nGRAPH_CLIENT_ID=client\nGRAPH_CLIENT_SECRET=secret\n",
    )

    result = check_clarity_setup(
        root=tmp_path,
        mailbox="clarity@sendthisfile.ai",
        use_graph=True,
    )

    assert result.ok
    assert "Graph credentials: present (client credentials)" in result.format()


def test_main_prints_preflight_result(tmp_path, monkeypatch, capsys):
    _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    main(["--mailbox", "clarity@sendthisfile.ai"])

    output = capsys.readouterr().out
    assert "# Clarity Setup Check" in output
    assert "OK: Clarity setup preflight passed." in output


def test_main_exits_nonzero_on_failed_preflight(tmp_path, monkeypatch, capsys):
    _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        main(["--mailbox", "missing@example.invalid"])

    assert exc_info.value.code == 1
    assert "Mailbox is not approved" in capsys.readouterr().out


def _write_config(root):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "email": {
              "approvedMailboxes": [
                {
                  "address": "clarity@sendthisfile.ai",
                  "accessMode": "read_write",
                  "allowedSenders": [
                    "scott.sexton@sendthisfile.com",
                    "sesexton@gmail.com"
                  ]
                },
                {"address": "legal@example.invalid", "accessMode": "read"}
              ],
              "defaultMailbox": "clarity@sendthisfile.ai",
              "folderNamespace": "Clarity",
              "folderPolicy": {
                "review": "Clarity/Review",
                "noise": "Clarity/Noise",
                "trash": "Deleted Items"
              },
              "maxMessages": 25
            }
          }
        }
        """,
        encoding="utf-8",
    )


def _write_env(root, content):
    (root / "config" / ".env").write_text(content, encoding="utf-8")
