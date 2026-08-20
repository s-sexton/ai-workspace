# Azure Environment

Last updated: August 12, 2026, Central time

Maintained by: Azure Infrastructure Expert

This document is the durable local map of the observed Azure environment. It is
based on read-only Azure CLI and Azure REST API calls. It should not be treated
as a deployment manifest or source of truth for making changes.

## Operating Boundary

- Analysis is read-only by default.
- Azure changes, removals, deployments, scaling, firewall changes, policy
  changes, identity changes, secret handling, billing changes, reservation
  purchases, and production configuration changes require explicit human
  approval.
- Do not collect or store secrets, keys, tokens, connection strings,
  authentication headers, or raw application settings in this repository.
- Reports and environment notes may contain confidential infrastructure
  metadata and should remain local unless approved for sharing.

## Azure CLI Context

Default subscription observed:

- Name: `stf-prd`
- Subscription ID: `482861e4-6ac9-4602-a687-75b23ac705ad`
- Tenant: `SendThisFile`
- Tenant ID: `550b3b81-1f78-4e78-ac75-1cd6fc1af30e`
- Tenant default domain: `sendthisfile.com`
- Signed-in user observed: `scott.sexton@sendthisfile.com`

Other accessible subscriptions/accounts visible from `az account list`:

- `stf-dev`
- `stf-bet`
- `stf-dbz`
- `stf-dev-sub`
- `stf-prod-sub`
- `stf-biz`
- `devkan`
- Two tenant-level accounts shown as `N/A(tenant level account)`

Current assessment depth:

- All accessible SendThisFile subscriptions were included in a lightweight
  cross-subscription inventory pass.
- `stf-prd` has been analyzed in the deepest first baseline pass.
- `stf-dev-sub` and `stf-prod-sub` need deeper security and cost follow-up
  because they contain running public-IP VMs and legacy production-style
  resources.

## Cross-Subscription Inventory

The standard review scope is all accessible SendThisFile subscriptions unless
the human operator explicitly narrows the scope.

| Subscription | Resource groups | Resources | Notes |
| --- | ---: | ---: | --- |
| `stf-prd` | 8 | 91 | Main production app subscription analyzed in the first baseline. WordPress VM `vm-stf-prd-001` retired August 12, 2026. |
| `stf-prod-sub` | 9 | 34 | Legacy/classic production-style resources, including four running public-IP VMs. |
| `stf-dev-sub` | 4 | 36 | Legacy dev network/storage/VM resources, including two running public-IP VMs. |
| `stf-dev` | 3 | 18 | Dev app resources, Function Apps, PostgreSQL, storage, API Management. |
| `stf-dbz` | 2 | 17 | DBZ app resources, Function Apps, PostgreSQL, storage. |
| `stf-biz` | 5 | 1 | AI workspace storage account plus mostly empty/default resource groups. |
| `devkan` | 1 | 1 | Azure Maps account. |
| `stf-bet` | 1 | 0 | Empty `stf-test-rg` resource group observed. |

Top cross-subscription flags:

- `stf-prod-sub` has four running VMs with public IPs:
  `stf-prod-oracle-standby-vm`, `stf-prod-build-vm`,
  `stf-prod-cacti-vm`, and `stf-prod-reports-vm`.
- `stf-dev-sub` has two running VMs with public IPs:
  `stf-dev-dev-vm` and `stf-dev-devdb-vm`.
- `stf-dev` storage account `stgstfdev001` reports minimum TLS `TLS1_0`,
  blob public access allowed, and network default action `Allow`.
- `stf-dbz` storage account `stgstfdbz001` reports minimum TLS `TLS1_0`,
  blob public access allowed, and network default action `Allow`.
- `stf-biz` storage account `staiworkspacestf` reports minimum TLS `TLS1_2`
  and blob public access disabled, but network default action `Allow`.
- `stf-bet` appears to contain no resources beyond `stf-test-rg`; confirm
  whether the empty resource group should remain.

## Resource Group Map

Resource groups observed in `stf-prd`:

- `rg-prd-001`: primary production application resources.
- `rg-net-001`: networking, private DNS, virtual network, gateways, and private
  endpoints.
- `rg-fd-001`: Azure Front Door profile and endpoints.
- `AzureBackupRG_eastus_1`: Azure Backup restore point collections.
- `NetworkWatcherRG`: Azure Network Watcher.
- `LogAnalyticsDefaultResources`: default Log Analytics query pack resources.
- `DefaultResourceGroup-EUS`: default resource group that appears in Advisor
  findings for a Recovery Services vault.
- `azureapp-auto-alerts-74057c-scott_sexton_sendthisfile_com`: auto-created
  alerting resource group.

## Application And Compute

Virtual machines:

- `vm-stf-prd-002`: Linux, `Standard_B1s`, running, Mautic workload tag,
  private IP `10.0.6.5`, public IP `52.255.158.136`.
- `vm-stf-prd-003`: Linux, `Standard_B2s`, running, Plausible/Docker workload
  tag, private IP `10.0.6.6`, public IP `20.25.73.81`.

Retired virtual machines:

- `vm-stf-prd-001`: retired August 12, 2026 after the WordPress marketing
  workload moved to Cloudflare. Removed resources included the VM, OS disk,
  NIC, public IP `20.124.114.228`, VM-specific NSG, and VM-specific SSH public
  key. Azure Backup recovery points were intentionally retained.

VM CPU metrics for August 4-11, 2026:

- `vm-stf-prd-002`: average `0.603%`, max `3.482%`.
- `vm-stf-prd-003`: average `1.259%`, max `2.204%`.

App Service plans:

- `wbsvf-prd-001`: Linux App Service plan, `P0v3`, capacity `2`, hosts two
  Function Apps, zone redundant `false`.
- `wbsvf-prd-003`: Workflow Standard plan, `WS1`, capacity `1`, zone redundant
  `false`.

Function Apps:

- `func-stf-prd-001`: Linux Function App, Node 22, running, `httpsOnly=false`,
  FTPS `AllAllowed`, always on, Application Insights linked.
- `func-stf-prd-002`: Linux Function App, Node 22, running, `httpsOnly=true`,
  public network access enabled, FTPS `FtpsOnly`, main and SCM default access
  action `Allow`, custom host `stf-admin.sendthisfile.net`.

Logic/workflow resources:

- `logic-prd-001`: Function/workflow app tagged as a Logic App replacement for
  timer triggers and workflow jobs.

## Data Services

Storage:

- `stgstfprd001`: StorageV2, `Standard_LRS`, HTTPS-only enabled,
  `allowBlobPublicAccess=true`, minimum TLS `TLS1_0`, network default action
  `Allow`.

PostgreSQL flexible servers:

- `psql-stf-prd-003`: PostgreSQL 16, `Standard_D4ds_v4`, General Purpose,
  East US 2, public network access disabled, HA disabled, geo-backup disabled,
  backup retention 7 days.
- `psql-stf-prd-004`: PostgreSQL 16, `Standard_D4ds_v4`, General Purpose,
  Central US, public network access disabled, HA disabled, geo-backup disabled,
  backup retention 7 days.

MySQL flexible server:

- `mysql-stf-prd-001`: MySQL 8.0.21, `Standard_B1ms`, Burstable, East US,
  public network access disabled, HA disabled, geo-backup disabled, backup
  retention 7 days.

Redis:

- `redis-stf-prd-001`: Basic C0, Redis 6.0, public network access disabled,
  non-SSL port disabled, minimum TLS 1.2.

## Network And Edge

Azure Front Door:

- Profile: `fd-prd-001`
- SKU: `Standard_AzureFrontDoor`
- Endpoints observed: `fd-dev`, `fd-prd`, `fd-dbz`

Network security groups:

- `vm-stf-prd-002-nsg`: allows Azure Front Door backend traffic to
  `10.0.6.5` on ports 80 and 443.
- `vm-stf-prd-003-nsg`: allows Azure Front Door backend traffic to
  `10.0.6.6` on ports 80 and 443.

Private endpoints:

- `pe-redis-prd-001`
- `pe-prd-003`
- `pe-stf-prd-001`
- `pe-stf-prd-002`

Private DNS zones observed include:

- `privatelink.postgres.database.azure.com`
- `privatelink.azurewebsites.net`
- `mysql-stf-prd-001.private.mysql.database.azure.com`

VPN gateway:

- `vnetg-prd-001` exists in `rg-net-001`; Advisor recommends zone and
  active-active redundancy review.

## Identity And Access Snapshot

Subscription/inherited RBAC assignments observed in the first pass include:

- `Owner`: `scott.sexton@sendthisfile.com`
- `Contributor`: `aaron@sendthisfile.com`, `dan.ziegelbein@sendthisfile.com`
- `User Access Administrator`: `aaron@sendthisfile.com`,
  `dan.ziegelbein@sendthisfile.com` at root scope `/`
- `Virtual Machine Administrator Login`: `scott.sexton@sendthisfile.com`,
  `aaron@sendthisfile.com`, `dan.ziegelbein@sendthisfile.com`
- Service principals with `Reader`, `Contributor`, `Cost Management Reader`,
  and `App Configuration Data Reader`; some principal names did not resolve.
- Group `rg-prd-001` has `App Configuration Data Reader`.

Review need:

- Validate broad subscription/root-scope human roles.
- Resolve unnamed service principals to application/object IDs and owners.
- Confirm whether resource-group or resource-scoped assignments can replace
  broad permissions where practical.

## Monitoring, Backup, And Advisor Signals

Observed monitoring resources:

- Application Insights component `incom-prd-001`.
- Metric alerts and scheduled query rules in `rg-prd-001`.
- Action groups including `ag-prod-notifications`, `Prod Postgress Monitor`,
  and Application Insights smart detection resources.
- Web tests for Mautic and Plausible.

Advisor high-impact themes:

- Reserved instance recommendations for PostgreSQL, App Service, and VMs.
- Zone redundancy recommendations for storage, databases, Redis, VPN gateway,
  App Service plan, and VMs.
- Front Door origin redundancy recommendation.
- Backup and geo-backup recommendations for PostgreSQL/MySQL.
- Backup alerting migration to Azure Monitor.
- VM Insights recommendations.
- Redis migration recommendation to Azure Managed Redis.

Coverage note:

- Security Center assessment list returned no rows through the current CLI
  context.
- Subscription diagnostic settings returned no rows.

## Cost And Pricing Notes

Actual cost status:

- `az consumption usage list` returned usage rows but not usable cost values in
  this CLI context.
- The `az costmanagement` extension is now installed, but in this environment
  it exposes export management rather than a `query` command.
- Direct Cost Management REST queries were rate-limited with HTTP `429`.
- Cost Management benefit recommendations returned no rows.
- No Cost Management exports are currently configured on the accessible
  subscriptions.

Public list-price examples gathered on August 11, 2026:

- Linux VM `Standard_B1s` in East US: about `$0.0104/hour`.
- Linux VM `Standard_B2s` in East US: about `$0.0416/hour`.
- Visible VM compute-only monthly list estimate at 730 hours is about
  `$68.33/month`, before disks, bandwidth, backup, discounts, reservations,
  taxes, and support.

Cost follow-up:

- Retry Cost Management actual-cost queries later.
- Prefer a Cost Management export for repeatable monthly resource-level cost
  analysis, subject to human approval because creating an export is an Azure
  configuration write.
- Validate Advisor reservation opportunities against actual steady-state usage
  before purchasing reservations.

Installed cost and analysis tooling:

- `costmanagement`
- `reservation`
- `resource-graph`
- `front-door`
- `scheduled-query`
- `storage-preview`
- `storage-discovery`

## Reserved Instance Notes

Active VM reserved instances observed on August 11, 2026:

- `VM_RI_09-13-2022_11-51_renewed`: `Standard_B1s`, quantity `2`,
  East US, 3-year term, scoped to `stf-prod-sub`, expires
  September 13, 2028, 100% utilization over 1, 7, and 30 day aggregates.
- `VM_RI_09-13-2022_12-50_renewed`: `Standard_D4s_v3`, quantity `1`,
  East US, 3-year term, scoped to `stf-prod-sub`, expires
  September 13, 2028, 100% utilization over 1, 7, and 30 day aggregates.
- `VM_RI_09-13-2022_12-56_renewed`: `Standard_D2s_v3`, quantity `1`,
  East US, 3-year term, scoped to `stf-prod-sub`, expires
  September 13, 2028, 100% utilization over 1, 7, and 30 day aggregates.

The active reservations match the current `stf-prod-sub` running VM footprint:
two `Standard_B1s` VMs, one `Standard_D4s_v3` VM, and one `Standard_D2s_v3`
VM. Renew is currently off for the active reservations. If any of these VMs
are retired, resized, or moved before 2028, reservation exchange/scope impact
should be reviewed first.

## Questionable Or Owner-Review Items

- Older API connections: `azureblob`, `azureblob-2`, `sendgrid`.
- Newer API connections from August 4, 2026: `teams`, `azurequeues`,
  `office365users`.
- Front Door endpoints named `fd-dev` and `fd-dbz` inside the production
  subscription/profile.
- Sparse or missing tags across many resources.
- Default resource groups: `LogAnalyticsDefaultResources`,
  `DefaultResourceGroup-EUS`, and
  `azureapp-auto-alerts-74057c-scott_sexton_sendthisfile_com`.

## Documentation And Reports

- Role RRE: `azure-engineer/docs/rre.md`
- Environment map: `azure-engineer/docs/environment.md`
- Initial dated assessment:
  `azure-engineer/reports/infrastructure-assessment-2026-08-11.md`
- Cross-subscription baseline:
  `azure-engineer/reports/cross-subscription-baseline-2026-08-11.md`
- Reservation and legacy VM follow-up:
  `azure-engineer/reports/reservation-and-legacy-vm-followup-2026-08-11.md`
- Cost tooling and Advisor follow-up:
  `azure-engineer/reports/cost-tooling-and-advisor-followup-2026-08-11.md`
- EOL and unsupported inventory review:
  `azure-engineer/reports/eol-unsupported-inventory-review-2026-08-11.md`
- VM retirement report:
  `azure-engineer/reports/vm-stf-prd-001-retirement-2026-08-12.md`
- Backlog:
  `azure-engineer/docs/backlog.md`

## Open Follow-Ups

1. Should a billing export be configured for actual cost analysis?
2. Should Azure Defender/Security Center access be expanded or verified?
3. Should tag policy or naming standards be documented for ownership,
   environment, cost center, and data classification?
