# Email

## Current Milestone

The current email milestone is intentionally local and read-only:

-   Read fake mailbox metadata
-   Require the mailbox to be listed in local approved mailbox config
-   Normalize message metadata
-   Apply deterministic placeholder classifications
-   Store metadata, hashes, and classifications in local Clarity memory
-   Propose review/noise folder destinations from local policy
-   Generate the local Clarity brief
-   Surface both review and noise classifications for inspection

It does not connect to live Exchange, Gmail, or Microsoft Graph.

It does not send, move, archive, delete, or modify email.
Folder moves are recorded only as proposed local actions that require approval.

## Shared Boundary

`common.email` owns the reusable email metadata boundary:

-   `EmailClient`
-   `EmailTransport`
-   `EmailMessage`
-   `EmailFolderProposal`
-   `StaticEmailTransport`
-   `classify_email_message`
-   `propose_email_folder_action`

Assistant workflows consume normalized `EmailMessage` objects. They should not
parse provider-specific payloads directly.

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
          "address": "legal@example.invalid",
          "accessMode": "read"
        }
      ],
      "defaultMailbox": "inbox@example.invalid",
      "folderPolicy": {
        "review": "Clarity/Review",
        "noise": "Clarity/Noise"
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

## Folder Policy

`assistant.email.folderPolicy` maps classification labels to proposed mailbox
folders. The current required labels are:

-   `review`
-   `noise`

The local review workflow records one proposed folder action per message. Those
actions are audit records only. They do not move messages.

## Memory Rules

Email memory stores:

-   Mailbox label
-   Message ID
-   Subject
-   Sender
-   Received timestamp
-   Content hash
-   Classification label and reason
-   Proposed folder action and destination

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
