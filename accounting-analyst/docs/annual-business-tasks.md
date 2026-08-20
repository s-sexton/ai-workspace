# Annual And Month-Specific Business Task Register

This register tracks business tasks that occur in specific months but are not
part of the every-month accounting checklist.

Do not store credentials, private tax filings, employee private data, customer
private data, bank details, raw reports, or legal correspondence in this file.

## Purpose

These tasks were provided from monthly business checklist-template markup. Some
items may be stale, duplicated, historical, or have inaccurate dates. Treat this
document as the intake and triage surface before creating reminders.

## Status Values

- `needs-review`: Intake captured, but current validity/timing must be
  confirmed.
- `candidate-active`: Likely still relevant, but details need validation.
- `stale-date-review`: Contains date-specific historical details that may be
  obsolete.
- `retire-candidate`: Likely no longer needed or should be folded into another
  workflow.
- `automation-candidate`: Should be evaluated for automation or notification.
- `confirmed-active`: Confirmed current by the human operator.

## Initial Triage Themes

- Quarterly compliance tasks appear in January, April, July, and October.
- Payroll/tax filing tasks appear quarterly and annually; several should be
  reconciled with QBDT Payroll Center due dates and current federal/state rules.
- Trademark, patent, Privacy Shield, Oracle Support, LastPass, SSL, and
  insurance tasks may need non-accounting owners or specialist review.
- Several tasks include historical years or dates that are already past as of
  2026-08-20 and should not become reminders without review.
- Some tasks duplicate every-month workflows, such as Hartford/BCBS/insurance
  and unemployment-rate updates.

## January

| ID | Status | Timing | Task | Related Page / Link | Initial Triage Notes |
| --- | --- | --- | --- | --- | --- |
| ABT-JAN-001 | candidate-active | Day 1 | Create new directory structure for documents | [Setting up Directory Structure for New Year](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/100335742/Setting+up+Directory+Structure+for+New+Year) | Likely annual setup task; confirm current directory conventions. |
| ABT-JAN-002 | candidate-active | Day 1 | Perform quarterly vulnerability scans via IBM portal on all servers and save results | | Quarterly control; confirm owner and storage location. |
| ABT-JAN-003 | candidate-active | Day 1 | Make sure prior year net income moved to retained earnings; run balance sheet to check | | Should be automatic; confirm QBDT close behavior and review-only evidence. |
| ABT-JAN-004 | candidate-active | Day 1 | Zero out prior year distributions | [Zero out distributions at beginning of the year](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/100466696/Zero+out+distributions+at+beginning+of+the+year) | Annual QBDT task; confirm still current. |
| ABT-JAN-005 | stale-date-review | Day 1 | SendThisFile service mark Section 8/9 filing window and USPTO review | [USPTO](http://www.uspto.gov) | Intake includes 2024/2025 dates for serial `78354547`, registration `2917528`; must verify current status before any reminder. |
| ABT-JAN-006 | candidate-active | Day 10 | Enter prior year's depreciation | [Entering Prior Year's Depreciation](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/102236161/Entering+Prior+Year+s+Depreciation) | Annual accounting close task; confirm source and QBDT entry. |
| ABT-JAN-007 | stale-date-review | Day 10-15 | Update Annual Refiling Survey, Bureau of Labor Statistics | [BLS Annual Refiling Survey](https://idcfars.bls.gov/) | Every 3 years; intake says last completed 2019 and email went to another person. Needs current cycle/owner check. |
| ABT-JAN-008 | candidate-active | Day 10 | Change unemployment and other employment tax rates in QuickBooks for new year, if any | | Also appears in November/December; consolidate into one annual rate-update workflow. |
| ABT-JAN-009 | candidate-active | Day 13 | Verify Intuit Enhanced Payroll subscription has been renewed | | Confirm whether subscription renewal is still annual and where evidence appears. |
| ABT-JAN-010 | candidate-active | Day 31 | Deposit FUTA tax payments for prior year | | Tie to payroll tax annual reports workflow and QBDT liability due dates. |
| ABT-JAN-011 | candidate-active | Day 31 | File Form 940/Schedule A Employer's Annual Federal Unemployment Tax Return for prior year | [Annual Payroll Reports and Taxes](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/100335635/Annual+Payroll+Reports+and+Taxes) | Annual payroll tax filing; confirm current process. |
| ABT-JAN-012 | candidate-active | Day 31 | File Form 941 Schedule B Employer's Quarterly Federal Tax Return for prior quarter | [Quarterly Payroll Reports and Taxes](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/100368414/Quarterly+Payroll+Reports+and+Taxes) | Quarterly payroll tax filing; confirm exact quarterly due date handling. |
| ABT-JAN-013 | candidate-active | Day 31 | E-file and pay Kansas/Missouri unemployment insurance for prior quarter | [Quarterly Payroll Reports and Taxes](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/100368414/Quarterly+Payroll+Reports+and+Taxes) | Quarterly payroll tax filing; confirm portals and evidence naming. |
| ABT-JAN-014 | candidate-active | Day 31 | Distribute W-2s and 1099s; file W-2, 1099, and KW-3 through KDOR | [Annual Payroll Reports and Taxes](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/100335635/Annual+Payroll+Reports+and+Taxes) | Annual wage/vendor reporting; sensitive, needs careful evidence rules. |
| ABT-JAN-015 | candidate-active | Day 31 | Mail 1099 Copy A and 1096 to IRS | | Verify whether still mailed or e-filed under current IRS rules/vendor process. |
| ABT-JAN-016 | candidate-active | Day 31 | Pay stockholders' quarterly distribution if declared to cover Federal and State tax on K-1 income | | Governance/tax decision; human/board approval required. |
| ABT-JAN-017 | candidate-active | Day 31 | Check State and Federal labor posters are current | [Federal posters](http://www.dol.gov/elaws/posters.htm); [Kansas posters](http://www.dol.ks.gov/ES/posters.html) | HR/compliance task; confirm owner and current links. |
| ABT-JAN-018 | candidate-active | Day 31 | Update greater-than-2-percent owners health insurance premiums in QuickBooks to reflect March premium | | Appears again in February/March; consolidate with BCBS/payroll item workflow. |
| ABT-JAN-019 | candidate-active | Day 31 | Update Form W-4 Employee's Withholding Certificate as required | | Required annually for employees who do not have taxes withheld; confirm current applicability. |

## February

| ID | Status | Timing | Task | Related Page / Link | Initial Triage Notes |
| --- | --- | --- | --- | --- | --- |
| ABT-FEB-001 | candidate-active | Month | Update greater-than-2-percent owners health insurance premiums in QuickBooks to reflect March premium | | Duplicate/carryover from January; consolidate. |
| ABT-FEB-002 | candidate-active | Month | Update Form W-4 as required for employees who do not have taxes withheld | | Duplicate/carryover from January; confirm current employee applicability. |
| ABT-FEB-003 | needs-review | Month | File Kansas Form AR Domestic and Foreign For Profit Corporate every two years | [Kansas annual reports](https://www.kansas.gov/annual-reports/index.do) | Confirm current biennial filing year and due date. |

## March

| ID | Status | Timing | Task | Related Page / Link | Initial Triage Notes |
| --- | --- | --- | --- | --- | --- |
| ABT-MAR-001 | candidate-active | Month | Send out new BCBS summary | | Benefits/HR communication; confirm owner and delivery method. |
| ABT-MAR-002 | candidate-active | Month | Update payroll item with newest BCBS amount for greater-than-2-percent shareholders | | Connect to BCBS and payroll setup workflow. |
| ABT-MAR-003 | needs-review | Month | Record general journal entry for Arukona interest payment | | Confirm whether still applicable. |
| ABT-MAR-004 | candidate-active | Month | File 1120S with IRS | | Tax filing; likely accountant/tax preparer involvement. |
| ABT-MAR-005 | candidate-active | Month | Distribute K-1 to stockholders | | Sensitive tax docs; confirm delivery/evidence method. |
| ABT-MAR-006 | needs-review | Month | File Kansas Form AR Domestic and Foreign For Profit Corporate Annual Report | [Kansas annual reports](https://www.kansas.gov/annual-reports/index.do) | May duplicate February biennial item; verify current cadence. |
| ABT-MAR-007 | candidate-active | Month | Submit prior year employee count to BCBS | [BCBS MLR](https://bcbsks.com/MLR) | Instructions usually arrive by email; confirm timing and source. |

## April

| ID | Status | Timing | Task | Related Page / Link | Initial Triage Notes |
| --- | --- | --- | --- | --- | --- |
| ABT-APR-001 | candidate-active | Day 1 | Perform quarterly vulnerability scans via IBM portal on all servers and save results | | Quarterly control; consolidate with January/July/October. |
| ABT-APR-002 | candidate-active | Day 15 | File Form K-120S Kansas Small Business Corporation Return | | Tax filing; confirm preparer/owner. |
| ABT-APR-003 | candidate-active | Day 15 | Distribute Kansas Schedule K-1 Equivalent Form K-120S | | Sensitive tax docs; confirm delivery/evidence method. |
| ABT-APR-004 | candidate-active | Day 15 | Schedule annual stockholders' and directors' meetings; send prior year-end financial statements and prior annual minutes | | Governance task; likely board/management owner. |
| ABT-APR-005 | stale-date-review | Day 18 | Renewal fee for irrigation controller patent `7123993`, application `10650631` | [USPTO maintenance fees](https://fees.uspto.gov/MaintenanceFees/?patentNumber=7123993) | Intake references due date 2018; verify whether any current patent maintenance remains. |
| ABT-APR-006 | candidate-active | Day 30 | Pay real estate taxes for 950 N. Santa Fe | | Confirm property ownership/current relevance and evidence storage. |
| ABT-APR-007 | candidate-active | Day 30 | File Form 941 Employer's Quarterly Federal Tax Return | | Quarterly payroll tax filing. |
| ABT-APR-008 | candidate-active | Day 30 | Pay FUTA taxes online for previous quarter if $500 or more | | Quarterly/annual payroll tax rule; confirm QBDT liability workflow. |
| ABT-APR-009 | candidate-active | Day 30 | E-file and pay Kansas unemployment insurance K-CNS 100 quarterly | | Quarterly payroll tax filing. |
| ABT-APR-010 | candidate-active | Day 30 | File and pay Missouri unemployment insurance | | Quarterly payroll tax filing. |

## May

| ID | Status | Timing | Task | Related Page / Link | Initial Triage Notes |
| --- | --- | --- | --- | --- | --- |
| ABT-MAY-001 | needs-review | Day 1-31 | Pay Hartford business insurance | | May duplicate monthly Hartford workflow; confirm policy/payment schedule. |
| ABT-MAY-002 | candidate-active | Day 31 | Annual stockholders' meeting | | Governance task; confirm actual annual meeting month. |
| ABT-MAY-003 | candidate-active | Day 31 | Annual board of directors meeting | | Governance task; confirm actual annual meeting month. |

## June

| ID | Status | Timing | Task | Related Page / Link | Initial Triage Notes |
| --- | --- | --- | --- | --- | --- |
| ABT-JUN-001 | candidate-active | Day 1-5 | Complete PCI self-assessment | [Clover Security](https://cloversecurity.com) | Security/compliance task; confirm current PCI vendor/process. |
| ABT-JUN-002 | stale-date-review | Day 15 | iSprink service mark renewal/continued use for registration `3,242,187` | [USPTO](http://www.uspto.gov) | Intake references 2016; verify current trademark status. |
| ABT-JUN-003 | needs-review | Day 13 | Pay Hartford business insurance | | May duplicate May/monthly Hartford workflow; confirm policy/payment schedule. |
| ABT-JUN-004 | candidate-active | Day 31 | Annual stockholders' meeting | | Duplicate of May; determine actual target month. |
| ABT-JUN-005 | candidate-active | Day 31 | Annual board of directors meeting | | Duplicate of May; determine actual target month. |

## July

| ID | Status | Timing | Task | Related Page / Link | Initial Triage Notes |
| --- | --- | --- | --- | --- | --- |
| ABT-JUL-001 | candidate-active | Day 1 | Perform quarterly vulnerability scans via IBM portal on all servers and save results | | Quarterly control. |
| ABT-JUL-002 | candidate-active | Day 1 | PCI Annual Self Assessment | | May duplicate June PCI item; verify timing. |
| ABT-JUL-003 | candidate-active | Day 1 | Review and update BCP plan document | | Business continuity task; confirm owner and storage. |
| ABT-JUL-004 | stale-date-review | Day 12 | Yellow file folder with red flag service mark renewal/continued use, registration `2,966,961` | [USPTO](http://www.uspto.gov) | Intake references 2014; verify current trademark status. |
| ABT-JUL-005 | stale-date-review | Day 1 | Yellow file folder with red flag Section 8 filing window, serial `85202926`, registration `4002384` | [USPTO](http://www.uspto.gov) | Intake includes 2020/2021/2022 dates and 2020 acceptance notice; verify current next deadline. |
| ABT-JUL-006 | needs-review | Day 1 | Pay Business Owners insurance, The Hartford | | May duplicate other Hartford items; confirm actual policy schedule. |
| ABT-JUL-007 | candidate-active | Day 1 | Pay Tech E&O insurance, due on 25th | | Insurance task; confirm provider, due date, evidence. |
| ABT-JUL-008 | candidate-active | Day 15 | File Form 941 Employer's Quarterly Federal Tax Return | | Date may be inaccurate; quarterly 941 is commonly end-of-month. Verify with QBDT/current rules. |
| ABT-JUL-009 | candidate-active | Day 15 | FUTA tax online for previous quarters if $500 or more | | Intake says no payment needed for this quarter; verify current liability. |
| ABT-JUL-010 | candidate-active | Day 15 | E-file and pay Kansas unemployment insurance K-CNS 100 | | Date may need verification. |
| ABT-JUL-011 | candidate-active | Day 15 | File and pay Missouri unemployment insurance | | Date may need verification. |
| ABT-JUL-012 | stale-date-review | Day 10-25 | Update Annual Refiling Survey, Bureau of Labor Statistics | [BLS Annual Refiling Survey](https://idcfars.bls.gov/) | Every 3 years; intake says last completed 2017, conflicts with September 2022 note. Verify current cycle. |

## August

| ID | Status | Timing | Task | Related Page / Link | Initial Triage Notes |
| --- | --- | --- | --- | --- | --- |
| ABT-AUG-001 | retire-candidate | Month | Placeholder - nothing to do | | Keep no reminder unless new August-specific task is identified. |

## September

| ID | Status | Timing | Task | Related Page / Link | Initial Triage Notes |
| --- | --- | --- | --- | --- | --- |
| ABT-SEP-001 | candidate-active | Day 1-15 | Update Annual Refiling Survey, Bureau of Labor Statistics | [BLS Annual Refiling Survey](https://idcfars.bls.gov/) | Every 3 years; intake says last completed 2022-09-01. Next likely cycle needs verification. |

## October

| ID | Status | Timing | Task | Related Page / Link | Initial Triage Notes |
| --- | --- | --- | --- | --- | --- |
| ABT-OCT-001 | candidate-active | Day 1 | Perform quarterly vulnerability scans via IBM portal on all servers and save results | | Quarterly control. |
| ABT-OCT-002 | candidate-active | Day 1 | Review LastPass Teams license | | Security/admin task; confirm owner and current tool. |
| ABT-OCT-003 | candidate-active | Day 1 | Renew SSL certificates, wildcard / EV | | Technical/security task; confirm owner and automation status. |
| ABT-OCT-004 | candidate-active | Day 31 | File Form 941 Employer's Quarterly Federal Tax Return | | Quarterly payroll tax filing. |
| ABT-OCT-005 | candidate-active | Day 31 | FUTA tax online for previous quarter(s) if $500 or more | | Quarterly/annual payroll tax rule. |
| ABT-OCT-006 | candidate-active | Day 31 | E-file and pay Kansas and Missouri unemployment insurance | | Quarterly payroll tax filing. |

## November

| ID | Status | Timing | Task | Related Page / Link | Initial Triage Notes |
| --- | --- | --- | --- | --- | --- |
| ABT-NOV-001 | stale-date-review | Day 20 | Renew Privacy Shield with BBB | | Privacy Shield framework status may be stale; verify current legal/compliance requirement. |
| ABT-NOV-002 | stale-date-review | Day 20 | Renew Privacy Shield with privacyshield.gov | [Privacy Shield](https://www.privacyshield.gov/) | Privacy Shield status may be stale; verify before keeping. |
| ABT-NOV-003 | candidate-active | Day 1 | Renew Oracle Support | | Vendor renewal; confirm owner, term, and evidence. |
| ABT-NOV-004 | candidate-active | Day 30 | Update Kansas unemployment contribution rate for upcoming year based on KDOL Experience Rating | [Adjusting Kansas Unemployment Rate](https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/93683713/Adjusting+Kansas+Unemployment+Rate) | Also appears in December/January; consolidate into annual payroll rate update workflow. |
| ABT-NOV-005 | candidate-active | Day 30 | Pay real estate taxes for Santa Fe property | | Confirm property/current relevance and due date. |

## December

| ID | Status | Timing | Task | Related Page / Link | Initial Triage Notes |
| --- | --- | --- | --- | --- | --- |
| ABT-DEC-001 | future-date-review | Day 1 | SendThisFile service mark Section 8/9 filing by 2034-12-13; serial `78537692`, registration `3029037` | [USPTO](http://www.uspto.gov) | Future trademark deadline; should be scheduled but not mixed into ordinary annual reminders until validated. |
| ABT-DEC-002 | candidate-active | Day 1 | Update Kansas unemployment contribution rate for upcoming year based on KDOL Experience Rating | | Duplicate of November item; consolidate. |
| ABT-DEC-003 | candidate-active | Day 1 | Pay property taxes for MacArthur properties; half due by December 20 | | Confirm property/current relevance and evidence. |
| ABT-DEC-004 | candidate-active | Day 1 | Update Missouri unemployment contribution rate for upcoming year; login required and no notification is sent | | Consolidate with annual payroll rate update workflow; reminder may be important because no notice is sent. |

## Confluence Pages To Review

The following pages were referenced in the intake and should be reviewed before
marking related tasks `confirmed-active`:

| Topic | Link |
| --- | --- |
| New year directory setup | https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/100335742/Setting+up+Directory+Structure+for+New+Year |
| Zero out distributions | https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/100466696/Zero+out+distributions+at+beginning+of+the+year |
| Prior year depreciation | https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/102236161/Entering+Prior+Year+s+Depreciation |
| Annual payroll reports and taxes | https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/100335635/Annual+Payroll+Reports+and+Taxes |
| Quarterly payroll reports and taxes | https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/100368414/Quarterly+Payroll+Reports+and+Taxes |
| Kansas unemployment rate adjustment | https://sendthisfile.atlassian.net/wiki/spaces/BIZ/pages/93683713/Adjusting+Kansas+Unemployment+Rate |

## Open Cleanup Questions

| ID | Question | Notes |
| --- | --- | --- |
| ABQ-001 | Which month-specific tasks belong to Accounting Analyst versus another role, such as security, legal, HR, or systems administration? | Vulnerability scans, SSL, LastPass, Privacy Shield, Oracle Support, trademarks, patents, and meetings may need owner review. |
| ABQ-002 | Which historical USPTO/patent/privacy tasks are still legally active? | Do not create reminders until verified. |
| ABQ-003 | What evidence folder and naming conventions apply to annual/quarterly payroll tax filings and business filings? | Likely monthly `Invoices and Receipts` or annual folders, but needs validation. |
| ABQ-004 | Should quarterly payroll tax tasks be one consolidated quarterly workflow rather than separate month-specific checklist rows? | January/April/July/October items are similar. |
| ABQ-005 | Should BLS Annual Refiling Survey be tracked as a three-year recurrence? | Intake contains conflicting last-completed years: 2017, 2019, and 2022. |
