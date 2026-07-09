# Jira Integration

The first Jira milestone uses a read-only Jira Cloud boundary in
`common.jira`.

## Scope

The Jira client currently supports only the first report workflow:

-   Build a configured JQL query from `JiraSettings`
-   Call Jira Cloud issue search through an injected transport
-   Normalize raw Jira issue JSON into report-friendly objects
-   Raise `JiraClientError` for failed retrieval or invalid response shape

It does not write to Jira, transition issues, schedule automation, or call an
LLM.

## Public API

Use these public objects from `common.jira`:

-   `JiraClient`
-   `JiraIssue`
-   `JiraUser`
-   `JiraIssueSearchResult`
-   `JiraClientError`
-   `UrllibJiraTransport`
-   `build_report_jql()`
-   `normalize_search_result()`

The milestone-oriented entry point is:

``` python
result = jira_client.fetch_report_issues()
```

## API Boundary

`JiraClient` accepts an injected transport instead of owning a concrete HTTP
library. The transport must provide:

``` python
response = transport.get(url, headers)
```

This keeps live Jira access isolated and lets tests use fake responses without
network calls.

`UrllibJiraTransport` is the standard-library live transport. It is used only
when a caller explicitly selects live Jira access.

The client targets the Jira Cloud enhanced JQL search path:

``` text
/rest/api/3/search/jql
```

In live mode, the client uses the Atlassian cloud ID route:

``` text
https://api.atlassian.com/ex/jira/{JIRA_CLOUD_ID}/rest/api/3/search/jql
```

By default, this route uses Basic auth from `JIRA_EMAIL` and `JIRA_API_TOKEN`,
matching the working `curl --user email:api_token` request shape. Bearer auth
can be selected explicitly with `--bearer` when `JIRA_ACCESS_TOKEN` is present.

## Normalized Issue Shape

`JiraIssue` contains the fields needed by the first Markdown report:

-   `key`
-   `summary`
-   `status`
-   `priority`
-   `assignee`
-   `updated`

Raw Jira field data is retained as `raw_fields` for future extension, but report
code should prefer the normalized attributes.

## Security

Jira credentials are passed in through `JiraCredentials`.

The client:

-   Uses read-only GET search requests
-   Does not log request headers
-   Keeps credentials out of object representations
-   Raises errors with status codes and field names, not secret values

Tests must use fake transports and must not call live Jira.

## Assistant Runner

The assistant runner defaults to static sample data:

``` powershell
python -m assistant.src.run_jira_report
```

Live Jira access requires an explicit flag:

``` powershell
python -m assistant.src.run_jira_report --live
```

Live mode requires `JIRA_CLOUD_ID`, `JIRA_EMAIL`, and `JIRA_API_TOKEN` from
`config/.env` or expected process environment values.

### Safe Diagnostics

To troubleshoot live Jira without exposing secrets:

``` powershell
python -m assistant.src.run_jira_report --live --show-query
```

To override JQL temporarily:

``` powershell
python -m assistant.src.run_jira_report --live --show-query --jql "project = STF ORDER BY updated DESC"
```

The diagnostic output must not include headers, API tokens, access tokens, or
credentials.
