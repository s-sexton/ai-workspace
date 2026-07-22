# Scheduling

Clarity scheduled work should stay local-first and explicit.

The repository provides a helper that prints PowerShell commands for registering
one Windows Task Scheduler task. It does not register the task by itself.

## Print A Daily Task

Before printing or registering the scheduled task, run a local preflight check:

``` powershell
python -m assistant.src.check_clarity_setup --mailbox clarity@sendthisfile.ai --graph
```

The preflight validates committed configuration, mailbox approval, required
Graph credential keys, and planned local paths. It does not read mail, write
files, or create a scheduled task.

From the workspace root:

``` powershell
python -m assistant.src.print_clarity_schedule --graph --gmail --at 07:30
```

The output is a PowerShell script that:

-   Creates a scheduled task action using `powershell.exe`
-   Sets the working directory to this repository
-   Runs `python -m assistant.src.run_clarity_cycle`
-   Refreshes every readable mailbox in `assistant.email.approvedMailboxes`
    when `--mailbox` is omitted
-   Writes the latest cycle report to `reports/clarity-cycle.md`
-   Appends console output to `logs/clarity-cycle.log`
-   Registers a daily trigger at the requested time

Inspect the printed script before running it. Registering the task is a local
infrastructure change and requires human approval.

## Safe Sample Task

To print a no-network sample schedule:

``` powershell
python -m assistant.src.print_clarity_schedule --mailbox clarity@sendthisfile.ai --sample-graph --at 07:30
```

## Live Graph Task

To print a live read-only Microsoft Graph schedule:

``` powershell
python -m assistant.src.print_clarity_schedule --graph --at 07:30
```

The scheduled cycle reads approved mailbox metadata, updates local Clarity
memory, writes the local brief, writes `reports/clarity-cycle.md`, and prints
the command center plus review and pending-action sections. It does not send,
move, archive, or delete email.

For mixed Outlook/shared mailboxes and Gmail, include both providers:

``` powershell
python -m assistant.src.print_clarity_schedule --graph --gmail --at 07:30
```

When `--mailbox` is omitted, the cycle refreshes every readable configured
mailbox. Use `--mailbox scott.sexton@sendthisfile.com` only for a focused
one-mailbox refresh. Gmail refresh currently applies to `gmail.com` addresses;
non-Gmail addresses use Microsoft Graph when `--graph` is supplied.

To run a combined email and calendar refresh manually:

``` powershell
python -m assistant.src.run_clarity_cycle --mailbox clarity@sendthisfile.ai --graph --refresh-calendar --calendar google-family --calendar-date 2026-07-10 --google-calendar
```

The combined cycle reads approved mailbox metadata, then reads approved
calendar metadata, then prints the command center from local memory. Calendar
refresh is read-only and does not create, update, delete, or respond to events.

To print a scheduled task that runs the same combined refresh:

``` powershell
python -m assistant.src.print_clarity_schedule --graph --gmail --refresh-calendar --calendar google-family --calendar-date 2026-07-10 --google-calendar --at 07:30
```

This still only prints the PowerShell registration script. Review it before
running it locally.

## Codex Pro Summarization Handoff

ChatGPT/Codex Pro cannot be used as an API key from local Python. To use Codex
as the summarization surface, schedule or run Clarity so it writes a local
handoff report:

``` powershell
python -m assistant.src.run_clarity_cycle --mailbox clarity@sendthisfile.ai --graph --codex-handoff
```

The cycle writes `reports/clarity-codex-handoff.md` with bounded local context
and instructions for Codex. A Codex scheduled task or an interactive Codex chat
can summarize that report without Clarity calling a paid API provider.

For a handoff without refreshing email first:

``` powershell
python -m assistant.src.generate_llm_brief --codex-handoff --request "Help me prioritize my morning"
```

If the cycle fails, the command exits with status `1`, writes a failure report
to the configured cycle report path, and records a failed `clarity-cycle` run in
local memory when memory is available. Error text is sanitized before it is
written to the report or memory.

Clarity also records the cycle in local memory. To check the last remembered
cycle:

``` powershell
python -m assistant.src.clarity "When did Clarity last run?"
```

To ask for a compact attention brief from local memory:

``` powershell
python -m assistant.src.clarity "What needs my attention?"
```

To ask for the broader daily command center:

``` powershell
python -m assistant.src.clarity "Give me my command center."
```

To generate the email-ready daily brief locally without sending email:

``` powershell
python -m assistant.src.generate_daily_brief --date 2026-07-16
```

That command writes `reports/clarity-daily-brief.md` by default. It is intended
to become the scheduled email body after the outbound mail transport is added.
Inbox attention items are grouped by source mailbox so Outlook, shared, and
family Gmail inboxes remain distinct in the brief. The brief also includes the
rolling seven-day calendar window starting on the brief date, open Jira
tickets, open delegated tasks, and pending Clarity approval counts. Use
`--days` to choose a different calendar window.

To preview the email envelope without sending:

``` powershell
python -m assistant.src.send_daily_brief --date 2026-07-16 --days 7
```

To send the generated daily brief through Microsoft Graph:

``` powershell
python -m assistant.src.send_daily_brief --date 2026-07-16 --days 7 --graph --execute
```

Schedule the send command only after the Graph `Mail.Send` permission and
mailbox scoping have been reviewed. The command requires both `--graph` and
`--execute` before it sends.

To refresh approved Microsoft Graph and Google calendars before the email body
is generated:

``` powershell
python -m assistant.src.send_daily_brief --days 7 --refresh-calendars --graph-calendars --google-calendars --graph --execute
```

The calendar refresh is read-only and runs for each approved calendar across
the rolling brief window. This keeps the "Day In A Glance" section current
instead of relying only on whatever calendar events were already remembered.

The intended scheduled daily email process is:

1. Refresh approved inbox metadata.
2. Refresh approved calendars for the rolling brief window.
3. Refresh the live Jira report into local memory.
4. Generate the daily brief from refreshed local memory.
5. Send the generated brief.

The one-command form is:

``` powershell
python -m assistant.src.send_daily_brief --days 7 --refresh-email --graph-email --gmail --refresh-calendars --graph-calendars --google-calendars --refresh-jira --graph --execute
```

All refresh steps are read-only. The only external write in this command is
the final Graph `sendMail`, which still requires `--graph --execute`.

To print a Windows scheduled task for that email send workflow:

``` powershell
python -m assistant.src.print_clarity_schedule --workflow daily-brief-send --task-name "Clarity Daily Brief" --graph --execute --at 07:30 --days 7
```

The schedule printer refuses daily brief send schedules where `--graph` and
`--execute` are not supplied together.

To print the daily brief send task with pre-send calendar refresh:

``` powershell
python -m assistant.src.print_clarity_schedule --workflow daily-brief-send --task-name "Clarity Daily Brief" --graph --execute --refresh-calendar --graph-calendar --google-calendar --at 07:30 --days 7
```

For `daily-brief-send`, both `--graph-calendar` and `--google-calendar` may be
used together. The generated task passes provider-specific refresh flags to
`send_daily_brief`, then sends the newly generated brief.

To print the full refresh-then-send daily task:

``` powershell
python -m assistant.src.print_clarity_schedule --workflow daily-brief-send --task-name "Clarity Daily Brief" --graph --execute --refresh-email --gmail --refresh-calendar --graph-calendar --google-calendar --refresh-jira --at 07:30 --days 7
```

For this workflow, `--graph` enables the final Graph send and, when
`--refresh-email` is supplied, the generated command also includes
`--graph-email` for approved non-Gmail inbox refresh.

If the manual send returns `Microsoft Graph sendMail failed with status 403`,
the app reached Graph but is not authorized to send as the configured sender.
Check that the Entra app has Microsoft Graph `Mail.Send` application
permission with admin consent, and that Exchange mailbox scoping allows the app
to send as `assistant.dailyBrief.sender`.

To process reply text locally against the latest daily brief manifest:

``` powershell
python -m assistant.src.process_daily_brief_reply --reply "Move item 1 to Noise"
```

Add `--execute` only when the parsed local-memory changes should be applied.
This still does not move mail or call external systems.

The Codex Scheduled reply-check task should call:

``` powershell
python -m assistant.src.poll_daily_brief_replies --graph
```

After the first dry-run checks look right, the scheduled command can use:

``` powershell
python -m assistant.src.poll_daily_brief_replies --graph --execute
```

The poller reads the configured Clarity sender mailbox, checks allowed senders
and authentication metadata, requires the subject to match the configured daily
brief subject prefix, skips replies already processed in local memory, and then
invokes the deterministic reply processor. It reads the full reply body so
instructions after the first preview lines are not silently missed. It still
does not move or delete mail.

To print a Windows scheduled task for the reply poll workflow:

``` powershell
python -m assistant.src.print_clarity_schedule --workflow daily-brief-reply-poll --task-name "Clarity Reply Poll" --mailbox clarity@sendthisfile.ai --graph --at 08:00
```

Add `--execute` to the printed reply poll schedule only after dry-run output is
reviewed. Execution applies supported local-memory reply commands; it still
does not move or delete email.

To choose a different cycle report path:

``` powershell
python -m assistant.src.print_clarity_schedule --mailbox clarity@sendthisfile.ai --graph --at 07:30 --cycle-report reports/morning-clarity-cycle.md
```

To choose a different console log path:

``` powershell
python -m assistant.src.print_clarity_schedule --mailbox clarity@sendthisfile.ai --graph --at 07:30 --log logs/morning-clarity-cycle.log
```

To print a scheduled task without console log redirection:

``` powershell
python -m assistant.src.print_clarity_schedule --mailbox clarity@sendthisfile.ai --graph --at 07:30 --no-log
```

Email moves remain separate. They require a locally approved action and an
explicit provider execution command such as
`python -m assistant.src.execute_email_moves --graph --execute` or
`python -m assistant.src.execute_email_moves --gmail --execute`. When the
configured Gmail Spam cleanup policy is enabled, the Gmail execution command
also moves current Spam messages for the configured Gmail mailbox to Trash.

## Remove The Task

If the task was registered with the default name, remove it with:

``` powershell
Unregister-ScheduledTask -TaskName "Clarity Email Cycle" -Confirm:$false
```
