# LifeOps Assistant

The `assistant` package contains **LifeOps Assistant**.

LifeOps Assistant helps with work and personal decision support. It gathers
approved information, organizes it into useful summaries, identifies risks or
opportunities, and recommends next actions while keeping the human in control.

## Scope

LifeOps Assistant covers both work and personal domains.

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

## Current Milestone

The current implementation is still intentionally narrow: the first read-only
Jira report.

Current components:

-   `assistant.src.jira_report`: generates Markdown from normalized Jira issues.
-   `assistant.src.run_jira_report`: runs the local fake Jira report workflow
    and writes `reports/jira-report.md`.

## Boundaries

LifeOps Assistant may gather, summarize, analyze, and recommend.

It must not send email, create or change calendar events, write to Jira,
transition workflows, delete data, make purchases, or make commitments without
explicit human approval.

Work and personal context should be kept clearly labeled.

This package should not call Jira directly for report formatting. Jira access
and normalization belong in `common.jira`; assistant modules consume normalized
objects and produce assistant-specific outputs.

## Local Report Check

Run the local fake Jira report workflow from the workspace root:

``` powershell
python -m assistant.src.run_jira_report
```

This command uses static sample Jira data. It does not call live Jira and does
not require real Jira credentials.

