# Monthly Distribution

This note documents the learned status for AM-019.

Do not store shareholder private details, bank details, transfer amounts,
confirmation numbers, tax advice, credentials, or sensitive financial data in
this file.

## Current Status

- Active monthly review task.
- Timing target is Day 10.
- Distribution only happens if needed.

## Decision Inputs

Distribution review may consider:

- Cash balance.
- Profitability.
- Shareholder decision factors.
- Tax planning.
- Other relevant circumstances.

## Decision Rights

The majority shareholder decides whether a distribution is needed.

The Accounting Analyst may help gather sanitized inputs, maintain the checklist,
track completion, and recommend questions for review. The Accounting Analyst
does not independently decide, approve, or initiate distributions.

## QBDT Recording

Use the QBDT memorized transaction named `Monthly Distribution`.

## Payment Handling

Distribution payments are made manually through the BofA portal.

## Evidence And Storage

Save a PDF capture of the successful BofA transfer for each shareholder in the
monthly `Invoices and Receipts` directory, such as
`YYYY\YYYYMM\Invoices and Receipts`.

Use the naming format:

```text
XXX-DIST-MMDDYYYY.pdf
```

`XXX` represents the shareholder initials.

## Completion Check

AM-019 is complete when any approved distribution has been recorded in QBDT,
paid through BofA, and the successful-transfer PDF captures have been saved in
the approved location. If no distribution is needed, record the review outcome
as `not needed` for that month.

## Streamlining Notes

- Define a checklist that separates decision inputs from the actual shareholder
  decision.
- Consider a read-only file-presence check for expected transfer confirmation
  PDFs after a distribution has been approved and paid.
