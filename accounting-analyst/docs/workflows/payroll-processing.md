# Payroll Processing

This note documents the learned status for AM-018.

Do not store employee compensation, payroll amounts, bank details, tax IDs,
paycheck images, credentials, confirmation numbers, or employee private data in
this file.

## Current Status

- Active monthly task.
- Target timing is Day 10, adjusted as needed so direct deposit reaches employee
  accounts by the 15th.
- Related Confluence page: `Processing Payroll`.
- The Confluence page is current.

## Payroll Setup

Payroll is believed to use QuickBooks Desktop Enhanced Payroll with direct
deposit.

## Timing

The top section of the `Processing Payroll` Confluence page describes the
current direct-deposit submission timing rule. Use that page as the source for
month-specific reminder timing, especially when the 15th falls on a weekend or
holiday.

Until the exact rule is parsed into an operating schedule, use conservative
reminders:

- Start review no later than the 7th.
- Warn on the 10th if payroll is not complete.
- Escalate earlier when the 15th is near a weekend or holiday.

## Review And Submission

No separate reports or approvals are required before submission. Scott manually
reviews each paycheck, then submits payroll.

## Completion Check

AM-018 is complete when payroll confirmation is received.

## Streamlining Notes

- Extract the Confluence lead-time rule into reminder logic that adjusts for
  weekends and holidays.
- Create a sanitized payroll run checklist that records review, submission, and
  confirmation status without storing employee-level payroll details.
