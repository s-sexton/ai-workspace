# Record Unearned Revenue

This note documents the learned monthly workflow for AM-005.

Do not store customer-level rows, database records, credentials, account
numbers, or sensitive transaction details in this file.

## Current Status

- Active monthly task.
- Timing: Day 1 monthly close work, for the prior month.
- Current source of truth for the procedure: [Recording Unearned Revenue](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/9928707/Recording+Unearned+Revenue).

## Current Process

1. Use the current supporting spreadsheet/report for unearned revenue.
2. The underlying data comes from the Classic service Oracle database through
   the Power BI report path.
3. In QuickBooks Desktop, use the memorized transaction named `Unearned Revenue`.
4. Post the memorized transaction to the last day of the prior month, because
   that is the month being closed.
5. Run a standard balance sheet.
6. Review the `Unearned Revenue` line item and confirm it matches the
   supporting spreadsheet.

## Completion Evidence

Record sanitized completion status in the monthly task register or completion
log:

- Close month.
- Date the memorized transaction was posted.
- Supporting spreadsheet/report name or safe source reference.
- Balance sheet tie-out status.
- Any exception requiring human review.

## Streamlining Notes

Power BI may not be a hard requirement for this workflow. It was originally used
with the hope of building more visual dashboards. A future improvement review
can evaluate whether an approved secure API/query can provide the needed data
directly.

Do not create, configure, or use direct Classic service Oracle/API access
without explicit human approval for source, authentication, data scope, output,
and decision boundaries.
