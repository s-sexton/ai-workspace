from __future__ import annotations

from typing import Any, Mapping

import pytest

from assistant.src.audit_outlook_rules import audit_outlook_rules, main
from common.configuration import ConfigurationError


class StaticRuleTransport:
    def __init__(self, rules: tuple[Mapping[str, Any], ...]):
        self.rules = rules
        self.mailboxes: list[str] = []

    def list_inbox_rules(self, mailbox: str) -> tuple[Mapping[str, Any], ...]:
        self.mailboxes.append(mailbox)
        return self.rules


def test_audit_outlook_rules_writes_read_only_report(tmp_path):
    _write_config(tmp_path)
    report_path = tmp_path / "reports" / "rules.md"
    transport = StaticRuleTransport(
        (
            {
                "id": "rule-2",
                "displayName": "Later rule",
                "sequence": 2,
                "isEnabled": False,
                "hasError": True,
                "isReadOnly": False,
                "conditions": {"senderContains": ["newsletter@example.invalid"]},
                "actions": {"delete": True},
            },
            {
                "id": "rule-3",
                "displayName": "Opaque rule",
                "sequence": 3,
                "isEnabled": True,
                "hasError": False,
                "isReadOnly": True,
                "conditions": {},
                "actions": {},
            },
            {
                "id": "rule-1",
                "displayName": "Suspicious activity",
                "sequence": 1,
                "isEnabled": True,
                "hasError": False,
                "isReadOnly": False,
                "conditions": {
                    "subjectContains": ["Suspicious Activities Report"],
                },
                "exceptions": {},
                "actions": {
                    "moveToFolder": "folder-id",
                    "stopProcessingRules": True,
                },
            },
        )
    )

    result = audit_outlook_rules(
        root=tmp_path,
        mailbox="scott.sexton@sendthisfile.com",
        output_path=report_path,
        rule_transport=transport,
    )

    assert result.mailbox == "scott.sexton@sendthisfile.com"
    assert result.rule_count == 3
    assert result.report_path == report_path
    assert transport.mailboxes == ["scott.sexton@sendthisfile.com"]
    report = report_path.read_text(encoding="utf-8")
    assert "# Outlook Rules Audit" in report
    assert "Mailbox: scott.sexton@sendthisfile.com" in report
    assert "Mode: read-only" in report
    assert report.index("## 1. Suspicious activity") < report.index("## 2. Later rule")
    assert "- Enabled: yes" in report
    assert "- Has error: no" in report
    assert "- Execution confidence: server-side likely" in report
    assert "Reason: Rule is enabled, Graph-visible, and has no reported error." in report
    assert "- Execution confidence: disabled" in report
    assert "Reason: Rule is not enabled." in report
    assert "- Execution confidence: needs manual Outlook review" in report
    assert "Reason: Rule is read-only through Microsoft Graph." in report
    assert "Reason: Rule has no Graph-visible conditions." in report
    assert "Reason: Rule has no Graph-visible actions." in report
    assert "subjectContains: Suspicious Activities Report" in report
    assert "moveToFolder: folder-id" in report
    assert "stopProcessingRules: true" in report


def test_audit_outlook_rules_rejects_unapproved_mailbox(tmp_path):
    _write_config(tmp_path)

    with pytest.raises(ConfigurationError):
        audit_outlook_rules(
            root=tmp_path,
            mailbox="unapproved@example.invalid",
            rule_transport=StaticRuleTransport(()),
        )


def test_main_prints_audit_summary(tmp_path, monkeypatch, capsys):
    _write_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    def fake_build_graph_rule_transport_from_config(**_):
        return StaticRuleTransport(
            (
                {
                    "id": "rule-1",
                    "displayName": "Suspicious activity",
                    "sequence": 1,
                    "isEnabled": True,
                    "hasError": False,
                    "isReadOnly": False,
                    "conditions": {
                        "subjectContains": ["Suspicious Activities Report"],
                    },
                    "actions": {"moveToFolder": "folder-id"},
                },
            )
        )

    monkeypatch.setattr(
        "assistant.src.audit_outlook_rules.build_graph_rule_transport_from_config",
        fake_build_graph_rule_transport_from_config,
    )

    main(["--mailbox", "scott.sexton@sendthisfile.com"])

    output = capsys.readouterr().out
    assert "# Outlook Rules Audit" in output
    assert "Mailbox: scott.sexton@sendthisfile.com" in output
    assert "Rules: 1" in output
    assert "Report:" in output
    report = (
        tmp_path / "reports" / "outlook-rules-scott-sexton-sendthisfile-com.md"
    ).read_text(encoding="utf-8")
    assert "## 1. Suspicious activity" in report


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
                  "address": "scott.sexton@sendthisfile.com",
                  "accessMode": "read_write"
                }
              ],
              "defaultMailbox": "scott.sexton@sendthisfile.com",
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
