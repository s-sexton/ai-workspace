# Azure Infrastructure Assessment - Initial Baseline

Assessment time: August 11, 2026, Central time

Scope analyzed: Azure CLI default subscription `stf-prd`
(`482861e4-6ac9-4602-a687-75b23ac705ad`) in the SendThisFile tenant.

Mode: read-only. No Azure resources, permissions, billing settings, or
configuration were changed.

## Executive Summary

The initial baseline found several credible risk and cost-review items:

- `stgstfprd001` allows blob public access, uses `TLS1_0` minimum TLS, and has
  network default action `Allow`.
- `func-stf-prd-001` has `httpsOnly` set to `false` and FTPS state
  `AllAllowed`.
- `func-stf-prd-002` is public-network enabled and both main and SCM access
  restrictions default to `Allow`.
- Three production Linux VMs are running with public IP addresses, although
  their explicit NSG rules only allow Azure Front Door backend traffic on
  ports 80 and 443.
- PostgreSQL and MySQL flexible servers have public network access disabled,
  which is good, but HA and geo-redundant backup are disabled and backup
  retention is 7 days.
- Azure Advisor repeatedly recommends reserved instances for PostgreSQL,
  App Service, and VMs.
- All three VMs show very low average CPU for August 4-11, 2026, suggesting a
  right-sizing review is worthwhile.
- Several older Logic App/API connections (`azureblob`, `azureblob-2`,
  `sendgrid`) should be owner/use validated.

## Inventory Snapshot

Resource groups found:

- `rg-prd-001`
- `rg-net-001`
- `rg-fd-001`
- `NetworkWatcherRG`
- `AzureBackupRG_eastus_1`
- `LogAnalyticsDefaultResources`
- `DefaultResourceGroup-EUS`
- `azureapp-auto-alerts-74057c-scott_sexton_sendthisfile_com`

Key production resources observed:

- VMs: `vm-stf-prd-001`, `vm-stf-prd-002`, `vm-stf-prd-003`
- App Service plans: `wbsvf-prd-001` (`P0v3`, capacity 2),
  `wbsvf-prd-003` (`WS1`, capacity 1)
- Function Apps: `func-stf-prd-001`, `func-stf-prd-002`
- Logic App/Workflow App: `logic-prd-001`
- Storage account: `stgstfprd001`
- PostgreSQL flexible servers: `psql-stf-prd-003`, `psql-stf-prd-004`
- MySQL flexible server: `mysql-stf-prd-001`
- Redis: `redis-stf-prd-001`
- Azure Front Door: `fd-prd-001`, with endpoints `fd-dev`, `fd-prd`, `fd-dbz`
- Recovery vaults: `rv-stf-prd-vm-001`, plus `vault-llqnvksh` surfaced by
  Advisor under `DefaultResourceGroup-EUS`
- Private endpoints: `pe-redis-prd-001`, `pe-prd-003`, `pe-stf-prd-001`,
  `pe-stf-prd-002`

## Security Findings

### High: Storage Account Allows Legacy TLS And Public-Oriented Defaults

Resource: `stgstfprd001`

Observed:

- `minimumTlsVersion`: `TLS1_0`
- `allowBlobPublicAccess`: `true`
- `networkRuleSet.defaultAction`: `Allow`
- `enableHttpsTrafficOnly`: `true`
- SKU: `Standard_LRS`

Why it matters:

TLS 1.0 should be treated as legacy. Allowing blob public access and broad
network defaults increases the chance that a future container or configuration
mistake exposes data.

Recommended human-reviewed actions:

- Confirm whether any workload still requires TLS 1.0.
- Plan migration to minimum TLS 1.2.
- Review blob containers for public access.
- Review whether network access can be restricted.

### Medium/High: Function App HTTPS And Deployment Access Posture

Resources: `func-stf-prd-001`, `func-stf-prd-002`

Observed:

- `func-stf-prd-001`: `httpsOnly=false`, `ftpsState=AllAllowed`,
  `minTlsVersion=1.2`, runtime `node|22`
- `func-stf-prd-002`: `httpsOnly=true`, `ftpsState=FtpsOnly`,
  `publicNetworkAccess=Enabled`, main and SCM default action `Allow`,
  runtime `node|22`

Why it matters:

Production functions should generally force HTTPS and limit publishing/SCM
exposure. Public network access may be appropriate, but it should be deliberate
and documented.

Recommended human-reviewed actions:

- Confirm whether `func-stf-prd-001` can require HTTPS.
- Confirm whether FTPS is needed at all, and whether `FtpsOnly` or disabled is
  appropriate.
- Review access restrictions for `func-stf-prd-002`, including SCM/Kudu.

### Medium: Public IPs On Production VMs

Resources:

- `vm-stf-prd-001`: public IP `20.124.114.228`, private IP `10.0.6.4`
- `vm-stf-prd-002`: public IP `52.255.158.136`, private IP `10.0.6.5`
- `vm-stf-prd-003`: public IP `20.25.73.81`, private IP `10.0.6.6`

Observed NSG posture:

- Explicit inbound allows are limited to Azure Front Door backend source on
  ports 80 and 443 for each VM.
- No explicit broad SSH/RDP allow rules were observed in the NSG list.

Why it matters:

The NSG rules look intentionally narrowed, but public IPs still expand the
attack surface and should be periodically validated against Front Door origin
protection, host firewalls, and management access paths.

Recommended human-reviewed actions:

- Confirm Front Door origin protection is complete.
- Confirm no management ports are exposed through another NSG, NIC rule, or
  host firewall path.
- Decide whether direct public IPs are still required.

### Medium: Broad RBAC At Subscription Scope

Observed subscription/inherited assignments include:

- `Owner`: `scott.sexton@sendthisfile.com`
- `Contributor`: `aaron@sendthisfile.com`, `dan.ziegelbein@sendthisfile.com`
- `User Access Administrator`: `aaron@sendthisfile.com`,
  `dan.ziegelbein@sendthisfile.com` at root scope `/`
- Several service principals with `Contributor`, `Reader`, or
  `Cost Management Reader`, some without resolved principal names.

Why it matters:

Broad subscription/root-scope roles are powerful. Unresolved service principals
deserve identity and owner validation.

Recommended human-reviewed actions:

- Validate each broad role assignment still has a business need.
- Resolve unnamed service principals to application/object IDs.
- Consider resource-group scoped roles where practical.

## Resilience And Backup Findings

Azure Advisor produced repeated high-impact resiliency recommendations:

- Front Door `fd-prd-001`: consider at least two origins.
- MySQL `mysql-stf-prd-001`: enable HA with zone redundancy.
- PostgreSQL `psql-stf-prd-003` and `psql-stf-prd-004`: enable HA with zone
  redundancy.
- Redis `redis-stf-prd-001`: enable zone redundancy.
- Storage `stgstfprd001`: enable zone redundancy.
- VMs `vm-stf-prd-001`, `vm-stf-prd-002`, `vm-stf-prd-003`: use availability
  zones / review migration path.
- VPN gateway `vnetg-prd-001`: use availability zones and active-active
  gateway redundancy.
- PostgreSQL `psql-stf-prd-003`: turn on backup and configure geo-redundant
  backup storage.
- Recovery vaults: switch to Azure Monitor based backup alerts.

Observed database settings:

- `psql-stf-prd-003`: PostgreSQL 16, `Standard_D4ds_v4`, public access
  disabled, HA disabled, geo-backup disabled, backup retention 7 days.
- `psql-stf-prd-004`: PostgreSQL 16, `Standard_D4ds_v4`, public access
  disabled, HA disabled, geo-backup disabled, backup retention 7 days.
- `mysql-stf-prd-001`: MySQL 8.0.21, `Standard_B1ms`, public access disabled,
  HA disabled, geo-backup disabled, backup retention 7 days.

Recommended human-reviewed actions:

- Classify each datastore by RPO/RTO expectation.
- Decide whether HA and geo-backup gaps are acceptable for each workload.
- Validate backup restore procedures, not only backup configuration.

## Cost And Pricing Findings

Actual tenant cost extraction status:

- `az consumption usage list` returned usage/resource rows but did not expose
  usable cost values in this CLI context.
- `az costmanagement` is not installed locally.
- Direct Cost Management REST queries were rate-limited with HTTP `429`.
- No benefit recommendation rows were returned by the Cost Management benefit
  recommendations API.

Azure Advisor cost recommendations:

- Consider PostgreSQL reserved instances.
- Consider App Service reserved instances.
- Consider VM reserved instances.

Public list-price signals gathered on August 11, 2026:

- Linux VM `Standard_B1s` in East US: about `$0.0104/hour`.
- Linux VM `Standard_B2s` in East US: about `$0.0416/hour`.
- Visible VM compute-only monthly list estimate at 730 hours:
  - `vm-stf-prd-001` B2s: about `$30.37/month`
  - `vm-stf-prd-002` B1s: about `$7.59/month`
  - `vm-stf-prd-003` B2s: about `$30.37/month`
  - Total visible VM compute: about `$68.33/month`, before disks, bandwidth,
    backup, reservations, discounts, taxes, and support.

VM CPU metrics for August 4-11, 2026:

- `vm-stf-prd-001`: average `0.741%`, max `2.134%`
- `vm-stf-prd-002`: average `0.603%`, max `3.482%`
- `vm-stf-prd-003`: average `1.259%`, max `2.204%`

Cost interpretation:

The VM compute spend itself appears modest at public Linux list prices, but
the sustained low CPU indicates these workloads should be reviewed for
right-sizing, consolidation, shutdown scheduling, or migration only after
validating memory, disk, network, application latency, and business criticality.
Advisor's reserved-instance recommendations suggest larger savings may exist
for PostgreSQL, App Service, and VMs once actual billed usage is available.

Recommended human-reviewed actions:

- Retry Cost Management query later or use a billing export for precise cost by
  resource.
- Review PostgreSQL/App Service/VM reservation recommendations against actual
  steady-state commitments.
- Add monthly cost review by resource group, service, and top resource once
  actual billing data is accessible.

## Questionable Or Ownership-Review Items

- API connections `azureblob`, `azureblob-2`, and `sendgrid` were created in
  June 2023. Confirm whether they are still used by `logic-prd-001`.
- API connections `teams`, `azurequeues`, and `office365users` were created on
  August 4, 2026. These look related to the current Teams relay milestone, but
  should have explicit owner/purpose tags.
- Resource groups and many resources have missing or sparse tags. Ownership,
  environment, data classification, and cost-center tags would improve review.
- Front Door has endpoints named `fd-dev`, `fd-prd`, and `fd-dbz` in the
  production subscription. Confirm whether non-production endpoints belong in
  this subscription/profile.
- `LogAnalyticsDefaultResources` and `DefaultResourceGroup-EUS` should be
  reviewed for intentional ownership and retained purpose.

## Coverage Gaps

- Only the default `stf-prd` subscription was analyzed in depth. Other visible
  subscriptions include `stf-dev`, `stf-bet`, `stf-dbz`, `stf-dev-sub`,
  `stf-prod-sub`, `devkan`, and `stf-biz`.
- Security Center assessments returned no rows through this CLI context.
- Subscription diagnostic settings returned no rows.
- Actual billed cost by resource was not available in this pass because of CLI
  command availability and Cost Management API rate limiting.
- Full app settings, connection secrets, storage keys, and raw resource
  properties were intentionally not collected.

## Recommended Next Steps

1. Validate the high-confidence configuration risks: storage TLS/public access,
   Function App HTTPS/FTPS/access restrictions, and broad RBAC.
2. Retry actual Cost Management queries and produce a top-cost-by-resource
   report.
3. Expand read-only assessment to all accessible SendThisFile subscriptions.
4. Review Advisor recommendations with workload owners and classify each as
   accept, defer, or plan.
5. Add missing ownership/purpose tags for resources and API connections.
