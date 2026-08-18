# Monthly Invoice Generation Workflow

Source page:
[Create Monthly Invoices with SaasAnt Transactions](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/94306305/Create+Monthly+Invoices+with+SaasAnt+Transactions)

Confluence page version consumed: 4.

This local note summarizes the operational workflow for AM-002. It is not a
replacement for the Confluence how-to. Do not store passwords, database
credentials, tokens, customer private data, invoice exports, or raw production
records in this file.

## Timing Rule

- Monthly invoices are due on the 1st of the month.
- If the 1st falls on a weekend or holiday, complete invoices on the next
  business day unless the human operator gives a different instruction.
- NASDAQ invoice handling requires Coupa.

## Prerequisites

- Latest invoice-processing spreadsheet from the approved OneDrive accounting
  folder.
- Production VPN connection for spreadsheet refresh.
- SendThisFile QuickBooks company file open.
- SaasAnt Transactions available.
- Access to send forms from QuickBooks using the approved accounting email
  account. Never store that password here.
- Approved production database access for the post-import invoice-cycle update.

## File Naming

- Monthly invoice spreadsheet: `MMDDYYYY-invoices.xlsx`
- SaasAnt success report: `MMDDYYYY-invoices-imported.csv`

## High-Level Steps

1. Locate the latest invoice-processing spreadsheet in the approved OneDrive
   accounting folder.
2. Create a new spreadsheet from the latest file using the monthly invoice
   naming convention: `MMDDYYYY-invoices.xlsx`.
3. Refresh the spreadsheet's embedded queries while connected to production VPN.
4. Save the refreshed spreadsheet.
5. Open SaasAnt Transactions and start an import.
6. Select `Invoice` as the transaction/list type.
7. Select the refreshed spreadsheet and the correct current-invoice sheet.
8. Select the saved mapping named `STF Invoice Mapping`.
9. Review SaasAnt mappings.
10. In import settings, confirm customer matching is set to Account No.
11. Review import data.
12. Send the import to QuickBooks.
13. Download the SaasAnt success report, name it
    `MMDDYYYY-invoices-imported.csv`, and save it with the invoice-processing
    files.
14. Review newly imported invoices in QuickBooks.
15. Mark each reviewed invoice with `Email Later`.
16. Use QuickBooks `Send Forms` to email invoices from the approved accounting
    email account.
17. Use the SaasAnt success report to generate the production database update
    statements for the next billing cycle. The Confluence page shows this Excel
    formula:
    `=CONCATENATE("call pBilling.processInvoice(", C2, "); commit;")`
18. The human operator manually runs the generated production database update
    statements.
19. Verify PPQ/action-date results: monthly invoices should move to next month
    and annual invoices should move to next year. The Confluence page shows
    this verification query pattern:
    `select actiondate from paymentprocessingqueue where accountid in (accountid1, acccountid2)`
20. After QuickBooks `Send Forms` has completed, AM-002 can be marked complete.

## SaasAnt Mapping

Use saved mapping `STF Invoice Mapping`.

Expected mapping:

| SaasAnt Field | Mapping |
| --- | --- |
| Customer | `ACCOUNTID` from spreadsheet |
| Invoice Date | `INVOICEDATE` from spreadsheet |
| Product/Service | Set to value if empty: `SendThisFile` |
| Product/Service Description | `INVOICEDESCRIPTION` from spreadsheet |
| Product/Service Amount | `INVOICEAMOUNT` from spreadsheet |

## Critical Review Points

- Confirm the correct spreadsheet and current-invoice sheet are selected.
- Confirm saved mapping `STF Invoice Mapping` is selected.
- Confirm SaasAnt customer matching uses Account No.
- Review import rows before sending to QuickBooks.
- Review each imported invoice in QuickBooks before sending.
- Confirm all intended invoices were sent.
- Confirm the post-import update changes the next invoice action date correctly.
- Use the success report to generate statements only for reviewed successful
  invoice imports.
- Treat production database updates as an approved/manual step that requires the
  proper production access path; never store credentials in this repo.
- If an imported invoice looks wrong, stop and route it for human review with
  Accounting Analyst input before sending or relying on that invoice.
- If AM-002 is blocked by VPN, spreadsheet refresh, QuickBooks company-file
  access, SaasAnt import failure, email authentication, or database access,
  notify the human operator.

## Known Limits

- The in-app browser exposed the Excel formula and PPQ query text that the API
  extraction missed.
- Production database updates are currently a manual human-operated step.
- The exact production database execution tool/path should remain outside this
  repo unless it can be documented without credentials or sensitive operational
  details.

## Streamlining Opportunities

Potential improvements are tracked in
`accounting-analyst/docs/improvement-backlog.md`.

Initial observations:

- The workflow has several pre-flight dependencies that can cause Day 1 delays:
  VPN, latest spreadsheet, QuickBooks company file, SaasAnt, saved mapping, and
  accounting email access.
- File naming is predictable and could be validated by a local helper before
  import.
- The success-report formula step is repetitive and vulnerable to copy/paste
  mistakes.
- The production database update should remain human-operated for now, but the
  generated statements and PPQ verification list could potentially be prepared
  more consistently by a local helper.
- Completion reporting would be stronger with a small monthly invoice-run
  record that captures the spreadsheet, success report, Send Forms completion,
  manual database update confirmation, and PPQ verification result.

## Questions

Open questions are tracked in `accounting-analyst/docs/questions.md`.
