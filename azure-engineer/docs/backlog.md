# Azure Engineer Backlog

Last updated: August 12, 2026, Central time

This backlog tracks to-do and research items found during read-only Azure
analysis. Items are recommendations for human review, not approval to change
Azure.

## Completed

### Retire `vm-stf-prd-001`

Status: Completed August 12, 2026

Outcome:

- WordPress marketing VM `vm-stf-prd-001` was removed after staged validation.
- Public `sendthisfile.com` and `www.sendthisfile.com` continued serving from
  Cloudflare before and after deletion.
- Removed resources included the VM, OS disk, NIC, public IP, VM-specific NSG,
  and VM-specific SSH public key.
- Azure Backup recovery points were intentionally retained.

Reference:

- Jira: `STF-3616`
- Report:
  `azure-engineer/reports/vm-stf-prd-001-retirement-2026-08-12.md`

## Priority 1

### Establish Azure EOL And Unsupported Resource Register

Status: Open

Evidence:

- Initial EOL review found active retirement or unsupported-version exposure in
  Redis, Application Insights URL ping tests, Azure Maps Gen1, Storage TLS
  1.0/1.1, CentOS VM images, B-series v1 VM sizes, Node.js 20 on one Function
  App, and MySQL 8.0 standard support horizon.
- Azure Advisor provides service retirement recommendations, but Microsoft
  documents that the Service Retirement workbook is a subset view and Azure
  Updates remains the broader lifecycle source.

Research questions:

- Which owner should approve migration planning for Redis, Azure Maps,
  Application Insights availability tests, legacy VMs, and MySQL?
- Should EOL review run monthly and feed Clarity a completion notice?
- Should we create a normalized local EOL register that maps Azure resource
  types, SKUs, runtimes, and database versions to known lifecycle dates?

Required approval:

- Any migration, runtime change, SKU change, storage TLS change, or retirement
  remediation is an Azure/application change and requires explicit human
  approval.

### Establish Actual Cost Export For Repeatable Analysis

Status: Open

Evidence:

- `az costmanagement` extension is installed, but this extension exposes export
  management, not `query`.
- Direct Cost Management query API returned HTTP `429 Too Many Requests`.
- `az consumption usage list` returns usage/resource rows, but cost and usage
  quantities are `None` in the current context.
- No Cost Management exports are configured for the accessible subscriptions.

Research questions:

- Which billing scope should own the cost export: billing account, billing
  profile, or each subscription?
- Which existing storage account should receive exports, or should a dedicated
  storage account be created?
- What export cadence and data type are needed: daily actual cost, amortized
  cost, or both?
- What minimal permission is required for the Azure Engineer to read exported
  cost data locally?

Required approval:

- Creating a Cost Management export is an Azure configuration write and
  requires explicit human approval before any action.

### Review Public-IP VM Exposure In `stf-prod-sub`

Status: Open

Evidence:

- `stf-prod-oracle-standby-vm`: public IP `13.68.254.69`.
- `stf-prod-build-vm`: public IP `104.211.10.154`.
- `stf-prod-cacti-vm`: public IP `168.62.38.248`.
- `stf-prod-reports-vm`: public IP `52.149.219.67`.
- Subnet NSG `stf-prod-001-snet-nsg` allows public HTTP/HTTPS to reports and
  several source-specific SSH/Oracle rules.

Research questions:

- Are all source IP allow-list entries current business systems?
- Should reports remain public on ports 80/443?
- Is Oracle standby access limited to still-valid production database sources?
- Is there a documented owner and patching process for each VM?

### Review Public-IP VM Exposure In `stf-dev-sub`

Status: Open

Evidence:

- `stf-dev-dev-vm`: public IP `13.90.101.206`.
- `stf-dev-devdb-vm`: public IP `13.82.96.42`.
- NSG `stf-dev-001-snet-nsg` allows public inbound 80/443/444 to
  `172.30.1.5` and SSH to `172.30.1.5` from four source IPs.
- `stf-dev-devdb-vm` tag says: `Can stay shutdown until needed`.

Research questions:

- Can `stf-dev-devdb-vm` be stopped when not actively needed?
- Is port 444 still required publicly?
- Are SSH source IPs still valid?
- Are backup, patching, and vulnerability assessment requirements defined for
  these legacy dev VMs?

### Review Legacy Storage TLS And Public Blob Settings

Status: Open

Evidence:

- `stgstfprd001`: minimum TLS `TLS1_0`, blob public access allowed, network
  default action `Allow`.
- `stgstfdev001`: minimum TLS `TLS1_0`, blob public access allowed, network
  default action `Allow`.
- `stgstfdbz001`: minimum TLS `TLS1_0`, blob public access allowed, network
  default action `Allow`.

Research questions:

- Are any clients still dependent on TLS 1.0 or TLS 1.1?
- Which containers, if any, are intentionally public?
- Can public blob access be disabled after container-level review?
- Can storage network access be narrowed without breaking legacy workloads?

## Priority 2

### Validate VM Reserved Instance Coverage And Renewal Intent

Status: Open

Evidence:

- Active VM reservations are scoped to `stf-prod-sub`.
- Active reservation coverage matches the four running `stf-prod-sub` VM
  sizes: two `Standard_B1s`, one `Standard_D4s_v3`, one `Standard_D2s_v3`.
- Reservation utilization is 100% for 1, 7, and 30 day aggregates.
- Renew is currently off for the active reservations.
- Reservations expire September 13, 2028.

Research questions:

- Should these reservations remain scoped only to `stf-prod-sub`?
- Is renewal intentionally off?
- Should alerts/reminders be added before the 2028 expiration window?
- If legacy VMs are retired before 2028, what is the reservation exchange or
  scope strategy?

### Analyze PostgreSQL And App Service Reservation Opportunities

Status: Open

Evidence:

- `stf-prd` Advisor cost recommendations include repeated high-impact
  PostgreSQL reserved instance recommendations.
- `stf-prd` Advisor cost recommendations include repeated high-impact
  App Service reserved instance recommendations.
- `psql-stf-prd-003` and `psql-stf-prd-004` are both PostgreSQL Flexible
  Server `Standard_D4ds_v4`.
- App Service plans include `wbsvf-prd-001` on `P0v3` with capacity `2` and
  `wbsvf-prd-003` on Workflow Standard `WS1`.

Research questions:

- Are PostgreSQL servers steady-state enough for reserved capacity?
- Is there existing PostgreSQL reserved capacity not visible in the VM
  reservation list?
- Is App Service `P0v3` steady-state enough for App Service reserved pricing?
- Does Workflow Standard `WS1` have an applicable commitment/plan discount, or
  is Advisor referring only to the App Service plan?

### Review `stf-prd` Function App Access Posture

Status: Open

Evidence:

- `func-stf-prd-001`: `httpsOnly=false`, FTPS `AllAllowed`.
- `func-stf-prd-002`: public network access enabled; main and SCM access
  restrictions default to `Allow`.

Research questions:

- Can HTTPS-only be enabled on `func-stf-prd-001`?
- Is FTPS still required?
- Should SCM/Kudu access be restricted by source, private endpoint, or identity
  workflow?

### Review Broad RBAC And Unresolved Service Principals

Status: Open

Evidence:

- Broad roles observed in `stf-prd`, including `Owner`, `Contributor`,
  `User Access Administrator`, and unnamed service principal assignments.

Research questions:

- Which unnamed service principals correspond to current applications?
- Can any human or service principal permissions be narrowed?
- Are root-scope `User Access Administrator` assignments still needed?

## Priority 3

### Formalize Clarity Completion Notification Handoff

Status: Open

Evidence:

- Scott clarified that Azure Engineer should not send Teams notifications
  directly.
- Clarity updated its operating docs to treat other agents' notification
  requests as handoffs or relay requests.
- Azure Engineer RRE now routes long-running task completion notifications
  through Clarity.

Research questions:

- What exact Clarity prompt or command format should Azure Engineer use for
  recurring completion notices?
- Should Clarity maintain delivery audit entries that Azure Engineer can read
  without querying Teams directly?
- Should Azure Engineer reports include a standard "notify Scott" summary block
  for Clarity to relay?

### Improve Cost Data Access

Status: Open

Evidence:

- Actual Cost Management query was rate-limited during the initial pass.
- `az consumption usage list` returned rows but not usable cost values in the
  current CLI context.

Research questions:

- Should a billing export be configured for repeatable local analysis?
- What permissions are needed for actual cost by resource?
- Should cost reviews be monthly by subscription, resource group, and top
  resource?

### Track Azure CLI Analysis Tooling

Status: Open

Evidence:

- Installed analysis extensions now include `costmanagement`, `reservation`,
  `resource-graph`, `front-door`, `scheduled-query`, `storage-preview`, and
  `storage-discovery`.
- Some installed extensions are preview: `containerapp`, `interactive`,
  `next`, `scenario-guide`, `scheduled-query`, `storage-preview`, and
  `webapp`.

Research questions:

- Which preview extensions are actually needed for Azure Engineer work?
- Should broken/stale extensions be removed if warnings return?
- Should extension versions be recorded in each major assessment?

### Validate Empty Or Sparse Subscriptions And Resource Groups

Status: Open

Evidence:

- `stf-bet` has `stf-test-rg` with no resources observed.
- `stf-biz` has five resource groups and one storage account.
- Several default resource groups appear across subscriptions.

Research questions:

- Which empty/default groups should remain for provider-managed resources?
- Are any groups abandoned experiments?
- What owner/purpose tags should be required?

### Document Tagging Standards

Status: Open

Evidence:

- Many resources have sparse or missing owner, purpose, environment, cost
  center, and data classification tags.

Research questions:

- What minimum tag set should apply to all Azure resources?
- Which legacy resources need tag remediation first?
- Should tag compliance be measured in read-only reports?
