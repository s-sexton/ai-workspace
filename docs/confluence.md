# Confluence Integration

Confluence is an approved documentation surface for sanitized workspace
knowledge.

## Visibility Boundary

The current Confluence environment uses the free tier. Treat Confluence as
broadly visible unless a future access model is verified and documented.

Do not publish any of the following to Confluence:

-   PII or private personal data
-   Keys, secrets, credentials, tokens, or authentication material
-   Raw mailbox content or private email bodies
-   Sensitive operational details
-   Confidential business, legal, compliance, financial, customer, or personal
    data

Confluence pages should contain sanitized role documentation, operating
guidance, high-level summaries, and links only when the target material is also
safe for broad visibility.

## Authentication

Confluence uses service-account OAuth credentials loaded from local environment
values.

Required local values:

-   `JIRA_CLOUD_ID`
-   `JIRA_SITE_URL`
-   `CONFLUENCE_OAUTH_CLIENT_ID`
-   `CONFLUENCE_OAUTH_CLIENT_SECRET`

`JIRA_CLOUD_ID` is reused for the Atlassian API gateway:

``` text
https://api.atlassian.com/ex/confluence/{JIRA_CLOUD_ID}/wiki/api/v2/...
```

`JIRA_SITE_URL` is reused for human-facing Confluence links with `/wiki`
appended when needed.

Do not log, print, commit, paste, or publish OAuth client secrets.

## Configuration API

Use `common.configuration.load_workspace_config()` and then:

``` python
config = load_workspace_config(include_process_env=True)
credentials = config.require_confluence_credentials()
```

This returns a `ConfluenceCredentials` object with:

-   `cloud_id`
-   `site_url`
-   `oauth_client_id`
-   `oauth_client_secret`

The secret fields are excluded from object representations.

## OAuth Token Exchange

Exchange the Confluence OAuth client credentials with Atlassian:

``` text
POST https://auth.atlassian.com/oauth/token
grant_type=client_credentials
client_id=...
client_secret=...
```

Then call Confluence with:

``` text
Authorization: Bearer <access token>
Accept: application/json
```

The access token is also secret material. Do not log or publish it.

## Read Pattern

Use read calls first to confirm the target space and parent page are visible:

``` text
GET /wiki/api/v2/spaces?limit=250
GET /wiki/api/v2/pages?space-id={spaceId}&limit=250
GET /wiki/api/v2/pages/{pageId}
```

For Clarity documentation, the expected space is:

-   Space name: `AI Workspace`
-   Space key: `AIWS`

The current Clarity parent page is:

-   Page title: `Clarity`

## Write Pattern

Only write after the human approves the specific Confluence action and after
the content has been checked for broad visibility.

Create a normal published page with:

``` text
POST /wiki/api/v2/pages
```

Use a payload shaped like:

``` json
{
  "spaceId": "SPACE_ID",
  "status": "current",
  "title": "Safe public-safe title",
  "parentId": "OPTIONAL_PARENT_PAGE_ID",
  "body": {
    "representation": "storage",
    "value": "<p>Sanitized page content.</p>"
  }
}
```

Use `status: "current"` for a visible published page. Do not create draft-only
tests when the goal is human visibility verification.

## Role Expectations

Other agents and analysts may use Confluence for sanitized documentation in
their role areas, but they must stay inside their own RRE decision rights.

If the requested Confluence write includes sensitive details, unclear audience,
credentials, private content, or a business/legal/compliance commitment,
escalate to the human before writing.

Clarity owns broad communication patterns and may relay documentation guidance,
but another role remains accountable for whether its own content is safe to
publish.
