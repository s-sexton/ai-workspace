"""Send a lightweight Gmail inbox summary to Microsoft Teams."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime, parseaddr
from pathlib import Path
from typing import Sequence
from zoneinfo import ZoneInfo

from assistant.src.run_email_review import build_gmail_read_transport_from_config
from common.configuration import ConfigurationError, load_workspace_config
from common.email import EmailClient, EmailMessage
from common.teams import TeamsWebhookTransport, post_lightweight_card_to_teams
from common.teams_manifest import (
    TeamsManifestItem,
    TeamsMessageManifest,
    create_teams_manifest,
    write_teams_manifest,
)


CENTRAL_TIME = ZoneInfo("America/Chicago")


@dataclass(frozen=True)
class GmailTeamsSummaryResult:
    """Safe Gmail-to-Teams summary details."""

    mailbox: str
    message_count: int
    manifest_path: Path
    response_status: int | None


def send_gmail_teams_summary(
    *,
    root: Path | str | None = None,
    mailbox: str = "sesexton@gmail.com",
    limit: int = 10,
    execute: bool = False,
    mention: str | None = "Scott Sexton",
    manifest_path: Path | str = Path("reports") / "teams-gmail-manifest.json",
    transport: TeamsWebhookTransport | None = None,
) -> GmailTeamsSummaryResult:
    """Read Gmail inbox metadata and optionally send a Teams summary."""

    config = load_workspace_config(root, include_process_env=True)
    email_settings = config.email_settings
    if mailbox not in email_settings.approved_mailboxes:
        raise ConfigurationError(f"Email mailbox is not approved: {mailbox}")
    if email_settings.access_mode_for(mailbox) not in ("read", "read_write"):
        raise ConfigurationError(f"Email mailbox is not approved for read access: {mailbox}")

    effective_limit = min(limit, email_settings.max_messages)
    client = EmailClient(
        transport=build_gmail_read_transport_from_config(root=config.root)
    )
    messages = client.list_messages(mailbox=mailbox, limit=effective_limit).messages
    resolved_manifest_path = _resolve_path(config.root, Path(manifest_path))
    manifest = create_gmail_teams_manifest(messages, mailbox=mailbox)
    write_teams_manifest(resolved_manifest_path, manifest)
    text = render_gmail_teams_summary(
        messages,
        mailbox=mailbox,
        mention=mention,
    )
    response_status = None
    if execute:
        response = post_lightweight_card_to_teams(
            webhook_url=config.env.get("TEAMS_CLARITY_WEBHOOK_URL", ""),
            text=text,
            transport=transport,
        )
        response_status = response.status_code
    return GmailTeamsSummaryResult(
        mailbox=mailbox,
        message_count=len(messages),
        manifest_path=resolved_manifest_path,
        response_status=response_status,
    )


def render_gmail_teams_summary(
    messages: Sequence[EmailMessage],
    *,
    mailbox: str,
    mention: str | None = None,
) -> str:
    """Render a compact Teams summary of Gmail inbox messages."""

    lines: list[str] = []
    if mention:
        lines.append(mention.strip())
        lines.append("")
    lines.append(f"**Gmail Inbox: {mailbox}**")
    lines.append("")
    if not messages:
        lines.append("No inbox messages found.")
        return "\n".join(lines)

    for index, message in enumerate(messages, 1):
        sender = _sender_display_text(message.sender)
        received = _formatted_received_at(message.received_at)
        link = gmail_message_link(message.message_id)
        lines.append(f"{index}. [{_clean_subject(message.subject)}]({link})")
        lines.append(f"   **From:** {sender}")
        lines.append(f"   **Date:** {received}")
    return "\n".join(lines)


def gmail_message_link(message_id: str) -> str:
    """Return a best-effort browser link to a Gmail message."""

    return f"https://mail.google.com/mail/u/0/#inbox/{message_id.strip()}"


def create_gmail_teams_manifest(
    messages: Sequence[EmailMessage],
    *,
    mailbox: str,
) -> TeamsMessageManifest:
    """Create a Teams manifest for Gmail summary items."""

    return create_teams_manifest(
        created_at=datetime.now(timezone.utc).isoformat(),
        items=tuple(
            TeamsManifestItem(
                number=index,
                source_type="gmail",
                mailbox=mailbox,
                external_id=message.message_id,
                subject=_clean_subject(message.subject),
                allowed_actions=("trash", "move_review", "move_noise"),
            )
            for index, message in enumerate(messages, 1)
        ),
    )


def _clean_subject(subject: str) -> str:
    return " ".join(subject.split()) or "(no subject)"


def _sender_display_text(sender: str | None) -> str:
    if sender is None or not sender.strip():
        return "Unknown sender"
    name, address = parseaddr(sender)
    if name.strip():
        return name.strip()
    clean_address = address.strip() or sender.strip()
    return clean_address.replace("@", " at ")


def _formatted_received_at(received_at: str | None) -> str:
    if received_at is None or not received_at.strip():
        return "Unknown date"
    parsed = _parse_received_at(received_at)
    if parsed is None:
        return received_at
    return parsed.astimezone(CENTRAL_TIME).strftime("%m/%d/%Y %I:%M %p")


def _parse_received_at(received_at: str) -> datetime | None:
    try:
        return parsedate_to_datetime(received_at)
    except (TypeError, ValueError, IndexError):
        pass
    try:
        return datetime.fromisoformat(received_at.replace("Z", "+00:00"))
    except ValueError:
        return None


def _resolve_path(workspace_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return workspace_root / path


def main(argv: Sequence[str] | None = None) -> None:
    """Send a lightweight Gmail inbox summary to Microsoft Teams."""

    args = _parse_args(argv)
    result = send_gmail_teams_summary(
        mailbox=args.mailbox,
        limit=args.limit,
        execute=args.execute,
        mention=args.mention,
        manifest_path=args.manifest,
    )
    print(f"Mailbox: {result.mailbox}")
    print(f"Messages: {result.message_count}")
    print(f"Manifest: {result.manifest_path}")
    if result.response_status is None:
        print("Teams send: dry-run")
    else:
        print(f"Teams send: HTTP {result.response_status}")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a lightweight Gmail inbox summary to Teams."
    )
    parser.add_argument("--mailbox", default="sesexton@gmail.com")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--mention", default="Scott Sexton")
    parser.add_argument(
        "--manifest",
        default=str(Path("reports") / "teams-gmail-manifest.json"),
        help="Teams manifest output path for numbered Gmail items.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Post the summary to Teams. Omit for a dry-run.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
