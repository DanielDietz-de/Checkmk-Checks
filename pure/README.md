# Pure checks

<!-- compatibility-badges:start -->
![Checkmk min](https://img.shields.io/badge/Checkmk%20min-2.3.0b1-2f4f4f) ![packaged](https://img.shields.io/badge/packaged-2.3.0p30-blue)
<!-- compatibility-badges:end -->

Special agent for Pure Storage FlashArray. Queries the FlashArray REST API
using the tested `purestorage==1.19.0` Python client and emits multiple Checkmk sections
covering alerts, array metadata, hardware components, drives, volumes,
volume performance, reduction details and TLS certificates.

## How it works

1. The special agent [`agent_pure`](src/pure/libexec/agent_pure) is
   invoked by the Checkmk site with the array IP and an API token. It
   opens a `purestorage.FlashArray` session and walks the following
   endpoints:
   - `list_messages(open=True)` -> `<<<pure_fa_errors>>>`: counts of
     critical / warning / info alerts.
   - `list_hardware()` -> `<<<pure_hardware>>>`: name, status, serial,
     speed, temperature, voltage, slot for each component (non-drive).
     Drives are filtered out here; a cache keeps the serial numbers for
     use in the drives section.
   - `list_drives()` -> `<<<pure_drives>>>`: drive name, status, serial,
     type, capacity. `unused` drives are skipped.
   - `get()` -> `<<<pure_array>>>`: array name, version, revision, id.
   - `list_volumes(space=True)` -> `<<<df>>>`: classic Checkmk filesystem
     section for each volume with size, used, free (in KB).
   - `list_volumes(action='monitor')` -> `<<<pure_arrayperformance>>>`:
     per-volume reads/writes, bandwidth, latency.
   - `list_volumes(space=True)` -> `<<<pure_arraydetails>>>`: data
     reduction, total reduction, shared / thin / snapshot / volume /
     size figures.
   - `list_certificates()` -> `<<<pure_arraycertificates>>>`: certificate
     name, common name, status, validity window and organisation info.
2. Check plugins under `src/pure/agent_based/` parse these sections and
   produce services for alerts, array inventory, array details, array
   performance, devices, hardware (fan / PSU / network / temp split out
   into separate modules), volumes (via the built-in `df` plugin) and
   certificates.

## Package contents

| Path | Purpose |
| --- | --- |
| `src/pure/libexec/agent_pure` | Special agent talking to the FlashArray REST API via `purestorage`. |
| `src/pure/server_side_calls/pure.py` | Server-side call wiring: preserves the Checkmk token reference and forwards timeout and TLS controls. |
| `src/pure/rulesets/special_agent.py` | WATO special-agent ruleset `pure` with the API token field. |
| `src/pure/agent_based/alerts.py` | Section + check `pure_fa_errors` (alert counters). |
| `src/pure/agent_based/array.py` | Array inventory / summary check. |
| `src/pure/agent_based/arraydetails.py` | Data reduction / space details per volume. |
| `src/pure/agent_based/arrayperformance.py` | Per-volume performance metrics. |
| `src/pure/agent_based/arraycertificates.py` | Management certificate expiry check. |
| `src/pure/agent_based/devices.py` | Drives check. |
| `src/pure/agent_based/hardware.py` | Generic hardware components check. |
| `src/pure/agent_based/hardware_fan.py` | Fan components. |
| `src/pure/agent_based/hardware_psu.py` | Power supplies. |
| `src/pure/agent_based/hardware_nw.py` | Network components. |
| `src/pure/agent_based/hardware_temp.py` | Temperature sensors. |
| `src/pure/agent_based/utils/pure.py` | Shared parsing helpers. |
| `src/pure/graphing/arraydetails.py` | Metric / graph definitions for array details. |

## Installation

1. Install the tested `purestorage` client into the Checkmk site:
   `pip3 install --no-deps purestorage==1.19.0`
2. On the FlashArray, create an API token for a dedicated user via the UI
   (Settings -> API Client) or on the CLI: `pureadmin create --api-token`.
3. Install the MKP on the Checkmk site.
4. Add the FlashArray as a host. In the Checkmk configuration, create a
   host rule under *Setup -> Agents -> Other integrations -> Pure via
   WebAPI* and store the API token there.

## Configuration

Rule: **Setup -> Agents -> Other integrations -> Pure via WebAPI**

| Parameter | Type | Meaning |
| --- | --- | --- |
| `token` | `Password` (required, non-empty) | FlashArray API token retained as a Checkmk password-store reference until the agent resolves it. |
| `timeout` | `Float` | Bounded request timeout in seconds; default 30. |
| `ca_file` | `String` | Optional CA bundle path for private PKI verification. |
| `no_cert_check` | `BooleanChoice` | Explicit temporary verification opt-out; mutually exclusive with `ca_file`. |

The host IP address is taken from `HostConfig.primary_ip_config` and
passed as `-i`.

## Services & metrics

Depending on the discovered sections, the following service groups are
created:

- Pure Alerts (critical / warning / info counts from the alert feed).
- Pure Array (name, version, revision, id).
- Pure Array Details / Performance per volume.
- Pure Drives / Hardware / Fans / PSUs / Network / Temperature
  (one service per physical component, CRIT when state is not healthy /
  ok).
- Volumes rendered as classic `df` filesystem services.
- Pure Array Certificates (one service per management certificate, with
  validity window).

## Known limitations

- Requires the tested `purestorage==1.19.0` client to be installed manually in the site; it is not shipped with the MKP. The agent validates the required constructor interface before connecting.
- The agent prints plain error messages and exits on connection or API
  errors; nothing is retried.
- Hardware filtering is done by name prefix (`CH`, `SH`) and excludes
  entries containing `PWR` - non-standard hardware labels may be missed.

<!-- code-derived-reference:start -->
## Code-derived operational reference

This section is generated from the canonical manifest and current source tree. Edit the code or manifest first, then run `python3 tools/ci/generate_package_reference.py --write` from the repository root.

### Installation

- Canonical package: `pure` version `2.0.6`; minimum Checkmk version `2.3.0b1`; maximum asserted version: not asserted; validate on the target release.
- Canonical manifest: `pure/src/info`; it declares 16 packaged files.
- Repository MKP artifacts present: `pure-1.0.mkp`, `pure-1.1.mkp`, `pure-1.2.0.mkp`, `pure-1.2.mkp`, `pure-1.3.0.mkp`, `pure-1.3.1.mkp` (additional historical artifacts omitted).
- No committed checksum file is present; do not distribute an unverified locally built artifact.
- Source under `src/` is authoritative; generated MKP files and this reference must match it.

### Configuration and components

- **Agent-based checks:** `src/pure/agent_based/alerts.py`, `src/pure/agent_based/array.py`, `src/pure/agent_based/arraycertificates.py`, `src/pure/agent_based/arraydetails.py`, `src/pure/agent_based/arrayperformance.py`, `src/pure/agent_based/devices.py`, `src/pure/agent_based/hardware.py`, `src/pure/agent_based/hardware_fan.py` and 4 more.
- **Server-side calls:** `src/pure/server_side_calls/pure.py`.
- **Rulesets:** `src/pure/rulesets/special_agent.py`.
- **Executables:** `src/pure/libexec/agent_pure`.
- **Graphing:** `src/pure/graphing/arraydetails.py`.
- Registered special-agent names: `pure`.
- Registered check plug-in names: `pure_array`, `pure_arraycertificates`, `pure_arraydetails`, `pure_arrayperformance`, `pure_drives`, `pure_fa_errors`, `pure_hardware`, `pure_hardware_fan`, `pure_hardware_nw`, `pure_hardware_psu`, `pure_hardware_temperature`.

### Validation

- Package-specific tests: `tests/test_pure_integrity.py`.
- Any behavior change must update or add focused tests before the generated documentation is refreshed.

### Security

- Server-side calls preserve Checkmk password-store references and the executable resolves them at runtime; direct plaintext options, where present, are limited to isolated command-line diagnostics.
- Static analysis did not identify a supported direct remote-network client. This is not proof of network isolation; review extensionless and non-Python executables before deployment.
- An explicit TLS-verification opt-out is present. Verification remains the secure default; use the opt-out only as a documented temporary exception and prefer a private CA bundle.

### Troubleshooting

- Emitted Checkmk sections detected in source: `df`, `pure_array`, `pure_arraycertificates`, `pure_arraydetails`, `pure_arrayperformance`, `pure_drives`, `pure_fa_errors`, `pure_hardware`.
- For special agents, inspect the generated command without exposing secrets, run it as the site user, and verify that every emitted section has a matching parser/check registration.
<!-- code-derived-reference:end -->
