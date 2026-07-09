# Configuration

Configuration is split between committed shared settings and ignored local
secrets.

## Local Secrets

`config/.env` (ignored)

Local secrets are read from `config/.env` when it exists. Values from the
process environment override values in `config/.env` for keys listed in the
local env file or in `config/.env.example`.

## Template

`config/.env.example` (committed)

The template documents required local environment keys without storing values.
For the first Jira milestone, the expected keys are:

-   `JIRA_CLOUD_ID`
-   `JIRA_EMAIL`
-   `JIRA_API_TOKEN`

## Shared Settings

`config/config.json` (committed)

Shared non-secret settings belong in `config/config.json`.

## Shared Loader

Use `common.configuration.load_workspace_config()` to load workspace settings.

The loader:

-   Finds the workspace root by locating `config/config.json`
-   Reads committed JSON settings
-   Reads ignored local values from `config/.env` when present
-   Allows process environment values to override local env file values
-   Avoids importing unrelated process environment variables
-   Keeps Jira API tokens out of object representations

## Public API

Use these public objects from `common.configuration`:

-   `load_workspace_config()`
-   `find_workspace_root()`
-   `WorkspaceConfig`
-   `JiraSettings`
-   `JiraCredentials`
-   `ConfigurationError`

`WorkspaceConfig.jira_settings` returns validated Jira report settings from
`config/config.json`.

`WorkspaceConfig.require_jira_credentials()` returns Jira credentials when all
required values are present. It raises `ConfigurationError` with missing key
names when values are incomplete. Error messages must not include secret values.

## Validation

The configuration subsystem currently validates only the settings needed for
the first Jira report milestone:

-   `assistant.jira.projects`: non-empty list of strings
-   `assistant.jira.maxResults`: positive integer
-   `assistant.jira.sortOrder`: non-empty string
-   `assistant.jira.reportFields`: non-empty list of strings

Missing `config/.env` is allowed. Missing Jira credentials are allowed until a
caller asks for required Jira credentials.

Malformed `.env` lines raise `ConfigurationError`.

## Tests

Run configuration tests with a repository-local temporary directory and pytest
cache disabled:

``` powershell
python -m pytest tests\test_configuration.py --basetemp tests\.pytest-tmp-run -p no:cacheprovider
```

Rule: Do not configure what is not used.
