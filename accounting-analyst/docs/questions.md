# Accounting Analyst Question Tracker

This file tracks open workflow questions so they do not get lost in chat.

Do not store passwords, credentials, customer private data, raw invoice rows,
bank details, or production database records in this file.

## Open Questions

| ID | Area | Question | Status | Notes |
| --- | --- | --- | --- | --- |
| AQ-001 | Monthly invoices | What is the exact naming convention for the new monthly invoice spreadsheet? | open | Related task: AM-002. |
| AQ-002 | Monthly invoices | What is the exact naming convention for the SaasAnt success report? | open | Related task: AM-002. |
| AQ-003 | Monthly invoices | What is the exact SaasAnt field mapping, or should a screenshot/export remain the source of truth outside this repo? | open | Confluence page has an embedded mapping image that text extraction did not capture. |
| AQ-004 | Monthly invoices | Should SaasAnt saved mappings truly remain blank every month, or is the guidance only saying not to choose an existing mapping during import? | open | Related task: AM-002. |
| AQ-005 | Monthly invoices | What does the missing Excel formula generate from the SaasAnt success report? | answered | Formula found through in-app browser DOM; see answered questions. |
| AQ-006 | Monthly invoices | What is the approved way to run the production database update statements after invoices import? | open | Keep credentials and production details out of this tracker. |
| AQ-007 | Monthly invoices | What PPQ query or report should verify that monthly invoices moved to next month and annual invoices moved to next year? | answered | Query pattern found through in-app browser DOM; see answered questions. |
| AQ-008 | Monthly invoices | Is AM-002 complete when QuickBooks Send Forms finishes, or only after a sent-email/report check? | open | Completion-report rule needed. |
| AQ-009 | Monthly invoices | What should happen when an imported invoice looks wrong during QuickBooks review? | open | Need exception workflow. |
| AQ-010 | Monthly invoices | Who should be notified if AM-002 is blocked by VPN, spreadsheet refresh, QuickBooks company-file access, SaasAnt import failure, email authentication, or database access? | open | Likely Clarity handoff rule plus human notification. |
| AQ-011 | BofA checking reconciliation | What is the Confluence link or page title for the new merchant-based reconciliation process? | answered | Related task: AM-008. |
| AQ-012 | Monthly invoices | Can the embedded Confluence images/attachments be accessed through the current Confluence OAuth route, browser session, or an export? | answered | Text body is readable through API; in-app browser can see the page and image buttons. Attachment API returned unauthorized. |

## Answered Questions

| ID | Area | Answer | Date |
| --- | --- | --- | --- |
| AQ-005 | Monthly invoices | The success-report formula shown on the Confluence page is `=CONCATENATE("call pBilling.processInvoice(", C2, "); commit;")`. It generates one production database call per success-report row using the account ID in column C. | 2026-08-18 |
| AQ-007 | Monthly invoices | The PPQ verification query pattern shown on the Confluence page is `select actiondate from paymentprocessingqueue where accountid in (accountid1, acccountid2)`. The page also shows an Excel formula for building the account ID list: `=CONCAT(IF(ISBLANK(I1), "select actiondate from paymentprocessingqueue where accountid in (",I1),C2,IF(ISBLANK(C3),")",", "))`. | 2026-08-18 |
| AQ-011 | BofA checking reconciliation | The related Confluence page surfaced in related content is `Reconcile Bank of America Checking (Merchant Account Driven)`: `https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/539688962/Reconcile+Bank+of+America+Checking+Merchant+Account+Driven`. | 2026-08-18 |
| AQ-012 | Monthly invoices | Yes, the in-app browser can see the open Confluence tab. The visible DOM includes image buttons for `inv1.PNG`, `inv2.PNG`, `image-20211101-150432.png`, `inv4.PNG`, `inv5.PNG`, and `inv6.PNG`. The direct Confluence attachment API was unauthorized, so image rendering should use the authenticated browser session or an export. | 2026-08-18 |
