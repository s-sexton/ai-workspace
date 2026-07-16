"""Shared configuration loading for AI Workspace."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


DEFAULT_CONFIG_PATH = Path("config") / "config.json"
DEFAULT_ENV_PATH = Path("config") / ".env"
DEFAULT_ENV_EXAMPLE_PATH = Path("config") / ".env.example"


class ConfigurationError(RuntimeError):
    """Raised when workspace configuration cannot be loaded."""


@dataclass(frozen=True)
class JiraCredentials:
    """Local Jira credentials loaded from environment values."""

    cloud_id: str | None = None
    site_url: str | None = None
    email: str | None = None
    api_token: str | None = field(default=None, repr=False)
    access_token: str | None = field(default=None, repr=False)

    @property
    def is_complete(self) -> bool:
        """Return whether all required Jira credential values are present."""

        return self.is_cloud_route_complete

    @property
    def is_basic_auth_complete(self) -> bool:
        """Return whether Basic-auth Jira credentials are present."""

        return all((self.site_url, self.email, self.api_token))

    @property
    def is_cloud_route_complete(self) -> bool:
        """Return whether cloud ID route Jira credentials are present."""

        return all((self.cloud_id, self.email, self.api_token))

    @property
    def is_bearer_auth_complete(self) -> bool:
        """Return whether Bearer-auth Jira credentials are present."""

        return all((self.cloud_id, self.access_token))


@dataclass(frozen=True)
class GraphCredentials:
    """Local Microsoft Graph credentials loaded from environment values."""

    tenant_id: str | None = None
    client_id: str | None = None
    client_secret: str | None = field(default=None, repr=False)
    access_token: str | None = field(default=None, repr=False)

    @property
    def is_client_secret_complete(self) -> bool:
        """Return whether app-only client secret credentials are present."""

        return all((self.tenant_id, self.client_id, self.client_secret))

    @property
    def is_bearer_auth_complete(self) -> bool:
        """Return whether a direct Graph access token is present."""

        return bool(self.access_token)


@dataclass(frozen=True)
class GoogleCredentials:
    """Local Google credentials loaded from environment values."""

    client_id: str | None = None
    client_secret: str | None = field(default=None, repr=False)
    refresh_token: str | None = field(default=None, repr=False)
    access_token: str | None = field(default=None, repr=False)

    @property
    def is_refresh_token_complete(self) -> bool:
        """Return whether refresh-token credentials are present."""

        return all((self.client_id, self.client_secret, self.refresh_token))

    @property
    def is_bearer_auth_complete(self) -> bool:
        """Return whether a direct Google access token is present."""

        return bool(self.access_token)


@dataclass(frozen=True)
class OpenAICredentials:
    """Local OpenAI API settings loaded from environment values."""

    api_key: str | None = field(default=None, repr=False)
    model: str | None = None
    base_url: str | None = None

    @property
    def is_complete(self) -> bool:
        """Return whether OpenAI API credentials are present."""

        return all((self.api_key, self.model))


@dataclass(frozen=True)
class JiraSettings:
    """Shared Jira report settings loaded from committed configuration."""

    projects: tuple[str, ...]
    max_results: int
    sort_order: str
    report_fields: tuple[str, ...]


@dataclass(frozen=True)
class GmailCleanupPolicy:
    """Gmail-specific cleanup policy loaded from committed configuration."""

    trash_spam: bool = False
    mailboxes: tuple[str, ...] = ()


@dataclass(frozen=True)
class EmailSettings:
    """Shared email settings loaded from committed configuration."""

    approved_mailboxes: tuple[str, ...]
    mailbox_access: Mapping[str, str]
    mailbox_allowed_senders: Mapping[str, tuple[str, ...]]
    folder_namespace: str
    folder_policy: Mapping[str, str]
    gmail_cleanup_policy: GmailCleanupPolicy
    default_mailbox: str
    max_messages: int

    def access_mode_for(self, mailbox: str) -> str | None:
        """Return the configured access mode for a mailbox."""

        return self.mailbox_access.get(mailbox)

    def folder_for_label(self, label: str) -> str | None:
        """Return the proposed destination folder for a classification label."""

        return self.folder_policy.get(label)

    def allowed_senders_for(self, mailbox: str) -> tuple[str, ...]:
        """Return allowed senders for a restricted mailbox."""

        return self.mailbox_allowed_senders.get(mailbox, ())


@dataclass(frozen=True)
class CalendarScope:
    """One approved calendar Clarity may read."""

    label: str
    source: str
    provider: str
    access_mode: str


@dataclass(frozen=True)
class CalendarSettings:
    """Shared calendar settings loaded from committed configuration."""

    approved_calendars: Mapping[str, CalendarScope]
    default_calendar: str
    max_events: int

    def scope_for(self, calendar: str) -> CalendarScope | None:
        """Return the configured scope for a calendar label."""

        return self.approved_calendars.get(calendar)


@dataclass(frozen=True)
class DailyBriefSettings:
    """Daily brief email settings loaded from committed configuration."""

    sender: str
    recipients: tuple[str, ...]
    subject_prefix: str


@dataclass(frozen=True)
class WorkspaceConfig:
    """Loaded workspace configuration and local environment values."""

    root: Path
    settings: Mapping[str, Any]
    env: Mapping[str, str] = field(repr=False)

    @property
    def jira_credentials(self) -> JiraCredentials:
        """Return Jira credentials from local environment values."""

        return JiraCredentials(
            cloud_id=self.env.get("JIRA_CLOUD_ID"),
            site_url=self.env.get("JIRA_SITE_URL"),
            email=self.env.get("JIRA_EMAIL"),
            api_token=self.env.get("JIRA_API_TOKEN"),
            access_token=self.env.get("JIRA_ACCESS_TOKEN"),
        )

    @property
    def graph_credentials(self) -> GraphCredentials:
        """Return Microsoft Graph credentials from local environment values."""

        return GraphCredentials(
            tenant_id=self.env.get("GRAPH_TENANT_ID"),
            client_id=self.env.get("GRAPH_CLIENT_ID"),
            client_secret=self.env.get("GRAPH_CLIENT_SECRET"),
            access_token=self.env.get("GRAPH_ACCESS_TOKEN"),
        )

    @property
    def google_credentials(self) -> GoogleCredentials:
        """Return Google credentials from local environment values."""

        return GoogleCredentials(
            client_id=self.env.get("GOOGLE_CLIENT_ID"),
            client_secret=self.env.get("GOOGLE_CLIENT_SECRET"),
            refresh_token=self.env.get("GOOGLE_REFRESH_TOKEN"),
            access_token=self.env.get("GOOGLE_ACCESS_TOKEN"),
        )

    @property
    def openai_credentials(self) -> OpenAICredentials:
        """Return OpenAI API credentials from local environment values."""

        return OpenAICredentials(
            api_key=self.env.get("OPENAI_API_KEY"),
            model=self.env.get("OPENAI_MODEL"),
            base_url=self.env.get("OPENAI_BASE_URL"),
        )

    @property
    def jira_settings(self) -> JiraSettings:
        """Return validated Jira report settings."""

        settings = _get_mapping(self.settings, ("assistant", "jira"))

        return JiraSettings(
            projects=_require_string_tuple(settings, "projects"),
            max_results=_require_positive_int(settings, "maxResults"),
            sort_order=_require_non_empty_string(settings, "sortOrder"),
            report_fields=_require_string_tuple(settings, "reportFields"),
        )

    @property
    def email_settings(self) -> EmailSettings:
        """Return validated email review settings."""

        settings = _get_mapping(self.settings, ("assistant", "email"))
        mailbox_access = _require_mailbox_access(settings, "approvedMailboxes")
        mailbox_allowed_senders = _mailbox_allowed_senders(settings, "approvedMailboxes")
        folder_namespace = _require_folder_namespace(settings, "folderNamespace")
        approved_mailboxes = tuple(mailbox_access)
        default_mailbox = _require_non_empty_string(settings, "defaultMailbox")
        if default_mailbox not in approved_mailboxes:
            raise ConfigurationError(
                "Email defaultMailbox must be listed in approvedMailboxes."
            )

        return EmailSettings(
            approved_mailboxes=approved_mailboxes,
            mailbox_access=MappingProxyType(mailbox_access),
            mailbox_allowed_senders=MappingProxyType(mailbox_allowed_senders),
            folder_namespace=folder_namespace,
            folder_policy=MappingProxyType(
                _require_folder_policy(settings, "folderPolicy", folder_namespace)
            ),
            gmail_cleanup_policy=_require_gmail_cleanup_policy(
                settings,
                "gmailCleanupPolicy",
                mailbox_access,
            ),
            default_mailbox=default_mailbox,
            max_messages=_require_positive_int(settings, "maxMessages"),
        )

    @property
    def calendar_settings(self) -> CalendarSettings:
        """Return validated calendar review settings."""

        settings = _get_mapping(self.settings, ("assistant", "calendar"))
        approved_calendars = _require_calendar_scopes(settings, "approvedCalendars")
        default_calendar = _require_non_empty_string(settings, "defaultCalendar")
        if default_calendar not in approved_calendars:
            raise ConfigurationError(
                "Calendar defaultCalendar must be listed in approvedCalendars."
            )

        return CalendarSettings(
            approved_calendars=MappingProxyType(approved_calendars),
            default_calendar=default_calendar,
            max_events=_require_positive_int(settings, "maxEvents"),
        )

    @property
    def daily_brief_settings(self) -> DailyBriefSettings:
        """Return validated daily brief email settings."""

        settings = _get_mapping(self.settings, ("assistant", "dailyBrief"))
        recipients = _require_string_tuple(settings, "recipients")
        return DailyBriefSettings(
            sender=_require_non_empty_string(settings, "sender"),
            recipients=recipients,
            subject_prefix=_require_non_empty_string(settings, "subjectPrefix"),
        )

    def require_jira_credentials(
        self,
        *,
        use_cloud_route: bool = True,
        use_bearer_auth: bool = False,
    ) -> JiraCredentials:
        """Return Jira credentials or raise when required values are missing."""

        credentials = self.jira_credentials
        required = (
            (
                ("JIRA_CLOUD_ID", credentials.cloud_id),
                ("JIRA_ACCESS_TOKEN", credentials.access_token),
            )
            if use_bearer_auth
            else (
                (
                    ("JIRA_CLOUD_ID", credentials.cloud_id),
                    ("JIRA_EMAIL", credentials.email),
                    ("JIRA_API_TOKEN", credentials.api_token),
                )
                if use_cloud_route
                else (
                    ("JIRA_SITE_URL", credentials.site_url),
                    ("JIRA_EMAIL", credentials.email),
                    ("JIRA_API_TOKEN", credentials.api_token),
                )
            )
        )
        missing = [key for key, value in required if not value]
        if missing:
            raise ConfigurationError(
                "Missing required Jira environment values: " + ", ".join(missing)
            )

        return credentials

    def require_graph_credentials(
        self,
        *,
        use_bearer_auth: bool = False,
    ) -> GraphCredentials:
        """Return Graph credentials or raise when required values are missing."""

        credentials = self.graph_credentials
        required = (
            (("GRAPH_ACCESS_TOKEN", credentials.access_token),)
            if use_bearer_auth
            else (
                ("GRAPH_TENANT_ID", credentials.tenant_id),
                ("GRAPH_CLIENT_ID", credentials.client_id),
                ("GRAPH_CLIENT_SECRET", credentials.client_secret),
            )
        )
        missing = [name for name, value in required if not value]
        if missing:
            raise ConfigurationError(
                "Missing required Graph environment values: " + ", ".join(missing)
            )

        return credentials

    def require_google_credentials(
        self,
        *,
        use_bearer_auth: bool = False,
    ) -> GoogleCredentials:
        """Return Google credentials or raise when required values are missing."""

        credentials = self.google_credentials
        required = (
            (("GOOGLE_ACCESS_TOKEN", credentials.access_token),)
            if use_bearer_auth
            else (
                ("GOOGLE_CLIENT_ID", credentials.client_id),
                ("GOOGLE_CLIENT_SECRET", credentials.client_secret),
                ("GOOGLE_REFRESH_TOKEN", credentials.refresh_token),
            )
        )
        missing = [name for name, value in required if not value]
        if missing:
            raise ConfigurationError(
                "Missing required Google environment values: " + ", ".join(missing)
            )

        return credentials

    def require_openai_credentials(self) -> OpenAICredentials:
        """Return OpenAI credentials or raise when required values are missing."""

        credentials = self.openai_credentials
        required = (
            ("OPENAI_API_KEY", credentials.api_key),
            ("OPENAI_MODEL", credentials.model),
        )
        missing = [name for name, value in required if not value]
        if missing:
            raise ConfigurationError(
                "Missing required OpenAI environment values: " + ", ".join(missing)
            )

        return credentials


def find_workspace_root(start: Path | str | None = None) -> Path:
    """Find the nearest parent directory containing the workspace config file."""

    current = Path(start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / DEFAULT_CONFIG_PATH).is_file():
            return candidate

    raise ConfigurationError(
        f"Could not find workspace root containing {DEFAULT_CONFIG_PATH}."
    )


def load_workspace_config(
    root: Path | str | None = None,
    env_path: Path | str | None = None,
    *,
    include_process_env: bool = True,
) -> WorkspaceConfig:
    """Load committed workspace settings and local environment values."""

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    config_path = workspace_root / DEFAULT_CONFIG_PATH
    local_env_path = Path(env_path) if env_path is not None else workspace_root / DEFAULT_ENV_PATH

    settings = _load_json(config_path)
    env_values = _load_env_file(local_env_path)

    if include_process_env:
        expected_env_keys = set(env_values) | _load_env_keys(
            workspace_root / DEFAULT_ENV_EXAMPLE_PATH
        )
        for key in expected_env_keys:
            value = os.environ.get(key)
            if value is not None:
                env_values[key] = value

    return WorkspaceConfig(
        root=workspace_root,
        settings=MappingProxyType(settings),
        env=MappingProxyType(env_values),
    )


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigurationError(f"Missing workspace configuration file: {path}")

    try:
        with path.open("r", encoding="utf-8") as config_file:
            loaded = json.load(config_file)
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"Invalid JSON in workspace configuration: {path}") from exc

    if not isinstance(loaded, dict):
        raise ConfigurationError(f"Workspace configuration must be a JSON object: {path}")

    return loaded


def _load_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            raise ConfigurationError(f"Invalid env line {line_number} in {path}")

        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            raise ConfigurationError(f"Missing env key on line {line_number} in {path}")

        values[key] = _strip_optional_quotes(value.strip())

    return values


def _load_env_keys(path: Path) -> set[str]:
    return set(_load_env_file(path))


def _strip_optional_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _get_mapping(settings: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any]:
    current: Any = settings
    for part in path:
        if not isinstance(current, Mapping) or part not in current:
            raise ConfigurationError(f"Missing configuration section: {'.'.join(path)}")
        current = current[part]

    if not isinstance(current, Mapping):
        raise ConfigurationError(f"Configuration section must be an object: {'.'.join(path)}")

    return current


def _require_non_empty_string(settings: Mapping[str, Any], key: str) -> str:
    value = settings.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"Configuration value must be a non-empty string: {key}")
    return value


def _require_positive_int(settings: Mapping[str, Any], key: str) -> int:
    value = settings.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ConfigurationError(f"Configuration value must be a positive integer: {key}")
    return value


def _require_string_tuple(settings: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = settings.get(key)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        raise ConfigurationError(
            f"Configuration value must be a non-empty list of strings: {key}"
        )
    return tuple(value)


def _require_mailbox_access(settings: Mapping[str, Any], key: str) -> dict[str, str]:
    value = settings.get(key)
    if not isinstance(value, list) or not value:
        raise ConfigurationError(
            f"Configuration value must be a non-empty list of mailbox objects: {key}"
        )

    mailbox_access: dict[str, str] = {}
    for index, item in enumerate(value, 1):
        if not isinstance(item, Mapping):
            raise ConfigurationError(f"Mailbox entry must be an object: {key}[{index}]")
        address = item.get("address")
        access_mode = item.get("accessMode")
        if not isinstance(address, str) or not address.strip():
            raise ConfigurationError(
                f"Mailbox address must be a non-empty string: {key}[{index}]"
            )
        if access_mode not in ("read", "read_write"):
            raise ConfigurationError(
                f"Mailbox accessMode must be read or read_write: {key}[{index}]"
            )
        clean_address = address.strip()
        if clean_address in mailbox_access:
            raise ConfigurationError(f"Duplicate approved mailbox: {clean_address}")
        mailbox_access[clean_address] = access_mode

    return mailbox_access


def _require_calendar_scopes(
    settings: Mapping[str, Any],
    key: str,
) -> dict[str, CalendarScope]:
    value = settings.get(key)
    if not isinstance(value, list) or not value:
        raise ConfigurationError(
            f"Configuration value must be a non-empty list of calendar objects: {key}"
        )

    approved_calendars: dict[str, CalendarScope] = {}
    for index, item in enumerate(value, 1):
        if not isinstance(item, Mapping):
            raise ConfigurationError(f"Calendar entry must be an object: {key}[{index}]")
        label = item.get("label")
        source = item.get("source")
        provider = item.get("provider", "sample")
        access_mode = item.get("accessMode", "read")
        if not isinstance(label, str) or not label.strip():
            raise ConfigurationError(
                f"Calendar label must be a non-empty string: {key}[{index}]"
            )
        if not isinstance(source, str) or not source.strip():
            raise ConfigurationError(
                f"Calendar source must be a non-empty string: {key}[{index}]"
            )
        if provider not in ("sample", "graph", "google"):
            raise ConfigurationError(
                f"Calendar provider must be sample, graph, or google: {key}[{index}]"
            )
        if access_mode not in ("read", "read_write"):
            raise ConfigurationError(
                f"Calendar accessMode must be read or read_write: {key}[{index}]"
            )
        clean_label = label.strip()
        if clean_label in approved_calendars:
            raise ConfigurationError(f"Duplicate approved calendar: {clean_label}")
        approved_calendars[clean_label] = CalendarScope(
            label=clean_label,
            source=source.strip(),
            provider=provider,
            access_mode=access_mode,
        )

    return approved_calendars


def _mailbox_allowed_senders(
    settings: Mapping[str, Any],
    key: str,
) -> dict[str, tuple[str, ...]]:
    value = settings.get(key)
    if not isinstance(value, list):
        raise ConfigurationError(
            f"Configuration value must be a non-empty list of mailbox objects: {key}"
        )

    allowed_senders: dict[str, tuple[str, ...]] = {}
    for index, item in enumerate(value, 1):
        if not isinstance(item, Mapping):
            raise ConfigurationError(f"Mailbox entry must be an object: {key}[{index}]")
        address = item.get("address")
        if not isinstance(address, str) or not address.strip():
            raise ConfigurationError(
                f"Mailbox address must be a non-empty string: {key}[{index}]"
            )
        raw_allowed_senders = item.get("allowedSenders", [])
        if raw_allowed_senders is None:
            raw_allowed_senders = []
        if not isinstance(raw_allowed_senders, list):
            raise ConfigurationError(
                f"Mailbox allowedSenders must be a list of strings: {key}[{index}]"
            )
        if any(
            not isinstance(sender, str) or not sender.strip()
            for sender in raw_allowed_senders
        ):
            raise ConfigurationError(
                f"Mailbox allowedSenders must be a list of strings: {key}[{index}]"
            )
        allowed_senders[address.strip()] = tuple(
            sender.strip() for sender in raw_allowed_senders
        )

    return allowed_senders


def _require_folder_namespace(settings: Mapping[str, Any], key: str) -> str:
    namespace = _require_non_empty_string(settings, key).strip()
    if "/" in namespace or "\\" in namespace:
        raise ConfigurationError(
            "Email folderNamespace must be a single folder name."
        )
    return namespace


def _require_folder_policy(
    settings: Mapping[str, Any],
    key: str,
    folder_namespace: str,
) -> dict[str, str]:
    value = settings.get(key)
    if not isinstance(value, Mapping) or not value:
        raise ConfigurationError(
            f"Configuration value must be a non-empty object: {key}"
        )

    folder_policy: dict[str, str] = {}
    for label, folder in value.items():
        if not isinstance(label, str) or not label.strip():
            raise ConfigurationError(
                f"Email folder policy label must be a non-empty string: {key}"
            )
        if not isinstance(folder, str) or not folder.strip():
            raise ConfigurationError(
                f"Email folder policy folder must be a non-empty string: {key}.{label}"
            )
        folder_policy[label.strip()] = folder.strip()

    for required_label in ("review", "noise", "trash"):
        if required_label not in folder_policy:
            raise ConfigurationError(
                f"Email folder policy must include label: {required_label}"
            )

    expected_prefix = f"{folder_namespace}/"
    for label, folder in folder_policy.items():
        if label == "trash":
            if folder != "Deleted Items":
                raise ConfigurationError(
                    "Email folder policy trash target must be Deleted Items."
                )
            continue
        if not folder.startswith(expected_prefix) or folder == expected_prefix:
            raise ConfigurationError(
                f"Email folder policy folder for {label} must be under {expected_prefix}"
            )

    return folder_policy


def _require_gmail_cleanup_policy(
    settings: Mapping[str, Any],
    key: str,
    mailbox_access: Mapping[str, str],
) -> GmailCleanupPolicy:
    value = settings.get(key, {})
    if value is None:
        value = {}
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"Configuration value must be an object: {key}")

    trash_spam = value.get("trashSpam", False)
    if not isinstance(trash_spam, bool):
        raise ConfigurationError(
            f"Configuration value must be a boolean: {key}.trashSpam"
        )

    raw_mailboxes = value.get("mailboxes", [])
    if raw_mailboxes is None:
        raw_mailboxes = []
    if not isinstance(raw_mailboxes, list):
        raise ConfigurationError(
            f"Configuration value must be a list of strings: {key}.mailboxes"
        )
    if any(not isinstance(mailbox, str) or not mailbox.strip() for mailbox in raw_mailboxes):
        raise ConfigurationError(
            f"Configuration value must be a list of strings: {key}.mailboxes"
        )

    mailboxes = tuple(mailbox.strip() for mailbox in raw_mailboxes)
    if trash_spam and not mailboxes:
        raise ConfigurationError(
            "Gmail cleanup policy requires at least one mailbox when trashSpam is true."
        )
    for mailbox in mailboxes:
        access_mode = mailbox_access.get(mailbox)
        if access_mode is None:
            raise ConfigurationError(
                f"Gmail cleanup mailbox must be approved: {mailbox}"
            )
        if access_mode != "read_write":
            raise ConfigurationError(
                f"Gmail cleanup mailbox must be read_write: {mailbox}"
            )

    return GmailCleanupPolicy(trash_spam=trash_spam, mailboxes=mailboxes)
