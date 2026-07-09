# Email

## Current Milestone

The current email milestone keeps reads and writes explicit:

-   Read fake mailbox metadata by default
-   Optionally read approved mailbox metadata from Microsoft Graph with
    `--graph`
-   Require the mailbox to be listed in local approved mailbox config
-   Normalize message metadata
-   Apply deterministic placeholder classifications
-   Apply mailbox sender allow-list and authentication rules before content rules
-   Store metadata, hashes, and classifications in local Clarity memory
-   Propose review/noise/trash folder destinations from local policy
-   Generate the local Clarity brief
-   Surface both review and noise classifications for inspection
-   Allow approved move proposals to be executed only with explicit
    `--graph --execute`

By default it does not connect to live Exchange, Gmail, or Microsoft Graph.
Explicit `--graph` review mode reads message metadata from Microsoft Graph, but
does not send, move, archive, or delete email. Folder moves are recorded first
as proposed local actions that require approval.

## Shared Boundary

`common.email` owns the reusable email metadata boundary:

-   `EmailClient`
-   `EmailMoveClient`
-   `EmailTransport`
-   `EmailMoveTransport`
-   `EmailMessage`
-   `EmailFolderProposal`
-   `EmailMoveRequest`
-   `EmailMoveResult`
-   `StaticEmailTransport`
-   `StaticEmailMoveTransport`
-   `StaticGraphEmailTransport`
-   `classify_email_message`
-   `graph_message_to_email_payload`
-   `propose_email_folder_action`

Assistant workflows consume normalized `EmailMessage` objects. They should not
parse provider-specific payloads directly.

`EmailMoveClient` is the small write-side boundary for moving one message inside
one mailbox. The command-line execution path requires both an approved local
move action and explicit `--graph --execute` flags.

`common.graph_email` contains the Microsoft Graph-specific runtime adapters:

-   `GraphClientCredentialsTokenProvider` requests app-only Graph tokens with
    the Microsoft identity client credentials flow.
-   `GraphEmailReadTransport` lists message metadata and fetches message headers
    for spoof/authentication checks.
-   `GraphEmailMoveTransport` resolves mailbox folder paths and calls the Graph
    message move API.
-   `UrllibGraphTransport` and `UrllibGraphTokenTransport` are standard-library
    HTTP adapters.

These adapters are isolated from the assistant workflow so they can be tested
with fake transports before live Graph writes are enabled.

`assistant.src.execute_email_moves.build_graph_move_transport_from_config()`
loads local Graph credentials and builds the Graph move transport for future
approved live execution paths. The public command-line execution path still
does not call this helper.

`assistant.src.run_email_review.build_graph_read_transport_from_config()` loads
local Graph credentials and builds the Graph read transport for explicit live
review paths. The public command-line review path still defaults to fake local
data unless `--graph` is passed.

## Approved Mailboxes

Approved mailbox scope is configured in `config/config.json`:

``` json
{
  "assistant": {
    "email": {
      "approvedMailboxes": [
        {
          "address": "inbox@example.invalid",
          "accessMode": "read_write"
        },
        {
          "address": "clarity@sendthisfile.ai",
          "accessMode": "read_write",
          "allowedSenders": [
            "scott.sexton@sendthisfile.com",
            "sesexton@gmail.com"
          ]
        },
        {
          "address": "legal@example.invalid",
          "accessMode": "read"
        }
      ],
      "defaultMailbox": "inbox@example.invalid",
      "folderNamespace": "Clarity",
      "folderPolicy": {
        "review": "Clarity/Review",
        "noise": "Clarity/Noise",
        "trash": "Deleted Items"
      },
      "maxMessages": 25
    }
  }
}
```

Even the fake local workflow must use an approved mailbox. Live mail connectors
must keep this approval boundary.

`read` means Clarity may inspect metadata and remember results. `read_write`
means a future approved design may allow scoped write actions such as moving
messages into approved review folders. The current implementation only reads
fake metadata regardless of access mode.

`allowedSenders` restricts a mailbox to messages from specific senders. For
`clarity@sendthisfile.ai`, Clarity should ignore anything not sent by
`scott.sexton@sendthisfile.com` or `sesexton@gmail.com`.

Restricted mailbox messages must also pass authentication checks. The current
local rule requires:

-   DMARC: `pass`
-   SPF or DKIM: `pass`

Transports may provide normalized `spf`, `dkim`, and `dmarc` values directly,
or provide raw `Authentication-Results` header text as `authentication_results`.
The local email boundary parses only SPF, DKIM, and DMARC status values from
that header. Explicit normalized values take precedence over parsed header
values.

Microsoft Graph message metadata should be converted with
`graph_message_to_email_payload()` before it reaches assistant workflows. That
helper maps:

-   `id` to message ID
-   `subject` to subject
-   `from.emailAddress.address` or `sender.emailAddress.address` to sender
-   `receivedDateTime` to received timestamp
-   `bodyPreview` to preview
-   `categories` to categories
-   `internetMessageHeaders` entries named `Return-Path` and
    `Authentication-Results` to authentication metadata

`StaticGraphEmailTransport` is a fake local transport for tests and dry runs
with Graph-shaped payloads. It does not call Microsoft Graph.

The local email review workflow can exercise that transport with:

``` powershell
python -m assistant.src.run_email_review --mailbox clarity@sendthisfile.ai --sample-graph
```

The live Microsoft Graph read path can be exercised with:

``` powershell
python -m assistant.src.run_email_review --mailbox clarity@sendthisfile.ai --graph
```

Use `--graph-bearer` with `--graph` only when intentionally testing a local
`GRAPH_ACCESS_TOKEN`; otherwise the command uses app-only client credentials
from `GRAPH_TENANT_ID`, `GRAPH_CLIENT_ID`, and `GRAPH_CLIENT_SECRET`.

If the sender is not allowed, authentication metadata is missing, or
authentication fails, the local workflow classifies the message as `trash` and
records a proposed move to the trash folder.

## Folder Policy

`assistant.email.folderPolicy` maps classification labels to proposed mailbox
folders. The current required labels are:

-   `review`
-   `noise`
-   `trash`

Folder targets are intentionally constrained. All assistant-managed non-trash
destinations must be children of `assistant.email.folderNamespace`, for example
`Clarity/Review` and `Clarity/Noise`. Trash is treated as a system folder and
must be configured as `Deleted Items`.

Configured non-trash folders can be checked with:

``` powershell
python -m assistant.src.ensure_email_folders --mailbox clarity@sendthisfile.ai
```

Missing configured folders can be created with:

``` powershell
python -m assistant.src.ensure_email_folders --mailbox clarity@sendthisfile.ai --execute
```

Folder creation requires the mailbox to be approved with `read_write` access.
It only creates folder paths from `assistant.email.folderPolicy` where the label
is not `trash`.

Folder moves are scoped to the mailbox being reviewed. If Clarity reviews
`scott.sexton@sendthisfile.com`, then an approved move to `Clarity/Review`
means the `Clarity/Review` folder inside the `scott.sexton@sendthisfile.com`
mailbox. If Clarity reviews `clarity@sendthisfile.ai`, the same folder name
refers to that mailbox's folder tree.

The local review workflow records one proposed folder action per message. Those
actions are audit records only. They do not move messages. Proposed folder
destinations are stored as structured action targets so future execution logic
can use the recorded target without parsing human-readable text. The action
queue also includes the email item ID, which maps to the provider message ID in
future live Graph workflows.

Pending proposed actions can be reviewed with:

``` powershell
python -m assistant.src.ask_memory pending-actions
```

The first Clarity command surface can answer common email-attention questions
from local memory:

``` powershell
python -m assistant.src.clarity "What emails need immediate attention?"
python -m assistant.src.clarity "What needs approval?"
```

It can also be opened as a small local prompt:

``` powershell
python -m assistant.src.clarity
```

It can refresh approved mailbox metadata before answering:

``` powershell
python -m assistant.src.clarity "What emails need immediate attention?" --refresh-email --mailbox clarity@sendthisfile.ai --graph
```

This refresh path records email metadata, classifications, proposed actions, and
the local brief before answering from memory. It does not execute proposed moves.

One non-interactive Clarity cycle can be run by a local scheduler:

``` powershell
python -m assistant.src.run_clarity_cycle --mailbox clarity@sendthisfile.ai --graph
```

The cycle performs a read-only refresh and prints safe review and pending-action
sections. It also writes `reports/clarity-cycle.md` by default. It does not
create the scheduled task itself.

To print PowerShell commands for registering that daily task with Windows Task
Scheduler:

``` powershell
python -m assistant.src.print_clarity_schedule --mailbox clarity@sendthisfile.ai --graph --at 07:30
```

See `docs/scheduling.md` for the scheduling workflow and removal command.

Local approval status can be updated with:

``` powershell
python -m assistant.src.update_action ACTION_ID approved
python -m assistant.src.update_action ACTION_ID rejected
```

Approving a proposed action only updates local memory. It does not execute a
mailbox move.

Approved local actions can be reviewed separately with:

``` powershell
python -m assistant.src.ask_memory approved-actions
```

Approved email move proposals can be previewed without execution with:

``` powershell
python -m assistant.src.ask_memory email-move-plan
```

The move plan is read-only. It lists the source mailbox, provider message ID,
and destination folder for approved local proposals.

Approved email moves can be dry-run with:

``` powershell
python -m assistant.src.execute_email_moves
```

Approved email moves can be executed through Microsoft Graph with:

``` powershell
python -m assistant.src.execute_email_moves --graph --execute
```

The dry run records a local audit action but does not call Graph or move
mailbox items. The command-line `--execute` path still fails closed unless
`--graph` is also passed. Before a move can appear in the executable section,
the approved action must still be attached to an `email_message` from an `email`
source, the source mailbox must still be configured with `read_write` access,
and the target folder must still be present in the current folder policy.
Approved local actions that no longer meet those rules are listed as blocked
moves. After a move executes successfully, the original approved move action is
marked `executed` so a later run will not try to move the same message again.

## Memory Rules

Email memory stores:

-   Mailbox label
-   Message ID
-   Subject
-   Sender
-   Return path when available
-   SPF/DKIM/DMARC result metadata when available
-   Received timestamp
-   Content hash
-   Classification label and reason
-   Proposed folder action and structured destination target

Email memory does not store raw message bodies by default.

Noise classifications can be inspected with:

``` powershell
python -m assistant.src.ask_memory noise-items
```

## Next Live-Mail Step

Before live Exchange or Gmail access is added, create a separate design proposal
covering:

-   Approved mailboxes
-   Read-only versus write scopes
-   Authentication and token storage
-   Folder move policy
-   Audit behavior
-   Failure handling
-   Human approval requirements
