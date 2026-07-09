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

-   `assistant.src.jira_report`: generates Markdown from normalized Jira issues.
-   `assistant.src.run_jira_report`: runs the local fake Jira report workflow
    and writes `reports/jira-report.md`.

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
not require real Jira credentials.

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

