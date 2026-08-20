# Payroll Tax Deposits

This note documents the learned status for AM-020.

Do not store payroll amounts, tax IDs, employee details, bank details,
confirmation numbers, filing contents, credentials, or sensitive tax data in
this file.

## Current Status

- Active monthly task.
- Performed after payroll processing.
- Actual due dates are displayed in QBDT Payroll Center > Pay Liabilities.
- Related Confluence page: `Processing Payroll`, section `Make Payroll Tax
  Deposits`.

## Filings And Portals

Monthly filings/payments include:

- Federal 941 deposit through EFTPS.gov.
- Kansas KW-5 through KDOR.
- Missouri MO-941 through mytax.mo.gov.

## Timing

Payroll tax deposits can be completed immediately after payroll if funds are
available. Each filing/payment must be completed before the due date shown in
QBDT Payroll Center > Pay Liabilities.

## Evidence And Storage

Save filing/payment PDFs in the monthly `Invoices and Receipts` folder, such as
`YYYY\YYYYMM\Invoices and Receipts`.

Expected filename patterns:

```text
EFTPS - RCPT - MMDDYYYY.pdf
KS Withholding - RCPT - MMDDYYYY.pdf
KS Withholding - RCPT2 - MMDDYYYY.pdf
MO-941 - MMDDYYYY.pdf
MO-941 - RCPT - MMDDYYYY.pdf
MO-941 - RCPT2 - MMDDYYYY.pdf
```

Kansas requires two receipts because it is reported semi-monthly: 1st through
15th and 16th through end of month.

For Missouri, save both the MO-941 report and confirmations for filing and
payment.

## Completion Check

AM-020 is complete when all required federal, Kansas, and Missouri monthly
filings/payments are completed by their QBDT Pay Liabilities due dates and the
expected PDFs are saved in the approved monthly location.

## Streamlining Notes

- Build a checklist from QBDT Pay Liabilities due dates after payroll is
  submitted.
- Consider a read-only filename check for expected confirmation PDFs.
