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
| AM-003 | replaced | Day 1 | Verify QBDT payment reminders configuration and review/send process | [Local workflow note](workflows/qbdt-payment-reminders.md) | Replaces manual `A/R Aging Detail w/ AccountID` email-decision task. QBDT prompts the user to review and send escalating unpaid-invoice reminders at 31, 61, 91, and 121 days after due date. |
| AM-004 | replaced | Day 1 | Verify QBDT payment reminders configuration instead of sending statements | [Create Statements](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/10158103/Create+Statements); [Local workflow note](workflows/qbdt-payment-reminders.md) | Manual statements are retired because QBDT payment reminders have been more effective. |
| AM-005 | open | Day 1 | Record Unearned Revenue | [Recording Unearned Revenue](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/9928707/Recording+Unearned+Revenue); [Local workflow note](workflows/unearned-revenue.md) | Monthly close task for the prior month. Uses the QBDT memorized transaction named `Unearned Revenue` and validates the balance sheet line item against the supporting spreadsheet. |
| AM-006 | replaced | Day 1 | Verify merchant clearing accounts process covers refunds and chargebacks | [Enter Refunds Charge Backs](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/11141121/Enter+Refunds+Charge+Backs); [Local workflow note](workflows/refunds-chargebacks.md) | Standalone refund/chargeback entry process is retired as of 2026-01-01 because refunds and chargebacks are handled through the merchant clearing accounts process. Historical Confluence page moved under `Archived Accounting Procedures`. |
| AM-007 | retired | Day 1 | Enter Pre-paid Expenses | [Enter Pre-paid Expenses](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/11829249/Enter+Pre-paid+Expenses); [Local workflow note](workflows/prepaid-expenses.md) | Retired as of 2026-08-18 because there are no longer prepaid expenses to enter. Historical Confluence page moved under `Archived Accounting Procedures`. |
| AM-008 | open | Day 1 | Reconcile BofA checking | [Reconcile Bank of America Checking Automated](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/10289170/Reconcile+Bank+of+America+Checking+Automated); [Reconcile Bank of America Checking Merchant Account Driven](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/539688962/Reconcile+Bank+of+America+Checking+Merchant+Account+Driven); [Local workflow note](workflows/bofa-checking-reconciliation.md) | Active task. Merchant-driven page is the current process; older automated page remains valid for showing how to reconcile the actual account in QBDT. Requires merchant statements and BofA checking statement/data to be ready. |
| AM-009 | retired | Day 1 | Reconcile Emprise Bank Checking Account | [Local workflow note](workflows/emprise-bank-checking.md) | Retired because the SendThisFile Emprise Bank checking account is closed. Historical statements remain in the Emprise Bank folder and historical information remains in QBDT. |
| AM-010 | open | Day 5 | Reconcile PayPal | [Reconcile PayPal Statements](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/297959425/Reconcile+PayPal+Statements); [Local workflow note](workflows/paypal-reconciliation.md) | Active task. Source report is stored in the PayPal folder. Complete when the PayPal account has been reconciled in QBDT. |
| AM-011 | open | Day 1 | Reconcile LiveOakBank investment statement | [Reconcile Investment Statements](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/11501571/Reconcile+Investment+Statements); [Local workflow note](workflows/investment-reconciliation.md) | Active task. Only current investment account is LiveOakBank. Source statement and QBDT reconciliation output live in the monthly `Investment Accounts` folder. |
| AM-012 | open | Day 1-5 | Review Classic refund processing and exceptions | [Local workflow note](workflows/classic-refund-review.md) | Active control task. Automated Classic refund job processes eligible annual customer refunds through Cybersource but pauses exceptions over threshold or with multiple refunds. Monthly customer refunds are manual. App refunds are requested via support and processed in Chargebee. |
| AM-013 | open | Day 1-7 | Pay contractor invoices for prior month and enter into QuickBooks | [Contractor Vendor Payments](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/1867789/Contractor+Vendor+Payments); [Local workflow note](workflows/contractor-vendor-payments.md) | Active task. Contractor invoices usually arrive by email to `accounting@` or directly to Scott. Scott approves them. Invoices are entered as bills in QBDT and complete when payment has been made. |
| AM-014 | open | Day 4 | Get list of enterprise accounts that failed billing | [Local workflow note](workflows/enterprise-failed-billing.md) | Active task. Failed billing list comes through the internal-alert distribution list and is handed off to support for customer outreach. |
| AM-015 | open | Day 10 / Day 20 | Verify Hartford insurance auto-draft and download invoice | [Local workflow note](workflows/hartford-insurance-premium.md) | Hartford is auto-drafted from checking on the 10th. Treat as a verify step, plus reminder to download the invoice when generated around the 20th. |
| AM-016 | open | Day 7 | Reconcile BofA credit cards | [Reconcile Bank of America Credit Cards](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/36601857/Reconcile+Bank+of+America+Credit+Cards); [Local workflow note](workflows/bofa-credit-card-reconciliation.md) | Active task. Credit card cycle closes on the 6th and the statement is usually ready by the 7th. Four cards roll up into one master statement. Verify receipts and complete QBDT reconciliation. |
| AM-017 | open | Day 7 | Complete financial statements and delivery to shareholders | [Local workflow note](workflows/financial-statements-shareholders.md) | Active task, but often pushed back. Target should be made firmer. Typical package includes P&L, balance sheet, and any requested additional reports. |
| AM-018 | open | Day 10 | Process payroll to be paid on the 15th of the month | [Processing Payroll](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/20414465/Processing+Payroll); [Local workflow note](workflows/payroll-processing.md) | Active task. QBDT Enhanced Payroll with direct deposit. Review each paycheck manually, submit payroll early enough for payday, and complete when confirmation is received. |
| AM-019 | open | Day 10 | Perform distribution if needed | [Local workflow note](workflows/monthly-distribution.md) | Active monthly review task. Majority shareholder decides whether distribution is needed after considering cash balance, profitability, shareholder decision, tax planning, and related factors. |
| AM-020 | open | After AM-018 / by QBDT due dates | Pay payroll taxes | [Processing Payroll - Make Payroll Tax Deposits](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/20414465/Processing+Payroll#Make-Payroll-Tax-Deposits); [Local workflow note](workflows/payroll-tax-deposits.md) | Active task after payroll. Federal 941, Kansas KW-5, and Missouri MO-941 liabilities are paid monthly. Due dates come from QBDT Payroll Center > Pay Liabilities. |
| AM-021 | open | Day 10 | Check for outstanding PPQ records that have not been processed | [Local workflow note](workflows/ppq-integrity-check.md) | Active queue-integrity control for Classic `paymentprocessingqueue`. Outstanding means action date is before today, which should not happen. Complete with a clean PPQ query. |
| AM-022 | replaced | On request | Provide pay stubs to employees if requested | [Local workflow note](workflows/pay-stubs.md) | Retire monthly send task. Employees can access pay stubs through the QuickBooks portal; Scott may provide a one-off copy when requested. |
| AM-023 | open | Day 15 | Manage AMEX chargebacks and cancellations | [Local workflow note](workflows/amex-chargebacks-cancellations.md) | Active reminder/review task. Separate from reconciliation because it creates a chance to challenge AMEX chargebacks and confirm Classic customer cancellation when chargebacks are accepted. |
| AM-024 | open | Day 25 | Pay BCBS via online ACH | [Paying BCBS](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/42532865/Paying+BCBS); [Local workflow note](workflows/bcbs-payment.md) | Active task. Invoice usually available around the 12th. Paid manually through the portal; QBDT vendor bill and vendor payment still need to be recorded for tracking. |
| AM-025 | duplicate/checkpoint | Day 27 | Second monthly chargeback and cancellation review | [Local workflow note](workflows/amex-chargebacks-cancellations.md) | Same control as AM-023, intended as a second monthly check near month end. |
| AM-026 | open | Last Day | Remove inactive Classic invoice customers from future automated billing | [Local workflow note](workflows/inactive-classic-invoice-customers.md) | Active control. Prevents canceled/non-paying Classic invoice customers from remaining in PPQ, which drives automated billing and SaasAnt/QBDT invoice import data. Bad-debt accounting follow-up still needs clarification. |
| AM-027 | automation-candidate | Last Day | Run integrity report in BIRT before credit-card billing | [Data Integrity Report](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/44793859/Data+Integrity+Report); [Local workflow note](workflows/birt-data-integrity-report.md) | Not ideal as a manual task. Report checks Classic PPQ for record anomalies before Classic credit-card billing; prime candidate for automation/notification with proof of execution. |
| AM-028 | retired/replaced | Customer setup | Run SaasAnt catch-all for new invoice customers | [Invoice Customers](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/111706113/Invoice+Customers); [Local workflow note](workflows/late-saasant-invoice-catchall.md) | Retire as monthly catch-all. This only impacts Classic and should be handled during the manual invoice-customer setup process. |
| AM-029 | rolled-up/automation-candidate | Last Day | Check blacklisted accounts for payment processing records | [Query for blacklisted paid plans](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/44662785/Query+for+blacklisted+paid+plans); [Local workflow note](workflows/blacklisted-paid-plans.md) | Roll into the AM-027 Classic integrity automation/notification work. Blacklisted accounts are manually blocked for abuse; Classic paid-plan records should be checked and an artifact generated. |

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
  current QuickBooks Payroll direct deposit funding time from the top section of
  the `Processing Payroll` Confluence page and applicable banking-day/holiday
  rules.
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

## Retired Or Replaced Manual Tasks

### AM-003 A/R Aging Email Review

- The prior manual task was to run `A/R Aging Detail w/ AccountID` and determine
  who needed to be emailed.
- This has been replaced by QuickBooks Desktop payment reminders with
  escalating language. QBDT prompts the user to review and send; reminders are
  not treated as fully autonomous sends.
- Current observed schedule: all customers, 31/61/91/121 days after due date.
- Keep a lightweight monthly control check to verify the reminder schedule is
  enabled and unchanged, and that recent check deposits have been received or
  considered before reminders are sent.

### AM-004 Send Statements

- The prior manual task was to send statements.
- This has also been replaced by QuickBooks Desktop payment reminders because
  payment reminders have been more effective than statements.
- Keep the historical Confluence statement how-to link for reference, but do not
  treat statement sending as an active monthly task unless the human operator
  reactivates it.
