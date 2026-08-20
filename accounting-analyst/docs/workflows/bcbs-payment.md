# BCBS Payment

This note documents the learned status for AM-024.

Do not store employee health information, insurance details, invoice contents,
bank details, payment confirmations, credentials, or sensitive benefit data in
this file.

## Current Status

- Active monthly task.
- Target payment timing is Day 25.
- Related Confluence page: `Paying BCBS`.
- The Confluence page is current.

## Invoice Timing

The BCBS invoice is usually available around the 12th of the month.

## Payment Handling

BCBS is paid manually through the portal.

The vendor bill and vendor payment still need to be recorded in QBDT for
tracking.

## Evidence And Storage

Save files in the monthly `Invoices and Receipts` folder, such as
`YYYY\YYYYMM\Invoices and Receipts`.

Expected filename patterns:

```text
BCBS - INV - MMDDYYYY.pdf
BCBS - RCPT - MMDDYYYY.pdf
```

## Completion Check

AM-024 is complete when the payment confirmation is saved and the QBDT vendor
bill/payment tracking entries are completed.

## Streamlining Notes

- Use a reminder around the 12th to download/save the invoice.
- Use a Day 25 reminder for portal payment and QBDT tracking.
- Consider a read-only filename check for the expected invoice and receipt PDFs.
