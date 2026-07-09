# Clarity Assistant

The `assistant` package contains **Clarity Assistant**.

Clarity Assistant reduces noisy tasks across work and personal life. It gathers
approved information, separates signal from noise, organizes what needs
attention, answers questions from approved context, and recommends next actions
while keeping the human in control.

## Scope

Clarity Assistant covers both work and personal domains.

Work examples:

-   SendThisFile Jira review
-   Jira Service Management review
-   Operational summaries
-   Prioritization recommendations
-   Future customer and business health review

Personal examples:

-   Gmail review
-   Family calendar awareness
-   Personal reminders
-   Household planning
-   Personal commitment review

Shared examples:

-   Answering questions from prior reports, feedback, and approved sources
-   Tracking delegated tasks that the human does not have time to handle
-   Remembering useful preferences without storing secrets

## Current Milestone

The current implementation is still intentionally narrow: the first read-only
Jira report.

Current components:

-   `assistant.src.clarity`: routes the first deterministic natural-language
    Clarity requests to local tools and memory.
-   `assistant.src.jira_report`: generates Markdown from normalized Jira issues.
-   `assistant.src.run_jira_report`: runs the local fake Jira report workflow
    and writes `reports/jira-report.md`.
-   `assistant.src.ask_memory`: answers a small set of read-only questions from
    local Clarity memory.
-   `assistant.src.record_feedback`: records human feedback for remembered
    items in local Clarity memory.
-   `assistant.src.delegate_task`: records delegated work in local Clarity
    memory.
-   `assistant.src.update_task`: updates delegated task status in local Clarity
    memory.
-   `assistant.src.update_action`: updates local approval status for proposed
    assistant actions.
-   `assistant.src.generate_brief`: generates a local Markdown brief from
    Clarity memory.
-   `assistant.src.run_email_review`: runs the first local read-only email
    metadata review workflow with fake mailbox data.
-   `common.memory`: records local Clarity memory for runs, Jira issues seen,
    classifications, feedback, and delegated tasks.

## Boundaries

Clarity Assistant may gather, summarize, analyze, and recommend.

It must not send email, create or change calendar events, write to Jira,
transition workflows, delete data, make purchases, or make commitments without
explicit human approval.

Work and personal context should be kept clearly labeled.

Longer-term memory and delegated work design lives in
`assistant/docs/persistence-memory.md`.

This package should not call Jira directly for report formatting. Jira access
and normalization belong in `common.jira`; assistant modules consume normalized
objects and produce assistant-specific outputs.

## Local Report Check

Run the local fake Jira report workflow from the workspace root:

``` powershell
python -m assistant.src.run_jira_report
```

This command uses static sample Jira data. It does not call live Jira and does
not require real Jira credentials. It writes the Markdown report and records a
local memory run in `logs/clarity-memory.duckdb`.

To skip local memory recording:

``` powershell
python -m assistant.src.run_jira_report --no-memory
```

To ask deterministic questions from local memory:

``` powershell
python -m assistant.src.ask_memory summary
python -m assistant.src.ask_memory latest-jira-run
python -m assistant.src.ask_memory recent-items
python -m assistant.src.ask_memory review-items
python -m assistant.src.ask_memory noise-items
python -m assistant.src.ask_memory feedback
python -m assistant.src.ask_memory actions
python -m assistant.src.ask_memory pending-actions
python -m assistant.src.ask_memory approved-actions
python -m assistant.src.ask_memory email-move-plan
python -m assistant.src.ask_memory open-tasks
```

To ask Clarity a first natural-language question:

``` powershell
python -m assistant.src.clarity "What emails need immediate attention?"
python -m assistant.src.clarity "What needs approval?"
python -m assistant.src.clarity "What did you do?"
python -m assistant.src.clarity "Show my email move plan"
```

To open a small local prompt:

``` powershell
python -m assistant.src.clarity
```

This is a deterministic command surface over local memory. It does not use an
LLM router yet.

To teach Clarity from a remembered item:

``` powershell
python -m assistant.src.record_feedback STF-1 noise "This was just an automated update."
python -m assistant.src.record_feedback ACCT-9 review "Keep surfacing billing issues."
```

To delegate local work for Clarity to track:

``` powershell
python -m assistant.src.delegate_task "Prepare daily review" "Summarize what needs attention." --next-step "Ask memory summary."
```

To update delegated work:

``` powershell
python -m assistant.src.update_task TASK_ID in_progress --next-step "Draft the review."
python -m assistant.src.update_task TASK_ID completed
```

To approve or reject a proposed local action:

``` powershell
python -m assistant.src.update_action ACTION_ID approved
python -m assistant.src.update_action ACTION_ID rejected
```

Approved local actions can be reviewed with:

``` powershell
python -m assistant.src.ask_memory approved-actions
```

Approved email move proposals can be previewed without execution with:

``` powershell
python -m assistant.src.ask_memory email-move-plan
```

To dry-run approved email moves and record a local audit action:

``` powershell
python -m assistant.src.execute_email_moves
```

Dry-run move planning re-checks current configuration. The source mailbox must
be approved with `read_write` access, and the destination folder must still be in
`assistant.email.folderPolicy`.

To execute approved moves through Microsoft Graph:

``` powershell
python -m assistant.src.execute_email_moves --graph --execute
```

Execution still requires an approved local action, an email source item, a
`read_write` mailbox, and a configured destination folder.

To generate a local brief from memory:

``` powershell
python -m assistant.src.generate_brief
```

To run the first local email metadata review:

``` powershell
python -m assistant.src.run_email_review
```

By default this uses fake mailbox data. It does not send, move, archive, or
delete email. The mailbox must be listed in `config/config.json` under
`assistant.email.approvedMailboxes` with `read` or `read_write` access. The
workflow records proposed review/noise folder actions from
`assistant.email.folderPolicy`, and non-trash targets must be under the
configured `assistant.email.folderNamespace`, but those proposals do not move
messages. Proposed folder moves are scoped to the mailbox being reviewed, so
`Clarity/Review` means that folder inside the source mailbox. Proposed actions
that require approval can be reviewed with:

``` powershell
python -m assistant.src.ask_memory pending-actions
```

To test the shared Clarity mailbox path with local Microsoft Graph-shaped sample
messages:

``` powershell
python -m assistant.src.run_email_review --mailbox clarity@sendthisfile.ai --sample-graph
```

To read an approved mailbox from Microsoft Graph instead, configure Graph values
in `config/.env`, then pass `--graph`:

``` powershell
python -m assistant.src.run_email_review --mailbox clarity@sendthisfile.ai --graph
```

This live Graph mode is still read-only. It records local proposed actions but
does not move, archive, delete, or send email.

To check whether configured Clarity folders exist in an approved `read_write`
mailbox:

``` powershell
python -m assistant.src.ensure_email_folders --mailbox clarity@sendthisfile.ai
```

To create missing configured folders:

``` powershell
python -m assistant.src.ensure_email_folders --mailbox clarity@sendthisfile.ai --execute
```

This only creates non-trash folders from `assistant.email.folderPolicy`, such as
`Clarity/Review` and `Clarity/Noise`.

To read from Jira Cloud instead, configure `config/.env` with
`JIRA_CLOUD_ID`, `JIRA_EMAIL`, and `JIRA_API_TOKEN`, then pass `--live`:

``` powershell
python -m assistant.src.run_jira_report --live
```

Live mode is still read-only. It reads Jira issues and writes a local Markdown
report; it does not write to Jira.

To show safe diagnostics while troubleshooting:

``` powershell
python -m assistant.src.run_jira_report --live --show-query
```

To temporarily test a narrower JQL query:

``` powershell
python -m assistant.src.run_jira_report --live --show-query --jql "project = STF ORDER BY updated DESC"
```

