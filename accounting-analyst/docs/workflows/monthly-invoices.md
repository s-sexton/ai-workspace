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

## High-Level Steps

1. Locate the latest invoice-processing spreadsheet in the approved OneDrive
   accounting folder.
2. Create a new spreadsheet from the latest file.
3. Refresh the spreadsheet's embedded queries while connected to production VPN.
4. Save the refreshed spreadsheet.
5. Open SaasAnt Transactions and start an import.
6. Select `Invoice` as the transaction/list type.
7. Select the refreshed spreadsheet and the correct current-invoice sheet.
8. Leave saved mappings blank unless the human operator confirms a named mapping
   should be used.
9. Review SaasAnt mappings.
10. In import settings, confirm customer matching is set to Account No.
11. Review import data.
12. Send the import to QuickBooks.
13. Download the SaasAnt success report and save it with the invoice-processing
    files.
14. Review newly imported invoices in QuickBooks.
15. Mark each reviewed invoice with `Email Later`.
16. Use QuickBooks `Send Forms` to email invoices from the approved accounting
    email account.
17. Use the SaasAnt success report to generate the production database update
    statements for the next billing cycle. The Confluence page shows this Excel
    formula:
    `=CONCATENATE("call pBilling.processInvoice(", C2, "); commit;")`
18. Run the approved production database update statements.
19. Verify PPQ/action-date results: monthly invoices should move to next month
    and annual invoices should move to next year. The Confluence page shows
    this verification query pattern:
    `select actiondate from paymentprocessingqueue where accountid in (accountid1, acccountid2)`

## Critical Review Points

- Confirm the correct spreadsheet and current-invoice sheet are selected.
- Confirm SaasAnt customer matching uses Account No.
- Review import rows before sending to QuickBooks.
- Review each imported invoice in QuickBooks before sending.
- Confirm all intended invoices were sent.
- Confirm the post-import update changes the next invoice action date correctly.
- Use the success report to generate statements only for reviewed successful
  invoice imports.
- Treat production database updates as an approved/manual step that requires the
  proper production access path; never store credentials in this repo.

## Known Gaps To Fill

- The Confluence page includes a mapping screenshot. The text extraction did not
  capture the exact SaasAnt field mapping.
- The in-app browser exposed the Excel formula and PPQ query text that the API
  extraction missed.
- The exact saved-file naming convention for the monthly spreadsheet and
  success report should be documented.
- The exact production database execution path should be documented without
  credentials or sensitive operational details.

## Questions

Open questions are tracked in `accounting-analyst/docs/questions.md`.
