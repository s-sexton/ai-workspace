"""Read-only Outlook Inbox rules audit."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from common.configuration import ConfigurationError, find_workspace_root, load_workspace_config
from common.graph_email import (
    GraphEmailRuleTransport,
    GraphTokenTransport,
    GraphTransport,
    build_graph_email_rule_transport,
)


DEFAULT_RULES_REPORT_DIR = Path("reports")


class OutlookRuleTransport(Protocol):
    """Minimal read-only Outlook rule transport."""

    def list_inbox_rules(self, mailbox: str) -> tuple[Mapping[str, Any], ...]:
        """Return raw Inbox rules for one mailbox."""


@dataclass(frozen=True)
class OutlookRulesAuditResult:
    """Result of one Outlook rules audit."""

    mailbox: str
    rule_count: int
    report_path: Path


@dataclass(frozen=True)
class RuleExecutionAssessment:
    """Conservative assessment of one Outlook rule's execution reliability."""

    confidence: str
    reasons: tuple[str, ...]


def audit_outlook_rules(
    *,
    root: Path | str | None = None,
    mailbox: str | None = None,
    output_path: Path | str | None = None,
    rule_transport: OutlookRuleTransport | None = None,
    use_bearer_auth: bool = False,
) -> OutlookRulesAuditResult:
    """Write a read-only Markdown audit of one mailbox's Outlook Inbox rules."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    config = load_workspace_config(workspace_root)
    email_settings = config.email_settings
    requested_mailbox = mailbox or email_settings.default_mailbox
    if requested_mailbox not in email_settings.approved_mailboxes:
        raise ConfigurationError(f"Email mailbox is not approved: {requested_mailbox}")
    if email_settings.access_mode_for(requested_mailbox) not in ("read", "read_write"):
        raise ConfigurationError(
            f"Email mailbox is not approved for read access: {requested_mailbox}"
        )

    transport = rule_transport or build_graph_rule_transport_from_config(
        root=workspace_root,
        use_bearer_auth=use_bearer_auth,
    )
    rules = transport.list_inbox_rules(requested_mailbox)
    resolved_output_path = _resolve_path(
        workspace_root,
        Path(output_path) if output_path is not None else _default_report_path(requested_mailbox),
    )
    _write_rules_report(
        output_path=resolved_output_path,
        mailbox=requested_mailbox,
        rules=rules,
    )
    return OutlookRulesAuditResult(
        mailbox=requested_mailbox,
        rule_count=len(rules),
        report_path=resolved_output_path,
    )


def build_graph_rule_transport_from_config(
    *,
    root: Path | str | None = None,
    graph_transport: GraphTransport | None = None,
    token_transport: GraphTokenTransport | None = None,
    use_bearer_auth: bool = False,
) -> GraphEmailRuleTransport:
    """Build a Graph Outlook rule transport from local workspace configuration."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    config = load_workspace_config(workspace_root)
    credentials = config.require_graph_credentials(use_bearer_auth=use_bearer_auth)
    try:
        mailbox_identity_overrides = config.email_settings.mailbox_graph_user_ids
    except ConfigurationError:
        mailbox_identity_overrides = {}
    return build_graph_email_rule_transport(
        credentials,
        graph_transport=graph_transport,
        token_transport=token_transport,
        use_bearer_auth=use_bearer_auth,
        mailbox_identity_overrides=mailbox_identity_overrides,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Run a read-only Outlook Inbox rules audit."""

    args = _parse_args(argv)
    result = audit_outlook_rules(
        mailbox=args.mailbox,
        output_path=args.output,
        use_bearer_auth=args.graph_bearer,
    )
    print("# Outlook Rules Audit")
    print()
    print(f"Mailbox: {result.mailbox}")
    print(f"Rules: {result.rule_count}")
    print(f"Report: {result.report_path}")


def _write_rules_report(
    *,
    output_path: Path,
    mailbox: str,
    rules: tuple[Mapping[str, Any], ...],
) -> None:
    lines = [
        "# Outlook Rules Audit",
        "",
        f"Mailbox: {mailbox}",
        "Folder: Inbox",
        f"Rules: {len(rules)}",
        "Mode: read-only",
        "",
    ]
    if not rules:
        lines.append("_No Inbox rules found._")
    for rule in sorted(rules, key=_rule_sort_key):
        lines.extend(_format_rule(rule))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _format_rule(rule: Mapping[str, Any]) -> list[str]:
    display_name = _string_value(rule.get("displayName")) or "(unnamed rule)"
    sequence = _string_value(rule.get("sequence")) or "unknown"
    assessment = _assess_rule_execution(rule)
    lines = [
        f"## {sequence}. {display_name}",
        "",
        f"- ID: {_string_value(rule.get('id')) or 'unknown'}",
        f"- Enabled: {_yes_no(rule.get('isEnabled'))}",
        f"- Has error: {_yes_no(rule.get('hasError'))}",
        f"- Read-only: {_yes_no(rule.get('isReadOnly'))}",
        f"- Execution confidence: {assessment.confidence}",
    ]
    for reason in assessment.reasons:
        lines.append(f"  - Reason: {reason}")
    lines.extend(_format_section("Conditions", rule.get("conditions")))
    lines.extend(_format_section("Exceptions", rule.get("exceptions")))
    lines.extend(_format_section("Actions", rule.get("actions")))
    lines.append("")
    return lines


def _assess_rule_execution(rule: Mapping[str, Any]) -> RuleExecutionAssessment:
    if rule.get("isEnabled") is False:
        return RuleExecutionAssessment(
            confidence="disabled",
            reasons=("Rule is not enabled.",),
        )

    reasons = []
    if rule.get("hasError") is True:
        reasons.append("Rule has an error in Outlook/Exchange.")
    if rule.get("isReadOnly") is True:
        reasons.append("Rule is read-only through Microsoft Graph.")
    if not _flatten_rule_value(rule.get("conditions")):
        reasons.append("Rule has no Graph-visible conditions.")
    if not _flatten_rule_value(rule.get("actions")):
        reasons.append("Rule has no Graph-visible actions.")

    if reasons:
        return RuleExecutionAssessment(
            confidence="needs manual Outlook review",
            reasons=tuple(reasons),
        )

    return RuleExecutionAssessment(
        confidence="server-side likely",
        reasons=("Rule is enabled, Graph-visible, and has no reported error.",),
    )


def _format_section(title: str, value: Any) -> list[str]:
    flattened = _flatten_rule_value(value)
    if not flattened:
        return [f"- {title}: none"]
    lines = [f"- {title}:"]
    for key, display_value in flattened:
        lines.append(f"  - {key}: {display_value}")
    return lines


def _flatten_rule_value(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        flattened = []
        for key, child_value in value.items():
            if child_value in (None, [], {}, ""):
                continue
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            flattened.extend(_flatten_rule_value(child_value, child_prefix))
        return flattened
    if isinstance(value, list):
        if not value:
            return []
        if all(not isinstance(item, (Mapping, list)) for item in value):
            return [(prefix or "value", ", ".join(_string_value(item) for item in value))]
        flattened = []
        for index, item in enumerate(value, start=1):
            child_prefix = f"{prefix}[{index}]" if prefix else f"value[{index}]"
            flattened.extend(_flatten_rule_value(item, child_prefix))
        return flattened
    return [(prefix or "value", _string_value(value))]


def _rule_sort_key(rule: Mapping[str, Any]) -> tuple[int, str]:
    sequence = rule.get("sequence")
    if isinstance(sequence, int):
        sequence_number = sequence
    else:
        sequence_number = 999999
    return (sequence_number, _string_value(rule.get("displayName")).lower())


def _yes_no(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return "unknown"


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _default_report_path(mailbox: str) -> Path:
    return DEFAULT_RULES_REPORT_DIR / f"outlook-rules-{_safe_filename(mailbox)}.md"


def _safe_filename(value: str) -> str:
    return "".join(character if character.isalnum() else "-" for character in value).strip("-")


def _resolve_path(workspace_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return workspace_root / path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write a read-only Outlook Inbox rules audit report."
    )
    parser.add_argument("--mailbox", default=None)
    parser.add_argument(
        "--output",
        default=None,
        help="Markdown report path. Defaults to reports/outlook-rules-<mailbox>.md.",
    )
    parser.add_argument(
        "--graph-bearer",
        action="store_true",
        help="Use GRAPH_ACCESS_TOKEN instead of app-only client credentials.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
