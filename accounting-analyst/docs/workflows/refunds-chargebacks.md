# Refunds And Chargebacks

This note documents the learned status for AM-006.

Do not store customer-level rows, merchant account statements, card data,
refund details, chargeback details, credentials, or sensitive transaction
details in this file.

## Current Status

- The standalone refund and chargeback entry process is retired/replaced.
- Effective retirement date: 2026-01-01.
- Historical source page: [Enter Refunds & Charge Backs](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/11141121/Enter+Refunds+Charge+Backs).

## Replacement Process

Refunds and chargebacks are handled through the merchant clearing accounts
process.

The key control is to avoid double counting:

- Refunds are included in daily submitted merchant amounts.
- They should not be counted again individually through the old standalone
  refunds and chargebacks process.

## Confluence Cleanup

The historical Confluence page was handled with the approved cleanup pattern:

- Added a top retired/historical reference notice.
- Added labels: `accounting-retired`, `historical-reference`, and
  `replaced-by-merchant-clearing`.
- Created `Accounting Monthly Close - Active Procedures`.
- Native Confluence archive was attempted but blocked because the tenant is not
  entitled to archiving.
- Created `Archived Accounting Procedures`.
- Moved the retired page under `Archived Accounting Procedures`.

## Monthly Task Handling

Do not send a reminder for a standalone AM-006 refund/chargeback entry task.

If a reminder is needed, it should be framed as a control check that the
merchant clearing accounts process captured refunds and chargebacks without
double counting.
