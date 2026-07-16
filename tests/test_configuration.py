from __future__ import annotations

import os

import pytest

from common.configuration import ConfigurationError, find_workspace_root, load_workspace_config


def test_load_workspace_config_reads_json_and_env_file(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        '{"workspace": {"name": "Test Workspace"}}',
        encoding="utf-8",
    )
    (config_dir / ".env").write_text(
        "JIRA_CLOUD_ID=test-cloud\nJIRA_SITE_URL=https://test.atlassian.net\nJIRA_EMAIL=user@example.com\nJIRA_API_TOKEN=secret\nJIRA_ACCESS_TOKEN=access-secret\nGRAPH_TENANT_ID=tenant\nGRAPH_CLIENT_ID=client\nGRAPH_CLIENT_SECRET=graph-secret\nGRAPH_ACCESS_TOKEN=graph-access\nGOOGLE_CLIENT_ID=google-client\nGOOGLE_CLIENT_SECRET=google-secret\nGOOGLE_REFRESH_TOKEN=google-refresh\nGOOGLE_ACCESS_TOKEN=google-access\nOPENAI_API_KEY=openai-secret\nOPENAI_MODEL=gpt-test\nOPENAI_BASE_URL=https://openai.example/v1\n",
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    assert config.root == tmp_path
    assert config.settings["workspace"]["name"] == "Test Workspace"
    assert config.jira_credentials.cloud_id == "test-cloud"
    assert config.jira_credentials.site_url == "https://test.atlassian.net"
    assert config.jira_credentials.email == "user@example.com"
    assert config.jira_credentials.api_token == "secret"
    assert config.jira_credentials.access_token == "access-secret"
    assert config.jira_credentials.is_complete
    assert config.graph_credentials.tenant_id == "tenant"
    assert config.graph_credentials.client_id == "client"
    assert config.graph_credentials.client_secret == "graph-secret"
    assert config.graph_credentials.access_token == "graph-access"
    assert config.graph_credentials.is_client_secret_complete
    assert config.graph_credentials.is_bearer_auth_complete
    assert config.google_credentials.client_id == "google-client"
    assert config.google_credentials.client_secret == "google-secret"
    assert config.google_credentials.refresh_token == "google-refresh"
    assert config.google_credentials.access_token == "google-access"
    assert config.google_credentials.is_refresh_token_complete
    assert config.google_credentials.is_bearer_auth_complete
    assert config.openai_credentials.api_key == "openai-secret"
    assert config.openai_credentials.model == "gpt-test"
    assert config.openai_credentials.base_url == "https://openai.example/v1"
    assert config.openai_credentials.is_complete


def test_require_openai_credentials_reports_missing_values(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    (config_dir / ".env").write_text("OPENAI_API_KEY=secret\n", encoding="utf-8")

    config = load_workspace_config(tmp_path, include_process_env=False)

    with pytest.raises(ConfigurationError) as exc_info:
        config.require_openai_credentials()

    assert "OPENAI_MODEL" in str(exc_info.value)


def test_jira_settings_are_validated_and_typed(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "jira": {
              "projects": ["STF", "SUPP"],
              "maxResults": 25,
              "sortOrder": "updated DESC",
              "reportFields": ["key", "summary"]
            }
          }
        }
        """,
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)
    jira_settings = config.jira_settings

    assert jira_settings.projects == ("STF", "SUPP")
    assert jira_settings.max_results == 25
    assert jira_settings.sort_order == "updated DESC"
    assert jira_settings.report_fields == ("key", "summary")


def test_email_settings_are_validated_and_typed(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "email": {
              "approvedMailboxes": [
                {
                  "address": "inbox@example.invalid",
                  "accessMode": "read_write",
                  "allowedSenders": [
                    "scott.sexton@sendthisfile.com",
                    "sesexton@gmail.com"
                  ]
                },
                {"address": "legal@example.invalid", "accessMode": "read"}
              ],
              "defaultMailbox": "inbox@example.invalid",
              "folderNamespace": "Clarity",
              "folderPolicy": {
                "review": "Clarity/Review",
                "noise": "Clarity/Noise",
                "trash": "Deleted Items"
              },
              "gmailCleanupPolicy": {
                "trashSpam": true,
                "mailboxes": ["inbox@example.invalid"]
              },
              "maxMessages": 50
            }
          }
        }
        """,
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)
    email_settings = config.email_settings

    assert email_settings.approved_mailboxes == (
        "inbox@example.invalid",
        "legal@example.invalid",
    )
    assert email_settings.access_mode_for("inbox@example.invalid") == "read_write"
    assert email_settings.access_mode_for("legal@example.invalid") == "read"
    assert email_settings.access_mode_for("missing@example.invalid") is None
    assert email_settings.allowed_senders_for("inbox@example.invalid") == (
        "scott.sexton@sendthisfile.com",
        "sesexton@gmail.com",
    )
    assert email_settings.allowed_senders_for("legal@example.invalid") == ()
    assert email_settings.folder_namespace == "Clarity"
    assert email_settings.folder_for_label("review") == "Clarity/Review"
    assert email_settings.folder_for_label("noise") == "Clarity/Noise"
    assert email_settings.folder_for_label("trash") == "Deleted Items"
    assert email_settings.folder_for_label("unknown") is None
    assert email_settings.gmail_cleanup_policy.trash_spam is True
    assert email_settings.gmail_cleanup_policy.mailboxes == ("inbox@example.invalid",)
    assert email_settings.default_mailbox == "inbox@example.invalid"
    assert email_settings.max_messages == 50


def test_email_gmail_cleanup_policy_defaults_to_disabled(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "email": {
              "approvedMailboxes": [
                {"address": "inbox@example.invalid", "accessMode": "read_write"}
              ],
              "defaultMailbox": "inbox@example.invalid",
              "folderNamespace": "Clarity",
              "folderPolicy": {
                "review": "Clarity/Review",
                "noise": "Clarity/Noise",
                "trash": "Deleted Items"
              },
              "maxMessages": 50
            }
          }
        }
        """,
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)
    email_settings = config.email_settings

    assert email_settings.gmail_cleanup_policy.trash_spam is False
    assert email_settings.gmail_cleanup_policy.mailboxes == ()


def test_email_gmail_cleanup_policy_requires_read_write_mailbox(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "email": {
              "approvedMailboxes": [
                {"address": "inbox@example.invalid", "accessMode": "read"}
              ],
              "defaultMailbox": "inbox@example.invalid",
              "folderNamespace": "Clarity",
              "folderPolicy": {
                "review": "Clarity/Review",
                "noise": "Clarity/Noise",
                "trash": "Deleted Items"
              },
              "gmailCleanupPolicy": {
                "trashSpam": true,
                "mailboxes": ["inbox@example.invalid"]
              },
              "maxMessages": 50
            }
          }
        }
        """,
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    with pytest.raises(ConfigurationError) as exc_info:
        config.email_settings

    assert "read_write" in str(exc_info.value)


def test_calendar_settings_are_validated_and_typed(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "calendar": {
              "approvedCalendars": [
                {
                  "label": "family",
                  "provider": "sample",
                  "source": "family",
                  "accessMode": "read"
                },
                {
                  "label": "work",
                  "provider": "graph",
                  "source": "scott.sexton@example.invalid",
                  "accessMode": "read_write"
                },
                {
                  "label": "google-family",
                  "provider": "google",
                  "source": "family-calendar@example.invalid",
                  "accessMode": "read"
                }
              ],
              "defaultCalendar": "family",
              "maxEvents": 50
            }
          }
        }
        """,
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)
    calendar_settings = config.calendar_settings

    assert tuple(calendar_settings.approved_calendars) == (
        "family",
        "work",
        "google-family",
    )
    family = calendar_settings.scope_for("family")
    work = calendar_settings.scope_for("work")
    google_family = calendar_settings.scope_for("google-family")
    assert family is not None
    assert family.provider == "sample"
    assert family.source == "family"
    assert work is not None
    assert work.provider == "graph"
    assert work.source == "scott.sexton@example.invalid"
    assert work.access_mode == "read_write"
    assert google_family is not None
    assert google_family.provider == "google"
    assert google_family.source == "family-calendar@example.invalid"
    assert calendar_settings.default_calendar == "family"
    assert calendar_settings.max_events == 50


def test_calendar_default_calendar_must_be_approved(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "calendar": {
              "approvedCalendars": [
                {
                  "label": "family",
                  "provider": "sample",
                  "source": "family",
                  "accessMode": "read"
                }
              ],
              "defaultCalendar": "work",
              "maxEvents": 50
            }
          }
        }
        """,
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    with pytest.raises(ConfigurationError) as exc_info:
        config.calendar_settings

    assert "defaultCalendar" in str(exc_info.value)


def test_calendar_provider_must_be_valid(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "calendar": {
              "approvedCalendars": [
                {
                  "label": "family",
                  "provider": "icloud",
                  "source": "family",
                  "accessMode": "read"
                }
              ],
              "defaultCalendar": "family",
              "maxEvents": 50
            }
          }
        }
        """,
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    with pytest.raises(ConfigurationError) as exc_info:
        config.calendar_settings

    assert "provider" in str(exc_info.value)


def test_email_default_mailbox_must_be_approved(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "email": {
              "approvedMailboxes": [
                {"address": "legal@example.invalid", "accessMode": "read"}
              ],
              "defaultMailbox": "inbox@example.invalid",
              "folderNamespace": "Clarity",
              "folderPolicy": {
                "review": "Clarity/Review",
                "noise": "Clarity/Noise",
                "trash": "Deleted Items"
              },
              "maxMessages": 50
            }
          }
        }
        """,
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    with pytest.raises(ConfigurationError) as exc_info:
        config.email_settings

    assert "defaultMailbox" in str(exc_info.value)


def test_email_mailbox_access_mode_must_be_valid(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "email": {
              "approvedMailboxes": [
                {"address": "inbox@example.invalid", "accessMode": "admin"}
              ],
              "defaultMailbox": "inbox@example.invalid",
              "folderNamespace": "Clarity",
              "folderPolicy": {
                "review": "Clarity/Review",
                "noise": "Clarity/Noise",
                "trash": "Deleted Items"
              },
              "maxMessages": 50
            }
          }
        }
        """,
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    with pytest.raises(ConfigurationError) as exc_info:
        config.email_settings

    assert "accessMode" in str(exc_info.value)


def test_email_allowed_senders_must_be_strings(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "email": {
              "approvedMailboxes": [
                {
                  "address": "clarity@sendthisfile.ai",
                  "accessMode": "read",
                  "allowedSenders": ["scott.sexton@sendthisfile.com", 123]
                }
              ],
              "defaultMailbox": "clarity@sendthisfile.ai",
              "folderNamespace": "Clarity",
              "folderPolicy": {
                "review": "Clarity/Review",
                "noise": "Clarity/Noise",
                "trash": "Deleted Items"
              },
              "maxMessages": 50
            }
          }
        }
        """,
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    with pytest.raises(ConfigurationError) as exc_info:
        config.email_settings

    assert "allowedSenders" in str(exc_info.value)


def test_email_folder_policy_must_include_required_labels(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "email": {
              "approvedMailboxes": [
                {"address": "inbox@example.invalid", "accessMode": "read"}
              ],
              "defaultMailbox": "inbox@example.invalid",
              "folderNamespace": "Clarity",
              "folderPolicy": {
                "review": "Clarity/Review"
              },
              "maxMessages": 50
            }
          }
        }
        """,
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    with pytest.raises(ConfigurationError) as exc_info:
        config.email_settings

    assert "noise" in str(exc_info.value)


def test_email_folder_policy_must_use_folder_namespace(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "email": {
              "approvedMailboxes": [
                {"address": "inbox@example.invalid", "accessMode": "read"}
              ],
              "defaultMailbox": "inbox@example.invalid",
              "folderNamespace": "Clarity",
              "folderPolicy": {
                "review": "Review",
                "noise": "Other/Noise",
                "trash": "Deleted Items"
              },
              "maxMessages": 50
            }
          }
        }
        """,
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    with pytest.raises(ConfigurationError) as exc_info:
        config.email_settings

    assert "Clarity/" in str(exc_info.value)


def test_email_folder_namespace_must_be_single_folder_name(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "email": {
              "approvedMailboxes": [
                {"address": "inbox@example.invalid", "accessMode": "read"}
              ],
              "defaultMailbox": "inbox@example.invalid",
              "folderNamespace": "Clarity/Review",
              "folderPolicy": {
                "review": "Clarity/Review",
                "noise": "Clarity/Noise",
                "trash": "Deleted Items"
              },
              "maxMessages": 50
            }
          }
        }
        """,
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    with pytest.raises(ConfigurationError) as exc_info:
        config.email_settings

    assert "folderNamespace" in str(exc_info.value)


def test_process_environment_overrides_local_env_file(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    (config_dir / ".env.example").write_text("JIRA_API_TOKEN=\n", encoding="utf-8")
    (config_dir / ".env").write_text("JIRA_API_TOKEN=from-file\n", encoding="utf-8")
    monkeypatch.setenv("JIRA_API_TOKEN", "from-process")

    config = load_workspace_config(tmp_path)

    assert config.jira_credentials.api_token == "from-process"


def test_require_jira_credentials_returns_complete_credentials(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    (config_dir / ".env").write_text(
        "JIRA_CLOUD_ID=test-cloud\nJIRA_EMAIL=user@example.com\nJIRA_API_TOKEN=secret\n",
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    assert config.require_jira_credentials().is_cloud_route_complete


def test_require_jira_credentials_can_validate_bearer_auth_values(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    (config_dir / ".env").write_text(
        "JIRA_CLOUD_ID=test-cloud\nJIRA_ACCESS_TOKEN=access-secret\n",
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    assert config.require_jira_credentials(use_bearer_auth=True).is_bearer_auth_complete


def test_require_graph_credentials_returns_complete_client_secret_values(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    (config_dir / ".env").write_text(
        "GRAPH_TENANT_ID=tenant\nGRAPH_CLIENT_ID=client\nGRAPH_CLIENT_SECRET=secret\n",
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    assert config.require_graph_credentials().is_client_secret_complete


def test_require_graph_credentials_can_validate_bearer_auth_values(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    (config_dir / ".env").write_text(
        "GRAPH_ACCESS_TOKEN=access-token\n",
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    assert config.require_graph_credentials(use_bearer_auth=True).is_bearer_auth_complete


def test_require_google_credentials_returns_complete_refresh_values(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    (config_dir / ".env").write_text(
        "GOOGLE_CLIENT_ID=client\nGOOGLE_CLIENT_SECRET=secret\nGOOGLE_REFRESH_TOKEN=refresh\n",
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    assert config.require_google_credentials().is_refresh_token_complete


def test_require_google_credentials_can_validate_bearer_auth_values(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    (config_dir / ".env").write_text(
        "GOOGLE_ACCESS_TOKEN=access-token\n",
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    assert config.require_google_credentials(use_bearer_auth=True).is_bearer_auth_complete


def test_require_google_credentials_reports_missing_values_without_secret_values(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    (config_dir / ".env").write_text(
        "GOOGLE_CLIENT_ID=client\nGOOGLE_CLIENT_SECRET=super-secret\n",
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    with pytest.raises(ConfigurationError) as exc_info:
        config.require_google_credentials()

    message = str(exc_info.value)
    assert "GOOGLE_REFRESH_TOKEN" in message
    assert "super-secret" not in message


def test_require_graph_credentials_reports_missing_values_without_secret_values(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    (config_dir / ".env").write_text(
        "GRAPH_TENANT_ID=tenant\nGRAPH_CLIENT_SECRET=super-secret\n",
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    with pytest.raises(ConfigurationError) as exc_info:
        config.require_graph_credentials()

    message = str(exc_info.value)
    assert "GRAPH_CLIENT_ID" in message
    assert "super-secret" not in message


def test_require_jira_credentials_can_validate_basic_auth_values(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    (config_dir / ".env").write_text(
        "JIRA_SITE_URL=https://test.atlassian.net\nJIRA_EMAIL=user@example.com\nJIRA_API_TOKEN=secret\n",
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    assert config.require_jira_credentials(use_cloud_route=False).is_basic_auth_complete


def test_require_jira_credentials_reports_missing_keys_without_secret_values(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    (config_dir / ".env").write_text(
        "JIRA_CLOUD_ID=test-cloud\nJIRA_API_TOKEN=secret\n",
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    with pytest.raises(ConfigurationError) as exc_info:
        config.require_jira_credentials()

    message = str(exc_info.value)
    assert "JIRA_EMAIL" in message
    assert "secret" not in message


def test_missing_local_env_file_is_allowed(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")

    config = load_workspace_config(tmp_path, include_process_env=False)

    assert config.env == {}
    assert not config.jira_credentials.is_complete


def test_find_workspace_root_walks_up_from_child_directory(tmp_path):
    config_dir = tmp_path / "config"
    child_dir = tmp_path / "assistant" / "src"
    config_dir.mkdir()
    child_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text("{}", encoding="utf-8")

    assert find_workspace_root(child_dir) == tmp_path


def test_secret_values_are_not_in_object_repr(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    (config_dir / ".env").write_text("JIRA_API_TOKEN=super-secret\n", encoding="utf-8")

    config = load_workspace_config(tmp_path, include_process_env=False)

    assert "super-secret" not in repr(config)
    assert "super-secret" not in repr(config.jira_credentials)


def test_settings_mapping_is_read_only(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")

    config = load_workspace_config(tmp_path, include_process_env=False)

    with pytest.raises(TypeError):
        config.settings["new"] = "value"


def test_invalid_json_raises_configuration_error(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{", encoding="utf-8")

    with pytest.raises(ConfigurationError):
        load_workspace_config(tmp_path, include_process_env=False)


def test_malformed_env_line_raises_configuration_error(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    (config_dir / ".env").write_text("JIRA_API_TOKEN\n", encoding="utf-8")

    with pytest.raises(ConfigurationError):
        load_workspace_config(tmp_path, include_process_env=False)


@pytest.mark.parametrize(
    ("jira_config", "expected_message"),
    [
        ('{"projects": [], "maxResults": 10, "sortOrder": "updated DESC", "reportFields": ["key"]}', "projects"),
        ('{"projects": ["STF"], "maxResults": 0, "sortOrder": "updated DESC", "reportFields": ["key"]}', "maxResults"),
        ('{"projects": ["STF"], "maxResults": 10, "sortOrder": "", "reportFields": ["key"]}', "sortOrder"),
        ('{"projects": ["STF"], "maxResults": 10, "sortOrder": "updated DESC", "reportFields": []}', "reportFields"),
    ],
)
def test_invalid_jira_settings_raise_configuration_error(
    tmp_path,
    jira_config,
    expected_message,
):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        f'{{"assistant": {{"jira": {jira_config}}}}}',
        encoding="utf-8",
    )

    config = load_workspace_config(tmp_path, include_process_env=False)

    with pytest.raises(ConfigurationError) as exc_info:
        config.jira_settings

    assert expected_message in str(exc_info.value)


def test_loader_does_not_import_unrelated_process_environment(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setitem(os.environ, "UNRELATED_SECRET", "do-not-load")

    config = load_workspace_config(tmp_path)

    assert "UNRELATED_SECRET" not in config.env
