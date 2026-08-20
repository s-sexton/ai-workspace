# Inactive Classic Invoice Customers

This note documents the learned status for AM-026.

Do not store customer names, account IDs, invoice details, database rows,
credentials, collection notes, or sensitive customer/payment data in this file.

## Current Status

- Active last-day control.
- Applies only to Classic invoice customers.
- Purpose is to prevent canceled or non-paying customers from remaining in PPQ.

## Why It Matters

PPQ means `paymentprocessingqueue`. PPQ drives automated billing and provides
invoice information for QBDT import through SaasAnt Transactions.

If a canceled or non-paying customer remains in PPQ, another invoice may be
generated.

## Inactive Forms

When trying to collect payment, Classic enterprise forms (`EP forms`) can be
inactivated through the admin app. The intent is that the customer may reach out
and submit payment.

## Handling

Removal/cancellation can be done through:

- Classic admin.
- Manual Classic database query/update.

Manual database work is human-controlled. The Accounting Analyst may document
the process, ask review questions, and track sanitized completion status, but
does not independently modify Classic database records.

## Completion Check

AM-026 is complete when the last-day review confirms canceled/non-paying Classic
invoice customers are not positioned to generate another invoice through PPQ.

## Open Clarification

The original checklist also says to log outstanding invoices as bad debt. The
current learned process describes AM-026 as a preventative billing step. Clarify
whether bad-debt write-off still belongs in this workflow or should be tracked
as a separate accounting task.

## Streamlining Notes

- Define a sanitized checklist for last-day PPQ prevention status.
- Keep bad-debt accounting separate unless the process confirms it belongs here.
