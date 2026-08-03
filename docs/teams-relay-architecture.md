# Teams Relay Architecture

Clarity's two-way Teams path should start with a Teams Workflow plus Azure
Storage Queue relay. This keeps Teams reachable while allowing local Clarity to
remain the system that reads private context, evaluates commands, and performs
approved work.

## Goal

Let the human interact with Clarity from Teams without requiring Clarity to run
in the cloud.

The relay must support:

-   Teams messages or card actions entering a durable queue
-   Local Clarity polling for inbound work
-   Local Clarity validating the sender and command
-   Local Clarity executing read-only commands or recording pending actions
-   Teams responses being posted back to the `AI Workspace` / `Clarity` channel

## Proposed Flow

``` text
Teams Workflow
    receives a Teams command or card action
    writes a command message to Azure Storage Queue

Azure Storage Queue: clarity-inbound
    stores pending Teams commands

Local Clarity worker
    polls clarity-inbound
    validates sender, command, and action references
    runs approved local Clarity command handling
    posts a Teams response through the existing webhook
    records audit history in local memory

Azure Storage Queue: clarity-deadletter
    stores commands that fail validation or exceed retry limits
```

An outbound queue may be added later if response posting should also be
durable. The first version can let the local worker post the response directly
through `TEAMS_CLARITY_WEBHOOK_URL`.

## Azure Resources

Initial resources:

-   Storage account
-   Queue: `clarity-inbound`
-   Queue: `clarity-deadletter`

Local secret names for the queue URLs are:

``` powershell
AZURE_TEAMS_RELAY_INBOUND_QUEUE_URL=...
AZURE_TEAMS_RELAY_DEADLETTER_QUEUE_URL=...
```

Treat queue URLs with SAS tokens as secrets.

Optional future queue:

-   Queue: `clarity-outbound`

## Message Shape

Inbound queue messages should be small JSON documents:

``` json
{
  "schemaVersion": 1,
  "source": "teams",
  "commandId": "opaque-id",
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

Card actions should include an action block:

``` json
{
  "schemaVersion": 1,
  "source": "teams",
  "commandId": "opaque-id",
  "receivedAt": "2026-08-03T15:30:00Z",
  "from": {
    "displayName": "Scott Sexton",
    "email": "scott.sexton@sendthisfile.com"
  },
  "conversation": {
    "team": "AI Workspace",
    "channel": "Clarity"
  },
  "text": null,
  "action": {
    "type": "gmail_trash",
    "manifestId": "teams-message-manifest-id",
    "itemNumbers": [1, 4]
  }
}
```

## Security

The relay is not trusted just because it came from Teams.

The local worker must:

-   Allow commands only from approved sender identities
-   Validate Teams Workflow messages against a shared secret, SAS permission,
    managed identity, or equivalent queue access policy
-   Resolve item numbers only through a local Teams message manifest
-   Keep destructive or external writes behind explicit approval unless a narrow
    standing policy exists
-   Record every accepted, rejected, failed, and completed command in local
    memory
-   Never store secrets in queue messages

## Teams Message Manifests

Every actionable Teams post should write a local manifest so later replies or
card actions can safely resolve item numbers.

Example:

``` json
{
  "manifestId": "opaque-id",
  "surface": "teams",
  "createdAt": "2026-08-03T15:30:00-05:00",
  "items": [
    {
      "number": 1,
      "sourceType": "gmail",
      "mailbox": "sesexton@gmail.com",
      "externalId": "gmail-message-id",
      "subject": "Example message",
      "allowedActions": ["trash", "move_review", "move_noise"]
    }
  ]
}
```

## First Implementation Slice

The first local slice should avoid Azure dependencies:

1. Define the queue message schema as Python dataclasses. Implemented.
2. Add validation for approved Teams sender identities. Implemented.
3. Add a local fake queue for tests. Implemented.
4. Add a local Teams command processor for read-only commands. Started:
   - `show open COMP tickets`
   - `show gmail inbox`
   - `show pending approvals`
5. Record command audit entries in local memory. Implemented.
6. Add local Teams message manifests for item-number resolution. Implemented.

After that works locally, wire Azure Storage Queue as the live queue transport.

## Future Slices

-   Azure Storage Queue transport
-   Teams Workflow setup guide
-   Local worker command loop
-   Teams manifest writer
-   Card action IDs
-   Pending-action command support
-   Optional outbound queue
