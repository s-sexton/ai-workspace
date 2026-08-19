# BofA Checking Reconciliation

This note documents the learned status for AM-008.

Do not store bank account numbers, merchant location numbers, statements,
customer-level rows, credentials, or sensitive transaction details in this file.

## Current Status

- Active monthly task.
- Timing: Day 1 monthly close work when required source statements/data are
  ready.
- Current process: [Reconcile Bank of America Checking (Merchant Account Driven)](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/539688962/Reconcile+Bank+of+America+Checking+Merchant+Account+Driven).
- Supporting mechanics reference: [Reconcile Bank of America Checking Automated](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/10289170/Reconcile+Bank+of+America+Checking+Automated).

## Learned Guidance

The merchant-account-driven page is the active reconciliation process.
It should stay updated and refined as the source of truth for reconciling BofA
checking using merchant-driven data.

The older automated BofA checking page remains valid for showing how to
reconcile the actual account in QuickBooks Desktop.

Merchant statements are a required driver for the reconciliation. The active
Confluence page now includes a top `Merchant Statement Collection` section so
the current process is self-contained and users do not need to rely on the
archived refunds/chargebacks page for current work.

Only the Classic SendThisFile service accepts AMEX, so AMEX merchant activity is
classified to Classic revenue and Classic merchant fee accounts.

If AMEX has chargebacks, refunds, or adjustments, record them in the American
Express section of the Revenues Worksheet on the `Chargebacks / Refunds /
Adjustments` row. The `AMEX Clearing` memorized transaction in QuickBooks
Desktop has empty placeholders for that activity.

For BofA Classic and BofA App end-of-month funding timing differences, the
current spreadsheet adjusts gross credit-card submissions by backing out
merchant-statement items not funded to BofA checking in the closing month and
adding them back in the next month when funded.

Manual Cybersource Virtual Terminal invoice payments may be supported from saved
receipts, clearing account activity, deposit-folder evidence, a Cybersource
report, the worksheet, or a combination of those sources.

The `Revenues Worksheet - MMYYYY.xlsx` is copied forward from the prior month,
renamed for the closing month, and updated by adding a new month column on the
`Merchant Reconciliation` tab.

QuickBooks Desktop memorized transaction changes are rare and are handled by
Scott when worksheet structure or accounts change.

Expected memorized transaction names:

- `AMEX Clearing`
- `BofA Classic Clearing`
- `BofA App Clearing`

Reviewing entries not on the BofA checking statement is a required monthly step
for both BofA Classic and BofA App because timing differences can occur in both
merchant statements.

## Dependency Rule

AM-008 cannot be treated as ready until both source categories are available:

- Merchant account statements/reports.
- BofA checking statement/data.
- Deposit evidence for manual invoice/payment matching.

If either source is missing, track the task as waiting on source availability
rather than as ready for reconciliation.

Expected AM-008 source checklist:

- BofA checking statement PDF in the yearly BofA checking statement folder.
- `887` BofA Merchant Services Processing Statement.
- `888` BofA Merchant Services Processing Statement.
- American Express Merchant Financial Activity Statement.
- `Revenues Worksheet - MMYYYY.xlsx`.
- Monthly `Deposits` folder.
- Final BofA checking reconciliation report after completion.

## Directory And Naming Notes

Monthly folders use the `YYYYMM` pattern under the year folder, for example:

`Accounting/Financial Records/2026/202607`

The month folder is built throughout the month. Deposits made during the month,
transactional invoices, receipts, merchant statements, the revenues worksheet,
and reconciliation reports are accumulated in the appropriate month-specific
folders as activity occurs.

Observed AM-008-related files in month folders:

- `887 - BofA Merchant Services Processing Statement - MMDDYYYY.pdf`
- `888 - BofA Merchant Services Processing Statement - MMDDYYYY.pdf`
- `American Express Merchant Financial Activity Statement - MMYYYY.xlsx`
- `Revenues Worksheet - MMYYYY.xlsx`
- `BofA Checking Reconciliation Month YYYY.pdf`

The `887` and `888` prefixes are intentional and are driven by the merchant IDs:

- `345468341887` - Cybersource / Classic.
- `345015373888` - Authorize.net / App.

Naming has not always been perfectly consistent. Day-specific documents need
the `DD` portion of a date when the transaction date matters. Monthly reports
such as merchant statements and checking statements may not inherently need the
day, but existing document-type naming conventions should not be changed
casually because consistency within each document type is valuable.

The yearly BofA checking statement folder remains the single source of truth for
BofA checking statement PDFs because Scott may add notes or highlights to those
PDFs:

`Accounting/Financial Records/YYYY/Bank of America/Checking Statement`

Do not duplicate the BofA checking statement into the monthly folder unless
Scott changes that source-of-truth rule.

The `Revenues Worksheet - MMYYYY.xlsx` should live directly in the monthly
`YYYYMM` folder. The final QBDT BofA checking reconciliation report also lives
directly in that monthly folder.

The `Deposits` folder is part of the AM-008 evidence package, especially for
manual invoice/payment matching. It is not all-inclusive because some customers
do not send remittance and must be identified from the BofA checking statement.

## Completion Check

AM-008 completion requires:

- BofA Classic Clearing equals `$0.00`.
- BofA App Clearing equals `$0.00`.
- AMEX Clearing equals `$0.00`.
- Bank feeds are processed for the closing month.
- The QuickBooks Desktop BofA checking reconciliation difference is `$0.00`.

If any clearing account is not zero, stop and investigate before reconciling
BofA checking. Typical causes include a missing deposit, double entry, or date
mismatch.

## Reminder Timing

Start checking AM-008 source availability on Day 1. The task is not ready for
completion until merchant statements/reports and BofA checking data are
available.

The BofA checking statement is most likely ready on the 1st. Merchant statements
may also be ready on the 1st, but they can take a couple of days before they
are accessible.

Reminder wording should say `start checking source availability` rather than
implying that the full reconciliation is ready on Day 1.

## Confluence Visibility Check

The active BofA merchant-driven Confluence page was checked on 2026-08-19.
Unauthenticated access redirected to Atlassian login, so the page does not
appear publicly readable on the internet.

The available OAuth credential could read the page and space metadata but did
not have enough scope to inspect detailed page restrictions or internal group
membership. Treat Confluence as an internal SendThisFile surface for this page,
while still avoiding unnecessary secrets, credentials, or raw private customer
data.

## Streamlining Idea: Carryforward Schedule

A formal carryforward schedule would make the spreadsheet's funding-timing
adjustments auditable by listing each end-of-month merchant batch that appears
on the merchant statement but funds to BofA checking in the next month.

Possible columns:

- Closing month.
- Processor/location.
- Merchant batch date.
- Funding date.
- Amount backed out of current month.
- Amount added into next month.
- BofA deposit reference or safe statement reference.
- Cleared in next-month reconciliation.

This may be unnecessary if the spreadsheet already provides enough visibility,
but it is a candidate control if funding timing differences become hard to
review later.

## Follow-Up Questions

- What exact BofA checking statement/export is used as the close source?
- Where are the merchant statements and BofA checking files saved for each
  closing month?
- What exceptions most often delay completion?
- Analyze local directory structures and naming conventions for merchant
  statements, BofA checking files, the revenues worksheet, and final
  reconciliation reports.
