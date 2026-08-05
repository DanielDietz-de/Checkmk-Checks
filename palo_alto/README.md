# Palo Alto enhanced checks

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.4.0-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.4.0p4-blue)
<!-- compatibility-badges:end -->

<img width="1364" height="384" alt="grafik" src="https://github.com/user-attachments/assets/a2f186d4-c4ef-4751-9956-af87f72fc23f" />



Consolidated SNMP checks for Palo Alto firewalls. This package replaces the
earlier separate `palo_alto_gp_tunnels` and `palo_alto_versions` MKPs (see
their READMEs), and adds the antivirus signature age check. All services
keep their existing identifiers, so migrating from the legacy packages does
not orphan services.

## Provided check plugins

| Check plugin | Service | Purpose |
| --- | --- | --- |
| `palo_alto_antivirus` | `Palo Alto antivirus version` | WARN/CRIT when the antivirus signature database has not been updated for longer than the configured age. |
| `palo_alto_gp_tunnels` | `Palo Alto GlobalProtect Tunnels` | WARN/CRIT when the remaining free GlobalProtect tunnel slots drop below the configured thresholds. |
| `palo_alto_threadid` | `Palo Alto Threat ID Version` | Reports the current Threat content version (always OK, informational). |
| `palo_alto_urlfilter` | `Palo Alto URL-Filtering Version` | Reports the current URL-Filtering content version (always OK, informational). |

All four checks share the same detection: `sysDescr` must start with
`Palo Alto` and the Palo Alto sub-tree `.1.3.6.1.4.1.25461.2.1.2.5.1.*` must
exist.

## Rulesets

| Ruleset | Applies to | Default |
| --- | --- | --- |
| `Palo Alto antivirus age` (Applications) | `palo_alto_antivirus` | WARN 24h, CRIT ~29h |
| `Palo Alto GlobalProtect tunnels` (Applications) | `palo_alto_gp_tunnels` | WARN 50 free slots, CRIT 15 free slots |

## Package contents

| Path | Purpose |
| --- | --- |
| `src/palo_alto/agent_based/antivirus.py` | `palo_alto_antivirus` section + check. |
| `src/palo_alto/agent_based/gp_tunnels.py` | `palo_alto_gp_tunnels` section + check. |
| `src/palo_alto/agent_based/threadid.py` | `palo_alto_threadid` section + check. |
| `src/palo_alto/agent_based/urlfilter.py` | `palo_alto_urlfilter` section + check. |
| `src/palo_alto/rulesets/antivirus.py` | WATO ruleset for antivirus age. |
| `src/palo_alto/rulesets/gp_tunnels.py` | WATO ruleset for GlobalProtect tunnel levels. |

## Installation

1. Uninstall any previously installed `palo_alto_gp_tunnels` and
   `palo_alto_versions` MKPs.
2. Install this MKP on the Checkmk site.
3. Add the Palo Alto firewall as an SNMP host and run service discovery.

## Known limitations

- The antivirus "age" is measured from the first time the plugin sees a
  given version string, not from the actual last update on the firewall.
- The Threat content version service was renamed from the earlier typo
  `TheadID Version` to `Threat ID Version` in 1.3.2. Existing services are
  rediscovered under the new name, so run a service discovery after upgrading.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `palo_alto` version `1.3.2`; minimum Checkmk version `2.4.0`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `palo_alto/src/info`; it declares 23 packaged files.
- Repository MKP artifacts present: `palo_alto-1.0.0.mkp`, `palo_alto-1.0.1.mkp`, `palo_alto-1.1.0.mkp`, `palo_alto-1.1.1.mkp`, `palo_alto-1.2.0.mkp`, `palo_alto-1.3.0.mkp` (additional historical artifacts omitted).
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/palo_alto/agent_based/antivirus.py`, `src/palo_alto/agent_based/dos_zone_red.py`, `src/palo_alto/agent_based/gp_tunnels.py`, `src/palo_alto/agent_based/ha.py`, `src/palo_alto/agent_based/panorama.py`, `src/palo_alto/agent_based/sessions.py`, `src/palo_alto/agent_based/threadid.py`, `src/palo_alto/agent_based/urlfilter.py`.
- **Rulesets:** `src/palo_alto/rulesets/antivirus.py`, `src/palo_alto/rulesets/dos_zone_red.py`, `src/palo_alto/rulesets/gp_tunnels.py`, `src/palo_alto/rulesets/ha.py`, `src/palo_alto/rulesets/panorama.py`, `src/palo_alto/rulesets/sessions.py`, `src/palo_alto/rulesets/threadid.py`, `src/palo_alto/rulesets/urlfilter.py`.
- **Graphing:** `src/palo_alto/graphing/palo_alto.py`.
- **Check manuals:** `src/palo_alto/checkman/palo_alto_dos_zone_red`, `src/palo_alto/checkman/palo_alto_ha`, `src/palo_alto/checkman/palo_alto_panorama`, `src/palo_alto/checkman/palo_alto_sessions`, `src/palo_alto/checkman/palo_alto_threadid`, `src/palo_alto/checkman/palo_alto_urlfilter`.
- Registered check plug-in names: `palo_alto_antivirus`, `palo_alto_dos_zone_red`, `palo_alto_gp_tunnels`, `palo_alto_ha`, `palo_alto_panorama`, `palo_alto_sessions`, `palo_alto_threadid`, `palo_alto_urlfilter`.

### Validation

- Package-specific tests: `tests/test_palo_alto_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- No Checkmk password or secret form was detected in the current package source.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.

### Troubleshooting

- No literal Checkmk section header was detected. Inspect the executable or notification exit status and the Checkmk log relevant to the component type.
- Verify deployment path, permissions, registration name, and the exact input/output contract represented by the source files above.
<!-- code-derived-reference:end -->
