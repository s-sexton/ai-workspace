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
review and pending-action sections. It does not send, move, archive, or delete
email.

If the cycle fails, the command exits with status `1`, writes a failure report
to the configured cycle report path, and records a failed `clarity-cycle` run in
local memory when memory is available. Error text is sanitized before it is
written to the report or memory.

Clarity also records the cycle in local memory. To check the last remembered
cycle:

``` powershell
python -m assistant.src.clarity "When did Clarity last run?"
```

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
explicit `python -m assistant.src.execute_email_moves --graph --execute` run.

## Remove The Task

If the task was registered with the default name, remove it with:

``` powershell
Unregister-ScheduledTask -TaskName "Clarity Email Cycle" -Confirm:$false
```
