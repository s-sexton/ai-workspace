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

`JIRA_CLOUD_ID` is the Atlassian cloud ID used to build the live Jira API URL:

``` text
https://api.atlassian.com/ex/jira/{JIRA_CLOUD_ID}/rest/api/3/...
```

`JIRA_EMAIL` and `JIRA_API_TOKEN` are used for Basic auth on that route,
matching the working Atlassian request shape.

Optional values may still be stored for fallback, comparison, or future auth
modes:

-   `JIRA_SITE_URL`
-   `JIRA_ACCESS_TOKEN`

Microsoft Graph runtime wiring uses these local values:

-   `GRAPH_TENANT_ID`
-   `GRAPH_CLIENT_ID`
-   `GRAPH_CLIENT_SECRET`
-   `GRAPH_ACCESS_TOKEN`

`GRAPH_TENANT_ID`, `GRAPH_CLIENT_ID`, and `GRAPH_CLIENT_SECRET` support
app-only client credentials token acquisition. `GRAPH_ACCESS_TOKEN` is available
for explicit Bearer-token experiments. These values are local secrets and must
not be committed.

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
-   Keeps Jira access tokens out of object representations
-   Keeps Graph client secrets out of object representations
-   Keeps Graph access tokens out of object representations

## Public API

Use these public objects from `common.configuration`:

-   `load_workspace_config()`
-   `find_workspace_root()`
-   `WorkspaceConfig`
-   `JiraSettings`
-   `JiraCredentials`
-   `GraphCredentials`
-   `EmailSettings`
-   `ConfigurationError`

`WorkspaceConfig.jira_settings` returns validated Jira report settings from
`config/config.json`.

`WorkspaceConfig.email_settings` returns approved mailbox settings from
`config/config.json`.

`WorkspaceConfig.require_jira_credentials()` returns Jira credentials when all
required values are present. It raises `ConfigurationError` with missing key
names when values are incomplete. Error messages must not include secret values.

`WorkspaceConfig.require_graph_credentials()` returns Microsoft Graph
credentials for client-secret token acquisition or Bearer-token experiments. It
raises `ConfigurationError` with missing key names when values are incomplete.
Error messages must not include secret values.

## Validation

The configuration subsystem currently validates the settings needed for the
Clarity Jira, email, calendar, and Graph read paths:

-   `assistant.jira.projects`: non-empty list of strings
-   `assistant.jira.maxResults`: positive integer
-   `assistant.jira.sortOrder`: non-empty string
-   `assistant.jira.reportFields`: non-empty list of strings
-   `assistant.email.approvedMailboxes`: non-empty list of mailbox objects with
    `address` and `accessMode`; optional `allowedSenders` may restrict a
    mailbox to specific senders
-   `assistant.email.defaultMailbox`: non-empty string listed in
    `approvedMailboxes`
-   `assistant.email.folderNamespace`: single folder name for assistant-managed
    move destinations
-   `assistant.email.folderPolicy`: non-empty object mapping classification
    labels to proposed folder destinations; must include `review`, `noise`, and
    `trash`
-   `assistant.email.maxMessages`: positive integer
-   `assistant.calendar.approvedCalendars`: non-empty list of calendar objects
    with `label`, `provider`, `source`, and `accessMode`
-   `assistant.calendar.defaultCalendar`: non-empty label listed in
    `approvedCalendars`
-   `assistant.calendar.maxEvents`: positive integer

Email `accessMode` must be either `read` or `read_write`. Current email
workflows only read fake metadata; `read_write` is reserved for future approved
mailbox actions.

Calendar `provider` must be `sample` or `graph`. Calendar `accessMode` must be
`read`; calendar writes are not supported. For Graph calendars, `source` is the
Graph user principal name used in the `/users/{source}/calendarView` request.

Email folder policy is used only to record proposed local actions. Non-trash
destinations must live under `assistant.email.folderNamespace`, such as
`Clarity/Review`. The trash destination must be `Deleted Items`. The current
workflow does not move messages.

Folder destinations are interpreted inside the source mailbox being reviewed.
For example, moving a message from `scott.sexton@sendthisfile.com` to
`Clarity/Review` means the `Clarity/Review` folder in that mailbox.

For the shared `clarity@sendthisfile.ai` mailbox, configure `allowedSenders`
with `scott.sexton@sendthisfile.com` and `sesexton@gmail.com`. Unauthorized
senders are classified as `trash` before content-based rules are applied.
Restricted mailbox messages must also pass authentication checks: DMARC must
pass, and either SPF or DKIM must pass. Messages with missing or failing
authentication metadata are classified as `trash`.

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
