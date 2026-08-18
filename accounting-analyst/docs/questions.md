# Accounting Analyst Question Tracker

This file tracks open workflow questions so they do not get lost in chat.

Do not store passwords, credentials, customer private data, raw invoice rows,
bank details, or production database records in this file.

## Question Status

| ID | Area | Question | Status | Notes |
| --- | --- | --- | --- | --- |
| AQ-001 | Monthly invoices | What is the exact naming convention for the new monthly invoice spreadsheet? | answered | See answered questions. |
| AQ-002 | Monthly invoices | What is the exact naming convention for the SaasAnt success report? | answered | See answered questions. |
| AQ-003 | Monthly invoices | What is the exact SaasAnt field mapping, or should a screenshot/export remain the source of truth outside this repo? | answered | Human provided mapping. |
| AQ-004 | Monthly invoices | Should SaasAnt saved mappings truly remain blank every month, or is the guidance only saying not to choose an existing mapping during import? | answered | Use saved mapping `STF Invoice Mapping`. |
| AQ-005 | Monthly invoices | What does the missing Excel formula generate from the SaasAnt success report? | answered | Formula found through in-app browser DOM; see answered questions. |
| AQ-006 | Monthly invoices | What is the approved way to run the production database update statements after invoices import? | answered | Currently a manual human-operated process using queries generated from formulas on the success report. |
| AQ-007 | Monthly invoices | What PPQ query or report should verify that monthly invoices moved to next month and annual invoices moved to next year? | answered | Query pattern found through in-app browser DOM; see answered questions. |
| AQ-008 | Monthly invoices | Is AM-002 complete when QuickBooks Send Forms finishes, or only after a sent-email/report check? | answered | Mark complete after QuickBooks Send Forms has completed. |
| AQ-009 | Monthly invoices | What should happen when an imported invoice looks wrong during QuickBooks review? | answered | Needs human review with Accounting Analyst input. |
| AQ-010 | Monthly invoices | Who should be notified if AM-002 is blocked by VPN, spreadsheet refresh, QuickBooks company-file access, SaasAnt import failure, email authentication, or database access? | answered | Notify the human operator. |
| AQ-011 | BofA checking reconciliation | What is the Confluence link or page title for the new merchant-based reconciliation process? | answered | Related task: AM-008. |
| AQ-012 | Monthly invoices | Can the embedded Confluence images/attachments be accessed through the current Confluence OAuth route, browser session, or an export? | answered | Text body is readable through API; in-app browser can see the page and image buttons. Attachment API returned unauthorized. |
| AQ-013 | A/R reminders | Should AM-003 remain as a manual A/R aging email-decision task? | answered | Retire manual task; QBDT payment reminders now handle escalating reminders. |
| AQ-014 | Statements | Should AM-004 remain as a manual statement-sending task? | answered | Retire manual statement sending; QBDT payment reminders are more effective. |
| AQ-015 | A/R reminders | How should we prevent QBDT payment reminders from being sent when payments have been received through any channel but not yet received/applied in QuickBooks? | answered | Use deposit-folder evidence, BofA Classic Clearing review when needed, and recent BofA ACH/wire activity review for transactions without remittance. |
| AQ-016 | A/R payment channels | For each payment channel, what source should be checked before sending reminders, and what evidence is enough to suppress or delay a reminder? | answered | Search month-specific deposit records by invoice, review BofA Classic Clearing when needed, and check recent BofA ACH/wire activity without remittance. |
| AQ-017 | Physical checks | What is the physical-check receipt and deposit process? | answered | Human pickup from mailbox, sign checks, deposit via BofA mobile app, photocopy, store electronic copies in Accounting records. |
| AQ-018 | ACH/wires | How are ACH/wire payments identified and confirmed before reminders are sent? | answered | Remittance identifies invoice/customer when available; BofA website/statement confirms funds arrived. |
| AQ-019 | Processor payments | How are phone payments and one-time-use credit cards processed and tied to invoices? | answered | Both use Cybersource/Visa Virtual Terminal. Phone payments are verified during the call; one-time-use card details arrive by accounting@ email/link. Processor payments settle in batches. |
| AQ-020 | Processor payments | What Cybersource/Visa source or report should be checked before QBDT payment reminders are sent? | answered | No Cybersource report is needed under the changed reconciliation process; use Virtual Terminal receipt plus receipt into BofA Classic Clearing account. |
| AQ-021 | Deposit records | What are the naming conventions for deposit/receipt records by collection method? | answered | Check batch, ACH, WIRE, and CSVT naming conventions documented. |
| AQ-022 | Processor payments | What BofA Classic Clearing view/report or receipt evidence should be checked before reminders are sent? | answered | Month-specific deposit-folder invoice evidence may be enough; review BofA Classic Clearing account/register when needed. |

## Answered Questions

| ID | Area | Answer | Date |
| --- | --- | --- | --- |
| AQ-005 | Monthly invoices | The success-report formula shown on the Confluence page is `=CONCATENATE("call pBilling.processInvoice(", C2, "); commit;")`. It generates one production database call per success-report row using the account ID in column C. | 2026-08-18 |
| AQ-001 | Monthly invoices | Monthly invoice spreadsheets should be named `MMDDYYYY-invoices.xlsx`. | 2026-08-18 |
| AQ-002 | Monthly invoices | SaasAnt success reports should be named `MMDDYYYY-invoices-imported.csv`. | 2026-08-18 |
| AQ-003 | Monthly invoices | SaasAnt mapping: Customer -> `ACCOUNTID`; Invoice Date -> `INVOICEDATE`; Product/Service -> set to value if empty `SendThisFile`; Product/Service Description -> `INVOICEDESCRIPTION`; Product/Service Amount -> `INVOICEAMOUNT`. | 2026-08-18 |
| AQ-004 | Monthly invoices | Select the saved mapping named `STF Invoice Mapping`. | 2026-08-18 |
| AQ-006 | Monthly invoices | The production database update remains a manual process run by the human operator using the queries generated from formulas included on the success report. | 2026-08-18 |
| AQ-007 | Monthly invoices | The PPQ verification query pattern shown on the Confluence page is `select actiondate from paymentprocessingqueue where accountid in (accountid1, acccountid2)`. The page also shows an Excel formula for building the account ID list: `=CONCAT(IF(ISBLANK(I1), "select actiondate from paymentprocessingqueue where accountid in (",I1),C2,IF(ISBLANK(C3),")",", "))`. | 2026-08-18 |
| AQ-008 | Monthly invoices | AM-002 should be marked complete after the QuickBooks Send Forms process has completed. | 2026-08-18 |
| AQ-009 | Monthly invoices | If an imported invoice looks wrong during QuickBooks review, it needs human review with input from the Accounting Analyst. | 2026-08-18 |
| AQ-010 | Monthly invoices | If AM-002 is blocked by VPN, spreadsheet refresh, QuickBooks company-file access, SaasAnt import failure, email authentication, or database access, notify the human operator. | 2026-08-18 |
| AQ-011 | BofA checking reconciliation | The related Confluence page surfaced in related content is `Reconcile Bank of America Checking (Merchant Account Driven)`: `https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/539688962/Reconcile+Bank+of+America+Checking+Merchant+Account+Driven`. | 2026-08-18 |
| AQ-012 | Monthly invoices | Yes, the in-app browser can see the open Confluence tab. The visible DOM includes image buttons for `inv1.PNG`, `inv2.PNG`, `image-20211101-150432.png`, `inv4.PNG`, `inv5.PNG`, and `inv6.PNG`. The direct Confluence attachment API was unauthorized, so image rendering should use the authenticated browser session or an export. | 2026-08-18 |
| AQ-013 | A/R reminders | AM-003 should be removed as a manual aging-report email-decision workflow. QuickBooks Desktop payment reminders are configured for all customers with escalating reminders at 31, 61, 91, and 121 days after due date. Keep a lightweight monthly configuration check instead. | 2026-08-18 |
| AQ-014 | Statements | AM-004 should be retired as a manual monthly statement-sending workflow because QBDT payment reminders have been more effective. Keep the historical statement how-to as a reference only unless the human operator reactivates statements. | 2026-08-18 |
| AQ-017 | Physical checks | Physical checks are picked up by the human operator at the mailbox location. There may or may not be checks. Received checks are signed by the human operator, deposited using the BofA mobile app, photocopied, and stored electronically in approved Accounting records folder structures. | 2026-08-18 |
| AQ-018 | ACH/wires | Some customers send remittance to `accounting@`, which flows into JSM and is saved with scanned-check records. Remittance helps identify invoice number/customer but does not prove funds arrived. BofA website/statement deposit activity is usually the source of truth for cash receipt. Without remittance, the human operator monitors BofA and uses deposit descriptions when possible to identify the customer. | 2026-08-18 |
| AQ-019 | Processor payments | Phone payments are handled while speaking with the customer, allowing the human operator to ask/verify invoice number and amount. The human operator logs into Cybersource and uses Virtual Terminal to enter customer/invoice, address, credit card information, and process the payment. One-time-use credit card payments use the same Virtual Terminal process, but the customer or third party sends invoice information and a link to one-time-use card details to `accounting@`. These payments do not receive directly into BofA checking one-by-one; they settle from the processor in batches, so reconciliation is different. | 2026-08-18 |
| AQ-020 | Processor payments | A Cybersource report is no longer needed because the reconciliation process changed. After processing payment through Virtual Terminal, the payment can be received into the BofA Classic Clearing account for that month's reconciliation. | 2026-08-18 |
| AQ-021 | Deposit records | Deposit naming conventions: check batches use `checks - MMDDYYYY.pdf`; ACH records use `Customer Name - ACH - INV#### - MMDDYYYY.pdf`; wire records may use `Customer Name - WIRE - INV#### - MMDDYYYY.pdf`; Cybersource/Visa Virtual Terminal records use `Customer Name - CSVT - INV#### - MMDDYYYY.pdf`. `CSVT` means Cybersource Virtual Terminal. | 2026-08-18 |
| AQ-015 | A/R reminders | Before sending QBDT reminders, check month-specific deposit evidence by invoice number, review BofA Classic Clearing when needed, and log into BofA to look for recent ACH/wire transactions with no remittance. If evidence suggests the invoice may already be paid but not applied in QuickBooks, suppress or delay the reminder and escalate for human review. | 2026-08-18 |
| AQ-016 | A/R payment channels | Practical sources before reminders: deposit folder invoice evidence for ACH/CSVT/check records; BofA Classic Clearing review for processor payments when needed; BofA website recent ACH/wire activity for transactions without remittance. | 2026-08-18 |
| AQ-022 | Processor payments | Searching the month-specific `Deposits` folder for matching invoice evidence may be enough, with BofA Classic Clearing account/register review when needed to confirm receipt into clearing. | 2026-08-18 |
