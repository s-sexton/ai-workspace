# Microsoft Teams

Clarity can post outbound notifications to a Microsoft Teams channel through a
Teams Workflows incoming webhook.

## Current Channel

The initial Teams notification surface is:

-   Team: `AI Workspace`
-   Channel: `Clarity`

This channel is intended for short Clarity notifications, such as test posts,
daily brief availability, pending approval counts, or attention summaries. It is
not a general log sink.

When Jira tickets are posted to Teams, each ticket key must be a hyperlink to
the actual Jira ticket. Use the browser-facing Jira ticket URL, not the
Atlassian API gateway URL.

## Local Secret

Store the webhook URL in the ignored local environment file:

``` powershell
TEAMS_CLARITY_WEBHOOK_URL=...
```

The webhook URL is a secret. Do not commit it, paste it into reports, or print
it in diagnostics.

## Webhook Type

Prefer a Teams Workflows incoming webhook over a legacy Office 365 connector
webhook. Microsoft is moving Teams webhook scenarios toward Workflows-based
webhooks, and new Clarity wiring should use that path.

## Current Capability

The current webhook is outbound only:

-   Clarity can post to the `AI Workspace` / `Clarity` channel.
-   Clarity does not yet read Teams messages.
-   Clarity does not yet process Teams replies.
-   Clarity does not approve, move, delete, create, or transition anything from
    Teams messages.

Two-way Teams communication should be implemented separately through an
approved Teams bot, outgoing webhook, or authenticated HTTP command surface.

## Test

Use a non-secret local script or command that reads `TEAMS_CLARITY_WEBHOOK_URL`
from `config/.env` and posts a small JSON payload. Diagnostics should report
only whether the post succeeded, never the webhook URL.
