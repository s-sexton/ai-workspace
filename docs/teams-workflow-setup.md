# Teams Workflow Relay Setup

This guide describes the Teams Workflow side of Clarity's two-way Teams relay.
The local worker remains the trusted decision point. The workflow should only
place small command messages into Azure Storage Queue.

## Existing Resources

The current Azure resources are:

-   Subscription: `stf-biz`
-   Resource group: `rg-ai-workspace`
-   Storage account: `staiworkspacestf`
-   Inbound queue: `clarity-inbound`
-   Dead-letter queue: `clarity-deadletter`

Local Clarity reads the queue URLs from `config/.env`:

``` powershell
AZURE_TEAMS_RELAY_INBOUND_QUEUE_URL=...
AZURE_TEAMS_RELAY_DEADLETTER_QUEUE_URL=...
```

These values include SAS tokens and must be treated as secrets.

## Workflow Responsibility

The Teams Workflow should:

1. Trigger from a message or action in the `AI Workspace` / `Clarity` channel.
2. Build a small relay JSON payload.
3. Write that payload to the `clarity-inbound` queue.
4. Avoid reading email, Jira, calendars, files, or secrets.
5. Avoid performing any action requested by the user directly.

The workflow is only the transport. Local Clarity validates sender identity,
routes commands, records audit history, and decides whether a command is
supported.

## Queue Message

Use this shape for inbound messages:

``` json
{
  "schemaVersion": 1,
  "source": "teams",
  "commandId": "workflow-run-or-guid",
  "receivedAt": "2026-08-03T15:30:00Z",
  "from": {
    "displayName": "Scott Sexton",
    "email": "scott.sexton@sendthisfile.com",
    "aadObjectId": "optional"
  },
  "conversation": {
    "team": "AI Workspace",
    "channel": "Clarity",
    "messageId": "optional",
    "replyToId": "optional"
  },
  "text": "show open COMP tickets",
  "action": null
}
```

For card actions, send `text` as `null` and include an `action` object:

``` json
{
  "type": "gmail_trash",
  "manifestId": "teams-message-manifest-id",
  "itemNumbers": [1, 4]
}
```

Supported card actions are intentionally limited to recording local approval
state. They do not move, delete, archive, or modify provider data directly.
The current supported email action types are:

-   `trash`
-   `move_review`
-   `move_noise`

Each action must include a `manifestId` and `itemNumbers`. Local Clarity
resolves those numbers through the matching Teams message manifest before
recording an approved local action.

## Message Encoding

The local Azure queue reader accepts either:

-   Plain JSON message text
-   Base64-encoded JSON message text

Plain JSON is easier for Teams Workflows. Base64 JSON matches the local REST
smoke helpers.

## Local Worker

Run the worker from the workspace root:

``` powershell
python -m assistant.src.process_teams_relay --azure --post-reply --limit 5
```

For a long-running local watcher:

``` powershell
python -m assistant.src.process_teams_relay --azure --post-reply --watch --active-interval-seconds 30 --idle-interval-seconds 3600 --limit 5
```

The default active window is Monday-Friday from 5:00 AM through 6:59 PM Central.
During active hours, the watcher sleeps 30 seconds between polls. Outside that
window, it sleeps one hour between polls.

Supported commands are read-only:

-   `show open COMP tickets`
-   `show Gmail inbox`
-   `show pending approvals`

Successful commands and supported manifest-backed card actions are completed in
`clarity-inbound`. Rejected senders, unsupported commands, unsupported actions,
and failed commands are moved to `clarity-deadletter`.

## Security Checks

The workflow should carry the Teams sender email and, when available, the Entra
object ID. The local worker currently enforces the approved sender email list.
Future hardening should add object ID validation before Teams becomes an
approval or write surface.

Do not place secrets, raw email bodies, message attachments, calendar details,
or Jira descriptions into queue messages. Put only the command/action and enough
metadata to audit where it came from.

Provider writes remain separate. After a Teams action records an approved local
cleanup action, local Clarity must still run the existing provider executor,
such as:

``` powershell
python -m assistant.src.execute_email_moves --gmail --execute
python -m assistant.src.execute_email_moves --graph --execute
```
