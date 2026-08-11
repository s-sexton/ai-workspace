# Azure Cross-Subscription Baseline

Assessment date: August 11, 2026, Central time

Mode: read-only. Azure CLI subscription context was switched for inventory
queries and restored to `stf-prd` afterward. No Azure resources were changed.

## Scope

All accessible SendThisFile tenant subscriptions with resource-management
scope were included:

| Subscription | Subscription ID | Resource groups | Resources |
| --- | --- | ---: | ---: |
| `stf-prd` | `482861e4-6ac9-4602-a687-75b23ac705ad` | 8 | 98 |
| `stf-prod-sub` | `c6bc0983-6449-4f6e-a6f1-f50b7d81d19c` | 9 | 34 |
| `stf-dev-sub` | `3c2cf111-6463-4182-bd51-36a2baf1ae7c` | 4 | 36 |
| `stf-dev` | `67231d30-aaf8-42c7-8557-f5d77aae34cd` | 3 | 18 |
| `stf-dbz` | `b7a67179-2fec-42ae-b75c-a3391ca5254c` | 2 | 17 |
| `stf-biz` | `fe73dbee-1d66-41fa-a2f1-cf8aabc734f8` | 5 | 1 |
| `devkan` | `f6d13d55-b07d-4796-a1a0-1340b7105178` | 1 | 1 |
| `stf-bet` | `6b4b3909-f9c1-4c2a-b6df-f987503323d6` | 1 | 0 |

## Key Findings

### `stf-prod-sub` Needs Deep Follow-Up

Observed resource groups:

- `NetworkWatcherRG`
- `vm-prod-rg`
- `database-prod-rg`
- `network-prod-rg`
- `aad-prod-rg`
- `rg-help`
- `maps-prod-rg`
- `rg-compliance`
- `ResourceMoverRG-eastus-southcentralus-eus2`

Notable resources:

- Running VMs with public IPs:
  `stf-prod-oracle-standby-vm`, `stf-prod-build-vm`,
  `stf-prod-cacti-vm`, `stf-prod-reports-vm`.
- Public IPs observed:
  `13.68.254.69`, `104.211.10.154`, `168.62.38.248`,
  `52.149.219.67`.
- Advisor signals include underutilized VM recommendations, availability-zone
  recommendations, disk zone alignment recommendations, VPN gateway redundancy
  recommendations, and Azure Maps Gen1 retirement for `maps-prod-001`.

Recommended next review:

- Network exposure and NSG review for all four VMs.
- VM utilization and cost review.
- Oracle standby ownership and backup/restore expectations.
- Azure Maps Gen1 migration path.

### `stf-dev-sub` Needs Deep Follow-Up

Observed resource groups:

- `network-dev-rg`
- `storage-dev-rg`
- `DefaultResourceGroup-EUS`
- `legacy-dev-rg`

Notable resources:

- Running VMs with public IPs: `stf-dev-dev-vm`, `stf-dev-devdb-vm`.
- Public IPs observed: `13.90.101.206`, `13.82.96.42`.
- Storage `stfdevstorage1`: minimum TLS `TLS1_2`, blob public access disabled,
  network default action `Deny`.
- Advisor signals include underutilized VM recommendation, storage shared-key
  prevention, Defender enablement, VM encryption/update/vulnerability
  recommendations, unrestricted network-port warning, and VM backup warnings.

Recommended next review:

- Confirm whether both legacy dev VMs are still required.
- Review NSG rules and management access.
- Review backup, patching, and vulnerability posture.

### `stf-dev` And `stf-dbz` Have Storage TLS/Public-Access Flags

`stf-dev` notable resources:

- Function Apps `func-stf-dev-001`, `func-stf-dev-002`
- PostgreSQL `psql-stf-dev-002`
- API Management `stf-api-dev-001`
- Storage `stgstfdev001`

`stf-dbz` notable resources:

- Function Apps `func-stf-dbz-001`, `func-stf-dbz-002`
- PostgreSQL `psql-stf-dbz-203`
- Storage `stgstfdbz001`

Storage flags:

- `stgstfdev001`: minimum TLS `TLS1_0`, blob public access allowed, network
  default action `Allow`.
- `stgstfdbz001`: minimum TLS `TLS1_0`, blob public access allowed, network
  default action `Allow`.

Recommended next review:

- Confirm whether any dev/dbz workloads require TLS 1.0.
- Review public blob/container exposure.
- Review whether default storage network access can be restricted.

### Small Or Mostly Empty Subscriptions

- `stf-biz`: five resource groups but only one observed resource,
  `staiworkspacestf`, used for AI Workspace local Codex sessions. Storage has
  TLS 1.2 and blob public access disabled; network default action is `Allow`.
- `devkan`: one Azure Maps account, `maps-devkan-001`.
- `stf-bet`: one empty resource group, `stf-test-rg`.

Recommended next review:

- Confirm ownership and retention purpose for empty/default resource groups.
- Confirm whether `stf-bet` should remain empty.
- Confirm whether `devkan` and `stf-biz` should be included in routine cost
  reporting.

## Standard Future Scope

Future Azure infrastructure reviews should include all accessible subscriptions
by default:

- `stf-prd`
- `stf-prod-sub`
- `stf-dev-sub`
- `stf-dev`
- `stf-dbz`
- `stf-biz`
- `devkan`
- `stf-bet`

If a review is intentionally limited to one subscription, the report should say
so in its scope section.
