# Email

## Current Milestone

The current email milestone keeps reads and writes explicit:

-   Read fake mailbox metadata by default
-   Optionally read approved mailbox metadata from Microsoft Graph with
    `--graph`
-   Optionally read approved Gmail metadata with `--gmail`
-   Require the mailbox to be listed in local approved mailbox config
-   Normalize message metadata
-   Apply deterministic review/noise/trash classifications
-   Apply mailbox sender allow-list and authentication rules before content rules
-   Store metadata, hashes, and classifications in local Clarity memory
-   Propose review/noise/trash folder destinations from local policy
-   Generate the local Clarity brief
-   Surface both review and noise classifications for inspection
-   Allow approved move proposals to be executed only with explicit
    `--graph --execute` or `--gmail --execute`

By default it does not connect to live Exchange, Gmail, or Microsoft Graph.
Explicit `--graph` review mode reads message metadata from Microsoft Graph.
Explicit `--gmail` review mode reads Gmail inbox metadata. Folder moves are
recorded first as proposed local actions that require approval.

Gmail execution supports archiving into configured Clarity labels and moving
messages to trash. It does not send email and does not permanently delete Gmail
messages.

Classification is intentionally conservative. Restricted mailbox sender and
authentication checks run first. Then operational, account, family, security,
and approval signals are kept for review. Only after those checks does Clarity
classify common promotional, digest, and subscription-style messages as noise.

Human feedback can tune future email classifications. Feedback is scoped to the
mailbox and matching message metadata. A prior `noise` or `review` feedback
record can override content rules on a later run when the sender and subject
match, or when the sender matches and the current message shares enough
sanitized subject/preview terms with the prior message. Feedback cannot override
restricted mailbox sender allow-list or authentication failures.

Mailbox-scoped sender and domain preferences provide a stronger local rule than
feedback learning:

``` powershell
python -m assistant.src.clarity "always mark emails from sender@example.com as noise" --mailbox inbox@example.invalid
python -m assistant.src.clarity "always mark emails from example.com as review" --mailbox inbox@example.invalid
python -m assistant.src.ask_memory email-preferences
```

Preferences run after restricted mailbox sender/authentication checks and before
feedback or general content rules.

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

`common.google_gmail` contains the Gmail-specific runtime adapters:

-   `GoogleGmailReadTransport` lists inbox message IDs and fetches metadata.
-   `GoogleGmailMoveTransport` moves messages to trash or archives them into a
    configured Clarity label.
-   `build_google_gmail_read_transport()` and
    `build_google_gmail_move_transport()` build Gmail transports from local
    Google credentials.

Gmail support uses Google OAuth credentials from `config/.env`. The intended
scope is:

``` text
https://www.googleapis.com/auth/gmail.modify
```

Do not use a Gmail send scope. Clarity does not send Gmail messages.

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
          "address": "sesexton@gmail.com",
          "accessMode": "read_write"
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
means approved move/trash actions may execute for that mailbox through an
explicit provider command.

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
python -m assistant.src.clarity "What needs my attention?"
python -m assistant.src.clarity "What needs approval?"
python -m assistant.src.clarity "When did Clarity last run?"
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

The live Gmail read path can be exercised with:

``` powershell
python -m assistant.src.run_email_review --mailbox sesexton@gmail.com --gmail
```

Use `--gmail-bearer` with `--gmail` only when intentionally testing a local
`GOOGLE_ACCESS_TOKEN`; otherwise the command uses refresh-token credentials
from `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REFRESH_TOKEN`.

One non-interactive Clarity cycle can be run by a local scheduler:

``` powershell
python -m assistant.src.run_clarity_cycle --mailbox clarity@sendthisfile.ai --graph
```

The cycle performs a read-only refresh and prints safe review and pending-action
sections. It also writes `reports/clarity-cycle.md` by default. It does not
create the scheduled task itself.

Before scheduling a live Graph cycle, check setup without reading mail:

``` powershell
python -m assistant.src.check_clarity_setup --mailbox clarity@sendthisfile.ai --graph
```

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

Approved Gmail cleanup actions can be executed with:

``` powershell
python -m assistant.src.execute_email_moves --gmail --execute
```

The dry run records a local audit action but does not call Graph or move
mailbox items. The command-line `--execute` path still fails closed unless
`--graph` or `--gmail` is also passed. Before a move can appear in the
executable section,
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
-   Sanitized subject/preview learning terms
-   Mailbox-scoped sender/domain preferences
-   Classification label and reason
-   Proposed folder action and structured destination target

Email memory does not store raw message bodies by default.

Noise classifications can be inspected with:

``` powershell
python -m assistant.src.ask_memory noise-items
```

Review and noise lists include a local `Item ID`. Use that ID to teach Clarity
when a classification was wrong or should be repeated:

``` powershell
python -m assistant.src.record_feedback ITEM_ID noise "This sender is promotional."
python -m assistant.src.record_feedback ITEM_ID review "Keep these school updates visible."
```

Feedback can also be recorded through the Clarity command surface:

``` powershell
python -m assistant.src.clarity "mark ITEM_ID as noise because this sender is promotional"
python -m assistant.src.clarity "mark ITEM_ID as review because keep these updates visible"
```

The next email review run consults those local feedback records before applying
general content rules.

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
