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

The client targets the Jira Cloud enhanced JQL search path:

``` text
/rest/api/3/search/jql
```

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

