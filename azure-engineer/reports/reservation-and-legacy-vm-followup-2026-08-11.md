# Reservation And Legacy VM Follow-Up

Assessment date: August 11, 2026, Central time

Mode: read-only. No Azure resources, reservations, permissions, billing
settings, or configuration were changed.

## Summary

The active VM reserved instances are real, visible, and currently well-aligned
to the `stf-prod-sub` legacy VM footprint:

- Two `Standard_B1s` reservations in East US.
- One `Standard_D4s_v3` reservation in East US.
- One `Standard_D2s_v3` reservation in East US.
- All active reservations are scoped to `stf-prod-sub`.
- All active reservations show 100% utilization over 1, 7, and 30 day
  aggregates.
- All active reservations expire on September 13, 2028.
- Renewal is currently off.

This changes the interpretation of the legacy production VMs: they still need
business-purpose, exposure, patching, and lifecycle review, but they do not
appear to be wasting VM reservation capacity today.

## Active VM Reservations

| Display name | Scope | SKU | Quantity | Term | Start | Expiry | Utilization |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| `VM_RI_09-13-2022_11-51_renewed` | `stf-prod-sub` | `Standard_B1s` | 2 | 3 years | 2025-09-13 | 2028-09-13 | 100% at 1/7/30 days |
| `VM_RI_09-13-2022_12-50_renewed` | `stf-prod-sub` | `Standard_D4s_v3` | 1 | 3 years | 2025-09-13 | 2028-09-13 | 100% at 1/7/30 days |
| `VM_RI_09-13-2022_12-56_renewed` | `stf-prod-sub` | `Standard_D2s_v3` | 1 | 3 years | 2025-09-13 | 2028-09-13 | 100% at 1/7/30 days |

Predecessor 2022 reservation orders exist with 2025 expiry dates and cancelled
provisioning state. The active orders are renewed replacements.

## Matching `stf-prod-sub` VM Footprint

| VM | Size | Public IP | Avg CPU Aug 4-11 | Max CPU Aug 4-11 | Reservation match |
| --- | --- | --- | ---: | ---: | --- |
| `stf-prod-oracle-standby-vm` | `Standard_D4s_v3` | `13.68.254.69` | 0.511% | 3.568% | Yes, 1x `D4s_v3` |
| `stf-prod-build-vm` | `Standard_B1s` | `104.211.10.154` | 0.443% | 0.827% | Yes, part of 2x `B1s` |
| `stf-prod-cacti-vm` | `Standard_B1s` | `168.62.38.248` | 2.093% | 2.266% | Yes, part of 2x `B1s` |
| `stf-prod-reports-vm` | `Standard_D2s_v3` | `52.149.219.67` | 0.630% | 0.760% | Yes, 1x `D2s_v3` |

Interpretation:

- Reservation coverage appears exact for current VM sizes and quantities.
- Utilization is 100%, so there is no immediate evidence of unused RI capacity.
- CPU utilization is still very low; if any VM is retired or resized, the RI
  plan should be reviewed first so a change does not strand reservation value.

## `stf-dev-sub` VM Footprint

| VM | Size | Public IP | Avg CPU Aug 4-11 | Max CPU Aug 4-11 | Notes |
| --- | --- | --- | ---: | ---: | --- |
| `stf-dev-dev-vm` | `Standard_B2s` | `13.90.101.206` | 1.280% | 1.531% | Legacy dev app VM. |
| `stf-dev-devdb-vm` | `Standard_D4as_v4` | `13.82.96.42` | 0.101% | 0.131% | Tag says it can stay shutdown until needed. |

No active reservations observed for these dev VMs. Advisor flagged
`stf-dev-devdb-vm` as an underutilized VM.

## Network Exposure Notes

### `stf-prod-sub`

NSG: `stf-prod-001-snet-nsg`

Notable inbound allows:

- SSH to Oracle standby on port 22 from two specific source IPs.
- SSH to build VM from three specific source IPs.
- SSH to reports VM from three specific source IPs.
- Oracle SQL*Net port 1521 to standby from multiple specific source IPs.
- Public HTTP/HTTPS from `*` to reports VM.

Interpretation:

- Rules are mostly source-specific, but the public reports HTTP/HTTPS rule is
  broad.
- Several allow-list IPs should be verified as current and necessary.
- Some rule names/descriptions are stale or inconsistent, such as a SantaFe SSH
  rule named `SANTAFE_SSH_To_Reports` that targets the build server IP.

### `stf-dev-sub`

NSG: `stf-dev-001-snet-nsg`

Notable inbound allows:

- Public TCP 80/443/444 to `172.30.1.5`.
- SSH to `172.30.1.5` from four specific source IPs.

Interpretation:

- Public port 444 deserves explicit owner and business-purpose validation.
- `stf-dev-devdb-vm` has a public IP but the observed subnet NSG rules target
  the app VM IP, not the DB VM IP. NIC-level rules and host firewall posture
  should still be verified.

## Pricing Context

Public East US Linux consumption list prices gathered on August 11, 2026:

- `Standard_B1s`: about `$0.0104/hour`.
- `Standard_D4s_v3`: about `$0.192/hour`.
- `Standard_D2s_v3`: about `$0.096/hour`.
- `Standard_B2s`: about `$0.0416/hour`.
- `Standard_D4as_v4`: about `$0.192/hour`.

These are public list prices, not actual billed costs. The active production
reservations should materially reduce the compute portion of `stf-prod-sub`
VM billing compared with on-demand rates.

## Follow-Up Items Added

The persistent backlog is maintained in `azure-engineer/docs/backlog.md`.
Priority items added from this pass:

- Review public-IP VM exposure in `stf-prod-sub`.
- Review public-IP VM exposure in `stf-dev-sub`.
- Review legacy storage TLS and public blob settings.
- Validate VM reserved instance coverage and renewal intent.
- Review Function App access posture.
- Review broad RBAC and unresolved service principals.
- Improve actual cost data access.
- Validate empty/sparse subscriptions and resource groups.
- Document Azure tagging standards.
