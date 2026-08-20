# Blacklisted Paid Plans

This note documents the learned status for AM-029.

Do not store customer names, account IDs, blacklist table rows, payment
processing records, database exports, credentials, or sensitive abuse/billing
details in this file.

## Current Status

- Roll into AM-027 Classic integrity automation/notification work.
- Historically a manual Classic last-day check.
- Related Confluence page: `Query for blacklisted paid plans`.

## Meaning

Blacklisted means SendThisFile found someone abusing the service and manually
placed them in a Blacklist table.

## Purpose

The check identifies blacklisted accounts that still have payment processing
records/paid-plan activity that should not continue.

## Future State

This should be one test in the automated Classic integrity check, alongside PPQ
record-anomaly checks.

The automation should generate a sanitized artifact proving the check was
performed and showing pass/fail or exception status.

## Completion Check

As a standalone manual task, completion was checking the query. In the future
combined control, completion should be the generated integrity-check artifact.

## Streamlining Notes

- Do not keep this as a separate month-end checklist item once the integrity
  automation exists.
- The artifact should not include customer identifiers or raw database rows.
