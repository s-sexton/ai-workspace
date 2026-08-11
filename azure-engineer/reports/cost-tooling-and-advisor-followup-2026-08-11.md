# Cost Tooling And Advisor Follow-Up

Assessment date: August 11, 2026, Central time

Mode: read-only. No Azure resources, Cost Management exports, billing
settings, reservations, or configuration were changed.

## Tooling Status

Installed Azure CLI extensions relevant to Azure Engineer work:

- `costmanagement` `1.0.0`
- `reservation` `0.3.1`
- `resource-graph` `2.1.1`
- `front-door` `2.3.0`
- `scheduled-query` `1.0.0b2`
- `storage-preview` `1.0.0b8`
- `storage-discovery` `1.0.0`

Important behavior:

- `az costmanagement` is installed, but it exposes export management and does
  not provide an `az costmanagement query` command in this environment.
- `az reservations reservation-order list` works for reservation order
  summaries.
- Detailed reservation utilization was still best retrieved through the
  read-only Reservation REST API.
- `az graph query` works and is useful for cross-subscription inventory without
  repeatedly switching CLI context.

## Actual Cost Access Status

Attempted actual-cost paths:

- Direct Cost Management query API for `stf-prd`, July 1-August 11, 2026:
  returned HTTP `429 Too Many Requests`.
- `az consumption usage list`, August 1-11, 2026: returned resource/product
  usage rows, but `pretaxCost`, `usageQuantity`, and `billableQuantity` were
  `None`.
- Cost Management export listing: no exports were configured on the accessible
  subscriptions.

Conclusion:

The current tooling is installed, but actual resource-level cost reporting is
still blocked by Cost Management query throttling and lack of a configured
export. The most reliable next step for repeatable cost work is likely a Cost
Management export, but creating one is an Azure write and requires explicit
human approval.

## Advisor Cost Recommendations

### `stf-prd`

Advisor cost recommendations:

- 12 rows: consider VM reserved instances.
- 12 rows: consider PostgreSQL reserved instances.
- 6 rows: consider App Service reserved instances.
- 3 rows: disable Front Door health probes when there is only one origin in an
  origin group.

Interpretation:

- VM RI recommendations may relate to `stf-prd` VMs, not the existing
  `stf-prod-sub` VM reservations.
- PostgreSQL and App Service reservation opportunities need deeper analysis
  once actual usage/cost data is available.
- Front Door health probe recommendations may indicate small avoidable cost
  and should be reviewed against origin health requirements.

### `stf-prod-sub`

Advisor cost recommendations:

- `stf-prod-oracle-standby-vm`: right-size or shutdown underutilized VM.
- `stf-prod-build-vm`: right-size or shutdown underutilized VM.
- `stf-prod-reports-vm`: right-size or shutdown underutilized VM.

Interpretation:

- Active VM reservations fully match the current `stf-prod-sub` VM footprint
  and show 100% utilization, so right-sizing or shutdown should be evaluated
  with reservation impact first.
- The cost question is not only "can the VM be cheaper?" but "can the workload
  be retired or redesigned without stranding reservation value or increasing
  operational risk?"

### `stf-dev-sub`

Advisor cost recommendations:

- `stf-dev-devdb-vm`: right-size or shutdown underutilized VM.
- 12 rows: consider VM reserved instances.

Interpretation:

- `stf-dev-devdb-vm` is the clearest immediate research item because its tag
  says it can stay shutdown until needed and observed CPU is near zero.
- Buying new VM reservations for dev workloads should not happen until workload
  necessity and runtime schedule are confirmed.

### Other Subscriptions

No Advisor cost rows were observed for:

- `stf-dev`
- `stf-dbz`
- `stf-biz`
- `devkan`
- `stf-bet`

## Resource Graph Cost-Relevant Inventory

Resource Graph confirmed nine running VMs across accessible subscriptions:

- `stf-prd`: three Linux VMs.
- `stf-prod-sub`: four Linux VMs.
- `stf-dev-sub`: two Linux VMs.

Cost-relevant non-VM resources from Resource Graph include:

- PostgreSQL Flexible Servers:
  `psql-stf-prd-003`, `psql-stf-prd-004`, `psql-stf-dev-002`,
  `psql-stf-dbz-203`.
- App Service plans:
  `wbsvf-prd-001`, `wbsvf-prd-003`, `wbsvf-dev-001`, `wbsvf-dbz-001`.
- Storage accounts:
  `stgstfprd001`, `stgstfdev001`, `stgstfdbz001`, `stfdevstorage1`,
  `staiworkspacestf`.

## Recommended Next Steps

1. Get approval to design, but not yet create, a Cost Management export plan.
2. Identify the correct billing scope and export destination for cost data.
3. Review PostgreSQL and App Service reservation recommendations after actual
   usage is available.
4. Review `stf-dev-devdb-vm` for shutdown schedule or retirement before any
   dev VM reservation purchase is considered.
5. Review `stf-prod-sub` underutilized VMs with reservation impact included.
