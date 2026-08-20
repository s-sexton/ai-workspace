# PPQ Integrity Check

This note documents the learned status for AM-021.

Do not store account IDs, customer details, database rows, SQL results,
credentials, connection strings, or sensitive Classic operational data in this
file.

## Current Status

- Active or semi-active monthly control.
- Target timing is Day 10.
- The task was created after an earlier issue and may no longer find frequent
  problems, but it protects Classic payment processing queue integrity.

## Meaning

PPQ means `paymentprocessingqueue`.

## Source

The check is against the Classic Oracle database.

## Exception Definition

A PPQ record is outstanding/not processed if it has an action date before today.
This condition should not happen.

## Exception Handling

If outstanding PPQ records are found:

- Research the cause.
- Manually adjust as appropriate.

Manual adjustments are human-controlled actions. The Accounting Analyst may
help document the process, ask review questions, and track sanitized completion
status, but does not independently modify Classic database records.

## Completion Check

AM-021 is complete when the PPQ query is clean.

## Streamlining Notes

- Track clean/exception status over time to decide whether this should remain a
  monthly checklist item or become exception-based monitoring.
- Keep any local log sanitized: check date, result, and whether human review was
  needed only.
