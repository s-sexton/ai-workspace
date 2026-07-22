"""Ensure configured Clarity email folders exist."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from common.configuration import ConfigurationError, find_workspace_root, load_workspace_config
from common.graph_email import (
    GraphEmailFolderTransport,
    GraphTokenTransport,
    GraphTransport,
    build_graph_email_folder_transport,
)


class EmailFolderTransport(Protocol):
    """Minimal folder transport needed by the assistant workflow."""

    def ensure_folder_path(self, *, mailbox: str, folder_path: str):
        """Ensure one folder path exists."""

    def folder_path_exists(self, *, mailbox: str, folder_path: str) -> bool:
        """Return whether one folder path exists."""


@dataclass(frozen=True)
class EmailFolderEnsureResult:
    """Result of checking or creating one configured folder."""

    mailbox: str
    folder_path: str
    status: str


def ensure_email_folders(
    *,
    root: Path | str | None = None,
    mailbox: str,
    execute: bool = False,
    folder_transport: EmailFolderTransport | None = None,
    use_bearer_auth: bool = False,
) -> tuple[EmailFolderEnsureResult, ...]:
    """Check or create configured Clarity email folders for one mailbox."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    config = load_workspace_config(workspace_root)
    email_settings = config.email_settings
    requested_mailbox = mailbox or email_settings.default_mailbox
    if requested_mailbox not in email_settings.approved_mailboxes:
        raise ConfigurationError(f"Email mailbox is not approved: {requested_mailbox}")
    if email_settings.access_mode_for(requested_mailbox) != "read_write":
        raise ConfigurationError(
            f"Email mailbox is not approved for folder writes: {requested_mailbox}"
        )

    transport = folder_transport or build_graph_folder_transport_from_config(
        root=workspace_root,
        use_bearer_auth=use_bearer_auth,
    )
    results = []
    for folder_path in _configured_folder_paths(email_settings.folder_policy):
        if execute:
            result = transport.ensure_folder_path(
                mailbox=requested_mailbox,
                folder_path=folder_path,
            )
            status = "created" if result.created else "exists"
        else:
            status = (
                "exists"
                if transport.folder_path_exists(
                    mailbox=requested_mailbox,
                    folder_path=folder_path,
                )
                else "missing"
            )
        results.append(
            EmailFolderEnsureResult(
                mailbox=requested_mailbox,
                folder_path=folder_path,
                status=status,
            )
        )
    return tuple(results)


def build_graph_folder_transport_from_config(
    *,
    root: Path | str | None = None,
    graph_transport: GraphTransport | None = None,
    token_transport: GraphTokenTransport | None = None,
    use_bearer_auth: bool = False,
) -> GraphEmailFolderTransport:
    """Build a Graph email folder transport from local workspace configuration."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    config = load_workspace_config(workspace_root)
    credentials = config.require_graph_credentials(use_bearer_auth=use_bearer_auth)
    try:
        mailbox_identity_overrides = config.email_settings.mailbox_graph_user_ids
    except ConfigurationError:
        mailbox_identity_overrides = {}
    return build_graph_email_folder_transport(
        credentials,
        graph_transport=graph_transport,
        token_transport=token_transport,
        use_bearer_auth=use_bearer_auth,
        mailbox_identity_overrides=mailbox_identity_overrides,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Check or create configured Clarity email folders."""

    args = _parse_args(argv)
    results = ensure_email_folders(
        mailbox=args.mailbox,
        execute=args.execute,
        use_bearer_auth=args.graph_bearer,
    )
    title = "Email Folder Creation" if args.execute else "Email Folder Check"
    print(f"# {title}")
    print()
    for result in results:
        print(f"- {result.mailbox}: {result.folder_path} [{result.status}]")


def _configured_folder_paths(folder_policy) -> tuple[str, ...]:
    return tuple(
        folder_path
        for label, folder_path in folder_policy.items()
        if label != "trash"
    )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check or create configured Clarity email folders."
    )
    parser.add_argument("--mailbox", required=True)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Create missing configured folders. Without this, only checks.",
    )
    parser.add_argument(
        "--graph-bearer",
        action="store_true",
        help="Use GRAPH_ACCESS_TOKEN instead of app-only client credentials.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
