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

The current implementation is intentionally narrow: a local Clarity command
surface, Jira reporting, explicit email review over approved sources, and local
sample calendar awareness.

Current components:

-   `assistant.src.clarity`: routes the first deterministic natural-language
    Clarity requests to local tools and memory.
-   `assistant.src.check_clarity_setup`: checks local Clarity setup without
    reading mail or writing files.
-   `assistant.src.run_clarity_cycle`: runs one scheduled-friendly Clarity email
    refresh cycle and prints a safe local summary.
-   `assistant.src.run_calendar_review`: runs the first local read-only sample
    calendar review and records event metadata.
-   `assistant.src.print_clarity_schedule`: prints PowerShell commands for
    registering a local Windows scheduled task.
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
python -m assistant.src.ask_memory attention-brief
python -m assistant.src.ask_memory focus-plan
python -m assistant.src.ask_memory command-center
python -m assistant.src.ask_memory calendar-items
python -m assistant.src.ask_memory llm-context
python -m assistant.src.ask_memory llm-prompt
python -m assistant.src.ask_memory latest-llm-brief
python -m assistant.src.ask_memory last-cycle
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
python -m assistant.src.clarity "What should I focus on?"
python -m assistant.src.clarity "Give me my command center."
python -m assistant.src.clarity "What is on my family calendar today?"
python -m assistant.src.clarity "What needs my attention?"
python -m assistant.src.clarity "What needs approval?"
python -m assistant.src.clarity "What did you do?"
python -m assistant.src.clarity "When did Clarity last run?"
python -m assistant.src.clarity "When was the latest fake LLM brief?"
python -m assistant.src.clarity "Show my email move plan"
```

To open a small local prompt:

``` powershell
python -m assistant.src.clarity
```

This is a deterministic command surface over local memory. It does not use an
LLM router yet.

The command center includes a compact email cleanup section with approved moves
ready for cleanup review, proposed moves still needing approval, and the command
for the full cleanup plan.

The command center also includes a compact calendar agenda from local Clarity
memory. It surfaces remembered event count, source calendar, start/end times,
and location when those metadata fields were captured.

Calendar questions can filter remembered events for simple dates such as
`today`, `tomorrow`, or an explicit `YYYY-MM-DD` date. They can also filter by
simple calendar source phrases such as `family calendar`, `work calendar`, or
`personal calendar`.

To inspect the bounded context intended for future LLM summarization:

``` powershell
python -m assistant.src.ask_memory llm-context
python -m assistant.src.ask_memory llm-prompt
```

These do not call an LLM. `llm-context` prints the local metadata-only context
Clarity would be allowed to summarize. `llm-prompt` wraps that context with the
future summarization instructions.

To validate a local future LLM summary output file:

``` powershell
python -m assistant.src.validate_llm_output path\to\summary.md
```

To exercise the LLM summary pipeline with a deterministic local provider:

``` powershell
python -m assistant.src.generate_llm_brief
```

This writes `reports/clarity-llm-brief.md` by default. It does not call an LLM;
it uses a fake local provider to test the prompt and output validation path.
When it writes the report, it records a local `fake-llm-brief` memory run.

To refresh approved email metadata before answering:

``` powershell
python -m assistant.src.clarity "What emails need immediate attention?" --refresh-email --mailbox clarity@sendthisfile.ai --graph
```

This reads metadata into local memory, regenerates the local brief, and then
answers from memory. It does not move, archive, delete, or send email.

To run one non-interactive Clarity cycle suitable for a scheduler:

``` powershell
python -m assistant.src.run_clarity_cycle --mailbox clarity@sendthisfile.ai --graph
```

This performs the same read-only email refresh and prints the command center
plus review/pending-action sections. It also writes `reports/clarity-cycle.md`
by default. Scheduling the command is an operator/environment concern; the
command itself does not create an operating-system scheduled task. If a cycle
fails, it writes a sanitized failure report and exits with status `1`.

To check local setup before scheduling:

``` powershell
python -m assistant.src.check_clarity_setup --mailbox clarity@sendthisfile.ai --graph
```

This validates local configuration and required Graph credential keys without
reading mail or writing files.

To print the PowerShell commands for a daily Windows scheduled task:

``` powershell
python -m assistant.src.print_clarity_schedule --mailbox clarity@sendthisfile.ai --graph --at 07:30
```

Review the printed script before running it. The generated task appends console
output to `logs/clarity-cycle.log` by default. See `docs/scheduling.md` for the
local scheduling workflow.

To teach Clarity from a remembered item:

``` powershell
python -m assistant.src.record_feedback STF-1 noise "This was just an automated update."
python -m assistant.src.record_feedback ACCT-9 review "Keep surfacing billing issues."
```

Email review and noise lists include a local `Item ID` that can be used for
feedback:

``` powershell
python -m assistant.src.ask_memory review-items
python -m assistant.src.record_feedback ITEM_ID noise "This sender is promotional."
python -m assistant.src.record_feedback ITEM_ID review "Keep these updates visible."
```

The same feedback can be captured through the Clarity command surface:

``` powershell
python -m assistant.src.clarity "mark ITEM_ID as noise because this sender is promotional"
python -m assistant.src.clarity "mark ITEM_ID as review because keep these updates visible"
```

For email, `noise` and `review` feedback is used on future review runs for
matching mailbox, sender, subject, and sanitized subject/preview terms. It does
not store raw message bodies by default, and it does not override restricted
mailbox sender or authentication checks.

Mailbox-specific sender and domain preferences can also be recorded:

``` powershell
python -m assistant.src.clarity "always mark emails from sender@example.com as noise" --mailbox inbox@example.invalid
python -m assistant.src.clarity "always mark emails from example.com as review" --mailbox inbox@example.invalid
python -m assistant.src.ask_memory email-preferences
python -m assistant.src.clarity "remove email preference PREFERENCE_ID"
```

Preferences apply after restricted mailbox sender/authentication checks and
before feedback or general content rules.

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

To review proposed and approved cleanup before executing any Gmail filing:

``` powershell
python -m assistant.src.email_cleanup_plan --mailbox sesexton@gmail.com
python -m assistant.src.ask_memory email-cleanup-plan
python -m assistant.src.clarity "show my email cleanup plan"
```

The cleanup plan is read-only. It separates approved moves that are ready to
execute, proposed moves that still need approval, and approved moves that are
currently blocked by configuration.

To run the first local sample calendar review:

``` powershell
python -m assistant.src.run_calendar_review --calendar family --date 2026-07-10
```

This records local sample calendar metadata and regenerates the Clarity brief.
It does not call live Google Calendar, Outlook Calendar, or Microsoft Graph
calendar APIs.

To read an approved Microsoft Graph calendar instead, configure
`assistant.calendar.approvedCalendars` with a `graph` provider, then run:

``` powershell
python -m assistant.src.run_calendar_review --calendar work --date 2026-07-10 --graph
```

This live Graph mode is still read-only. It records local calendar event
metadata and does not create, update, delete, or respond to calendar events.

To read an approved Google Calendar instead, configure
`assistant.calendar.approvedCalendars` with a `google` provider, then run:

``` powershell
python -m assistant.src.run_calendar_review --calendar google-family --date 2026-07-10 --google
```

This live Google mode is still read-only. It records local calendar event
metadata and does not create, update, delete, or respond to calendar events.

To dry-run approved email moves and record a local audit action:

``` powershell
python -m assistant.src.execute_email_moves
```

Dry-run move planning re-checks current configuration. The source mailbox must
be approved with `read_write` access, and the destination folder must still be in
`assistant.email.folderPolicy`. Dry-run and execution output summarize
ready/moved counts, blocked/skipped counts, source mailbox totals, and
destination folder totals.

To execute approved moves through Microsoft Graph:

``` powershell
python -m assistant.src.execute_email_moves --graph --execute
```

To execute approved Gmail cleanup actions:

``` powershell
python -m assistant.src.execute_email_moves --gmail --execute
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

To read approved Gmail inbox metadata instead, enable the Gmail API, authorize
Google with `https://www.googleapis.com/auth/gmail.modify`, then run:

``` powershell
python -m assistant.src.run_email_review --mailbox sesexton@gmail.com --gmail
```

This records local proposed actions but does not execute cleanup.

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

