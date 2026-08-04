# Huawei WLC Monitoring

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.5.0-blue)
<!-- compatibility-badges:end -->

Legacy 1.6-era SNMP check for Huawei Wireless LAN Controllers. One service per access point reports the AP run state, management IP, up/down traffic, and the number of online users.

## How it works

The check walks `.1.3.6.1.4.1.2011.6.139.13.3.3.1` on devices whose sysObjectID equals `.1.3.6.1.4.1.2011.2.240.6` and reads:

- `.4` — `hwWlanApName`
- `.6` — `hwWlanApRunState`
- `.13` — `hwWlanApIpAddress`
- `.58` — `hwWlanApAirportUpTraffic`
- `.59` — `hwWlanApAirportDwTraffic`
- `.44` — `hwWlanApOnlineUserNum`

Run state is mapped via a static dictionary (`idle`, `autofind`, `typeNotMatch`, `fault`, `config`, `configFailed`, `download`, `normal`, `committing`, `commitFailed`, `standby`, `verMismatch`, `nameConflicted`, `invalid`). States `fault`, `configFailed`, `commitFailed`, `nameConflicted`, `invalid` map to CRIT; `verMismatch` and `standby` map to WARN.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/checks/huawei_wlc` | Legacy 1.6 check definition (registers via `check_info`). |

## Installation

1. Install the MKP on a Checkmk 1.6 site.
2. Configure SNMP access to the WLC.
3. Run service discovery — one `AP <name>` service per access point is created.

## Services & metrics

- **Service:** `AP <name>` — one per AP
- **Metric:** `users` (number of currently associated clients)

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `huawei_wlc` version `2.0.1`; minimum Checkmk version `2.4.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `huawei_wlc/src/info`; it declares 3 packaged files.
- Repository MKP artifacts present: `huawei_wlc-1.0.0.mkp`, `huawei_wlc-1.0.1.mkp`, `huawei_wlc-1.0.2.mkp`, `huawei_wlc-2.0.0.mkp`, `huawei_wlc-2.0.1.mkp`.
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/huawei_wlc/agent_based/huawei_wlc.py`.
- **Rulesets:** `src/huawei_wlc/rulesets/huawei_wlc.py`.
- **Check manuals:** `src/huawei_wlc/checkman/huawei_wlc`.
- Registered check plug-in names: `huawei_wlc`.

### Validation

- Package-specific tests: `tests/test_huawei_wlc_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
