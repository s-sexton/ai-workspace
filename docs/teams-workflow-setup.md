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

## Start The Watcher With Codex Scheduled

Use Codex Scheduled when you want Clarity to be supervised by Codex and show
runs in the Scheduled surface.

1. Open Codex **Scheduled**.
2. Create a new scheduled task attached to the local `ai-workspace` project.
3. Use the local project checkout, not a background worktree, because the
   watcher needs local `config/.env`, `logs`, and `reports`.
4. Set the schedule to start once when you want the watcher active, such as
   `5:00 AM` on weekdays. The worker itself handles the 30-second and 1-hour
   polling cadence after it starts.
5. Use this task prompt:

``` text
Start the local Clarity Teams relay watcher.

From the ai-workspace project root, run:

python -m assistant.src.process_teams_relay --azure --post-reply --watch --active-interval-seconds 30 --idle-interval-seconds 3600 --limit 5

Keep the process running. Do not modify files unless the command itself writes
normal Clarity logs or reports. Do not run destructive commands. Do not execute
email moves, Jira writes, calendar writes, or workflow transitions. If
authentication, network, queue, or permission errors occur, report them and
stop.
```

6. Review the first run output. If the queue is empty, expected output includes:

``` text
Processed: 0
Completed: 0
Dead-lettered: 0
Teams replies: 0
```

## Start The Watcher Manually

For a foreground manual run from PowerShell:

``` powershell
python -m assistant.src.process_teams_relay --azure --post-reply --watch --active-interval-seconds 30 --idle-interval-seconds 3600 --limit 5
```

Leave that PowerShell window open. Stop it with `Ctrl+C`.

## Test The Inbound Relay

After the watcher is running, send a small Gmail summary card:

``` powershell
python -m assistant.src.send_gmail_teams_summary --mailbox sesexton@gmail.com --limit 5 --execute
```

This posts the card, writes `reports/teams-gmail-manifest.json`, and records
the five Gmail items in local Clarity memory so future actions can resolve to
real message metadata.

To test a read-only Teams text command through the queue:

``` powershell
python -m assistant.src.enqueue_teams_relay --text "show pending approvals"
```

The watcher should consume that queue message and post a Teams reply.

To simulate a future Teams card action for item `1`:

``` powershell
python -m assistant.src.enqueue_teams_relay --action move_review --item 1 --manifest reports\teams-gmail-manifest.json
```

The watcher should consume the action and record an approved local move action
for item `1`. It does not move Gmail directly. Verify the recorded action with:

``` powershell
python -m assistant.src.ask_memory approved-actions
```

Expected output should include the Gmail subject, mailbox, and destination
classification. If the subject is missing, regenerate the Gmail Teams summary
so the manifest and Clarity memory are aligned before testing actions.

## Print A Windows Scheduled Task

Windows Task Scheduler is the fallback if Codex Scheduled is not enough. Print
the registration script:

``` powershell
python -m assistant.src.print_clarity_schedule --workflow teams-relay-worker --task-name "Clarity Teams Relay" --post-reply --watch --active-interval-seconds 30 --idle-interval-seconds 3600 --limit 5 --at 05:00
```

Review the printed script before running it. Registering the task is a local
infrastructure change and should be done by the operator.

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
