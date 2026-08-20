# Late SaasAnt Invoice Catch-All

This note documents the learned status for AM-028.

Do not store customer names, account IDs, invoice rows, database records,
credentials, or sensitive billing details in this file.

## Current Status

- Retired/replaced as a recurring last-day task.
- Applies only to Classic.

## Original Purpose

This was a catch-all in case a customer was migrated to invoice billing instead
of automatic payment and the invoice did not get into QBDT.

## Replacement Process

This should be handled during the manual process of setting up the Classic
invoice customer.

Related Confluence page: `Invoice Customers`.

## Completion Check

There is no recurring monthly completion check. For a customer setup, completion
belongs to the invoice-customer setup workflow.

## Streamlining Notes

Retire AM-028 from the month-end checklist and preserve the control in the
Classic invoice-customer setup process.
