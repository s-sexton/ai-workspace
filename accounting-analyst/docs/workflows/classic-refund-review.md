# Classic Refund Review

This note documents the learned status for AM-012.

Do not store customer names, account IDs, refund amounts by customer, payment
details, credentials, raw emails, or sensitive transaction details in this file.

## Current Status

- Active monthly control task.
- Timing: Days 1-5.
- This is a review of the Classic refund process, not a generic cancellation
  task.

## Scope

AM-012 concerns specific Classic customer refunds.

App refunds are requested via support and processed directly in Chargebee.

## Classic Automated Refund Process

An automated cron job attempts to process refunds for Classic annual customers.
The Classic system pushes refunds through Cybersource.

The automated process sends reports to `accounting@`, which feeds into JSM:

- Pending refunds when the job pauses because a threshold is hit.
- Completed refunds when refunds are processed.

The automated job pauses and does not process refunds when:

- A single refund is over `$50`.
- A single account has more than one refund.

Those exceptions require review and manual processing.

## Manual Review

For paused automated refunds, Scott manually pulls up the customer/account to
understand what happened.

Common scenario: a customer signed up more than once, generating multiple
refunds. Most reviewed items are pushed through, but there have been cases where
the automated refund was not correct.

Monthly customer refund requests are manual.

## Completion Check

AM-012 is complete when:

- Refunds are clear.
- A completed refunds email has hit the `accounting@` JSM queue.
