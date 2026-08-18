# Accounting Analyst Monthly Task Register

This register tracks recurring monthly accounting tasks that the human operator
assigns to the Accounting Analyst.

The Accounting Analyst may learn the task, track whether the human reports it
as complete, and prepare reminder handoffs to Clarity. Clarity owns approved
Teams and email notification delivery.

Do not store sensitive accounting data, customer private data, bank details,
credentials, raw QuickBooks exports, or transaction-level private business
details in this file.

## Reminder Handoff Format

When asking Clarity to notify the human, use this shape:

```text
Accounting Analyst notification request for Clarity:

I am the Accounting Analyst.
Please send Scott a Teams notification and/or email.

Topic:
Brief description:
Due date:
Completion status:
Recommended timing:
Notes:
```

Only include sanitized content suitable for the selected notification surface.

## Tasks

These tasks were provided from Jira checklist-template markup. Status reflects
the template item state at intake, not the current month's completion.

| ID | Template Status | Timing | Task | How-To / Related Page | Notes |
| --- | --- | --- | --- | --- | --- |
| AM-001 | open | Everyday | Manage `accounting@` and `billing@` emails in support CRM system | | |
| AM-002 | open | Day 1 | Send invoices | [Create Monthly Invoices with SaasAnt Transactions](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/94306305/Create+Monthly+Invoices+with+SaasAnt+Transactions); [Local workflow note](workflows/monthly-invoices.md) | Remember to use Coupa for NASDAQ invoice. |
| AM-003 | open | Day 1 | Run `A/R Aging Detail w/ AccountID` report and determine who needs to get emailed | | |
| AM-004 | open | Day 1 | Send statements | [Create Statements](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/10158103/Create+Statements) | |
| AM-005 | open | Day 1 | Record Unearned Revenue | [Recording Unearned Revenue](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/9928707/Recording+Unearned+Revenue) | |
| AM-006 | open | Day 1 | Process refunds and chargebacks | [Enter Refunds Charge Backs](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/11141121/Enter+Refunds+Charge+Backs) | |
| AM-007 | open | Day 1 | Enter Pre-paid Expenses | [Enter Pre-paid Expenses](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/11829249/Enter+Pre-paid+Expenses) | |
| AM-008 | open | Day 1 | Reconcile BofA checking | [Reconcile Bank of America Checking Automated](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/10289170/Reconcile+Bank+of+America+Checking+Automated); [Reconcile Bank of America Checking Merchant Account Driven](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/539688962/Reconcile+Bank+of+America+Checking+Merchant+Account+Driven) | Requires both merchant account statements and BofA checking statement/data to be ready. |
| AM-009 | open | Day 1 | Reconcile Emprise Bank Checking Account | | |
| AM-010 | open | Day 5 | Reconcile PayPal | [Reconcile PayPal Statements](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/297959425/Reconcile+PayPal+Statements) | |
| AM-011 | open | Day 1 | Reconcile Investment statement | [Reconcile Investment Statements](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/11501571/Reconcile+Investment+Statements) | |
| AM-012 | open | Day 1-5 | Refund cancelations | | |
| AM-013 | open | Day 1-7 | Pay contractor invoices for prior month and enter into QuickBooks | [Contractor Vendor Payments](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/1867789/Contractor+Vendor+Payments) | |
| AM-014 | open | Day 4 | Get list of enterprise accounts that failed billing | | Should be in internal-alert email. |
| AM-015 | open | Day 5 | Pay Hartford insurance premium | | |
| AM-016 | open | Day 7 | Reconcile BofA credit cards | [Reconcile Bank of America Credit Cards](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/36601857/Reconcile+Bank+of+America+Credit+Cards) | Verify you have all receipts. |
| AM-017 | open | Day 7 | Complete financial statements and delivery to shareholders | | |
| AM-018 | open | Day 10 | Process payroll to be paid on the 15th of the month | [Processing Payroll](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/20414465/Processing+Payroll) | |
| AM-019 | open | Day 10 | Perform distribution if needed | | |
| AM-020 | open | Day 10 | Pay payroll taxes | [Processing Payroll - Make Payroll Tax Deposits](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/20414465/Processing+Payroll#Make-Payroll-Tax-Deposits) | Federal withholding, Social Security, Medicare/Form 941, KS/MO state withholding. |
| AM-021 | open | Day 10 | Check for outstanding PPQ records that have not been processed | | |
| AM-022 | open | Day 15 | Send pay stubs to employees | | |
| AM-023 | open | Day 15 | Manage AMEX chargebacks and cancellations | | |
| AM-024 | open | Day 25 | Pay BCBS via online ACH | [Paying BCBS](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/42532865/Paying+BCBS) | |
| AM-025 | open | Day 27 | Manage AMEX and BofA merchant account chargebacks and cancellations | | |
| AM-026 | open | Last Day | Cancel invoice customers whose forms are marked inactive | | Make sure to log all outstanding invoices as bad debt. |
| AM-027 | open | Last Day | Run integrity report in BIRT before credit-card billing | [Data Integrity Report](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/44793859/Data+Integrity+Report) | |
| AM-028 | open | Last Day | Run SaasAnt to bring over any new invoices for the month | | |
| AM-029 | open | Last Day | Check blacklisted accounts for payment processing records | [Query for blacklisted paid plans](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/44662785/Query+for+blacklisted+paid+plans) | |

## Completion Log

Use this section to record what was done and when the human reports completion.

| Month | Task ID | Completion Status | Completed Date | Source / Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

## Timing Rules

### Invoices

- Monthly invoices should be completed on the 1st of the month.
- If the 1st falls on a weekend or holiday, invoices should be completed on the
  next business day unless the human operator specifies a different schedule for
  that month.
- AM-002 reminders should be based on the effective invoice date, not only the
  calendar day number.

### Payroll

- Payroll checks must be completed early enough for direct deposits to reach
  employee accounts by the 15th of the month.
- AM-018 is critical when the 15th falls on a weekend or holiday because the
  QuickBooks Payroll submission deadline may move earlier.
- Before calculating payroll reminder timing for a specific month, verify the
  current QuickBooks Payroll direct deposit funding time and applicable
  banking-day/holiday rules.
- Intuit guidance says payroll is not processed on weekends or state or federal
  holidays, so the effective submission deadline must be based on business
  processing days rather than calendar days.
- Until the exact funding time is confirmed for the active QuickBooks Payroll
  setup, use conservative reminders: start review no later than the 7th, warn on
  the 10th if not complete, and escalate earlier when the 15th is near a weekend
  or holiday.

## Dependency Rules

### BofA Checking Reconciliation

- AM-008 cannot be completed until both prerequisite sources are ready:
  merchant account statements and BofA checking statement/data.
- The reminder should ask whether both prerequisites are ready before treating
  the task as simply due.
- If either prerequisite is missing, track AM-008 as waiting on source
  availability rather than as ready for reconciliation.
- The related Confluence page for the new merchant-based reconciliation process
  is linked from AM-008. Keep this register limited to sanitized guidance and
  links.
