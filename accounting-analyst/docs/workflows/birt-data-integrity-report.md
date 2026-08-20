# BIRT Data Integrity Report

This note documents the learned status for AM-027.

Do not store customer details, account IDs, database rows, anomaly exports,
credentials, connection strings, or sensitive Classic operational data in this
file.

## Current Status

- Last-day Classic billing control.
- Not ideal as a recurring manual task.
- Prime candidate for automation/notification.
- Related Confluence page: `Data Integrity Report`.
- The Confluence page is current.

## Purpose

The BIRT integrity report checks PPQ for record anomalies before Classic
credit-card billing.

The future automation should also include the blacklisted paid-plan check from
AM-029 as one Classic integrity test.

## Scope

This protects Classic billing.

## Exception Handling

If the report finds issues, follow-up is usually manual.

## Completion Check

Current completion is a checkbox that the report was run.

If automated, completion should include proof that the check was performed and a
sanitized pass/fail or exception status.

## Streamlining Notes

- Evaluate automation or semi-automation for running the check and notifying on
  results.
- Include blacklisted paid-plan detection in the automated Classic integrity
  check.
- Any direct Classic data access or notification workflow requires explicit
  design approval.
- Define a manual remediation checklist for anomalies without storing sensitive
  result rows in the repo.
