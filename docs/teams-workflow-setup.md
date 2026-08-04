# Teams Relay Setup

This guide describes the Teams-to-Clarity relay. The local worker remains the
trusted decision point. The cloud-side workflow should only place small command
messages into Azure Storage Queue.

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

The Teams workflow or Logic App should:

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

When watch mode starts, Clarity writes the running process ID to:

``` text
logs/clarity-teams-relay.pid
```

Check the recorded PID from PowerShell:

``` powershell
Get-Content logs\clarity-teams-relay.pid
```

The PID file is removed when the watcher exits normally. If Windows or Codex
terminates the process abruptly, the file can become stale, so confirm the PID
exists before relying on it:

``` powershell
$pidValue = Get-Content logs\clarity-teams-relay.pid
Get-Process -Id $pidValue
```

Use `--pid-file <path>` only when running a second watcher that needs a distinct
status file.

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

The watcher should consume that queue message and post a Teams reply. Relay
replies are capped to a Teams-safe length. If a command produces a large
response, the Teams card is truncated and the local Clarity memory keeps the
full command audit.

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

After queue URLs, webhook URL, and approved Teams sender identity are configured,
run the relay preflight. It reports whether required values are present without
printing the secret URLs:

``` powershell
python -m assistant.src.check_clarity_setup --mailbox clarity@sendthisfile.ai --teams-relay
```

Supported commands are read-only:

-   `show open COMP tickets`
-   `show Gmail inbox`
-   `show pending approvals`
-   `Clarity show email move plan`
-   `Clarity health`
-   `Clarity trash 1 2`
-   `Clarity review 3`
-   `Clarity noise 4 5`
-   `Clarity add this to your learning list: [request]`

Successful commands and supported manifest-backed card actions are completed in
`clarity-inbound`. Rejected senders, unsupported commands, unsupported actions,
and failed commands are moved to `clarity-deadletter`.

The numbered action commands operate on the latest local Teams manifest, which
is normally written when Clarity sends a Gmail inbox summary to Teams. They
record approved local email actions only. Provider moves/deletes still require
the email move executor.

Use `Clarity show email move plan` to preview the currently approved provider
move/delete plan from Teams before executing provider writes locally.

When `--post-reply` is enabled, Clarity records a `post_teams_relay_reply` audit
entry with the Teams webhook status code after a successful reply post.
Unsupported commands receive a Teams reply that starts with `I don't understand
what you are asking yet` before the queue message is dead-lettered for audit.

The learning-list command records a local delegated task titled `Clarity
learning request`. It does not change Clarity's behavior automatically. A human
or assistant must review the task and decide whether to implement a new
deterministic command, mailbox rule, or policy update.

Use `Clarity health` as the first smoke test after changing the Logic App,
queue settings, webhook, or local watcher. It reports the local processor PID,
the watcher PID file value, configured sender identity counts, and the most
recent Teams reply audit entry without touching mail, calendar, or Jira data.

## Security Checks

The workflow should carry the Teams sender email and, when available, the Entra
object ID. The local worker enforces the approved sender email list and, when
`assistant.teamsRelay.requireAadObjectId` is true, the approved Entra object ID
list.

Configure approved Teams identities in `config/config.json`:

``` json
"teamsRelay": {
  "requireAadObjectId": true,
  "approvedSenders": [
    {
      "email": "scott.sexton@sendthisfile.com",
      "aadObjectId": "entra-object-id-from-teams"
    }
  ]
}
```

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

## Logic App Relay Option

Use an Azure Logic App when Power Automate requires a Premium license for the
Azure Queue Storage action. Prefer a Consumption Logic App for the first relay
because the workflow is small and event-driven.

The Logic App should be:

-   Name: `logic-clarity-teams-relay`
-   Resource group: `rg-ai-workspace`
-   Region: same region as the storage account when practical
-   Plan type: `Consumption`

The Logic App workflow should be:

``` text
Microsoft Teams trigger
-> For each notification
-> Microsoft Teams: Get message details
-> Office 365 Users: Get user profile (V2)
-> Condition
-> Azure Queue Storage: Put a message on a queue
```

Use the Microsoft Teams trigger named like `When a new message is added to a
chat or channel`.

Configure the trigger for:

-   Team: `AI Workspace`
-   Channel: `Clarity`

After `Get message details`, add `Office 365 Users - Get user profile (V2)`.
For the user ID, use the sender user ID from `Get message details`. If the
designer requires an expression, use:

``` text
body('Get_message_details')?['from']?['user']?['id']
```

Add a condition before the queue action. The condition should only continue
when the sender is the human operator and either the message mentions Clarity or
the message is a reply in the channel thread.

If the designer only allows row-based conditions, model this logic:

``` text
Body PlainTextContent contains Clarity
```

Add a sender check using the profile action:

``` text
Mail equals scott.sexton@sendthisfile.com
```

If `Mail` is empty in your tenant, use:

``` text
User Principal Name equals scott.sexton@sendthisfile.com
```

The local worker also rejects unapproved sender emails and object IDs before
routing commands.

In the true branch, add the Azure Queue Storage action named like `Put a
message on a queue`. Configure it for:

-   Storage account: `staiworkspacestf`
-   Queue: `clarity-inbound`

Use this message content:

``` json
{
  "schemaVersion": 1,
  "source": "teams",
  "commandId": "@{workflow()?['run']['name']}",
  "receivedAt": "@{utcNow()}",
  "from": {
    "displayName": "@{body('Get_message_details')?['from']?['user']?['displayName']}",
    "email": "@{coalesce(body('Get_user_profile_(V2)')?['mail'], body('Get_user_profile_(V2)')?['userPrincipalName'])}",
    "aadObjectId": "@{body('Get_message_details')?['from']?['user']?['id']}"
  },
  "conversation": {
    "team": "AI Workspace",
    "channel": "Clarity",
    "messageId": "@{items('For_each')?['messageId']}",
    "replyToId": "@{items('For_each')?['replyToMessageId']}"
  },
  "text": "@{body('Get_message_details')?['body']?['plainTextContent']}",
  "action": null
}
```

The extra profile lookup is necessary because the Teams `Get message details`
action can return an empty sender email even when the message came from the
connected user. Keep the Logic App trigger and condition restricted to the
Clarity channel and add object ID validation before using Teams as an
approval/write surface.

Validate the pasted message content carefully. In particular, the closing
`from` object must be followed by a comma before `conversation`:

``` json
  },
  "conversation": {
```

Malformed JSON is moved to the dead-letter queue by the local watcher and will
not produce a Teams reply.

Leave the false branch empty.

After saving the Logic App, test from Teams with:

``` text
Clarity show pending approvals
```

The local watcher should consume the queue message and post a reply back to the
Clarity channel within the configured polling interval.

If no reply appears, check the Logic App run history first. If the run
succeeded, run a one-shot local poll from the workspace root:

``` powershell
python -m assistant.src.process_teams_relay --azure --post-reply --limit 1
```

Expected successful output includes one processed and completed message. If the
message is rejected, inspect the sender email carried by the Logic App payload
and update the local allowed sender list only after confirming the value is the
operator's real Teams identity.
