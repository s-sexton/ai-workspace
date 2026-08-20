# AMEX Chargebacks And Cancellations

This note documents the learned status for AM-023 and AM-025.

Do not store customer names, cardholder details, chargeback documents, account
IDs, merchant account numbers, card details, credentials, or sensitive dispute
details in this file.

## Current Status

- Active reminder/review task, but not always driven by a new notice.
- Target timing has two checkpoints: Day 15 and Day 27.
- If no notice arrived by email or mail, use this as a reminder to check the
  AMEX portal and other notice channels.
- AM-025 is not a separate workflow; it is the second monthly checkpoint for the
  same chargeback/cancellation control.

## Relationship To Reconciliation

This is separate from AMEX merchant-statement reconciliation. This workflow
exists because chargeback notices may allow SendThisFile to challenge a
chargeback submitted by a cardholder.

## Notice Channels

AMEX chargeback/cancellation notices may arrive through:

- AMEX portal.
- Email.
- Mail.

## Scope

AMEX activity is Classic-only because only the Classic SendThisFile service
accepts AMEX.

## Review Action

For each notice:

- Review the chargeback.
- Challenge if necessary.
- Most of the time, accept the chargeback.
- If accepted, confirm the customer is actually canceled in the Classic system.

Confirming cancellation is critical because otherwise the customer could keep
being charged. Chargebacks can also negatively affect merchant ranking and may
increase fees.

## Completion Check

Each checkpoint is complete when the chargeback/cancellation review is complete.

## Streamlining Notes

- Create a sanitized checklist that confirms notice channels were checked.
- Include a cancellation-verification step for accepted chargebacks.
