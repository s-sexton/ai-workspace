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
python -m assistant.src.print_clarity_schedule --mailbox clarity@sendthisfile.ai --graph --at 07:30
```

The output is a PowerShell script that:

-   Creates a scheduled task action using `powershell.exe`
-   Sets the working directory to this repository
-   Runs `python -m assistant.src.run_clarity_cycle`
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
python -m assistant.src.print_clarity_schedule --mailbox clarity@sendthisfile.ai --graph --at 07:30
```

The scheduled cycle reads approved mailbox metadata, updates local Clarity
memory, writes the local brief, writes `reports/clarity-cycle.md`, and prints
the command center plus review and pending-action sections. It does not send,
move, archive, or delete email.

To run a combined email and calendar refresh manually:

``` powershell
python -m assistant.src.run_clarity_cycle --mailbox clarity@sendthisfile.ai --graph --refresh-calendar --calendar google-family --calendar-date 2026-07-10 --google-calendar
```

The combined cycle reads approved mailbox metadata, then reads approved
calendar metadata, then prints the command center from local memory. Calendar
refresh is read-only and does not create, update, delete, or respond to events.

To print a scheduled task that runs the same combined refresh:

``` powershell
python -m assistant.src.print_clarity_schedule --mailbox clarity@sendthisfile.ai --graph --refresh-calendar --calendar google-family --calendar-date 2026-07-10 --google-calendar --at 07:30
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

To preview the email envelope without sending:

``` powershell
python -m assistant.src.send_daily_brief --date 2026-07-16
```

To send the generated daily brief through Microsoft Graph:

``` powershell
python -m assistant.src.send_daily_brief --date 2026-07-16 --graph --execute
```

Schedule the send command only after the Graph `Mail.Send` permission and
mailbox scoping have been reviewed. The command requires both `--graph` and
`--execute` before it sends.

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
invokes the deterministic reply processor. It still does not move or delete
mail.

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
