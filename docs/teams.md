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

## Message Format

Prefer lightweight message-style notifications for simple summaries and quick
pings. The current Teams Workflows webhook renders Adaptive Card payloads but
does not render raw `{"text": "..."}` payloads in the channel, so lightweight
notifications should use a minimal Adaptive Card with one wrapped text block.
Use richer Adaptive Cards only when the message needs stronger structure,
grouped review sections, or future action buttons.

Set `msteams.width` to `Full` on Teams Adaptive Card payloads so Clarity
notifications use the available channel width when Teams honors that rendering
hint.

For Jira summaries, the preferred lightweight format is:

``` markdown
Scott Sexton

**Open COMP Jira Tickets**

- [COMP-78](https://example.atlassian.net/browse/COMP-78) - Complete August 2026 Business Tasks
- [COMP-78](https://example.atlassian.net/browse/COMP-78) - **In Progress** - Complete August 2026 Business Tasks
```

Richer cards remain appropriate for approval-heavy or action-oriented workflows.

For Gmail inbox tests, send only the requested batch size and render subjects
as best-effort Gmail message links when a Gmail message ID is available. Avoid
rendering sender email addresses as clickable links; prefer the sender display
name when present, otherwise break bare email autolinking. Format Gmail dates as
Central time using `MM/DD/YYYY HH:MM AM/PM`.

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

Two-way Teams communication should use the Teams Workflow plus Azure Storage
Queue relay design before moving Clarity into a cloud runtime. Teams Workflow
messages enter an inbound queue, and a local Clarity worker polls, validates,
processes, audits, and replies through the existing Teams notification surface.

See `docs/teams-relay-architecture.md`.

## Test

Use a non-secret local script or command that reads `TEAMS_CLARITY_WEBHOOK_URL`
from `config/.env` and posts a small JSON payload. Diagnostics should report
only whether the post succeeded, never the webhook URL.
