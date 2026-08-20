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
| AQ-023 | Unearned revenue | Is AM-005 still an active monthly task? | answered | Yes, monthly task. |
| AQ-024 | Unearned revenue | Does the related Confluence page define the current process? | answered | Yes, the current process is defined by the Confluence page. |
| AQ-025 | Unearned revenue | What is the source data for the unearned revenue calculation? | answered | Classic service Oracle database data that feeds the Power BI report. |
| AQ-026 | Unearned revenue | What QuickBooks transaction is used to record unearned revenue? | answered | QBDT memorized transaction named `Unearned Revenue`. |
| AQ-027 | Unearned revenue | What date should be used when posting the monthly memorized transaction? | answered | Last day of the prior month, because that is the month being closed. |
| AQ-028 | Unearned revenue | What is the completion check after posting? | answered | Run a standard balance sheet and confirm the `Unearned Revenue` line item matches the supporting spreadsheet. |
| AQ-029 | Unearned revenue | Is Power BI still required for this workflow, or could the data be obtained more directly? | answered | Power BI may not be required; evaluate whether a secure direct API/query could provide the needed data. |
| AQ-030 | Refunds and chargebacks | Is AM-006 still an active standalone monthly task? | answered | No; the standalone process is retired/replaced as of 2026-01-01. |
| AQ-031 | Refunds and chargebacks | What process replaced standalone refunds and chargebacks? | answered | Merchant clearing accounts process; refunds are included in daily submitted amounts and should not be counted again individually. |
| AQ-032 | Confluence cleanup | How should retired Confluence procedure pages be handled when native Confluence archive is unavailable? | answered | Mark retired, label, create/update an active procedure index, and move the page under `Archived Accounting Procedures`. |
| AQ-033 | Prepaid expenses | Is AM-007 still an active monthly task? | answered | No; the company used to have prepaid expenses, but does not any longer. |
| AQ-034 | Prepaid expenses | How should the retired prepaid expenses Confluence page be handled? | answered | Mark retired, label, add to active-procedure index as retired, and move under `Archived Accounting Procedures`. |
| AQ-035 | BofA checking reconciliation | Is AM-008 still an active monthly task? | answered | Yes. |
| AQ-036 | BofA checking reconciliation | Is the merchant-account-driven Confluence page the current process? | answered | Yes. |
| AQ-037 | BofA checking reconciliation | Is the older automated BofA checking page still useful? | answered | Yes; it remains valid for showing how to reconcile the actual account in QBDT. |
| AQ-038 | BofA checking reconciliation | Should the archived refunds/chargebacks merchant-statement process be copied into the active merchant-driven reconciliation page? | answered | Yes; merchant reports drive how the BofA checking reconciliation is performed. |
| AQ-039 | BofA checking reconciliation | Is the merchant-driven page the source of truth? | answered | Yes for BofA checking reconciliation using merchant-driven data; keep updated and refined. |
| AQ-040 | BofA checking reconciliation | Where should monthly source files be saved and what naming conventions should be used? | open | Analyze local directory structures and naming conventions later. |
| AQ-041 | BofA checking reconciliation | How should AMEX merchant activity be classified? | answered | AMEX is always Classic because only the Classic SendThisFile service accepts AMEX. |
| AQ-042 | BofA checking reconciliation | How should AMEX chargebacks/refunds/adjustments be recorded? | answered | Use the AMEX section row `Chargebacks / Refunds / Adjustments`; QBDT `AMEX Clearing` memorized transaction has placeholders. |
| AQ-043 | BofA checking reconciliation | Should funding timing differences have a formal carryforward schedule? | open | Current spreadsheet handles the adjustment; explain/review what a formal schedule would look like. |
| AQ-044 | BofA checking reconciliation | What source supports manual Cybersource Virtual Terminal invoice payment totals? | answered | Could be saved receipts, clearing activity, deposit folder evidence, Cybersource report, worksheet, or a combination. |
| AQ-045 | BofA checking reconciliation | What is the AM-008 completion check? | answered | All three clearing accounts zero, bank feeds processed for the month, and QBDT reconciliation difference zero. |
| AQ-046 | Confluence visibility | Is the BofA merchant-driven Confluence page publicly available? | answered | Unauthenticated access redirects to Atlassian login; detailed internal restrictions could not be verified with current OAuth scope. |
| AQ-047 | BofA checking reconciliation | Is the `Revenues Worksheet - MMYYYY.xlsx` copied forward each month? | answered | Yes; copy prior month, rename, and add a new month column on `Merchant Reconciliation`. |
| AQ-048 | BofA checking reconciliation | Who updates QBDT memorized transactions if worksheet structure or accounts change? | answered | Scott; changes are rare. |
| AQ-049 | BofA checking reconciliation | What are the exact QBDT memorized transaction names? | answered | `AMEX Clearing`, `BofA Classic Clearing`, and `BofA App Clearing`. |
| AQ-050 | BofA checking reconciliation | Should entries not on the BofA checking statement be reviewed monthly for both Classic and App? | answered | Yes; timing differences have occurred in both merchant statements. |
| AQ-051 | BofA checking reconciliation | What should happen if clearing accounts are not zero before BofA checking reconciliation? | answered | Stop and investigate; likely missing deposit, double entry, or date mismatch. |
| AQ-052 | BofA checking reconciliation | When should Clarity remind Scott about AM-008? | answered | Day 1 should start checking source availability. |
| AQ-053 | BofA checking reconciliation | Should the BofA checking statement PDF stay only in the yearly BofA statement folder or also be copied to monthly folders? | answered | Stay in yearly BofA checking statement folder as single source of truth. |
| AQ-054 | BofA checking reconciliation | Are `887` and `888` intended permanent prefixes for BofA merchant statement filenames? | answered | Yes; driven by merchant IDs for Cybersource/Classic and Authorize.net/App. |
| AQ-055 | BofA checking reconciliation | Should monthly report filenames include day-of-month? | answered | Existing conventions should be preserved; day-specific docs need DD, monthly reports may not, but changing now may be problematic. |
| AQ-056 | BofA checking reconciliation | Where should `Revenues Worksheet - MMYYYY.xlsx` and QBDT reconciliation report live? | answered | Directly in the monthly `YYYYMM` folder. |
| AQ-057 | BofA checking reconciliation | Is a mostly empty current-month folder normal? | answered | Not necessarily; the folder builds during the month as deposits, invoices, receipts, and typed directories accumulate. |
| AQ-058 | BofA checking reconciliation | Is the monthly `Deposits` folder part of the formal AM-008 evidence package? | answered | Yes, but not all-inclusive because some customers do not send remittance and must be identified from BofA checking statement activity. |
| AQ-059 | BofA checking reconciliation | What should be on the expected AM-008 source checklist? | answered | BofA checking statement PDF, `887` statement, `888` statement, AMEX statement, Revenues Worksheet, Deposits folder, and final reconciliation report after completion. |
| AQ-060 | BofA checking reconciliation | Which AM-008 sources are usually ready on Day 1 versus later? | answered | BofA checking is most likely ready on the 1st. Merchant statements may be ready on the 1st but can take a couple days. |
| AQ-061 | BofA checking reconciliation | How should the Day 1 AM-008 reminder be worded? | answered | Say `start checking source availability`, not that reconciliation is ready. |
| AQ-062 | Emprise Bank checking | Is AM-009 still an active monthly task? | answered | No; the SendThisFile Emprise Bank account has been closed. |
| AQ-063 | Emprise Bank checking | Is there a Confluence page for AM-009? | answered | No. |
| AQ-064 | Emprise Bank checking | Where are Emprise Bank statements stored? | answered | Emprise Bank folder. |
| AQ-065 | Emprise Bank checking | Is any current reconciliation completion check needed? | answered | No active task; historical information remains in QBDT. |
| AQ-066 | PayPal reconciliation | Is AM-010 still an active monthly task? | answered | Yes. |
| AQ-067 | PayPal reconciliation | Is the related PayPal Confluence page current? | answered | Yes. |
| AQ-068 | PayPal reconciliation | Where are PayPal source reports stored? | answered | PayPal folder. |
| AQ-069 | PayPal reconciliation | What is the PayPal source of truth? | answered | The report in the PayPal folder. |
| AQ-070 | PayPal reconciliation | What is the AM-010 completion check? | answered | PayPal account reconciled in QBDT. |
| AQ-071 | PayPal reconciliation | What common PayPal exception should be remembered? | answered | Occasionally money is transferred from PayPal to BofA checking, typically leaving about `$1,000` in PayPal. |
| AQ-072 | Investment reconciliation | Is AM-011 still active? | answered | Yes; current investment is LiveOakBank only. |
| AQ-073 | Investment reconciliation | Is the investment reconciliation Confluence page current? | answered | Yes. |
| AQ-074 | Investment reconciliation | Which investment account/provider is in scope? | answered | Only LiveOakBank. |
| AQ-075 | Investment reconciliation | Where are investment statements and reconciliations stored? | answered | Monthly folder under `Investment Accounts`; holds both original statement and QBDT reconciliation. |
| AQ-076 | Investment reconciliation | What is the investment reconciliation source of truth? | answered | PDF statement. |
| AQ-077 | Investment reconciliation | What is the AM-011 completion check? | answered | LiveOakBank account reconciled in QBDT. |
| AQ-078 | Classic refund review | Is AM-012 still active and what is its real purpose? | answered | Active as a review/control of the Classic refund process. |
| AQ-079 | Classic refund review | Which refunds are included? | answered | Specific Classic customer refunds. App refunds are requested via support. |
| AQ-080 | Classic refund review | What creates the refund reports? | answered | Automated process emails pending/completed refund reports to accounting@, feeding JSM. |
| AQ-081 | Classic refund review | What causes automated Classic refunds to pause? | answered | Single refund over `$50` or a single account with more than one refund. |
| AQ-082 | Classic refund review | How are paused automated refunds reviewed? | answered | Manually pull up customer/account to understand what happened; usually push through but sometimes not correct. |
| AQ-083 | Classic refund review | What systems issue refunds? | answered | Classic system pushes refunds through Cybersource; App refunds are processed directly in Chargebee. |
| AQ-084 | Classic refund review | What is the completion check? | answered | Refunds are clear and completed refunds email has hit accounting@ JSM queue. |
| AQ-085 | Contractor vendor payments | Is AM-013 still active? | answered | Yes. |
| AQ-086 | Contractor vendor payments | Is the contractor vendor payments Confluence page current? | answered | Yes. |
| AQ-087 | Contractor vendor payments | Where do contractor invoices arrive? | answered | Usually email to `accounting@` or directly to Scott. |
| AQ-088 | Contractor vendor payments | Who approves contractor invoices? | answered | Scott. |
| AQ-089 | Contractor vendor payments | Are contractor invoices entered as bills in QBDT first? | answered | Yes. |
| AQ-090 | Contractor vendor payments | What is the AM-013 completion check? | answered | Payment has been made. |
| AQ-091 | Enterprise failed billing | Is AM-014 still active? | answered | Yes. |
| AQ-092 | Enterprise failed billing | Does the list still come from internal-alert email? | answered | Yes. |
| AQ-093 | Enterprise failed billing | Who receives the internal-alert distribution list? | answered | Scott and a developer. |
| AQ-094 | Enterprise failed billing | What happens after Scott receives the failed billing list? | answered | Scott forwards it to support, and support reaches out to each customer to help update their credit card. |
| AQ-095 | Enterprise failed billing | Is AM-014 a support handoff? | answered | Yes; hand-off to support. |
| AQ-096 | Hartford insurance premium | Is AM-015 an active manual payment task? | answered | No; Hartford is auto-drafted from checking on the 10th. |
| AQ-097 | Hartford insurance premium | What should AM-015 reminders do? | answered | Verify auto-draft and remind Scott to download the invoice. |
| AQ-098 | Hartford insurance premium | When is the Hartford invoice usually generated? | answered | Around the 20th of the month. |
| AQ-099 | BofA credit card reconciliation | When does the BofA credit card billing cycle close and when is the statement usually ready? | answered | Billing cycle closes on the 6th; statement is usually ready by the 7th. |
| AQ-100 | BofA credit card reconciliation | Is the related Confluence page current? | answered | Yes, but it probably needs to be reviewed/revived. |
| AQ-101 | BofA credit card reconciliation | Where are BofA credit card statements stored? | answered | Current-year folder path pattern: `YYYY\Bank of America\Credit Card Statement`. |
| AQ-102 | BofA credit card reconciliation | Where are current-month credit card invoices and receipts stored? | answered | Current-month folder path pattern: `YYYY\YYYYMM\Invoices and Receipts`. |
| AQ-103 | BofA credit card reconciliation | Are there multiple credit cards or cardholders? | answered | Yes. There are four credit cards, but they roll up into one master account and one statement. |
| AQ-104 | BofA credit card reconciliation | What is the AM-016 completion check? | answered | QBDT reconciliation completed. |
| AQ-105 | Financial statements | Is AM-017 still an active Day 7 task? | answered | It should be active, but is often pushed back. The date needs to be made firmer. |
| AQ-106 | Financial statements | What reports are included in the shareholder financial statement package? | answered | P&L, balance sheet, and whatever else might be requested. |
| AQ-107 | Financial statements | What source systems feed the financial statement package? | answered | Mostly QBDT, possibly a spreadsheet too. Automation is desired. |
| AQ-108 | Financial statements | Where should the final financial statement package be stored? | answered | The `YYYYMM` monthly folder. |
| AQ-109 | Financial statements | How are statements currently delivered and what should be improved? | answered | Usually email today, but a better delivery method is needed. |
| AQ-110 | Financial statements | What is the AM-017 completion check? | answered | Reports delivered and questions answered. |
| AQ-111 | Payroll processing | Is AM-018 still an active Day 10 task? | answered | Yes. |
| AQ-112 | Payroll processing | Is the Confluence payroll page current? | answered | Yes; use `Processing Payroll`. |
| AQ-113 | Payroll processing | Which payroll setup is used? | answered | Believed to be QBDT Enhanced Payroll with direct deposit. |
| AQ-114 | Payroll processing | How many business days before payday must payroll be submitted for direct deposit? | answered | The top section of the Confluence payroll page describes the current rule. |
| AQ-115 | Payroll processing | What reports or approvals are needed before payroll is submitted? | answered | No separate reports or approvals; manually review each paycheck, then submit. |
| AQ-116 | Payroll processing | What is the AM-018 completion check? | answered | Confirmation received. |
| AQ-117 | Monthly distribution | Is AM-019 still an active monthly review task? | answered | Yes. |
| AQ-118 | Monthly distribution | What triggers a distribution review? | answered | Cash balance, profitability, shareholder decision, tax planning, and related considerations. |
| AQ-119 | Monthly distribution | Who decides whether a distribution is needed? | answered | Majority shareholder. |
| AQ-120 | Monthly distribution | How is the distribution recorded in QBDT? | answered | Use the memorized transaction named `Monthly Distribution`. |
| AQ-121 | Monthly distribution | How is the distribution paid? | answered | Manually through the BofA portal. |
| AQ-122 | Monthly distribution | What is the AM-019 completion evidence? | answered | Saved PDF captures of successful BofA transfers, one per shareholder, stored in monthly `Invoices and Receipts` using `XXX-DIST-MMDDYYYY.pdf`. |
| AQ-123 | Payroll tax deposits | Is AM-020 still active and when should it be done? | answered | Yes; after payroll and before the QBDT Payroll Center Pay Liabilities due dates. |
| AQ-124 | Payroll tax deposits | Is AM-020 tied to the same payroll Confluence page? | answered | Yes; use the `Make Payroll Tax Deposits` section. |
| AQ-125 | Payroll tax deposits | Which payroll tax filings/deposits are paid monthly? | answered | Federal 941, Kansas KW-5, and Missouri MO-941 are all paid monthly. |
| AQ-126 | Payroll tax deposits | Which portals are used for payroll tax payments? | answered | EFTPS.gov, KDOR, and mytax.mo.gov. |
| AQ-127 | Payroll tax deposits | Can payroll tax deposits be done immediately after payroll? | answered | Yes, if funds are available and each filing/payment is completed before its QBDT Pay Liabilities due date. |
| AQ-128 | Payroll tax deposits | What is the AM-020 completion evidence and naming convention? | answered | Save each filing/payment confirmation PDF in monthly `Invoices and Receipts` using the documented federal, Kansas, and Missouri filename patterns. |
| AQ-129 | PPQ integrity check | Is AM-021 still an active Day 10 task? | answered | Kinda; it was created for an earlier issue and may now be overlooked, but its purpose is Classic payment queue integrity. |
| AQ-130 | PPQ integrity check | Does PPQ stand for `paymentprocessingqueue`? | answered | Yes. |
| AQ-131 | PPQ integrity check | What system or database is checked for outstanding PPQ records? | answered | Classic Oracle DB. |
| AQ-132 | PPQ integrity check | What makes a PPQ record outstanding or not processed? | answered | It has an action date before today, which should not happen. |
| AQ-133 | PPQ integrity check | What action is taken when outstanding records are found? | answered | Research, then manually adjust. |
| AQ-134 | PPQ integrity check | What is the AM-021 completion check? | answered | Clean PPQ query. |
| AQ-135 | Pay stubs | Is AM-022 still an active Day 15 task? | answered | Not really; employees can get pay stubs through the QuickBooks portal or request a one-off copy from Scott. |
| AQ-136 | AMEX chargebacks and cancellations | Is AM-023 still active on Day 15? | answered | Maybe; primarily a reminder to check if no notification arrived by email or mail. |
| AQ-137 | AMEX chargebacks and cancellations | Is AM-023 separate from AMEX merchant-statement reconciliation work? | answered | Yes; it is separate because it gives an opportunity to challenge a cardholder chargeback. |
| AQ-138 | AMEX chargebacks and cancellations | Where do AMEX chargeback/cancellation notices arrive? | answered | AMEX portal, email, or mail. |
| AQ-139 | AMEX chargebacks and cancellations | What action is taken for AMEX chargebacks? | answered | Review and challenge if necessary; usually accept and make sure the customer is actually canceled in the system. |
| AQ-140 | AMEX chargebacks and cancellations | Are AMEX chargebacks only Classic customers? | answered | Yes. |
| AQ-141 | AMEX chargebacks and cancellations | What is the AM-023 completion check? | answered | Review completed. |
| AQ-142 | BCBS payment | Is AM-024 still active around Day 25? | answered | Yes. |
| AQ-143 | BCBS payment | Is the BCBS Confluence page current? | answered | Yes; use `Paying BCBS`. |
| AQ-144 | BCBS payment | How is BCBS paid? | answered | Manually through the portal. |
| AQ-145 | BCBS payment | When is the BCBS invoice usually available? | answered | Around the 12th of the month. |
| AQ-146 | BCBS payment | Where are BCBS invoice and payment confirmation saved? | answered | Monthly `Invoices and Receipts` folder using `BCBS - INV - MMDDYYYY.pdf` and `BCBS - RCPT - MMDDYYYY.pdf`. |
| AQ-147 | BCBS payment | What is the AM-024 completion check? | answered | Payment confirmation saved, with vendor bill and vendor payment still recorded in QBDT for tracking. |
| AQ-148 | Chargeback and cancellation review | Is AM-025 a separate workflow from AM-023? | answered | No; they should be the same thing. The goal was to check twice per month, once mid-month and once near month end. |
| AQ-149 | Inactive Classic invoice customers | Is AM-026 still active on the last day? | answered | Yes; it is another check to make sure canceled or non-paying customers are removed from PPQ. |
| AQ-150 | Inactive Classic invoice customers | What is the purpose of AM-026? | answered | Prevent canceled/non-paying Classic invoice customers from staying in PPQ, which drives automated billing and provides invoice information for QBDT import via SaasAnt Transactions. |
| AQ-151 | Inactive Classic invoice customers | What forms are marked inactive and where are they managed? | answered | Classic enterprise forms (`EP forms`) can be inactivated through the admin app while trying to collect payment. |
| AQ-152 | Inactive Classic invoice customers | Which customers are in scope? | answered | Only Classic invoice customers. |
| AQ-153 | Inactive Classic invoice customers | How can cancellation/removal be done? | answered | From Classic admin or manually by querying the Classic database. |
| AQ-154 | Inactive Classic invoice customers | What is the accounting purpose of this step? | answered | Prevent another invoice from being generated. |
| AQ-155 | Inactive Classic invoice customers | Does AM-026 still require logging outstanding invoices as bad debt, and if so what is the QBDT process? | open | Old checklist says to log outstanding invoices as bad debt, but current explanation focused on preventing future invoices. |
| AQ-156 | BIRT data integrity report | Is AM-027 still active on the last day? | answered | Not as an ideal manual task; it is a prime candidate for automation/notification. |
| AQ-157 | BIRT data integrity report | Is the Data Integrity Report Confluence page current? | answered | Yes. |
| AQ-158 | BIRT data integrity report | What does the BIRT integrity report check? | answered | PPQ record anomalies. |
| AQ-159 | BIRT data integrity report | Which billing run does the report protect? | answered | Classic. |
| AQ-160 | BIRT data integrity report | What action is taken when the report finds issues? | answered | Usually manual follow-up. |
| AQ-161 | BIRT data integrity report | What is the AM-027 completion check? | answered | Today it is a checkbox that it was done; if automated, proof that it ran should be captured. |
| AQ-162 | SaasAnt invoice catch-all | Is AM-028 still active as a last-day task? | answered | It can probably go away as a monthly catch-all. |
| AQ-163 | SaasAnt invoice catch-all | What was the purpose of AM-028? | answered | Catch cases where a Classic customer migrated to invoices instead of automatic payment and the invoice did not get into QBDT. |
| AQ-164 | SaasAnt invoice catch-all | Which customers does AM-028 impact? | answered | Classic only. |
| AQ-165 | SaasAnt invoice catch-all | Where should this process happen instead? | answered | During the manual invoice-customer setup process, covered by the `Invoice Customers` Confluence page. |
| AQ-166 | Blacklisted paid plans | Should AM-029 remain separate? | answered | No; roll it into the integrity check that needs automation. |
| AQ-167 | Blacklisted paid plans | Is the related Confluence page current/useful? | answered | Yes; `Query for blacklisted paid plans` identifies how to find the accounts. |
| AQ-168 | Blacklisted paid plans | What does blacklisted mean? | answered | Someone was found abusing the service and manually placed in a Blacklist table. |
| AQ-169 | Blacklisted paid plans | What system/customer set is in scope? | answered | Classic; historically a manual step. |
| AQ-170 | Blacklisted paid plans | What is the desired future-state artifact? | answered | Automation should generate an artifact proving the check was performed and showing sanitized result status. |

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
| AQ-023 | Unearned revenue | AM-005 is an active monthly task. | 2026-08-18 |
| AQ-024 | Unearned revenue | The related Confluence page `Recording Unearned Revenue` defines the current process. | 2026-08-18 |
| AQ-025 | Unearned revenue | The source data is the Classic service Oracle database data that feeds the Power BI report. | 2026-08-18 |
| AQ-026 | Unearned revenue | QuickBooks Desktop has a memorized transaction named `Unearned Revenue` for this workflow. | 2026-08-18 |
| AQ-027 | Unearned revenue | The memorized transaction is posted to the last day of the prior month, because that is the month being closed. | 2026-08-18 |
| AQ-028 | Unearned revenue | After posting, run a standard balance sheet and confirm the `Unearned Revenue` line item matches the supporting spreadsheet. | 2026-08-18 |
| AQ-029 | Unearned revenue | Power BI may not be a hard requirement anymore. It was originally used in hopes of building more visual dashboards; evaluate whether a secure direct API/query could provide the needed data directly. | 2026-08-18 |
| AQ-030 | Refunds and chargebacks | The top Confluence information block says the standalone refunds/chargebacks process is no longer needed as of 2026-01-01. AM-006 should not be treated as an active standalone Day 1 task. | 2026-08-18 |
| AQ-031 | Refunds and chargebacks | Refunds and chargebacks are handled through the merchant clearing accounts process. Refunds are included in daily submitted amounts and should not be counted again individually. | 2026-08-18 |
| AQ-032 | Confluence cleanup | Native Confluence archive was blocked because the tenant is not entitled to archiving. Fallback used for `Enter Refunds & Charge Backs`: add a retired/historical notice, add labels `accounting-retired`, `historical-reference`, and `replaced-by-merchant-clearing`, create/update `Accounting Monthly Close - Active Procedures`, create `Archived Accounting Procedures`, and move the retired page under that parent. | 2026-08-18 |
| AQ-033 | Prepaid expenses | AM-007 is retired. The company used to have prepaid expenses, but does not any longer. | 2026-08-18 |
| AQ-034 | Prepaid expenses | The `Enter Pre-paid Expenses` Confluence page was marked retired/historical, labeled `accounting-retired`, `historical-reference`, and `no-longer-needed`, added to `Accounting Monthly Close - Active Procedures` as retired, and moved under `Archived Accounting Procedures`. Native Confluence archive remains unavailable because the tenant is not entitled to archiving. | 2026-08-18 |
| AQ-035 | BofA checking reconciliation | AM-008 remains an active monthly task. | 2026-08-18 |
| AQ-036 | BofA checking reconciliation | The current process is `Reconcile Bank of America Checking (Merchant Account Driven)`: `https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/539688962/Reconcile+Bank+of+America+Checking+Merchant+Account+Driven`. | 2026-08-18 |
| AQ-037 | BofA checking reconciliation | The older `Reconcile Bank of America Checking Automated` page is still valid when showing how to reconcile the actual account in QuickBooks Desktop. | 2026-08-18 |
| AQ-038 | BofA checking reconciliation | The merchant statement collection steps from the retired `Enter Refunds & Charge Backs` page should live at the top of the active merchant-driven reconciliation page because merchant reports drive the reconciliation. The active Confluence page was updated with a `Merchant Statement Collection` section. | 2026-08-18 |
| AQ-039 | BofA checking reconciliation | For BofA checking reconciliation using merchant-driven data, the merchant-driven Confluence page is the source of truth and should be kept updated and refined. | 2026-08-19 |
| AQ-041 | BofA checking reconciliation | Only the Classic SendThisFile service accepts AMEX, so AMEX is always classified as Classic Revenue and related Classic merchant fees. | 2026-08-19 |
| AQ-042 | BofA checking reconciliation | AMEX chargebacks/refunds/adjustments go in the American Express section of the Revenues Worksheet on the `Chargebacks / Refunds / Adjustments` row. The QBDT memorized transaction `AMEX Clearing` has empty placeholders for that activity. | 2026-08-19 |
| AQ-044 | BofA checking reconciliation | Manual Cybersource Virtual Terminal invoice payment totals could come from saved receipts, clearing account activity, deposit-folder evidence, a Cybersource report, the worksheet itself, or a combination. | 2026-08-19 |
| AQ-045 | BofA checking reconciliation | Completion requires all three clearing accounts to be `$0.00`, bank feeds processed for the closing month, and QBDT BofA checking reconciliation difference at `$0.00`. | 2026-08-19 |
| AQ-046 | Confluence visibility | Verification on 2026-08-19: unauthenticated access to the BofA merchant-driven Confluence page redirects to Atlassian login, so it does not appear publicly internet-readable. The available OAuth credential can read page/space metadata but cannot inspect detailed page restrictions or internal group membership because restrictions endpoints return insufficient-scope responses. | 2026-08-19 |
| AQ-047 | BofA checking reconciliation | Yes. The `Revenues Worksheet - MMYYYY.xlsx` is copied from the prior month, renamed, and a new month column is added on the `Merchant Reconciliation` tab. | 2026-08-19 |
| AQ-048 | BofA checking reconciliation | Scott updates QBDT memorized transactions if worksheet structure or accounts change; changes are rare. | 2026-08-19 |
| AQ-049 | BofA checking reconciliation | Memorized transaction names are exactly `AMEX Clearing`, `BofA Classic Clearing`, and `BofA App Clearing`. | 2026-08-19 |
| AQ-050 | BofA checking reconciliation | Yes. Review entries not on the BofA checking statement for both BofA Classic and BofA App because timing differences have occurred in both merchant statements. | 2026-08-19 |
| AQ-051 | BofA checking reconciliation | If any clearing account is not zero, investigate before reconciling BofA checking. Typical causes include missing deposit, double entry, or date mismatch. | 2026-08-19 |
| AQ-052 | BofA checking reconciliation | AM-008 reminders should start on Day 1 by checking whether source documents/data are available. | 2026-08-19 |
| AQ-053 | BofA checking reconciliation | BofA checking statement PDFs should stay in the yearly `Bank of America/Checking Statement` folder as the single source of truth because Scott may add notes or highlights to the PDFs. Do not copy to the month folder unless this rule changes. | 2026-08-19 |
| AQ-054 | BofA checking reconciliation | Yes. BofA merchant statement prefixes `887` and `888` are intentional because they map to merchant IDs: `345468341887` for Cybersource/Classic and `345015373888` for Authorize.net/App. | 2026-08-19 |
| AQ-055 | BofA checking reconciliation | Naming has not always been perfectly consistent. Date-specific items need a day component when the transaction date matters. Monthly reports such as merchant statements and checking statements may not inherently need `DD`, but existing document-type naming conventions should generally be preserved because changing them now could be problematic. | 2026-08-19 |
| AQ-056 | BofA checking reconciliation | `Revenues Worksheet - MMYYYY.xlsx` lives directly in the monthly `YYYYMM` folder. The QBDT BofA checking reconciliation report also lives directly in that monthly folder. | 2026-08-19 |
| AQ-057 | BofA checking reconciliation | A current-month folder being sparse is not necessarily expected or unexpected; it is built throughout the month as deposits, transactional invoices, receipts, and type-specific directories accumulate. | 2026-08-19 |
| AQ-058 | BofA checking reconciliation | The `Deposits` folder is part of AM-008 evidence, especially for manual invoice/payment matching. It is not all-inclusive because some customers do not send remittance and must be identified from BofA checking statement activity. | 2026-08-19 |
| AQ-059 | BofA checking reconciliation | Expected AM-008 source checklist: BofA checking statement PDF in yearly folder, `887` BofA merchant statement, `888` BofA merchant statement, AMEX merchant statement, `Revenues Worksheet - MMYYYY.xlsx`, monthly `Deposits` folder, and final BofA checking reconciliation report after completion. | 2026-08-19 |
| AQ-060 | BofA checking reconciliation | BofA checking is most likely ready on the 1st. Merchant statements may also be ready on the 1st, but they can take a couple of days before they are accessible. | 2026-08-19 |
| AQ-061 | BofA checking reconciliation | The Day 1 AM-008 reminder should say to start checking source availability rather than implying the full reconciliation is ready. | 2026-08-19 |
| AQ-062 | Emprise Bank checking | AM-009 is retired because the SendThisFile Emprise Bank account has been closed. | 2026-08-19 |
| AQ-063 | Emprise Bank checking | There is no Confluence page for this retired workflow. | 2026-08-19 |
| AQ-064 | Emprise Bank checking | Emprise Bank statements are stored in the Emprise Bank folder, which is the historical statement source of truth. | 2026-08-19 |
| AQ-065 | Emprise Bank checking | No current reconciliation completion check is needed because the account is closed; historical information remains in QBDT. | 2026-08-19 |
| AQ-066 | PayPal reconciliation | AM-010 is an active monthly task. | 2026-08-19 |
| AQ-067 | PayPal reconciliation | The `Reconcile PayPal Statements` Confluence page is current. | 2026-08-19 |
| AQ-068 | PayPal reconciliation | PayPal statements/reports are stored in the PayPal folder. | 2026-08-19 |
| AQ-069 | PayPal reconciliation | The source of truth is the report in the PayPal folder. | 2026-08-19 |
| AQ-070 | PayPal reconciliation | AM-010 is complete once the PayPal account has been reconciled in QBDT. | 2026-08-19 |
| AQ-071 | PayPal reconciliation | Occasionally money is transferred from the PayPal account to BofA checking. When this happens, the practice is typically to leave about `$1,000` in PayPal. | 2026-08-19 |
| AQ-072 | Investment reconciliation | AM-011 is active. The only current investment is LiveOakBank. | 2026-08-19 |
| AQ-073 | Investment reconciliation | The `Reconcile Investment Statements` Confluence page is current. | 2026-08-19 |
| AQ-074 | Investment reconciliation | Only LiveOakBank is in scope for current investment reconciliation. | 2026-08-19 |
| AQ-075 | Investment reconciliation | Investment statements are stored in the monthly folders under `Investment Accounts`. That folder holds both the original statement and the QBDT reconciliation output. | 2026-08-19 |
| AQ-076 | Investment reconciliation | The PDF statement is the source of truth. | 2026-08-19 |
| AQ-077 | Investment reconciliation | AM-011 is complete once the LiveOakBank account is reconciled in QBDT. | 2026-08-19 |
| AQ-078 | Classic refund review | AM-012 should be treated as a review/control of the Classic refund process rather than a generic refund-cancellations task. | 2026-08-19 |
| AQ-079 | Classic refund review | AM-012 concerns specific Classic customer refunds. App refunds are requested via support. | 2026-08-19 |
| AQ-080 | Classic refund review | An automated cron job attempts to process refunds for Classic annual customers. It emails reports for pending refunds that hit a threshold and completed refunds to `accounting@`, which feeds into JSM. | 2026-08-19 |
| AQ-081 | Classic refund review | The automated Classic refund job pauses and does not process refunds when a single refund is over `$50` or a single account has more than one refund. Those cases require review and manual processing. | 2026-08-19 |
| AQ-082 | Classic refund review | For paused automated refunds, Scott manually pulls up the customer/account to see what happened. Sometimes customers signed up more than once, generating multiple refunds. Most are pushed through, but some have been incorrect. | 2026-08-19 |
| AQ-083 | Classic refund review | Classic refunds are pushed through Cybersource by the Classic system. App refunds are done directly in Chargebee. | 2026-08-19 |
| AQ-084 | Classic refund review | AM-012 is complete when refunds are clear and a completed refunds email has hit the `accounting@` JSM queue. | 2026-08-19 |
| AQ-085 | Contractor vendor payments | AM-013 remains active for Days 1-7. | 2026-08-19 |
| AQ-086 | Contractor vendor payments | The `Contractor Vendor Payments` Confluence page is current. | 2026-08-19 |
| AQ-087 | Contractor vendor payments | Contractor invoices usually arrive by email to `accounting@` or directly to Scott. | 2026-08-19 |
| AQ-088 | Contractor vendor payments | Scott approves contractor invoices. | 2026-08-19 |
| AQ-089 | Contractor vendor payments | Contractor invoices are entered as bills in QuickBooks Desktop before payment. | 2026-08-19 |
| AQ-090 | Contractor vendor payments | AM-013 is complete when payment has been made. | 2026-08-19 |
| AQ-091 | Enterprise failed billing | AM-014 remains active around Day 4. | 2026-08-19 |
| AQ-092 | Enterprise failed billing | The failed billing list still comes from the internal-alert email. | 2026-08-19 |
| AQ-093 | Enterprise failed billing | The internal-alert distribution list has two members: Scott and a developer. | 2026-08-19 |
| AQ-094 | Enterprise failed billing | Scott forwards the failed billing list to the support person, who reaches out to each customer and helps them update their credit card. | 2026-08-19 |
| AQ-095 | Enterprise failed billing | AM-014 is a hand-off to support. | 2026-08-19 |
| AQ-096 | Hartford insurance premium | AM-015 is not a manual pay task. Hartford is set up to auto-draft from checking on the 10th. | 2026-08-19 |
| AQ-097 | Hartford insurance premium | AM-015 should be a verification step and a reminder to download the invoice. | 2026-08-19 |
| AQ-098 | Hartford insurance premium | The Hartford invoice is usually generated around the 20th of the month. | 2026-08-19 |
| AQ-099 | BofA credit card reconciliation | The BofA credit card billing cycle closes on the 6th of the month and the statement is usually ready by the 7th. | 2026-08-19 |
| AQ-100 | BofA credit card reconciliation | The `Reconcile Bank of America Credit Cards` Confluence page is still current, but probably needs to be reviewed/revived. | 2026-08-19 |
| AQ-101 | BofA credit card reconciliation | BofA credit card statements are stored in the current-year `Bank of America\Credit Card Statement` folder, for example `2026\Bank of America\Credit Card Statement`. | 2026-08-19 |
| AQ-102 | BofA credit card reconciliation | Current-month credit card invoices and receipts are stored in the monthly `Invoices and Receipts` folder, for example `2026\202608\Invoices and Receipts`. | 2026-08-19 |
| AQ-103 | BofA credit card reconciliation | There are four credit cards, but they roll up into a master account, so there is only one statement. | 2026-08-19 |
| AQ-104 | BofA credit card reconciliation | AM-016 completion is the QBDT reconciliation. | 2026-08-19 |
| AQ-105 | Financial statements | AM-017 should be an active Day 7 task, but it often gets pushed back. The monthly close process needs to be firmer about this date. | 2026-08-19 |
| AQ-106 | Financial statements | The shareholder financial statement package usually includes P&L, balance sheet, and any other requested reports. | 2026-08-19 |
| AQ-107 | Financial statements | Reports are mostly generated from QBDT, but a spreadsheet may also be involved. Scott would like to automate this if practical. | 2026-08-19 |
| AQ-108 | Financial statements | Final financial statement packages should be stored in the monthly `YYYYMM` folder. | 2026-08-19 |
| AQ-109 | Financial statements | Statements are usually delivered by email today, but a better delivery method is needed. | 2026-08-19 |
| AQ-110 | Financial statements | AM-017 is complete when the reports have been delivered and questions answered. | 2026-08-19 |
| AQ-111 | Payroll processing | AM-018 remains an active Day 10 task. | 2026-08-20 |
| AQ-112 | Payroll processing | The `Processing Payroll` Confluence page is current: `https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/20414465/Processing+Payroll`. | 2026-08-20 |
| AQ-113 | Payroll processing | Payroll is believed to use QuickBooks Desktop Enhanced Payroll with direct deposit. | 2026-08-20 |
| AQ-114 | Payroll processing | The top section of the `Processing Payroll` Confluence page describes the direct-deposit submission timing rule. Use that page as the timing source rather than hard-coding a lead time until reviewed. | 2026-08-20 |
| AQ-115 | Payroll processing | No separate reports or approvals are needed before submitting payroll. Scott manually reviews each paycheck, then submits payroll. | 2026-08-20 |
| AQ-116 | Payroll processing | AM-018 is complete when payroll confirmation is received. | 2026-08-20 |
| AQ-117 | Monthly distribution | AM-019 remains an active monthly review task. | 2026-08-20 |
| AQ-118 | Monthly distribution | Distribution review considers cash balance, profitability, shareholder decision, tax planning, and related factors. | 2026-08-20 |
| AQ-119 | Monthly distribution | The majority shareholder decides whether a distribution is needed. | 2026-08-20 |
| AQ-120 | Monthly distribution | Distributions are recorded in QBDT using the memorized transaction named `Monthly Distribution`. | 2026-08-20 |
| AQ-121 | Monthly distribution | Distributions are paid manually through the BofA portal. | 2026-08-20 |
| AQ-122 | Monthly distribution | Completion evidence is saved PDF captures of successful BofA transfers, one per shareholder, stored in the monthly `Invoices and Receipts` directory using the format `XXX-DIST-MMDDYYYY.pdf`, where `XXX` is the shareholder initials. | 2026-08-20 |
| AQ-123 | Payroll tax deposits | AM-020 remains active and should be done after payroll. Actual due dates are displayed in QBDT Payroll Center > Pay Liabilities. | 2026-08-20 |
| AQ-124 | Payroll tax deposits | AM-020 is tied to the `Processing Payroll` Confluence page, specifically the `Make Payroll Tax Deposits` section for Federal 941, Kansas KW-5, and Missouri MO-941. | 2026-08-20 |
| AQ-125 | Payroll tax deposits | Federal 941 deposits, Kansas KW-5, and Missouri MO-941 are all paid monthly. | 2026-08-20 |
| AQ-126 | Payroll tax deposits | Payment portals are EFTPS.gov for federal, KDOR for Kansas, and mytax.mo.gov for Missouri. | 2026-08-20 |
| AQ-127 | Payroll tax deposits | Payroll tax deposits can be done immediately after payroll as long as funds are available and each filing/payment is completed before the due date shown in QBDT Payroll Center > Pay Liabilities. | 2026-08-20 |
| AQ-128 | Payroll tax deposits | Save each filing/payment PDF in the monthly `Invoices and Receipts` folder. Federal: `EFTPS - RCPT - MMDDYYYY.pdf`. Kansas: `KS Withholding - RCPT - MMDDYYYY.pdf` and `KS Withholding - RCPT2 - MMDDYYYY.pdf` because Kansas is reported semi-monthly. Missouri: `MO-941 - MMDDYYYY.pdf`, `MO-941 - RCPT - MMDDYYYY.pdf`, and `MO-941 - RCPT2 - MMDDYYYY.pdf`. | 2026-08-20 |
| AQ-129 | PPQ integrity check | AM-021 is still somewhat active. It was created because of an earlier issue and may not be a common problem now, but its purpose is to maintain Classic payment processing queue integrity. | 2026-08-20 |
| AQ-130 | PPQ integrity check | PPQ means `paymentprocessingqueue`. | 2026-08-20 |
| AQ-131 | PPQ integrity check | Outstanding PPQ records are checked in the Classic Oracle DB. | 2026-08-20 |
| AQ-132 | PPQ integrity check | A PPQ record is outstanding/not processed if it has an action date before today. This should not happen. | 2026-08-20 |
| AQ-133 | PPQ integrity check | If outstanding PPQ records are found, research first, then manually adjust as appropriate. Manual adjustment remains a human-controlled action. | 2026-08-20 |
| AQ-134 | PPQ integrity check | AM-021 is complete when the PPQ query is clean. | 2026-08-20 |
| AQ-135 | Pay stubs | AM-022 should not be treated as a monthly pay-stub send task. Employees can log into the QuickBooks portal to get pay stubs, or request a one-off copy from Scott. | 2026-08-20 |
| AQ-136 | AMEX chargebacks and cancellations | AM-023 is maybe active as a Day 15 reminder/review. It is primarily a reminder to check if no AMEX chargeback/cancellation notification has arrived by email or mail. | 2026-08-20 |
| AQ-137 | AMEX chargebacks and cancellations | AM-023 is separate from AMEX merchant-statement reconciliation. This review gives SendThisFile an opportunity to challenge a chargeback submitted by a cardholder. | 2026-08-20 |
| AQ-138 | AMEX chargebacks and cancellations | AMEX chargeback/cancellation notices may arrive through the AMEX portal, email, or mail. | 2026-08-20 |
| AQ-139 | AMEX chargebacks and cancellations | For an AMEX chargeback, review and challenge if necessary. Most times the chargeback is accepted, but it is critical to make sure the customer is actually canceled in the Classic system; otherwise billing could continue. Chargebacks can negatively affect merchant ranking and increase fees. | 2026-08-20 |
| AQ-140 | AMEX chargebacks and cancellations | AMEX chargebacks are Classic-only because only Classic SendThisFile accepts AMEX. | 2026-08-20 |
| AQ-141 | AMEX chargebacks and cancellations | AM-023 completion is the review. | 2026-08-20 |
| AQ-142 | BCBS payment | AM-024 remains active around Day 25. | 2026-08-20 |
| AQ-143 | BCBS payment | The `Paying BCBS` Confluence page is current: `https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/42532865/Paying+BCBS`. | 2026-08-20 |
| AQ-144 | BCBS payment | BCBS is paid manually through the portal. | 2026-08-20 |
| AQ-145 | BCBS payment | The BCBS invoice is usually available around the 12th of the month. | 2026-08-20 |
| AQ-146 | BCBS payment | Save BCBS files in the monthly `Invoices and Receipts` folder. Invoice format: `BCBS - INV - MMDDYYYY.pdf`. Payment confirmation format: `BCBS - RCPT - MMDDYYYY.pdf`. | 2026-08-20 |
| AQ-147 | BCBS payment | AM-024 completion evidence is payment confirmation. The vendor bill and vendor payment still have to be made in QBDT for tracking. | 2026-08-20 |
| AQ-148 | Chargeback and cancellation review | AM-025 should be treated as the same chargeback/cancellation review as AM-023. The likely original goal was to check twice per month: once in the middle of the month and once near the end. | 2026-08-20 |
| AQ-149 | Inactive Classic invoice customers | AM-026 remains active on the last day of the month. | 2026-08-20 |
| AQ-150 | Inactive Classic invoice customers | AM-026 exists as another check to make sure canceled or non-paying Classic invoice customers are removed from PPQ. PPQ drives automated billing and provides invoice information for QBDT import through SaasAnt Transactions. | 2026-08-20 |
| AQ-151 | Inactive Classic invoice customers | When trying to collect payment, Classic enterprise forms (`EP forms`) can be inactivated through the admin app with the hope that the customer reaches out and submits payment. | 2026-08-20 |
| AQ-152 | Inactive Classic invoice customers | AM-026 applies only to Classic invoice customers. | 2026-08-20 |
| AQ-153 | Inactive Classic invoice customers | The customer can be handled from Classic admin or manually by querying the Classic database. Manual database changes remain human-controlled. | 2026-08-20 |
| AQ-154 | Inactive Classic invoice customers | This is a preventative step so another invoice is not generated. | 2026-08-20 |
| AQ-156 | BIRT data integrity report | AM-027 should not remain only a manual last-day task if it can be automated. It is a prime candidate for automation/notification. | 2026-08-20 |
| AQ-157 | BIRT data integrity report | The `Data Integrity Report` Confluence page is current. | 2026-08-20 |
| AQ-158 | BIRT data integrity report | The BIRT integrity report checks PPQ for record anomalies. | 2026-08-20 |
| AQ-159 | BIRT data integrity report | The report protects Classic credit-card billing. | 2026-08-20 |
| AQ-160 | BIRT data integrity report | If the report finds issues, follow-up is usually manual. | 2026-08-20 |
| AQ-161 | BIRT data integrity report | Current completion is checking that it was done. If automated, completion should be proof that the check was performed. | 2026-08-20 |
| AQ-162 | SaasAnt invoice catch-all | AM-028 can probably be retired as a last-day monthly catch-all. | 2026-08-20 |
| AQ-163 | SaasAnt invoice catch-all | AM-028 was a catch-all for cases where a Classic customer was migrated to invoice billing instead of automatic payment and the invoice did not get into QBDT. | 2026-08-20 |
| AQ-164 | SaasAnt invoice catch-all | AM-028 only impacts Classic. | 2026-08-20 |
| AQ-165 | SaasAnt invoice catch-all | This should be handled during the manual process of setting up the customer, covered by the `Invoice Customers` Confluence page: `https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/111706113/Invoice+Customers`. | 2026-08-20 |
| AQ-166 | Blacklisted paid plans | AM-029 should be rolled into the Classic integrity check that needs automation. | 2026-08-20 |
| AQ-167 | Blacklisted paid plans | The `Query for blacklisted paid plans` Confluence page identifies how to find the accounts: `https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/44662785/Query+for+blacklisted+paid+plans`. | 2026-08-20 |
| AQ-168 | Blacklisted paid plans | Blacklisted means SendThisFile found someone abusing the service and manually placed them in a Blacklist table. | 2026-08-20 |
| AQ-169 | Blacklisted paid plans | This has historically been a manual Classic step, but it can be improved. | 2026-08-20 |
| AQ-170 | Blacklisted paid plans | There is currently no artifact. Future automation should generate an artifact proving the check was performed and showing sanitized result status. | 2026-08-20 |
