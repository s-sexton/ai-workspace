# QuickBooks Desktop Payment Reminders

This note documents the replacement for the former AM-003 manual A/R aging email
review and AM-004 monthly statement sending.

Do not store customer names, invoice details, email bodies, account numbers, or
private collections notes in this file.

## Process Decision

The prior monthly task `AM-003 - Run A/R Aging Detail w/ AccountID report and
determine who needs to get emailed` is retired as a manual recurring task.

The prior monthly task `AM-004 - Send statements` is also retired as a manual
recurring task because payment reminders have been more effective than
statements.

QuickBooks Desktop payment reminders now prompt the QBDT user to review and
send unpaid-invoice reminder emails using escalating reminder language as
invoices age. The reminders are not treated as fully autonomous sends.

## Current Reminder Schedule

Screenshot reviewed on 2026-08-18 showed:

- Reminder schedule: `Unpaid Invoice Reminder`
- Enabled: yes
- Customer group: all customers
- Reminder timing:
  - 31 days after due date
  - 61 days after due date
  - 91 days after due date
  - 121 days after due date

## Monthly Control Check

Instead of manually running the A/R aging report or sending statements, perform
a lightweight monthly control check:

- Confirm the `Unpaid Invoice Reminder` schedule is still enabled.
- Confirm the schedule still applies to the intended customer group.
- Confirm reminder timing remains 31, 61, 91, and 121 days after due date.
- Confirm the QBDT user reviewed and sent any reminder prompts that required
  action.
- Before reminders are sent, consider whether recent check deposits have been
  received into the checking account but not yet recorded in QuickBooks.
- Confirm no known issue prevented QBDT reminders from sending.
- Escalate to the human operator if the schedule is disabled, changed, or
  believed not to be sending.

## Completion Rule

The replacement control check is complete when the reminder configuration has
been reviewed, any required QBDT reminder prompts have been handled, and any
exceptions have been reported to the human operator.

## Tightening Opportunity

There is a timing risk when payment has arrived through any channel but has not
yet been received or applied in QuickBooks. In that case, a customer may still
appear eligible for a payment reminder even though payment has effectively
arrived.

Invoices can be paid through multiple channels, and the pre-send review needs
to account for the payment path:

| Payment channel | Current note |
| --- | --- |
| Physical check mailed to company mailbox | Human operator drives to mailbox location, picks up any checks, signs them, deposits them using the BofA mobile app, photocopies them, and stores electronic copies in Accounting records. Deposit/application timing can lag QuickBooks receipt. |
| Direct ACH or wire payment | Deposit/application timing can lag QuickBooks receipt. Remittance may identify invoice, but BofA deposit is usually the source of truth that funds arrived. |
| Payment by phone | Processed in Cybersource/Visa Virtual Terminal while speaking with the customer. Invoice number and amount can be asked/verified during the call. Processor payments settle in batches rather than directly as individual BofA checking deposits. |
| Third-party processor one-time-use credit card | Processed in Cybersource/Visa Virtual Terminal. Customer or third party sends invoice information and a link to one-time-use card details to `accounting@`. Processor payments settle in batches rather than directly as individual BofA checking deposits. |

### Physical Check Control Notes

- First reliable signal: human mailbox pickup.
- Pickup result may be either checks received or no checks received.
- When checks are received, the human operator signs them, deposits them through
  the BofA mobile app, photocopies them, and stores electronic copies in the
  approved Accounting records folder structure.
- Before QBDT payment reminders are sent, recent physical-check activity should
  be considered so reminders are not sent for invoices paid by check but not yet
  received/applied in QuickBooks.
- Do not store check images, customer names, account numbers, or deposit details
  in this workflow note.

### ACH/Wire Control Notes

- Some customers send remittance details to `accounting@`, which then flows
  into the JSM process.
- Remittance details are saved to the same Accounting records location as
  scanned checks.
- A remittance is attribution evidence: it helps identify which invoice number
  the customer intends to pay.
- A remittance is not cash evidence by itself because it does not prove the
  payment has hit the bank account.
- The usual source of truth that funds arrived is a deposit shown on the BofA
  website or bank statement.
- If no remittance is sent, the human operator monitors BofA activity and uses
  the deposit description when possible to identify the customer.
- Before QBDT payment reminders are sent, ACH/wire deposits and remittances
  should be considered together: BofA confirms receipt, while remittance or bank
  description helps identify the customer/invoice.

### Processor Payment Control Notes

Processor payment channels include phone payments and one-time-use credit card
payments. These are handled differently from physical checks and ACH/wires.

Phone payment path:

- The human operator is speaking with the customer.
- The human operator can ask for and verify the invoice number and payment
  amount during the call.
- The payment is entered in Cybersource/Visa Virtual Terminal.
- Virtual Terminal entry includes customer/invoice details, address, credit card
  information, and the payment processing action.
- After processing the payment, the human operator has the opportunity to save
  the receipt.
- The receipt is saved with the rest of the deposit records using the applicable
  collection-method naming convention.

One-time-use credit card path:

- The customer or third party sends an email to `accounting@` with invoice
  information and a link to a page containing one-time-use card information.
- The email flows through the accounting/JSM process.
- The human operator uses Cybersource/Visa Virtual Terminal to enter the
  payment, using the same general process as phone payments.
- After processing the payment, the human operator saves the receipt with the
  rest of the deposit records using the applicable collection-method naming
  convention.

Settlement/reconciliation note:

- Payments taken through Cybersource/Visa Virtual Terminal do not get received
  directly into BofA checking as one deposit per invoice.
- Processor payments arrive from the processor in batches.
- Reconciliation for these payments is different from checks and ACH/wires.
- Because the reconciliation process changed, a Cybersource report is not
  expected to be part of the reminder pre-check.
- After the Virtual Terminal payment is processed, the payment can be received
  into the BofA Classic Clearing account for that month's reconciliation.
- Before QBDT payment reminders are sent, recent Virtual Terminal receipts and
  BofA Classic Clearing activity should be considered so customers are not
  reminded for invoices paid through the processor but not yet otherwise
  reflected in QuickBooks.
- Saved Virtual Terminal receipts are part of the evidence trail for these
  payments.

Recommended process improvement:

- Add a pre-send check for recent deposits, Virtual Terminal receipts, or BofA
  Classic Clearing activity that may affect whether an invoice is truly unpaid.
- Define who confirms whether each payment channel has been applied before
  reminder prompts are sent.
- Consider a local exception checklist or report for unapplied/unreceived check
  deposits, ACH/wire payments, and processor payments before reminder review.
- Escalate questionable reminders to the human operator before sending.

Practical pre-reminder check:

- Search the month-specific `Deposits` folder for deposit evidence matching the
  invoice number, such as ACH or CSVT receipt files.
- Review the BofA Classic Clearing account/register when needed to confirm
  processor payments have been received there.
- Log into BofA and review recent ACH/wire transactions that do not have
  remittance, using transaction description details when possible to identify
  the customer or invoice.
- If deposit evidence or recent BofA activity suggests an invoice may already
  be paid but not yet applied in QuickBooks, suppress or delay the reminder and
  escalate for human review.

## Deposit Record Naming Conventions

Observed in the approved Accounting records deposit folder:

| Collection method | Naming convention |
| --- | --- |
| Check batch | `checks - MMDDYYYY.pdf` |
| ACH | `Customer Name - ACH - INV#### - MMDDYYYY.pdf` |
| Wire | `Customer Name - WIRE - INV#### - MMDDYYYY.pdf` |
| Cybersource/Visa Virtual Terminal | `Customer Name - CSVT - INV#### - MMDDYYYY.pdf` |

`CSVT` means Cybersource Virtual Terminal.

## Streamlining Note

This is a tool-removal/streamlining decision: manual monthly report-and-email
and statement-sending steps have been replaced by QBDT's built-in payment
reminder functionality, preserving human oversight through configuration,
review/send, and deposit-application checks.
